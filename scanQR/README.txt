# scanQR 操作マニュアル

## 1. 概要

scanQR は、指定フォルダ内に保存された PDF を監視し、PDF内のQRコードを読み取って自動保存するツールです。

主な機能：

* 指定フォルダを監視
* PDFを自動検出
* PDF全ページを順番にQRコード読取
* QR読取成功時、自動リネームして保存
* QRが見つからない場合は次PDFへ移動
* トレイアイコンから終了可能
* 二重起動防止

---

## 2. 動作条件

必要ライブラリ：

* PyMuPDF（fitz）
* OpenCV
* NumPy
* Pillow
* pystray

インストール：

```bash
pip install pymupdf opencv-python numpy pillow pystray
```

確認：

```bash
pip list
```

---

## 3. フォルダ構成

例：

```text
scanQR/
│
├─ scanQR.py
├─ scanQR.ini
├─ scanQR.ico
│
├─ C:\SCAN
│      sample.pdf
│
└─ C:\OUTPUT
```

説明：

| ファイル       | 説明       |
| ---------- | -------- |
| scanQR.py  | プログラム本体  |
| scanQR.ini | 設定ファイル   |
| scanQR.ico | トレイアイコン  |
| C:\SCAN    | 監視対象フォルダ |
| C:\OUTPUT  | 保存先      |

---

## 4. 設定方法（INIファイル）

scanQR.py と同じ場所に作成します。

ファイル名：

```text
scanQR.ini
```

内容：

```ini
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

```ini
[SCAN]
watch_folder=D:\INPUT
output_folder=D:\RESULT
exit_delay=30
```

---

## 5. 起動方法

### 通常起動

```bash
python scanQR.py
```

または

```bash
scanQR.exe
```

起動例：

```text
監視: C:\SCAN
保存: C:\OUTPUT
```

---

## 6. コマンドライン指定

設定を一時的に変更できます。

優先順位：

```text
コマンドライン
↓
scanQR.ini
↓
プログラム既定値
```

### 監視フォルダ変更

```bash
python scanQR.py --watch C:\TEMP
```

---

### 保存先変更

```bash
python scanQR.py --output D:\RESULT
```

---

### 終了待機時間変更

```bash
python scanQR.py --delay 30
```

---

### 複数指定

```bash
python scanQR.py ^
--watch C:\SCAN ^
--output D:\OUTPUT ^
--delay 30
```

PowerShell：

```powershell
python .\scanQR.py --watch C:\SCAN --output D:\OUTPUT --delay 30
```

---

## 7. QRコード仕様

PDF内のQRは以下形式を想定しています。

例：

```text
filename=test.pdf
```

意味：

| キー       | 説明      |
| -------- | ------- |
| filename | 保存ファイル名 |

保存結果：

```text
C:\OUTPUT\test.pdf
```

重複時：

```text
test.pdf
test_1.pdf
test_2.pdf
```

---

## 8. 処理の流れ

```text
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
```

---

## 9. 終了方法

方法1：トレイアイコン

```text
右クリック → 終了
```

方法2：

ウィンドウを閉じる

方法3：

```bash
Ctrl + C
```

---

## 10. よくあるエラー

### QRなし

表示：

```text
QRなし: sample.pdf
```

原因：

* QRが存在しない
* 読取できない

---

### PDF読込失敗

表示：

```text
PDF読込失敗
```

原因：

* PDF破損
* 保存途中

---

### 二重起動停止

起動時：

```text
既存プロセス終了
```

原因：

同時起動防止機能

---

## 11. バージョン

scanQR.py
全ページQR対応版
コマンドライン対応版

■変更履歴
Ver1.0.0.0　2026/06/16　Kawamura　初版
Ver2.0.0.0　2026/06/23　Kawamura　コマンドライン対応版

