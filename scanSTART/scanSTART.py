import sys
import os
import json
import requests
import threading
import time
import ctypes

# Windows APIの定義（警告ウィンドウを探してキーを送信するため）
def auto_click_y_loop(stop_event):
    """
    確定回避版：ウィンドウのアクティブ状態に関係なく、
    「はい(Y)」ボタンに対して直接クリック信号を送りつけるロジック。
    """
    user32 = ctypes.windll.user32
    
    # Windowsメッセージの定義
    WM_COMMAND = 0x0111
    # 「はい(Y)」ボタンの識別子（一般的なダイアログでは IDYES = 6）
    # ScanSnap Homeのこのダイアログが標準的なダイアログであれば 6 で動作します
    IDYES = 6 
    
    print("DEBUG: 警告ウィンドウの裏側監視を開始しました...")
    
    while not stop_event.is_set():
        # タイトルが「ScanSnap Home」のウィンドウを探す
        hwnd = user32.FindWindowW(None, "ScanSnap Home")
        if hwnd != 0:
            if user32.IsWindowVisible(hwnd):
                # ウィンドウが見つかったら、ボタンの描画を少し待つ
                time.sleep(0.3)
                
                # ウィンドウハンドル(hwnd)に対して、「はい(IDYES)」が押されたという信号を直接送る
                # これにより、最前面にいなくても、マウス操作中であっても、裏でボタンが押されます
                user32.PostMessageW(hwnd, WM_COMMAND, IDYES, 0)
                
                print("DEBUG: ScanSnapの警告ウィンドウへ直接クリック信号(IDYES)を送信しました。")
                break
        
        time.sleep(0.1)
                
def launch_scan(save_directory="C:\\scan"):
    default_port = 45537
    session_id = None
    target_host = None
    version = "1_0_5"
    
    # 念のため保存先フォルダが存在しない場合は作成する
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
        print(f"DEBUG: 保存先フォルダを作成しました -> {save_directory}")

    print(f"DEBUG: スキャン処理を開始します（保存先: {save_directory}）")

    # ★追加：警告ウィンドウを裏で監視するスレッドを起動
    stop_clicker = threading.Event()
    clicker_thread = threading.Thread(target=auto_click_y_loop, args=(stop_clicker,), daemon=True)
    clicker_thread.start()

    try:
        # 1. サーバーのポート探索とセッションIDの取得
        for p in range(15):
            port = default_port + p
            host = f"http://localhost:{port}"
            connect_url = f"{host}/api/scanner/connect/{version}"
            headers = {"Content-Type": "application/json; charset=utf-8"}
            
            try:
                response = requests.get(connect_url, headers=headers, timeout=1.0)
                if response.status_code == 200:
                    res_json = response.json()
                    if res_json.get("keyword") == "ScanSnapWebSDK" and res_json.get("sessionid"):
                        target_host = host
                        session_id = res_json.get("sessionid")
                        print(f"DEBUG: 接続成功！ ポート: {port}, SessionID: {session_id}")
                        break
            except requests.exceptions.RequestException:
                continue

        if not session_id or not target_host:
            print("Error: ScanSnap Home Web SDKサービスに接続できませんでした。")
            return False

        # 2. スキャンをキックする (startscan)
        scan_url = f"{target_host}/api/scanner/startscan"
        scan_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "sessionid": session_id
        }
        
        # JSの仕様に完全準拠した生の設定値（state）
        scan_data = {
            "compression": 5,   # 圧縮形式：5 = JPEG圧縮
            "format": 2,        # ファイル形式：1 = PDFファイル
            "scanMode": 2,      # 画質：2 = ファイン
            "colorMode": 1,     # カラーモード：1 = カラー
            "scanningSide": 0,  # 読み取り面：0 = 両面
        }

        print(f"DEBUG: スキャン命令を送信します...")
        scan_response = requests.post(scan_url, headers=scan_headers, json=scan_data, timeout=120.0)
        
        if scan_response.status_code == 200:
            scan_result = scan_response.json()
            scan_code = scan_result.get("code")
            scan_files_data = scan_result.get("data", [])
            
            if scan_code == 0 and len(scan_files_data) > 0:
                print(f"▶ スキャン成功。{len(scan_files_data)}件のファイルを回収します。")
                
                # 返ってきたファイル（画像）の数だけループ処理
                for file_info in scan_files_data:
                    file_id = file_info.get("fileId")
                    file_name = file_info.get("fileName")  # 例: "20260630174026.jpg"
                    
                    if not file_id:
                        continue
                        
                    blob_url = f"{target_host}/api/scanner/converttoblob/{file_id}"
                    blob_headers = {"sessionid": session_id}
                    
                    print(f"DEBUG: ファイル取得中 -> {file_name} (ID: {file_id})")
                    blob_response = requests.get(blob_url, headers=blob_headers, timeout=10.0)
                    
                    if blob_response.status_code == 200:
                        # 1. 拡張子は変えず、そのままのファイル名（.jpg）で保存先パスを作成
                        full_save_path = os.path.join(save_directory, file_name)
                        
                        # まず、ScanSnapから届いた生の画像データ（JPG）をそのまま保存
                        with open(full_save_path, "wb") as f:
                            f.write(blob_response.content)
                        print(f"【画像保存完了】 -> {full_save_path}")
                        
                        # 2. 保存したJPGを元に、別名で本物の「.pdf」ファイルを生成して保存
                        try:
                            from PIL import Image
                            
                            # 保存パスの末尾を .jpg から .pdf に変更したパスを作る
                            pdf_save_path = os.path.splitext(full_save_path)[0] + ".pdf"
                            
                            # さっき保存した画像を開いて、本物のPDFとして別名保存
                            with Image.open(full_save_path) as img:
                                img.convert('RGB').save(pdf_save_path, 'PDF')
                            print(f"【PDF変換完了】 -> {pdf_save_path}")
                            
                            # ★ここを追加：PDF変換が成功したら、元のJPGファイルを削除する
                            if os.path.exists(full_save_path):
                                os.remove(full_save_path)
                            
                        except ImportError:
                            print("⚠️お知らせ: Pillowライブラリが未導入のため、PDFへの変換はスキップしました。")
                        except Exception as e:
                            print(f"⚠️PDF変換中にエラーが発生しました: {e}")
                                            
                return True
            else:
                print(f"Error: スキャンデータが空、または異常コードが返りました。(Code: {scan_code})")
                return False
        else:
            print(f"Error: スキャン通信失敗 (Status: {scan_response.status_code})")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Error: 通信エラーが発生しました。({e})")
        return False
        
    finally:
        # ★追加：スキャン処理が終わったら（成否問わず）監視スレッドを確実に終了させる
        stop_clicker.set()

if __name__ == "__main__":
    # デフォルトの保存先
    target_dir = "C:\\scan"
    
    # コマンドの第1引数に保存先が指定されていればそれを使用する
    if len(sys.argv) > 1:
        if not sys.argv[1].endswith(".sswp"):
            target_dir = sys.argv[1]

    launch_scan(target_dir)
