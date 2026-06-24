■デフォルト
c:\scan         ;監視フォルダー 
5               ;終了待機秒数（デフォルト5秒）

■コマンドライン
scanQR.exe 監視フォルダー 監視時間
例）c:\scanQR.exe c:\scan 10

■ini設定
[SCAN]
watch_folder = C:\SCAN  ;監視フォルダー
exit_delay = 5.0        ;終了待機秒数（デフォルト5秒）

※EXEと同じフォルダーにscanQR.iniを配置して、上記の内容を記載してください。

■起動設定順序
コマンドラインなければiniファイルなければデフォルト設定が有効になる。

■動作
監視フォルダーのQRコード付きのPDFファイルを読み込み、指定したフォルダーに指定したファイル名で保存します。
保存後、指定した秒数だけ待機してから終了します。

■その他
scanQR.ini 設定ファイル
scanQR.py メインのソースコード
scantest.py QRコードを読み取るテスト用のスクリプト

■QR情報
folder=				；保存先フォルダー指定
filename=			；保存ファイル名

例）
folder=c:\scan_test
filename=test.pdf
