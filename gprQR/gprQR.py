# gprQR.py

import os
import sys
import time
import shutil
import signal
import atexit
import threading
import configparser

import fitz  # PyMuPDF
import cv2
import numpy as np

from PIL import Image
import pystray

DEFAULT_FOLDER = r"C:\SCAN"
DEFAULT_OUTPUT = r"C:\OUTPUT"
DEFAULT_DELAY = 5.0

def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

BASE = base_dir()
INI = os.path.join(BASE, "gprQR.ini")

def load_config():
    watch = DEFAULT_FOLDER
    output = DEFAULT_OUTPUT
    delay = DEFAULT_DELAY

    if os.path.exists(INI):
        try:
            cfg = configparser.ConfigParser()
            cfg.read(INI, encoding="utf-8")
            watch = cfg.get("SCAN", "watch_folder", fallback=watch)
            output = cfg.get("SCAN", "output_folder", fallback=output)
            delay = cfg.getfloat("SCAN", "exit_delay", fallback=delay)
        except:
            pass

    return watch, output, delay

WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config()

# ---------------------
# コマンドライン引数
# 優先順位: 引数 > gprQR.ini > デフォルト値
# ---------------------
args = sys.argv[1:]
i = 0

while i < len(args):
    try:
        if args[i] == "--watch":
            WATCH_FOLDER = args[i + 1]
            i += 2
            continue

        if args[i] in ("-o", "--output"):
            OUTPUT_FOLDER = args[i + 1]
            i += 2
            continue

        if args[i] == "--delay":
            EXIT_DELAY = float(args[i + 1])
            i += 2
            continue

        if args[i] in ("-h", "--help"):
            print("\ngprQR.py\n")
            print("使用方法:")
            print("python gprQR.py [--watch フォルダ] [-o/--output フォルダ] [--delay 秒]")
            print("\n例:")
            print("python gprQR.py --watch C:\\SCAN -o D:\\OUT --delay 30")
            sys.exit()
    except Exception:
        pass
    i += 1

os.makedirs(WATCH_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

PID_FILE = os.path.join(WATCH_FOLDER, "gprqr.pid")

processed = set()
icon = None
running = True

def stop():
    global running
    running = False
    try:
        os.remove(PID_FILE)
    except:
        pass
    try:
        if icon:
            icon.stop()
    except:
        pass
    os._exit(0)

def signal_stop(*_args):
    stop()

signal.signal(signal.SIGTERM, signal_stop)
atexit.register(stop)

def stop_existing():
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE) as f:
            pid = int(f.read())
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        return True
    except:
        try:
            os.remove(PID_FILE)
        except:
            pass
        return False

if stop_existing():
    sys.exit()

with open(PID_FILE, "w") as f:
    f.write(str(os.getpid()))

# ---------------------
# QR読取コア処理（画像データからQR検出）
# ---------------------
def decode_qr_from_image(img_bgr):
    detector = cv2.QRCodeDetector()
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # 既存の複数スケールによるアプローチを踏襲
    for scale in [1, 2]:
        test = gray
        if scale > 1:
            test = cv2.resize(
                gray,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_CUBIC
            )
        try:
            qr, _, _ = detector.detectAndDecode(test)
            if qr:
                return qr
        except:
            pass
    return None

# ---------------------
# ファイル種別に応じたQR読取
# ---------------------
def read_qr(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    
    # PDFの場合の処理
    if ext == ".pdf":
        try:
            with fitz.open(file_path) as doc:
                for page_no in range(len(doc)):
                    for dpi in [200, 300, 400]:
                        page = doc[page_no]
                        pix = page.get_pixmap(dpi=dpi)
                        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                            pix.height, pix.width, pix.n
                        )
                        if pix.n == 4:
                            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                        elif pix.n == 1:
                            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                        
                        qr = decode_qr_from_image(img)
                        if qr:
                            print(f"QR検出(PDF) page={page_no+1} dpi={dpi}")
                            return qr
        except Exception as e:
            print("PDF QR読取失敗:", e)
            
    # 画像ファイルの場合の処理 (.png, .jpg, .jpeg, .bmp, .tif, .tiff)
    elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"):
        try:
            # OpenCVは日本語パスで失敗することがあるため、np.fromfileで堅牢に読み込み
            img_array = np.fromfile(file_path, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is not None:
                qr = decode_qr_from_image(img)
                if qr:
                    print(f"QR検出(画像): {os.path.basename(file_path)}")
                    return qr
        except Exception as e:
            print("画像 QR読取失敗:", e)
            
    return None

# ---------------------
# 再試行
# ---------------------
def retry_qr(path):
    for i in range(5):  # 仕様の「再試行 1/5」表示に合わせ5回に調整
        qr = read_qr(path)
        if qr:
            return qr
        print(f"再試行 {i+1}/5")
        time.sleep(0.3)
    return None

# ---------------------
# テキスト出力と重複回避処理
# ---------------------
def save_output_txt(src_file_path, folder, content_text):
    os.makedirs(folder, exist_ok=True)
    
    # 元ファイル名（拡張子なし）を取得して「QRTXT_元ファイル名.txt」を作成
    base_name = os.path.splitext(os.path.basename(src_file_path))[0]
    dst_filename = f"QRTXT_{base_name}.txt"
    dst = os.path.join(folder, dst_filename)
    
    base, ext = os.path.splitext(dst)
    n = 1
    # ファイル名重複時の連番処理
    while os.path.exists(dst):
        dst = f"{base}_{n}{ext}"
        n += 1
        
    try:
        with open(dst, "w", encoding="utf-8") as f:
            f.write(content_text)
        print("保存:", dst)
    except Exception as e:
        print("テキスト保存エラー:", e)

def wait_complete(path):
    old = -1
    for _ in range(30):
        try:
            size = os.path.getsize(path)
            if size == old:
                return True
            old = size
        except:
            pass
        time.sleep(1)
    return False

# ---------------------
# メイン監視ループ
# ---------------------
def monitor():
    print("監視:", WATCH_FOLDER)
    print("保存:", OUTPUT_FOLDER)
    
    SUPPORTED_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")
    empty = None

    while running:
        try:
            files = []
            for f in os.listdir(WATCH_FOLDER):
                p = os.path.join(WATCH_FOLDER, f)
                if p.lower().endswith(SUPPORTED_EXTENSIONS):
                    files.append(p)

            target = [x for x in files if x not in processed]

            if not target:
                if empty is None:
                    empty = time.time()
                elif time.time() - empty >= EXIT_DELAY:
                    print("一定時間新規対象なしのため終了します。")
                    stop()
            else:
                empty = None

            for path in target:
                if not wait_complete(path):
                    processed.add(path)
                    continue

                qr = retry_qr(path)

                # 読み取り結果に応じてテキスト内容を分岐 (A案採用)
                if qr:
                    # 改行コードが混在している可能性を考慮しそのまま書き込み
                    txt_content = qr
                else:
                    print("QRなし:", os.path.basename(path))
                    txt_content = "QR_NOT_FOUND"

                # テキストファイルの出力
                save_output_txt(path, OUTPUT_FOLDER, txt_content)
                
                # 処理済みリストへ追加
                processed.add(path)

        except Exception as e:
            print("監視エラー:", e)

        time.sleep(0.5)

def tray():
    global icon
    icon_file = os.path.join(BASE, "gprQR.ico")
    try:
        if os.path.exists(icon_file):
            img = Image.open(icon_file).convert("RGBA")
        else:
            img = Image.new("RGB", (64, 64), (0, 150, 255))
    except:
        img = Image.new("RGB", (64, 64), (255, 0, 0))

    icon = pystray.Icon(
        "gprQR",
        img,
        "gprQR",
        menu=pystray.Menu(
            pystray.MenuItem("終了", lambda: stop())
        ),
    )
    icon.run()

# 監視スレッド起動
threading.Thread(target=monitor, daemon=True).start()

# トレイアイコン実行（メインスレッド）
tray()