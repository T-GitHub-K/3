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


# ----------------------------------
# 設定
# ----------------------------------

DEFAULT_FOLDER = r"C:\SCAN"

INI = os.path.join(
    os.path.dirname(
        sys.argv[0]
    ),
    "scanQR.ini"
)


def load_watch_folder():

    if len(sys.argv) > 1:

        return sys.argv[1]

    if os.path.exists(
        INI
    ):

        try:

            cfg = (
                configparser
                .ConfigParser()
            )

            cfg.read(
                INI,
                encoding="utf-8"
            )

            return (
                cfg.get(
                    "SCAN",
                    "watch_folder",
                    fallback=
                    DEFAULT_FOLDER
                )
            )

        except:
            pass

    return DEFAULT_FOLDER


WATCH_FOLDER = (
    load_watch_folder()
)

os.makedirs(
    WATCH_FOLDER,
    exist_ok=True
)


PID_FILE = os.path.join(
    WATCH_FOLDER,
    "scanqr.pid"
)

processed = set()

icon = None

running = True


# ----------------------------------
# 既存停止
# ----------------------------------

def stop_existing():

    if not os.path.exists(
        PID_FILE
    ):

        return False

    try:

        with open(
            PID_FILE
        ) as f:

            pid = int(
                f.read()
            )

        print(
            "既存停止:",
            pid
        )

        os.kill(
            pid,
            signal.SIGTERM
        )

        time.sleep(
            2
        )

        return True

    except:

        try:
            os.remove(
                PID_FILE
            )
        except:
            pass

        return False


if stop_existing():

    sys.exit()


with open(
    PID_FILE,
    "w"
) as f:

    f.write(
        str(
            os.getpid()
        )
    )


# ----------------------------------
# 終了
# ----------------------------------

def stop():

    global running
    global icon

    running = False

    try:

        os.remove(
            PID_FILE
        )

    except:
        pass

    try:

        if icon:

            icon.stop()

    except:
        pass

    os._exit(
        0
    )


def signal_stop(
    *_args
):

    stop()


signal.signal(
    signal.SIGTERM,
    signal_stop
)

atexit.register(
    stop
)


# ----------------------------------
# QR読取
# ----------------------------------

def read_qr(pdf):

    doc = fitz.open(
        pdf
    )

    page = doc[0]

    pix = page.get_pixmap(
        matrix=
        fitz.Matrix(
            3,
            3
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

    doc.close()

    if pix.n == 4:

        img = cv2.cvtColor(
            img,
            cv2.COLOR_RGBA2BGR
        )

    gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
    )

    gray = cv2.threshold(
        gray,
        180,
        255,
        cv2.THRESH_BINARY
    )[1]

    detector = (
        cv2.QRCodeDetector()
    )

    text, _, _ = (
        detector.detectAndDecode(
            gray
        )
    )

    return text


# ----------------------------------
# QR解析
# ----------------------------------

def parse_qr(text):

    result = {}

    for line in text.splitlines():

        if "=" in line:

            k, v = line.split(
                "=",
                1
            )

            result[
                k
                .strip()
                .lower()
            ] = (
                v.strip()
            )

    return result


# ----------------------------------
# 移動
# ----------------------------------

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

    base, ext = (
        os.path.splitext(
            dst
        )
    )

    n = 1

    while os.path.exists(
        dst
    ):

        dst = (
            f"{base}_{n}{ext}"
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


# ----------------------------------
# 保存完了待ち
# ----------------------------------

def wait_complete(
    path
):

    old = -1

    for _ in range(
        30
    ):

        try:

            size = (
                os.path.getsize(
                    path
                )
            )

            if (
                size
                ==
                old
            ):

                return True

            old = size

        except:
            pass

        time.sleep(
            1
        )

    return False


# ----------------------------------
# QRリトライ
# ----------------------------------

def retry_qr(
    path
):

    for i in range(
        5
    ):

        try:

            qr = (
                read_qr(
                    path
                )
            )

            if qr:

                return qr

        except:
            pass

        print(
            f"再試行 {i+1}"
        )

        time.sleep(
            2
        )

    return None


# ----------------------------------
# 監視
# ----------------------------------

def monitor():

    print(
        "監視開始:",
        WATCH_FOLDER
    )

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

                if (
                    p
                    .lower()
                    .endswith(
                        ".pdf"
                    )
                ):

                    files.append(
                        p
                    )

            files.sort(
                key=
                os.path.getmtime
            )

            for path in files:

                if (
                    path
                    in processed
                ):

                    continue

                if (
                    not
                    wait_complete(
                        path
                    )
                ):

                    continue

                qr = (
                    retry_qr(
                        path
                    )
                )

                if (
                    not qr
                ):

                    continue

                info = (
                    parse_qr(
                        qr
                    )
                )

                folder = (
                    info.get(
                        "folder"
                    )
                )

                filename = (
                    info.get(
                        "filename"
                    )
                )

                if (
                    folder
                    and
                    filename
                ):

                    move_file(
                        path,
                        folder,
                        filename
                    )

                    processed.add(
                        path
                    )

        except Exception as e:

            print(
                e
            )

        time.sleep(
            2
        )


# ----------------------------------
# トレイ
# ----------------------------------

def tray():

    global icon

    img = Image.new(
        "RGB",
        (
            64,
            64
        ),
        (
            0,
            150,
            255
        )
    )

    icon = (
        pystray.Icon(
            "ScanQR",
            img,
            "ScanQR",
            menu=
            pystray.Menu(

                pystray.MenuItem(
                    "終了",
                    lambda:
                    stop()
                )

            )
        )
    )

    icon.run()


threading.Thread(
    target=monitor,
    daemon=True
).start()


tray()