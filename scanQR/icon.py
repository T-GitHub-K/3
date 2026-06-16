from PIL import Image

img = Image.open("scanQR.bmp")

img.save(
    "scanQR.ico",
    sizes=[
        (16,16),
        (32,32),
        (48,48),
        (64,64)
    ]
)