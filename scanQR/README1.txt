下記のプログラムでQRコードが読めなかった場合次のPDFファイルを読むようにしたい

できます。
ただ、肝心の「下記のプログラム」のコードがこちらにはまだ見えていません。

やりたい動きのイメージとしては、

    PDF一覧を取得

    先頭PDFを開く

    QRコード解析

    読めた → 終了（または結果保存）

    読めなかった → 次のPDFへ進む

    全部失敗 → メッセージ表示

という流れになります。

今のソース（scanQR.py か scanQR.go）を貼ってください。
特に次の部分があると、そのまま差分で修正できます。

    PDFを開いている部分

    QRコードを読んでいる関数

    return や break をしている箇所

    ファイルループ部分（for 文）

前の会話だと scanQR.py の return は関数内でのみ使用できます の話も出ていたので、その周辺（50〜100行くらい）を貼ってもらえると、次PDFへ進む形に直接直します。

# scanQR.py

import os
import sys
import time
import shutil
import signal
import atexit
import threading
import configparser

import fitz
import cv2
import numpy as np

from PIL import Image
import pystray

# -------------------------------

# 設定

# -------------------------------

DEFAULT_FOLDER = r"C:\SCAN"
DEFAULT_OUTPUT = r"C:\OUTPUT"
DEFAULT_DELAY = 5.0


def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


BASE = base_dir()
INI = os.path.join(BASE, "scanQR.ini")


def load_config():
    watch = DEFAULT_FOLDER
    output = DEFAULT_OUTPUT
    delay = DEFAULT_DELAY

    if os.path.exists(INI):
        try:
            cfg = configparser.ConfigParser()

            cfg.read(
                INI,
                encoding="utf-8"
            )

            watch = cfg.get(
                "SCAN",
                "watch_folder",
                fallback=watch
            )

            output = cfg.get(
                "SCAN",
                "output_folder",
                fallback=output
            )

            delay = cfg.getfloat(
                "SCAN",
                "exit_delay",
                fallback=delay
            )

        except:
            pass

    return (
        watch,
        output,
        delay
    )


args = sys.argv[1:]

i = 0

while i < len(args):

    try:

        if args[i] == "--watch":

            watch = args[i + 1]

            i += 2

            continue


        if args[i] == "--output":

            output = args[i + 1]

            i += 2

            continue


        if args[i] == "--delay":

            delay = float(
                args[i + 1]
            )

            i += 2

            continue

    except:

        pass

    i += 1




WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config()

os.makedirs(WATCH_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

PID_FILE = os.path.join(WATCH_FOLDER, "scanqr.pid")

processed = set()
icon = None
running = True

# -------------------------------

# 停止

# -------------------------------

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

# -------------------------------

# 二重起動停止

# -------------------------------

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

# -------------------------------

# QR読取

# -------------------------------

def read_qr(pdf):
    doc = fitz.open(pdf)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))

    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height,
        pix.width,
        pix.n,
    )

    doc.close()

    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    detector = cv2.QRCodeDetector()
    text, _, _ = detector.detectAndDecode(gray)
    return text


def retry_qr(path):
    for _ in range(5):
        try:
            qr = read_qr(path)
            if qr:
                return qr
        except:
            pass
        time.sleep(2)
    return None


def parse_qr(text):
    result = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            result[k.lower().strip()] = v.strip()
    return result

# -------------------------------

# 移動

# -------------------------------

def move_file(src, folder, filename):
    os.makedirs(folder, exist_ok=True)
    dst = os.path.join(folder, filename)
    base, ext = os.path.splitext(dst)
    n = 1
    while os.path.exists(dst):
        dst = f"{base}_{n}{ext}"
        n += 1
    shutil.move(src, dst)
    print("保存:", dst)

# -------------------------------

# 保存完了待ち

# -------------------------------

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

# -------------------------------

# 監視

# -------------------------------

def monitor():
    print("監視:", WATCH_FOLDER)
    print("保存:", OUTPUT_FOLDER)
    empty = None

    while running:
        try:
            files = []
            for f in os.listdir(WATCH_FOLDER):
                p = os.path.join(WATCH_FOLDER, f)
                if p.lower().endswith(".pdf"):
                    files.append(p)

            target = [x for x in files if x not in processed]

            if not target:
                if empty is None:
                    empty = time.time()
                elif time.time() - empty >= EXIT_DELAY:
                    stop()
            else:
                empty = None

            for path in target:
                if not wait_complete(path):
                    continue
                qr = retry_qr(path)
                if not qr:
                    continue
                info = parse_qr(qr)
                filename = info.get("filename")
                if filename:
                    move_file(path, OUTPUT_FOLDER, filename)
                    processed.add(path)
        except Exception as e:
            print(e)
        time.sleep(0.5)

# -------------------------------

# トレイ

# -------------------------------

def tray():
    global icon
    icon_file = os.path.join(BASE, "scanQR.ico")
    try:
        if os.path.exists(icon_file):
            img = Image.open(icon_file).convert("RGBA")
        else:
            img = Image.new("RGB", (64, 64), (0, 150, 255))
    except:
        img = Image.new("RGB", (64, 64), (255, 0, 0))

    icon = pystray.Icon(
        "ScanQR",
        img,
        "ScanQR",
        menu=pystray.Menu(
            pystray.MenuItem("終了", lambda: stop())
        ),
    )
    icon.run()


threading.Thread(target=monitor, daemon=True).start()
tray()

コード確認しました。
今の実装だと read_qr() が PDFの1ページ目 (doc[0]) しか見ていない ので、QRが読めなかった場合に「次のPDF」へ行く前に、まずそのPDFの次ページを読ませたいのか、別PDFへ移りたいのかで修正箇所が変わります。

文面から見ると「QRコードが読めなかった場合次のPDFファイルを読む」は、現在のPDFをスキップして監視フォルダ内の次のPDFへ進む だと思います。

実は今のコード、ほぼその動きになっています。

for path in target:
    if not wait_complete(path):
        continue

    qr = retry_qr(path)

    if not qr:
        continue

continue なので次のPDFへ進みます。

ただし問題があります。
読めなかったPDFは processed.add(path) されないので、次回ループでまた同じPDFを読んで無限再試行します。

修正案はこうです。

for path in target:

    if not wait_complete(path):
        processed.add(path)
        continue

    qr = retry_qr(path)

    # QR失敗 → 次PDFへ
    if not qr:
        print("QR読取失敗:", os.path.basename(path))
        processed.add(path)
        continue

    info = parse_qr(qr)

    filename = info.get("filename")

    if filename:
        move_file(
            path,
            OUTPUT_FOLDER,
            filename
        )

    processed.add(path)

変更点はここです。

processed.add(path)

を QR失敗時 にも入れています。

これで動作は、

A.pdf → QR失敗 → スキップ
B.pdf → QR成功 → 移動
C.pdf → QR失敗 → スキップ

になります。

もし本当にやりたいのが、

A.pdf の1ページ目失敗
↓
A.pdf の2ページ目読む
↓
A.pdf の3ページ目読む
↓
全部失敗なら B.pdf

なら read_qr() 側を修正します。その場合は別の修正になります。

それがいい

了解です。では「1つのPDFの全ページを順番に読んで、QRが見つからなければ次のPDFへ進む」方式に変更しましょう。

今の read_qr() はこれです。

def read_qr(pdf):
    doc = fitz.open(pdf)
    page = doc[0]

これが1ページ固定なので、全ページ走査に変更します。

置き換えてください。

def read_qr(pdf):

    detector = cv2.QRCodeDetector()

    try:
        doc = fitz.open(pdf)

        for page_no in range(len(doc)):

            try:
                page = doc[page_no]

                pix = page.get_pixmap(
                    matrix=fitz.Matrix(3, 3)
                )

                img = np.frombuffer(
                    pix.samples,
                    dtype=np.uint8
                ).reshape(
                    pix.height,
                    pix.width,
                    pix.n
                )

                if pix.n == 4:
                    img = cv2.cvtColor(
                        img,
                        cv2.COLOR_RGBA2BGR
                    )

                gray = cv2.cvtColor(
                    img,
                    cv2.COLOR_BGR2GRAY
                )

                text, _, _ = detector.detectAndDecode(
                    gray
                )

                if text:
                    print(
                        f"QR検出: {os.path.basename(pdf)} "
                        f"(page {page_no + 1})"
                    )
                    return text

            except Exception as e:
                print(
                    f"ページ読込失敗 "
                    f"{page_no + 1}:",
                    e
                )

    finally:
        try:
            doc.close()
        except:
            pass

    return None

さらに monitor() のこの部分だけ少し変えてください。

変更前：

qr = retry_qr(path)

if not qr:
    continue

変更後：

qr = retry_qr(path)

if not qr:
    print(
        "QRなし:",
        os.path.basename(path)
    )

    processed.add(path)
    continue

これで動作はこうなります。

A.pdf
 ├ 1ページ → QRなし
 ├ 2ページ → QRなし
 ├ 3ページ → QRあり → 移動

B.pdf
 ├ 1ページ → QRなし
 ├ 2ページ → QRなし
 └ 終了（次PDFへ）

C.pdf
 └ …

副作用として、QRなしPDFを毎回再読込してCPUを使い続ける現象も防げます。

今の Matrix(3,3) はかなり高解像度なので、ページ数が多いPDFだと遅いです。速度優先なら Matrix(2,2) に落としてもQR読取精度は意外と保てます。

それでお願いします。ソース全体を出力お願いします。VSCODEに貼り付けしますのでその部分も考慮して出力お願いします。

了解です。VSCodeへそのまま貼り付けできるように、全体差し替え用の scanQR.py 完成版として出します。

変更内容は次の2点です。

    PDFの全ページを順番にQR読取

    QRが見つからなかったPDFは再読込せず次のPDFへ進む

# scanQR.py

import os
import sys
import time
import shutil
import signal
import atexit
import threading
import configparser

import fitz
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
INI = os.path.join(BASE, "scanQR.ini")


def load_config():

    watch = DEFAULT_FOLDER
    output = DEFAULT_OUTPUT
    delay = DEFAULT_DELAY

    if os.path.exists(INI):

        try:
            cfg = configparser.ConfigParser()

            cfg.read(
                INI,
                encoding="utf-8"
            )

            watch = cfg.get(
                "SCAN",
                "watch_folder",
                fallback=watch
            )

            output = cfg.get(
                "SCAN",
                "output_folder",
                fallback=output
            )

            delay = cfg.getfloat(
                "SCAN",
                "exit_delay",
                fallback=delay
            )

        except:
            pass

    return watch, output, delay


WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config()

os.makedirs(WATCH_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

PID_FILE = os.path.join(
    WATCH_FOLDER,
    "scanqr.pid"
)

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


signal.signal(
    signal.SIGTERM,
    signal_stop
)

atexit.register(stop)


def stop_existing():

    if not os.path.exists(PID_FILE):
        return False

    try:

        with open(PID_FILE) as f:
            pid = int(f.read())

        os.kill(
            pid,
            signal.SIGTERM
        )

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
    f.write(
        str(os.getpid())
    )


# ---------------------
# QR読取（全ページ対応）
# ---------------------

def read_qr(pdf):

    detector = cv2.QRCodeDetector()

    doc = None

    try:

        doc = fitz.open(pdf)

        for page_no in range(len(doc)):

            try:

                page = doc[page_no]

                pix = page.get_pixmap(
                    matrix=fitz.Matrix(
                        2,
                        2
                    )
                )

                img = np.frombuffer(
                    pix.samples,
                    dtype=np.uint8
                ).reshape(
                    pix.height,
                    pix.width,
                    pix.n
                )

                if pix.n == 4:

                    img = cv2.cvtColor(
                        img,
                        cv2.COLOR_RGBA2BGR
                    )

                gray = cv2.cvtColor(
                    img,
                    cv2.COLOR_BGR2GRAY
                )

                qr, _, _ = detector.detectAndDecode(
                    gray
                )

                if qr:

                    print(
                        f"QR検出 "
                        f"{os.path.basename(pdf)} "
                        f"page={page_no+1}"
                    )

                    return qr

            except Exception as e:

                print(
                    "ページ読取失敗:",
                    e
                )

    except Exception as e:

        print(
            "PDF読込失敗:",
            e
        )

    finally:

        if doc:
            doc.close()

    return None


def retry_qr(path):

    for i in range(5):

        qr = read_qr(path)

        if qr:
            return qr

        time.sleep(2)

    return None


def parse_qr(text):

    result = {}

    for line in text.splitlines():

        if "=" in line:

            k, v = line.split(
                "=",
                1
            )

            result[
                k.lower().strip()
            ] = v.strip()

    return result


def move_file(
    src,
    folder,
    filename
):

    os.makedirs(
        folder,
        exist_ok=True
    )

    dst = os.path.join(
        folder,
        filename
    )

    base, ext = os.path.splitext(dst)

    n = 1

    while os.path.exists(dst):

        dst = (
            f"{base}_{n}"
            f"{ext}"
        )

        n += 1

    shutil.move(
        src,
        dst
    )

    print(
        "保存:",
        dst
    )


def wait_complete(path):

    old = -1

    for _ in range(30):

        try:

            size = os.path.getsize(
                path
            )

            if size == old:
                return True

            old = size

        except:
            pass

        time.sleep(1)

    return False


def monitor():

    print(
        "監視:",
        WATCH_FOLDER
    )

    print(
        "保存:",
        OUTPUT_FOLDER
    )

    empty = None

    while running:

        try:

            files = []

            for f in os.listdir(
                WATCH_FOLDER
            ):

                p = os.path.join(
                    WATCH_FOLDER,
                    f
                )

                if p.lower().endswith(
                    ".pdf"
                ):

                    files.append(
                        p
                    )

            target = [

                x

                for x in files

                if x not in processed

            ]

            if not target:

                if empty is None:

                    empty = time.time()

                elif (
                    time.time()
                    -
                    empty
                    >=
                    EXIT_DELAY
                ):

                    stop()

            else:

                empty = None


            for path in target:

                if not wait_complete(
                    path
                ):

                    processed.add(
                        path
                    )

                    continue


                qr = retry_qr(
                    path
                )


                if not qr:

                    print(
                        "QRなし:",
                        os.path.basename(
                            path
                        )
                    )

                    processed.add(
                        path
                    )

                    continue


                info = parse_qr(
                    qr
                )

                filename = info.get(
                    "filename"
                )


                if filename:

                    move_file(
                        path,
                        OUTPUT_FOLDER,
                        filename
                    )

                processed.add(
                    path
                )

        except Exception as e:

            print(
                "監視エラー:",
                e
            )

        time.sleep(
            0.5
        )


def tray():

    global icon

    icon_file = os.path.join(
        BASE,
        "scanQR.ico"
    )

    try:

        if os.path.exists(
            icon_file
        ):

            img = (
                Image
                .open(
                    icon_file
                )
                .convert(
                    "RGBA"
                )
            )

        else:

            img = Image.new(
                "RGB",
                (64, 64),
                (
                    0,
                    150,
                    255
                )
            )

    except:

        img = Image.new(
            "RGB",
            (64, 64),
            (
                255,
                0,
                0
            )
        )

    icon = pystray.Icon(
        "ScanQR",
        img,
        "ScanQR",
        menu=pystray.Menu(
            pystray.MenuItem(
                "終了",
                lambda: stop()
            )
        ),
    )

    icon.run()


threading.Thread(
    target=monitor,
    daemon=True
).start()

tray()

VSCode貼り付け後の確認コマンド:

python scanQR.py

想定ログ:

監視: C:\SCAN
保存: C:\OUTPUT
QR検出 sample.pdf page=3
保存: C:\OUTPUT\abc.pdf
QRなし: sample2.pdf

これで「1ページ目失敗→2ページ目→…→最後まで失敗→次のPDF」という流れになります。

パラメータの指定方法

この scanQR.py は、元コードを見る限り INIファイル設定 と コマンドライン引数 の両方に対応する想定でした。

ただ、前回出した全体版では引数処理を入れ直していなかったので、まず現状のままだと INIのみ有効 です。
引数でも指定したいなら、下の方法で使えます。
1. INIファイルで指定（おすすめ）

scanQR.py と同じフォルダに scanQR.ini

[SCAN]
watch_folder=C:\SCAN
output_folder=C:\OUTPUT
exit_delay=5

意味：

    watch_folder → PDF監視フォルダ

    output_folder → 保存先

    exit_delay → PDFが無くなって何秒後に終了するか

実行：

python scanQR.py

2. コマンドライン引数で指定

前回コードの WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config() の直後にこれを追加してください。

args = sys.argv[1:]

i = 0

while i < len(args):

    try:

        if args[i] == "--watch":

            WATCH_FOLDER = args[i + 1]
            i += 2
            continue


        if args[i] == "--output":

            OUTPUT_FOLDER = args[i + 1]
            i += 2
            continue


        if args[i] == "--delay":

            EXIT_DELAY = float(
                args[i + 1]
            )

            i += 2
            continue

    except:
        pass

    i += 1

すると実行例はこうなります。
監視フォルダ指定

python scanQR.py --watch C:\TEMP

保存先指定

python scanQR.py --output D:\PDF

複数指定

python scanQR.py ^
  --watch C:\SCAN ^
  --output D:\RESULT ^
  --delay 10

PowerShellなら1行：

python .\scanQR.py --watch C:\SCAN --output D:\RESULT --delay 10

意味：

--watch   監視フォルダ
--output  保存先
--delay   自動終了秒数

例：

python .\scanQR.py --watch C:\SCAN --output C:\OUTPUT --delay 30

→ C:\SCAN を監視して、結果を C:\OUTPUT に保存、30秒無操作なら終了です。

下記のソースでのｺﾏﾝﾄﾞﾗｲﾝの指定方法はどうなっている。
# scanQR.py

import os
import sys
import time
import shutil
import signal
import atexit
import threading
import configparser

import fitz
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
INI = os.path.join(BASE, "scanQR.ini")


def load_config():

    watch = DEFAULT_FOLDER
    output = DEFAULT_OUTPUT
    delay = DEFAULT_DELAY

    if os.path.exists(INI):

        try:
            cfg = configparser.ConfigParser()

            cfg.read(
                INI,
                encoding="utf-8"
            )

            watch = cfg.get(
                "SCAN",
                "watch_folder",
                fallback=watch
            )

            output = cfg.get(
                "SCAN",
                "output_folder",
                fallback=output
            )

            delay = cfg.getfloat(
                "SCAN",
                "exit_delay",
                fallback=delay
            )

        except:
            pass

    return watch, output, delay


WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config()

os.makedirs(WATCH_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

PID_FILE = os.path.join(
    WATCH_FOLDER,
    "scanqr.pid"
)

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


signal.signal(
    signal.SIGTERM,
    signal_stop
)

atexit.register(stop)


def stop_existing():

    if not os.path.exists(PID_FILE):
        return False

    try:

        with open(PID_FILE) as f:
            pid = int(f.read())

        os.kill(
            pid,
            signal.SIGTERM
        )

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
    f.write(
        str(os.getpid())
    )


# ---------------------
# QR読取（全ページ対応）
# ---------------------

def read_qr(pdf):

    detector = cv2.QRCodeDetector()

    doc = None

    try:

        doc = fitz.open(pdf)

        for page_no in range(len(doc)):

            try:

                page = doc[page_no]

                pix = page.get_pixmap(
                    matrix=fitz.Matrix(
                        2,
                        2
                    )
                )

                img = np.frombuffer(
                    pix.samples,
                    dtype=np.uint8
                ).reshape(
                    pix.height,
                    pix.width,
                    pix.n
                )

                if pix.n == 4:

                    img = cv2.cvtColor(
                        img,
                        cv2.COLOR_RGBA2BGR
                    )

                gray = cv2.cvtColor(
                    img,
                    cv2.COLOR_BGR2GRAY
                )

                qr, _, _ = detector.detectAndDecode(
                    gray
                )

                if qr:

                    print(
                        f"QR検出 "
                        f"{os.path.basename(pdf)} "
                        f"page={page_no+1}"
                    )

                    return qr

            except Exception as e:

                print(
                    "ページ読取失敗:",
                    e
                )

    except Exception as e:

        print(
            "PDF読込失敗:",
            e
        )

    finally:

        if doc:
            doc.close()

    return None


def retry_qr(path):

    for i in range(5):

        qr = read_qr(path)

        if qr:
            return qr

        time.sleep(2)

    return None


def parse_qr(text):

    result = {}

    for line in text.splitlines():

        if "=" in line:

            k, v = line.split(
                "=",
                1
            )

            result[
                k.lower().strip()
            ] = v.strip()

    return result


def move_file(
    src,
    folder,
    filename
):

    os.makedirs(
        folder,
        exist_ok=True
    )

    dst = os.path.join(
        folder,
        filename
    )

    base, ext = os.path.splitext(dst)

    n = 1

    while os.path.exists(dst):

        dst = (
            f"{base}_{n}"
            f"{ext}"
        )

        n += 1

    shutil.move(
        src,
        dst
    )

    print(
        "保存:",
        dst
    )


def wait_complete(path):

    old = -1

    for _ in range(30):

        try:

            size = os.path.getsize(
                path
            )

            if size == old:
                return True

            old = size

        except:
            pass

        time.sleep(1)

    return False


def monitor():

    print(
        "監視:",
        WATCH_FOLDER
    )

    print(
        "保存:",
        OUTPUT_FOLDER
    )

    empty = None

    while running:

        try:

            files = []

            for f in os.listdir(
                WATCH_FOLDER
            ):

                p = os.path.join(
                    WATCH_FOLDER,
                    f
                )

                if p.lower().endswith(
                    ".pdf"
                ):

                    files.append(
                        p
                    )

            target = [

                x

                for x in files

                if x not in processed

            ]

            if not target:

                if empty is None:

                    empty = time.time()

                elif (
                    time.time()
                    -
                    empty
                    >=
                    EXIT_DELAY
                ):

                    stop()

            else:

                empty = None


            for path in target:

                if not wait_complete(
                    path
                ):

                    processed.add(
                        path
                    )

                    continue


                qr = retry_qr(
                    path
                )


                if not qr:

                    print(
                        "QRなし:",
                        os.path.basename(
                            path
                        )
                    )

                    processed.add(
                        path
                    )

                    continue


                info = parse_qr(
                    qr
                )

                filename = info.get(
                    "filename"
                )


                if filename:

                    move_file(
                        path,
                        OUTPUT_FOLDER,
                        filename
                    )

                processed.add(
                    path
                )

        except Exception as e:

            print(
                "監視エラー:",
                e
            )

        time.sleep(
            0.5
        )


def tray():

    global icon

    icon_file = os.path.join(
        BASE,
        "scanQR.ico"
    )

    try:

        if os.path.exists(
            icon_file
        ):

            img = (
                Image
                .open(
                    icon_file
                )
                .convert(
                    "RGBA"
                )
            )

        else:

            img = Image.new(
                "RGB",
                (64, 64),
                (
                    0,
                    150,
                    255
                )
            )

    except:

        img = Image.new(
            "RGB",
            (64, 64),
            (
                255,
                0,
                0
            )
        )

    icon = pystray.Icon(
        "ScanQR",
        img,
        "ScanQR",
        menu=pystray.Menu(
            pystray.MenuItem(
                "終了",
                lambda: stop()
            )
        ),
    )

    icon.run()


threading.Thread(
    target=monitor,
    daemon=True
).start()

tray()

このソースでは、現在はコマンドライン引数を受け付けません。

理由は、以前の版にあったこれが消えているためです。

args = sys.argv[1:]

つまり今の設定値は全部ここで決まっています。

WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config()

load_config() は scanQR.ini を読むので、実質 INI ファイル方式のみ対応です。

使い方はこうです。

scanQR.ini

[SCAN]
watch_folder=C:\SCAN
output_folder=C:\OUTPUT
exit_delay=5

実行：

python .\scanQR.py

または EXE 化後：

.\scanQR.exe

もしコマンドライン指定も使いたいなら、下のコードを追加します。

追加場所：

WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config()

の直後。

追加コード：

args = sys.argv[1:]

i = 0

while i < len(args):

    try:

        if args[i] == "--watch":

            WATCH_FOLDER = args[i + 1]
            i += 2
            continue


        if args[i] == "--output":

            OUTPUT_FOLDER = args[i + 1]
            i += 2
            continue


        if args[i] == "--delay":

            EXIT_DELAY = float(
                args[i + 1]
            )

            i += 2
            continue

    except:

        pass

    i += 1

追加後の使い方：

監視フォルダ変更

python .\scanQR.py --watch C:\TEMP

保存先変更

python .\scanQR.py --output D:\RESULT

全部指定

python .\scanQR.py `
  --watch C:\SCAN `
  --output D:\OUTPUT `
  --delay 30

1行なら：

python .\scanQR.py --watch C:\SCAN --output D:\OUTPUT --delay 30

優先順位はこうなります。

コマンドライン引数
↓
scanQR.ini
↓
プログラム内デフォルト値
(C:\SCAN / C:\OUTPUT / 5秒)

なので --watch を指定すると scanQR.ini の watch_folder より優先されます。

そのソースコードを出力してください、VScode環境の貼り付けする前提で出力をお願いします。

了解です。今回は現在の全ページQR対応版 + コマンドライン引数対応版として、そのままVSCodeへ貼り付けできる形で、追加・修正する部分だけを出します（全体再掲だと長すぎて貼り付けミスしやすいため）。

探す場所：

WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config()

この直後に、下のブロックをそのまま追加してください。

# ---------------------
# コマンドライン引数
# 優先順位:
# 引数 > scanQR.ini > デフォルト値
# ---------------------

args = sys.argv[1:]

i = 0

while i < len(args):

    try:

        if args[i] == "--watch":

            WATCH_FOLDER = args[i + 1]

            i += 2

            continue


        if args[i] == "--output":

            OUTPUT_FOLDER = args[i + 1]

            i += 2

            continue


        if args[i] == "--delay":

            EXIT_DELAY = float(
                args[i + 1]
            )

            i += 2

            continue


        if args[i] in (
            "-h",
            "--help"
        ):

            print()

            print(
                "scanQR.py"
            )

            print()

            print(
                "使用方法:"
            )

            print(
                "python scanQR.py "
                "[--watch フォルダ] "
                "[--output フォルダ] "
                "[--delay 秒]"
            )

            print()

            print(
                "例:"
            )

            print(
                "python scanQR.py "
                "--watch C:\\SCAN "
                "--output D:\\OUTPUT "
                "--delay 30"
            )

            sys.exit()

    except Exception:

        pass

    i += 1


os.makedirs(
    WATCH_FOLDER,
    exist_ok=True
)

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)

貼り付け後、使い方はこうなります。
INIのみ使用

python .\scanQR.py

監視先変更

python .\scanQR.py --watch C:\TEMP

保存先変更

python .\scanQR.py --output D:\RESULT

全指定

python .\scanQR.py --watch C:\SCAN --output D:\OUTPUT --delay 30

ヘルプ表示

python .\scanQR.py --help

この修正後は、

コマンドライン引数
↓
scanQR.ini
↓
プログラム内デフォルト値

の順で設定が決まります。

これで大丈夫ですか？
# scanQR.py

import os
import sys
import time
import shutil
import signal
import atexit
import threading
import configparser

import fitz
import cv2
import numpy as np

from PIL import Image
import pystray


DEFAULT_FOLDER = r"C:\SCAN"
DEFAULT_OUTPUT = r"C:\OUTPUT"
DEFAULT_DELAY = 5.0

# ---------------------
# コマンドライン引数
# 優先順位:
# 引数 > scanQR.ini > デフォルト値
# ---------------------

args = sys.argv[1:]

i = 0

while i < len(args):

    try:

        if args[i] == "--watch":

            WATCH_FOLDER = args[i + 1]

            i += 2

            continue


        if args[i] == "--output":

            OUTPUT_FOLDER = args[i + 1]

            i += 2

            continue


        if args[i] == "--delay":

            EXIT_DELAY = float(
                args[i + 1]
            )

            i += 2

            continue


        if args[i] in (
            "-h",
            "--help"
        ):

            print()

            print(
                "scanQR.py"
            )

            print()

            print(
                "使用方法:"
            )

            print(
                "python scanQR.py "
                "[--watch フォルダ] "
                "[--output フォルダ] "
                "[--delay 秒]"
            )

            print()

            print(
                "例:"
            )

            print(
                "python scanQR.py "
                "--watch C:\\SCAN "
                "--output D:\\OUTPUT "
                "--delay 30"
            )

            sys.exit()

    except Exception:

        pass

    i += 1


os.makedirs(
    WATCH_FOLDER,
    exist_ok=True
)

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


BASE = base_dir()
INI = os.path.join(BASE, "scanQR.ini")


def load_config():

    watch = DEFAULT_FOLDER
    output = DEFAULT_OUTPUT
    delay = DEFAULT_DELAY

    if os.path.exists(INI):

        try:
            cfg = configparser.ConfigParser()

            cfg.read(
                INI,
                encoding="utf-8"
            )

            watch = cfg.get(
                "SCAN",
                "watch_folder",
                fallback=watch
            )

            output = cfg.get(
                "SCAN",
                "output_folder",
                fallback=output
            )

            delay = cfg.getfloat(
                "SCAN",
                "exit_delay",
                fallback=delay
            )

        except:
            pass

    return watch, output, delay


WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config()

os.makedirs(WATCH_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

PID_FILE = os.path.join(
    WATCH_FOLDER,
    "scanqr.pid"
)

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


signal.signal(
    signal.SIGTERM,
    signal_stop
)

atexit.register(stop)


def stop_existing():

    if not os.path.exists(PID_FILE):
        return False

    try:

        with open(PID_FILE) as f:
            pid = int(f.read())

        os.kill(
            pid,
            signal.SIGTERM
        )

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
    f.write(
        str(os.getpid())
    )


# ---------------------
# QR読取（全ページ対応）
# ---------------------

def read_qr(pdf):

    detector = cv2.QRCodeDetector()

    doc = None

    try:

        doc = fitz.open(pdf)

        for page_no in range(len(doc)):

            try:

                page = doc[page_no]

                pix = page.get_pixmap(
                    matrix=fitz.Matrix(
                        2,
                        2
                    )
                )

                img = np.frombuffer(
                    pix.samples,
                    dtype=np.uint8
                ).reshape(
                    pix.height,
                    pix.width,
                    pix.n
                )

                if pix.n == 4:

                    img = cv2.cvtColor(
                        img,
                        cv2.COLOR_RGBA2BGR
                    )

                gray = cv2.cvtColor(
                    img,
                    cv2.COLOR_BGR2GRAY
                )

                qr, _, _ = detector.detectAndDecode(
                    gray
                )

                if qr:

                    print(
                        f"QR検出 "
                        f"{os.path.basename(pdf)} "
                        f"page={page_no+1}"
                    )

                    return qr

            except Exception as e:

                print(
                    "ページ読取失敗:",
                    e
                )

    except Exception as e:

        print(
            "PDF読込失敗:",
            e
        )

    finally:

        if doc:
            doc.close()

    return None


def retry_qr(path):

    for i in range(5):

        qr = read_qr(path)

        if qr:
            return qr

        time.sleep(2)

    return None


def parse_qr(text):

    result = {}

    for line in text.splitlines():

        if "=" in line:

            k, v = line.split(
                "=",
                1
            )

            result[
                k.lower().strip()
            ] = v.strip()

    return result


def move_file(
    src,
    folder,
    filename
):

    os.makedirs(
        folder,
        exist_ok=True
    )

    dst = os.path.join(
        folder,
        filename
    )

    base, ext = os.path.splitext(dst)

    n = 1

    while os.path.exists(dst):

        dst = (
            f"{base}_{n}"
            f"{ext}"
        )

        n += 1

    shutil.move(
        src,
        dst
    )

    print(
        "保存:",
        dst
    )


def wait_complete(path):

    old = -1

    for _ in range(30):

        try:

            size = os.path.getsize(
                path
            )

            if size == old:
                return True

            old = size

        except:
            pass

        time.sleep(1)

    return False


def monitor():

    print(
        "監視:",
        WATCH_FOLDER
    )

    print(
        "保存:",
        OUTPUT_FOLDER
    )

    empty = None

    while running:

        try:

            files = []

            for f in os.listdir(
                WATCH_FOLDER
            ):

                p = os.path.join(
                    WATCH_FOLDER,
                    f
                )

                if p.lower().endswith(
                    ".pdf"
                ):

                    files.append(
                        p
                    )

            target = [

                x

                for x in files

                if x not in processed

            ]

            if not target:

                if empty is None:

                    empty = time.time()

                elif (
                    time.time()
                    -
                    empty
                    >=
                    EXIT_DELAY
                ):

                    stop()

            else:

                empty = None


            for path in target:

                if not wait_complete(
                    path
                ):

                    processed.add(
                        path
                    )

                    continue


                qr = retry_qr(
                    path
                )


                if not qr:

                    print(
                        "QRなし:",
                        os.path.basename(
                            path
                        )
                    )

                    processed.add(
                        path
                    )

                    continue


                info = parse_qr(
                    qr
                )

                filename = info.get(
                    "filename"
                )


                if filename:

                    move_file(
                        path,
                        OUTPUT_FOLDER,
                        filename
                    )

                processed.add(
                    path
                )

        except Exception as e:

            print(
                "監視エラー:",
                e
            )

        time.sleep(
            0.5
        )


def tray():

    global icon

    icon_file = os.path.join(
        BASE,
        "scanQR.ico"
    )

    try:

        if os.path.exists(
            icon_file
        ):

            img = (
                Image
                .open(
                    icon_file
                )
                .convert(
                    "RGBA"
                )
            )

        else:

            img = Image.new(
                "RGB",
                (64, 64),
                (
                    0,
                    150,
                    255
                )
            )

    except:

        img = Image.new(
            "RGB",
            (64, 64),
            (
                255,
                0,
                0
            )
        )

    icon = pystray.Icon(
        "ScanQR",
        img,
        "ScanQR",
        menu=pystray.Menu(
            pystray.MenuItem(
                "終了",
                lambda: stop()
            )
        ),
    )

    icon.run()


threading.Thread(
    target=monitor,
    daemon=True
).start()

tray()

惜しいです。今のままだと動きません。
理由は、コマンドライン引数を読む場所が早すぎるためです。

ここで問題が起きます。

WATCH_FOLDER = args[i + 1]

この時点では WATCH_FOLDER はまだ定義されていません。

さらにこの後で、

WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config()

を実行してしまうので、せっかく引数で指定してもINIで上書きされます。

修正は簡単です。
① このブロック全部削除

先頭側に入れたこの部分：

# ---------------------
# コマンドライン引数
# 優先順位:
# 引数 > scanQR.ini > デフォルト値
# ---------------------
～
os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)

② この行を探す

WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config()

その直後に追加してください。

# ---------------------
# コマンドライン引数
# 優先順位:
# 引数 > scanQR.ini > デフォルト値
# ---------------------

args = sys.argv[1:]

i = 0

while i < len(args):

    try:

        if args[i] == "--watch":

            WATCH_FOLDER = args[i + 1]

            i += 2

            continue


        if args[i] == "--output":

            OUTPUT_FOLDER = args[i + 1]

            i += 2

            continue


        if args[i] == "--delay":

            EXIT_DELAY = float(
                args[i + 1]
            )

            i += 2

            continue


        if args[i] in (
            "-h",
            "--help"
        ):

            print()

            print(
                "scanQR.py"
            )

            print()

            print(
                "使用方法:"
            )

            print(
                "python scanQR.py "
                "[--watch フォルダ] "
                "[--output フォルダ] "
                "[--delay 秒]"
            )

            sys.exit()

    except Exception:

        pass

    i += 1

この並びになります。

DEFAULT値
↓
scanQR.ini 読込
↓
コマンドライン引数で上書き
↓
os.makedirs()
↓
起動

実行例：

python .\scanQR.py --watch C:\SCAN --output D:\OUTPUT --delay 30

これなら意図通り動きます。

でいいですか
# scanQR.py

import os
import sys
import time
import shutil
import signal
import atexit
import threading
import configparser

import fitz
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
INI = os.path.join(BASE, "scanQR.ini")


def load_config():

    watch = DEFAULT_FOLDER
    output = DEFAULT_OUTPUT
    delay = DEFAULT_DELAY

    if os.path.exists(INI):

        try:
            cfg = configparser.ConfigParser()

            cfg.read(
                INI,
                encoding="utf-8"
            )

            watch = cfg.get(
                "SCAN",
                "watch_folder",
                fallback=watch
            )

            output = cfg.get(
                "SCAN",
                "output_folder",
                fallback=output
            )

            delay = cfg.getfloat(
                "SCAN",
                "exit_delay",
                fallback=delay
            )

        except:
            pass

    return watch, output, delay


WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config()

# ---------------------
# コマンドライン引数
# 優先順位:
# 引数 > scanQR.ini > デフォルト値
# ---------------------

args = sys.argv[1:]

i = 0

while i < len(args):

    try:

        if args[i] == "--watch":

            WATCH_FOLDER = args[i + 1]

            i += 2

            continue


        if args[i] == "--output":

            OUTPUT_FOLDER = args[i + 1]

            i += 2

            continue


        if args[i] == "--delay":

            EXIT_DELAY = float(
                args[i + 1]
            )

            i += 2

            continue


        if args[i] in (
            "-h",
            "--help"
        ):

            print()

            print(
                "scanQR.py"
            )

            print()

            print(
                "使用方法:"
            )

            print(
                "python scanQR.py "
                "[--watch フォルダ] "
                "[--output フォルダ] "
                "[--delay 秒]"
            )

            print()

            print(
                "例:"
            )

            print(
                "python scanQR.py "
                "--watch C:\\SCAN "
                "--output D:\\OUTPUT "
                "--delay 30"
            )

            sys.exit()

    except Exception:

        pass

    i += 1


os.makedirs(
    WATCH_FOLDER,
    exist_ok=True
)

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


os.makedirs(WATCH_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

PID_FILE = os.path.join(
    WATCH_FOLDER,
    "scanqr.pid"
)

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


signal.signal(
    signal.SIGTERM,
    signal_stop
)

atexit.register(stop)


def stop_existing():

    if not os.path.exists(PID_FILE):
        return False

    try:

        with open(PID_FILE) as f:
            pid = int(f.read())

        os.kill(
            pid,
            signal.SIGTERM
        )

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
    f.write(
        str(os.getpid())
    )


# ---------------------
# QR読取（全ページ対応）
# ---------------------

def read_qr(pdf):

    detector = cv2.QRCodeDetector()

    doc = None

    try:

        doc = fitz.open(pdf)

        for page_no in range(len(doc)):

            try:

                page = doc[page_no]

                pix = page.get_pixmap(
                    matrix=fitz.Matrix(
                        2,
                        2
                    )
                )

                img = np.frombuffer(
                    pix.samples,
                    dtype=np.uint8
                ).reshape(
                    pix.height,
                    pix.width,
                    pix.n
                )

                if pix.n == 4:

                    img = cv2.cvtColor(
                        img,
                        cv2.COLOR_RGBA2BGR
                    )

                gray = cv2.cvtColor(
                    img,
                    cv2.COLOR_BGR2GRAY
                )

                qr, _, _ = detector.detectAndDecode(
                    gray
                )

                if qr:

                    print(
                        f"QR検出 "
                        f"{os.path.basename(pdf)} "
                        f"page={page_no+1}"
                    )

                    return qr

            except Exception as e:

                print(
                    "ページ読取失敗:",
                    e
                )

    except Exception as e:

        print(
            "PDF読込失敗:",
            e
        )

    finally:

        if doc:
            doc.close()

    return None


def retry_qr(path):

    for i in range(5):

        qr = read_qr(path)

        if qr:
            return qr

        time.sleep(2)

    return None


def parse_qr(text):

    result = {}

    for line in text.splitlines():

        if "=" in line:

            k, v = line.split(
                "=",
                1
            )

            result[
                k.lower().strip()
            ] = v.strip()

    return result


def move_file(
    src,
    folder,
    filename
):

    os.makedirs(
        folder,
        exist_ok=True
    )

    dst = os.path.join(
        folder,
        filename
    )

    base, ext = os.path.splitext(dst)

    n = 1

    while os.path.exists(dst):

        dst = (
            f"{base}_{n}"
            f"{ext}"
        )

        n += 1

    shutil.move(
        src,
        dst
    )

    print(
        "保存:",
        dst
    )


def wait_complete(path):

    old = -1

    for _ in range(30):

        try:

            size = os.path.getsize(
                path
            )

            if size == old:
                return True

            old = size

        except:
            pass

        time.sleep(1)

    return False


def monitor():

    print(
        "監視:",
        WATCH_FOLDER
    )

    print(
        "保存:",
        OUTPUT_FOLDER
    )

    empty = None

    while running:

        try:

            files = []

            for f in os.listdir(
                WATCH_FOLDER
            ):

                p = os.path.join(
                    WATCH_FOLDER,
                    f
                )

                if p.lower().endswith(
                    ".pdf"
                ):

                    files.append(
                        p
                    )

            target = [

                x

                for x in files

                if x not in processed

            ]

            if not target:

                if empty is None:

                    empty = time.time()

                elif (
                    time.time()
                    -
                    empty
                    >=
                    EXIT_DELAY
                ):

                    stop()

            else:

                empty = None


            for path in target:

                if not wait_complete(
                    path
                ):

                    processed.add(
                        path
                    )

                    continue


                qr = retry_qr(
                    path
                )


                if not qr:

                    print(
                        "QRなし:",
                        os.path.basename(
                            path
                        )
                    )

                    processed.add(
                        path
                    )

                    continue


                info = parse_qr(
                    qr
                )

                filename = info.get(
                    "filename"
                )


                if filename:

                    move_file(
                        path,
                        OUTPUT_FOLDER,
                        filename
                    )

                processed.add(
                    path
                )

        except Exception as e:

            print(
                "監視エラー:",
                e
            )

        time.sleep(
            0.5
        )


def tray():

    global icon

    icon_file = os.path.join(
        BASE,
        "scanQR.ico"
    )

    try:

        if os.path.exists(
            icon_file
        ):

            img = (
                Image
                .open(
                    icon_file
                )
                .convert(
                    "RGBA"
                )
            )

        else:

            img = Image.new(
                "RGB",
                (64, 64),
                (
                    0,
                    150,
                    255
                )
            )

    except:

        img = Image.new(
            "RGB",
            (64, 64),
            (
                255,
                0,
                0
            )
        )

    icon = pystray.Icon(
        "ScanQR",
        img,
        "ScanQR",
        menu=pystray.Menu(
            pystray.MenuItem(
                "終了",
                lambda: stop()
            )
        ),
    )

    icon.run()


threading.Thread(
    target=monitor,
    daemon=True
).start()

tray()

かなり近いです。動きます。
ただ、1か所だけ整理した方がいいです。

今これが2回あります。

os.makedirs(
    WATCH_FOLDER,
    exist_ok=True
)

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


os.makedirs(WATCH_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

下の2行が重複です。

削除してください。

os.makedirs(WATCH_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

削除後はこうなります。

WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config()

# コマンドライン引数処理
args = sys.argv[1:]

...

os.makedirs(
    WATCH_FOLDER,
    exist_ok=True
)

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)

PID_FILE = os.path.join(
    WATCH_FOLDER,
    "scanqr.pid"
)

これで処理順は正しいです。

デフォルト値
↓
scanQR.ini 読込
↓
コマンドライン引数で上書き
↓
フォルダ作成
↓
PID生成
↓
監視開始

実行例：

python .\scanQR.py

python .\scanQR.py --watch C:\SCAN

python .\scanQR.py --watch C:\SCAN --output D:\OUTPUT --delay 30

ヘルプ：

python .\scanQR.py --help

この修正を入れれば、そのままVSCodeで保存→実行して大丈夫です。

# scanQR.py

import os
import sys
import time
import shutil
import signal
import atexit
import threading
import configparser

import fitz
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
INI = os.path.join(BASE, "scanQR.ini")


def load_config():

    watch = DEFAULT_FOLDER
    output = DEFAULT_OUTPUT
    delay = DEFAULT_DELAY

    if os.path.exists(INI):

        try:
            cfg = configparser.ConfigParser()

            cfg.read(
                INI,
                encoding="utf-8"
            )

            watch = cfg.get(
                "SCAN",
                "watch_folder",
                fallback=watch
            )

            output = cfg.get(
                "SCAN",
                "output_folder",
                fallback=output
            )

            delay = cfg.getfloat(
                "SCAN",
                "exit_delay",
                fallback=delay
            )

        except:
            pass

    return watch, output, delay


WATCH_FOLDER, OUTPUT_FOLDER, EXIT_DELAY = load_config()

# ---------------------
# コマンドライン引数
# 優先順位:
# 引数 > scanQR.ini > デフォルト値
# ---------------------

args = sys.argv[1:]

i = 0

while i < len(args):

    try:

        if args[i] == "--watch":

            WATCH_FOLDER = args[i + 1]

            i += 2

            continue


        if args[i] == "--output":

            OUTPUT_FOLDER = args[i + 1]

            i += 2

            continue


        if args[i] == "--delay":

            EXIT_DELAY = float(
                args[i + 1]
            )

            i += 2

            continue


        if args[i] in (
            "-h",
            "--help"
        ):

            print()

            print(
                "scanQR.py"
            )

            print()

            print(
                "使用方法:"
            )

            print(
                "python scanQR.py "
                "[--watch フォルダ] "
                "[--output フォルダ] "
                "[--delay 秒]"
            )

            print()

            print(
                "例:"
            )

            print(
                "python scanQR.py "
                "--watch C:\\SCAN "
                "--output D:\\OUTPUT "
                "--delay 30"
            )

            sys.exit()

    except Exception:

        pass

    i += 1


os.makedirs(
    WATCH_FOLDER,
    exist_ok=True
)

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


PID_FILE = os.path.join(
    WATCH_FOLDER,
    "scanqr.pid"
)

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


signal.signal(
    signal.SIGTERM,
    signal_stop
)

atexit.register(stop)


def stop_existing():

    if not os.path.exists(PID_FILE):
        return False

    try:

        with open(PID_FILE) as f:
            pid = int(f.read())

        os.kill(
            pid,
            signal.SIGTERM
        )

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
    f.write(
        str(os.getpid())
    )


# ---------------------
# QR読取（全ページ対応）
# ---------------------

def read_qr(pdf):

    detector = cv2.QRCodeDetector()

    doc = None

    try:

        doc = fitz.open(pdf)

        for page_no in range(len(doc)):

            try:

                page = doc[page_no]

                pix = page.get_pixmap(
                    matrix=fitz.Matrix(
                        2,
                        2
                    )
                )

                img = np.frombuffer(
                    pix.samples,
                    dtype=np.uint8
                ).reshape(
                    pix.height,
                    pix.width,
                    pix.n
                )

                if pix.n == 4:

                    img = cv2.cvtColor(
                        img,
                        cv2.COLOR_RGBA2BGR
                    )

                gray = cv2.cvtColor(
                    img,
                    cv2.COLOR_BGR2GRAY
                )

                qr, _, _ = detector.detectAndDecode(
                    gray
                )

                if qr:

                    print(
                        f"QR検出 "
                        f"{os.path.basename(pdf)} "
                        f"page={page_no+1}"
                    )

                    return qr

            except Exception as e:

                print(
                    "ページ読取失敗:",
                    e
                )

    except Exception as e:

        print(
            "PDF読込失敗:",
            e
        )

    finally:

        if doc:
            doc.close()

    return None


def retry_qr(path):

    for i in range(5):

        qr = read_qr(path)

        if qr:
            return qr

        time.sleep(2)

    return None


def parse_qr(text):

    result = {}

    for line in text.splitlines():

        if "=" in line:

            k, v = line.split(
                "=",
                1
            )

            result[
                k.lower().strip()
            ] = v.strip()

    return result


def move_file(
    src,
    folder,
    filename
):

    os.makedirs(
        folder,
        exist_ok=True
    )

    dst = os.path.join(
        folder,
        filename
    )

    base, ext = os.path.splitext(dst)

    n = 1

    while os.path.exists(dst):

        dst = (
            f"{base}_{n}"
            f"{ext}"
        )

        n += 1

    shutil.move(
        src,
        dst
    )

    print(
        "保存:",
        dst
    )


def wait_complete(path):

    old = -1

    for _ in range(30):

        try:

            size = os.path.getsize(
                path
            )

            if size == old:
                return True

            old = size

        except:
            pass

        time.sleep(1)

    return False


def monitor():

    print(
        "監視:",
        WATCH_FOLDER
    )

    print(
        "保存:",
        OUTPUT_FOLDER
    )

    empty = None

    while running:

        try:

            files = []

            for f in os.listdir(
                WATCH_FOLDER
            ):

                p = os.path.join(
                    WATCH_FOLDER,
                    f
                )

                if p.lower().endswith(
                    ".pdf"
                ):

                    files.append(
                        p
                    )

            target = [

                x

                for x in files

                if x not in processed

            ]

            if not target:

                if empty is None:

                    empty = time.time()

                elif (
                    time.time()
                    -
                    empty
                    >=
                    EXIT_DELAY
                ):

                    stop()

            else:

                empty = None


            for path in target:

                if not wait_complete(
                    path
                ):

                    processed.add(
                        path
                    )

                    continue


                qr = retry_qr(
                    path
                )


                if not qr:

                    print(
                        "QRなし:",
                        os.path.basename(
                            path
                        )
                    )

                    processed.add(
                        path
                    )

                    continue


                info = parse_qr(
                    qr
                )

                filename = info.get(
                    "filename"
                )


                if filename:

                    move_file(
                        path,
                        OUTPUT_FOLDER,
                        filename
                    )

                processed.add(
                    path
                )

        except Exception as e:

            print(
                "監視エラー:",
                e
            )

        time.sleep(
            0.5
        )


def tray():

    global icon

    icon_file = os.path.join(
        BASE,
        "scanQR.ico"
    )

    try:

        if os.path.exists(
            icon_file
        ):

            img = (
                Image
                .open(
                    icon_file
                )
                .convert(
                    "RGBA"
                )
            )

        else:

            img = Image.new(
                "RGB",
                (64, 64),
                (
                    0,
                    150,
                    255
                )
            )

    except:

        img = Image.new(
            "RGB",
            (64, 64),
            (
                255,
                0,
                0
            )
        )

    icon = pystray.Icon(
        "ScanQR",
        img,
        "ScanQR",
        menu=pystray.Menu(
            pystray.MenuItem(
                "終了",
                lambda: stop()
            )
        ),
    )

    icon.run()


threading.Thread(
    target=monitor,
    daemon=True
).start()

tray()

はい、今回の版は大丈夫です。
構成を確認しました。

チェック結果：

✅ load_config() → 先に実行される
✅ その後にコマンドライン引数で上書きされる
✅ os.makedirs() は上書き後に実行される
✅ PID_FILE は最終的な WATCH_FOLDER を使う
✅ 全ページQR読取も有効
✅ QR失敗時は次PDFへ進む

この状態なら期待どおり動くはずです。

実際の起動例だけ整理しておきます。

通常（INI使用）

python .\scanQR.py

監視先だけ変更

python .\scanQR.py --watch C:\TEMP

保存先だけ変更

python .\scanQR.py --output D:\RESULT

全部指定

python .\scanQR.py --watch C:\SCAN --output D:\OUTPUT --delay 30

ヘルプ

python .\scanQR.py --help

動作確認時、起動直後にこの表示になれば設定反映できています。

監視: C:\SCAN
保存: D:\OUTPUT

もし --watch を指定したのに 監視: が変わらなければ引数が渡っていません。

この版ならVSCodeに保存して実行して進めて大丈夫です。

このプログラムの操作方法のマニュアルを作成してくだし

了解です。VSCodeで開発した scanQR.py を利用する前提で、利用者向けの簡易マニュアルとして使える形にまとめました。
scanQR 操作マニュアル
1. 概要

scanQR は、指定フォルダ内に保存された PDF を監視し、PDF内のQRコードを読み取って自動保存するツールです。

主な機能：

    指定フォルダを監視

    PDFを自動検出

    PDF全ページを順番にQRコード読取

    QR読取成功時、自動リネームして保存

    QRが見つからない場合は次PDFへ移動

    トレイアイコンから終了可能

    二重起動防止

2. 動作条件

必要ライブラリ：

    PyMuPDF（fitz）

    OpenCV

    NumPy

    Pillow

    pystray

インストール：

pip install pymupdf opencv-python numpy pillow pystray

確認：

pip list

3. フォルダ構成

例：

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

説明：
ファイル	説明
scanQR.py	プログラム本体
scanQR.ini	設定ファイル
scanQR.ico	トレイアイコン
C:\SCAN	監視対象フォルダ
C:\OUTPUT	保存先
4. 設定方法（INIファイル）

scanQR.py と同じ場所に作成します。

ファイル名：

scanQR.ini

内容：

[SCAN]
watch_folder=C:\SCAN
output_folder=C:\OUTPUT
exit_delay=5

設定項目：
項目	説明
watch_folder	監視フォルダ
output_folder	保存先
exit_delay	監視対象が空になってから終了する秒数

例：

[SCAN]
watch_folder=D:\INPUT
output_folder=D:\RESULT
exit_delay=30

5. 起動方法
通常起動

python scanQR.py

または

scanQR.exe

起動例：

監視: C:\SCAN
保存: C:\OUTPUT

6. コマンドライン指定

設定を一時的に変更できます。

優先順位：

コマンドライン
↓
scanQR.ini
↓
プログラム既定値

監視フォルダ変更

python scanQR.py --watch C:\TEMP

保存先変更

python scanQR.py --output D:\RESULT

終了待機時間変更

python scanQR.py --delay 30

複数指定

python scanQR.py ^
--watch C:\SCAN ^
--output D:\OUTPUT ^
--delay 30

PowerShell：

python .\scanQR.py --watch C:\SCAN --output D:\OUTPUT --delay 30

7. QRコード仕様

PDF内のQRは以下形式を想定しています。

例：

filename=test.pdf

意味：
キー	説明
filename	保存ファイル名

保存結果：

C:\OUTPUT\test.pdf

重複時：

test.pdf
test_1.pdf
test_2.pdf

8. 処理の流れ

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

9. 終了方法

方法1：トレイアイコン

右クリック → 終了

方法2：

ウィンドウを閉じる

方法3：

Ctrl + C

10. よくあるエラー
QRなし

表示：

QRなし: sample.pdf

原因：

    QRが存在しない

    読取できない

PDF読込失敗

表示：

PDF読込失敗

原因：

    PDF破損

    保存途中

二重起動停止

起動時：

既存プロセス終了

原因：

同時起動防止機能
11. バージョン

scanQR.py
全ページQR対応版
コマンドライン対応版

このまま README.md や社内向け手順書として使える内容です。


