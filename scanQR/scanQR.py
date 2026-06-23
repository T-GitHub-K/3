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