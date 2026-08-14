"""PIL -> QImage conversion, used only by the real camera backend.

Avoids depending on Pillow's own ImageQt shim (version-sensitive about which
Qt binding it detects) by converting raw pixel bytes directly.
"""
from __future__ import annotations

from PIL import Image
from PySide6.QtGui import QImage


def pil_to_qimage(img: Image.Image) -> QImage:
    if img.mode != "RGB":
        img = img.convert("RGB")
    data = img.tobytes("raw", "RGB")
    qimg = QImage(data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888)
    # QImage doesn't copy the buffer by default; the PIL bytes object goes out
    # of scope when this function returns, so force a deep copy now.
    return qimg.copy()
