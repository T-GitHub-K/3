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
DEFAULT_DELAY = 5.0


def base_dir():

    if getattr(
        sys,
        "frozen",
        False
    ):

        return os.path.dirname(
            sys.executable
        )

    return os.path.dirname(
        __file__
    )


BASE = base_dir()

INI = os.path.join(
    BASE,
    "scanQR.ini"
)


def load_config():

    folder = DEFAULT_FOLDER

    delay = DEFAULT_DELAY

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

            folder = (
                cfg.get(
                    "SCAN",
                    "watch_folder",
                    fallback=
                    DEFAULT_FOLDER
                )
            )

            delay = (
                cfg.getfloat(
                    "SCAN",
                    "exit_delay",
                    fallback=
                    DEFAULT_DELAY
                )
            )

        except:

            pass


    if len(
        sys.argv
    ) > 1:

        folder = (
            sys.argv[1]
        )

    if len(
        sys.argv
    ) > 2:

        try:

            delay = float(
                sys.argv[2]
            )

        except:

            pass

    return (
        folder,
        delay
    )


WATCH_FOLDER, EXIT_DELAY = (
    load_config()
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


# -------------------------------
# 停止
# -------------------------------

def stop():

    global running

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


# -------------------------------
# 二重起動停止
# -------------------------------

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


# -------------------------------
# QR読取
# -------------------------------

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

    detector = (
        cv2.QRCodeDetector()
    )

    text, _, _ = (
        detector.detectAndDecode(
            gray
        )
    )

    return text


def retry_qr(
    path
):

    for _ in range(
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

        time.sleep(
            2
        )

    return None


def parse_qr(
    text
):

    result = {}

    for line in text.splitlines():

        if "=" in line:

            k, v = (
                line.split(
                    "=",
                    1
                )
            )

            result[
                k
                .lower()
                .strip()
            ] = (
                v
                .strip()
            )

    return result


# -------------------------------
# 移動
# -------------------------------

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


# -------------------------------
# 保存完了待ち
# -------------------------------

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

            if size == old:

                return True

            old = size

        except:

            pass

        time.sleep(
            1
        )

    return False


# -------------------------------
# 監視
# -------------------------------

def monitor():

    print(
        "監視開始:",
        WATCH_FOLDER
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

            target = [

                x

                for x

                in files

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

                    continue


                qr = (
                    retry_qr(
                        path
                    )
                )

                if not qr:

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
            0.5
        )


# -------------------------------
# トレイ
# -------------------------------

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

    except:

        img = Image.new(
            "RGB",
            (
                64,
                64
            ),
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

        menu=
        pystray.Menu(

            pystray.MenuItem(

                "終了",

                lambda:
                stop()

            )

        )

    )

    icon.run()


threading.Thread(

    target=monitor,

    daemon=True

).start()

tray()