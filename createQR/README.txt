■動作
パラメータで指定した内容をQRコード化してpng形式の画像データを生成します。

■実行環境
createQR.EXE
createQR.ico
を同じフォルダーに入れます。

■パラメータ
--folder 必須 2026/06/24廃止
--filename 必須
-o / --output 出力先（省略時 qr.png）
--size-mm QRサイズ指定（mm）(省略時 40mm)
--auto-size 文字量から自動サイズ決定
--ftext QR下部文字（日本語対応）
日本語フォント自動選択（Windows優先）
QR誤り訂正 L
300dpi保存
余白付き

■コマンドライン例
c:\createQR.exe
--folder "\\Fleet016\TAXCON\T_東京\M_ムサシ交通\監査資料\日常点検表"　2026/06/24廃止 
--filename "日常点検表_20260616_123456_12345678_河　村　武　男.pdf" 
-o test.png
--auto-size
--ftext "日常 A-10001"

■その他
createQR.py       メインのソースコード
createQR.ico      ﾀｽｸﾄﾚｲｱｲｺﾝﾌｧｲﾙ

■変更履歴
Ver1.0.0.0　2026/06/19　Kawamura　初版
Ver1.1.0.0　2026/06/24　Kawamura　--folderパラメータ廃止