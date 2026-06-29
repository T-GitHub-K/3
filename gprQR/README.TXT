■プログラム名
gprQR.EXE

■動作
gprQR は指定フォルダーを監視し、対象ファイルからQRコードを読み取り、
読取結果をTXTファイルとして出力する監視型ツールです。

対象ファイルは PDF および画像ファイルです。

監視対象フォルダーに対象ファイルが配置されると自動処理を行い、
一定時間対象ファイルが存在しない場合は自動終了します。

本プログラムはファイル暗号化、通信、アップロード、
外部転送機能を持ちません。

■ 主な機能
・監視フォルダーの自動監視
・PDF内QRコード読取
・画像ファイルQRコード読取
・TXT形式で読取結果保存
・同名ファイル連番出力
・設定ファイル（INI）対応
・一定時間経過後の自動終了

■対応ファイル

PDF
・.pdf

画像
・.png
・.jpg
・.jpeg
・.bmp
・.tif
・.tiff

■出力仕様

出力ファイル名：

QRTXT_元ファイル名.txt

例：

入力
C:\SCAN\A001.pdf

出力
D:\OUTPUT\QRTXT_A001.txt

同名ファイル存在時：

QRTXT_A001.txt
QRTXT_A001_1.txt
QRTXT_A001_2.txt

QR読取成功時：

例）

filename=test.pdf
folder=C:\DATA

TXT内容：

filename=test.pdf
folder=C:\DATA

QR読取失敗時：

TXT生成あり

内容：

QR_NOT_FOUND

■パラメータ
DEFAULT_FOLDER = r"C:\SCAN"
DEFAULT_OUTPUT = r"C:\OUTPUT"
DEFAULT_DELAY = 5.0

--watch

監視フォルダー指定

例：

--watch C:\SCAN

-o

TXT出力先指定

例：

-o D:\OUTPUT

--delay

終了待機秒数

例：

--delay 30

## 実行例

基本実行：

python gprQR.py

監視フォルダー指定：

python gprQR.py --watch C:\SCAN

出力先指定：

python gprQR.py -o D:\OUTPUT

全指定：

python gprQR.py ^
--watch C:\SCAN ^
-o D:\OUTPUT ^
--delay 30

■設定ファイル（gprQR.ini）

同一フォルダーに配置してください。

内容例：

[SCAN]

watch_folder=C:\SCAN

output_folder=D:\OUTPUT

exit_delay=30

## 設定優先順位

設定値は次の優先順位で決定されます。

① コマンドライン引数

↓

② gprQR.ini

↓

③ プログラム既定値

## 既定値

監視フォルダー：

C:\SCAN

出力先：

C:\OUTPUT

終了待機時間：

30秒

■必要ライブラリ

PyMuPDF

opencv-python

numpy


■注意事項

・対象ファイルは処理完了まで削除しないでください

・出力先フォルダーへの書込権限が必要です

・QRコード品質により読取精度が変動します

・PDFのページ数が多い場合、処理時間が増加します

■変更履歴
Ver1.0.0.0　2026/06/29　Kawamura　初版

