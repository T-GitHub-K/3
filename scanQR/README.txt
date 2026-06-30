■プログラム名
scanQR.EXE

■動作
scanQR は、指定フォルダ内に保存された PDF を監視し、PDF内のQRコードを読み取って自動保存するツールです。

主な機能：

* 指定フォルダを監視
* PDFを自動検出
* PDF全ページを順番にQRコード読取
* QR読取成功時、自動リネームして保存
* QRが見つからない場合は次PDFへ移動
* トレイアイコンから終了可能
* 二重起動防止

説明：

| ファイル       | 説明       |
| ---------- | -------- |
| scanQR.py  | プログラム本体  |
| scanQR.ini | 設定ファイル   |
| scanQR.ico | トレイアイコン  |
| C:\SCAN    | 監視対象フォルダ |　デフォルト
| C:\OUTPUT  | 保存先      |　デフォルト


■パラメータ---
優先順位：コマンドライン
↓
scanQR.ini
↓
プログラム既定値

・コマンドライン指定
### 監視フォルダ変更
scanQR.EXE --watch C:\TEMP

### 保存先変更
scanQR.EXE --output D:\RESULT

### 終了待機時間変更
scanQR.EXE --delay 30

### 複数指定
scanQR.EXE --watch C:\SCAN --output D:\OUTPUT --delay 30


・INIファイル
scanQR.py と同じ場所に作成します。
ファイル名：scanQR.ini
内容：
[SCAN]
watch_folder=C:\SCAN
output_folder=C:\OUTPUT
exit_delay=5
```

設定項目：

| 項目            | 説明                 |
| ------------- | ------------------ |
| watch_folder  | 監視フォルダ             |
| output_folder | 保存先                |
| exit_delay    | 監視対象が空になってから終了する秒数 |

例：
[SCAN]
watch_folder=D:\INPUT
output_folder=D:\RESULT
exit_delay=30

■QRコード仕様
PDF内のQRは以下形式を想定しています。

例：
filename=test.pdf

意味：

| キー       | 説明      |
| -------- | ------- |
| filename | 保存ファイル名 |

保存結果：

C:\OUTPUT\test.pdf
```

重複時：
test.pdf
test_1.pdf
test_2.pdf

■処理の流れ

起動
 ↓
監視開始
 ↓
PDF検出
 ↓
保存完了待機
 ↓
PDF全ページQR読取
 ↓
成功？
 ├ Yes → 保存
 └ No → 次PDF
 ↓
監視継続

■終了方法
方法1：トレイアイコン
右クリック → 終了

方法2：
ウィンドウを閉じる

方法3：
Ctrl + C

■よくあるエラー
### QRなし
表示：
QRなし: sample.pdf
原因：
* QRが存在しない
* 読取できない

### PDF読込失敗
表示：
PDF読込失敗
原因：
* PDF破損
* 保存途中

■二重起動停止

起動時：
既存プロセス終了
原因：
同時起動防止機能

■変更履歴
Ver1.0.0.0　2026/06/16　Kawamura　初版
Ver2.0.0.0　2026/06/23　Kawamura　コマンドライン対応版
Ver2.1.0.0　2026/06/27　Kawamura　読取精度改良版
　普通のPDF → 200dpiで即終了（速い）
　小さいQR → 300dpi＋2倍で救済
　難しいPDF → 400dpiへ昇格

