import os
import shutil

import fitz
import cv2
import numpy as np


PDF = r"C:\SCAN\20260616.pdf"


# ========================
# QR解析
# ========================

def parse_qr(text):

    data = {}

    for line in text.splitlines():

        if "=" in line:

            k, v = line.split(
                "=",
                1
            )

            data[
                k
                .strip()
                .lower()
            ] = (
                v.strip()
            )

    return data


# ========================
# 同名回避
# ========================

def create_dst(folder, filename):

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

    return dst


# ========================
# PDF→画像
# ========================

print(
    "PDF読込開始"
)

doc = fitz.open(
    PDF
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


# ========================
# QR読取
# ========================

print(
    "QR解析開始"
)

detector = (
    cv2.QRCodeDetector()
)

text, points, _ = (

    detector.detectAndDecode(
        img
    )

)


print()
print(
    "結果="
)

print(
    repr(
        text
    )
)

print()

print(
    "座標="
)

print(
    points
)

print()


if not text:

    print(
        "QR未検出"
    )

    exit()


# ========================
# QR値取得
# ========================

info = parse_qr(
    text
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


print(
    "folder="
)

print(
    repr(
        folder
    )
)

print()

print(
    "filename="
)

print(
    repr(
        filename
    )
)

print()


if not folder:

    print(
        "ERROR: folderなし"
    )

    exit()


if not filename:

    print(
        "ERROR: filenameなし"
    )

    exit()


# ========================
# 保存先
# ========================

os.makedirs(
    folder,
    exist_ok=True
)

dst = create_dst(
    folder,
    filename
)


print(
    "保存先="
)

print(
    dst
)

print()

print(
    "パス長="
)

print(
    len(
        dst
    )
)

print()


if len(
    dst
) > 260:

    print(
        "警告: パス長超過"
    )


print()

print(
    "保存先存在確認"
)

print(
    os.path.exists(
        folder
    )
)

print()


# ========================
# アクセステスト
# ========================

try:

    os.listdir(
        folder
    )

    print(
        "アクセス成功"
    )

except Exception as e:

    print(
        "アクセス失敗"
    )

    print(
        repr(
            e
        )
    )

    exit()


# ========================
# 実際に移動
# ========================

print()

print(
    "移動実行"
)

print()

print(
    "元="
)

print(
    PDF
)

print()

print(
    "先="
)

print(
    dst
)

print()


try:

    shutil.move(

        PDF,

        dst

    )

    print()

    print(
        "移動成功"
    )

    print()

    print(
        "存在確認="
    )

    print(
        os.path.exists(
            dst
        )
    )

except Exception as e:

    print()

    print(
        "移動失敗"
    )

    print()

    print(
        repr(
            e
        )
    )


print()

print(
    "終了"
)