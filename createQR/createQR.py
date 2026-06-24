import argparse
import os

import qrcode
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


def calc_auto_size_mm(text):

    length = len(text.encode("utf-8"))

    if length < 100:
        return 30

    elif length < 180:
        return 35

    elif length < 260:
        return 40

    elif length < 350:
        return 45

    else:
        return 50


def get_font(size):

    candidates = [

        r"C:\Windows\Fonts\meiryo.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
        r"C:\Windows\Fonts\YuGothM.ttc",
        r"C:\Windows\Fonts\YuGothR.ttc",

    ]

    for font_path in candidates:

        if os.path.exists(font_path):

            try:

                return ImageFont.truetype(
                    font_path,
                    size
                )

            except Exception:

                pass

    return ImageFont.load_default()


def create_qr(
        text,
        output,
        size_mm,
        footer):

    qr = qrcode.QRCode(

        version=None,

        error_correction=qrcode.constants.ERROR_CORRECT_L,

        box_size=10,

        border=2,

    )

    qr.add_data(text)

    qr.make(
        fit=True
    )

    img = qr.make_image(

        fill_color="black",

        back_color="white"

    ).convert("RGB")

    dpi = 300

    pixel = int(
        size_mm
        / 25.4
        * dpi
    )

    img = img.resize(
        (
            pixel,
            pixel
        )
    )

    if footer:

        font = get_font(
            max(
                14,
                pixel // 14
            )
        )

        temp_draw = ImageDraw.Draw(img)

        bbox = temp_draw.textbbox(

            (
                0,
                0
            ),

            footer,

            font=font

        )

        text_width = bbox[2] - bbox[0]

        text_height = bbox[3] - bbox[1]

        canvas = Image.new(

            "RGB",

            (
                pixel,
                pixel + text_height + 20
            ),

            "white"

        )

        canvas.paste(

            img,

            (
                0,
                0
            )

        )

        draw = ImageDraw.Draw(
            canvas
        )

        x = (
            pixel
            - text_width
        ) // 2

        y = (
            pixel
            + 5
        )

        draw.text(

            (
                x,
                y
            ),

            footer,

            fill="black",

            font=font

        )

        img = canvas

    img.save(

        output,

        dpi=(
            dpi,
            dpi
        )

    )

    print()

    print(
        f"保存完了 : {output}"
    )

    print(
        f"QRサイズ : {size_mm:.1f} mm"
    )

    if footer:

        print(
            f"下部文字 : {footer}"
        )


def main():

    parser = argparse.ArgumentParser(

        description="QRコード生成"

    )

    
    parser.add_argument(

        "--filename",

        required=True,

        help="ファイル名"

    )

    parser.add_argument(

        "-o",

        "--output",

        default="qr.png"

    )

    parser.add_argument(

        "--size-mm",

        type=float,

        help="QRサイズ(mm)"

    )

    parser.add_argument(

        "--auto-size",

        action="store_true",

        help="サイズ自動"

    )

    parser.add_argument(

        "--ftext",

        help="下部文字（日本語可）"

    )

    args = parser.parse_args()

    text = (
        f"filename={args.filename}"
    )

    if args.size_mm:

        size_mm = args.size_mm

    elif args.auto_size:

        size_mm = calc_auto_size_mm(
            text
        )

    else:

        size_mm = 40

    create_qr(

        text=text,

        output=args.output,

        size_mm=size_mm,

        footer=args.ftext

    )


if __name__ == "__main__":

    main()