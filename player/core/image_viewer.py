"""图片解码：Pillow → QPixmap。"""

import io

from PIL import Image

from compat import QtGui


def load_image_pixmap(raw: bytes):
    """从字节流加载图片，返回 QPixmap；失败返回 None。"""
    try:
        img = Image.open(io.BytesIO(raw))
        img = img.convert('RGBA')
    except Exception:
        return None

    data = img.tobytes('raw', 'RGBA')
    qimage = QtGui.QImage(
        data, img.width, img.height,
        QtGui.QImage.Format_RGBA8888,
    )
    # QImage 不持有 data 的所有权，需要 copy 一份
    qimage = qimage.copy()
    return QtGui.QPixmap.fromImage(qimage)