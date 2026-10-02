"""图片显示界面：支持缩放、适应窗口。"""

from compat import Qt, QtWidgets, QtGui
from player.core.image_viewer import load_image_pixmap

(
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea,
) = (
    QtWidgets.QWidget, QtWidgets.QVBoxLayout, QtWidgets.QHBoxLayout,
    QtWidgets.QLabel, QtWidgets.QPushButton, QtWidgets.QScrollArea,
)


class ImageWidget(QWidget):
    """图片查看页。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._fit_mode = True
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # 滚动区 + 图片
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setObjectName("ImageScroll")

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setObjectName("ImageView")
        self.scroll.setWidget(self.image_label)
        root.addWidget(self.scroll, 1)

        # 底部工具条
        bar = QHBoxLayout()
        self.title = QLabel("—")
        self.title.setObjectName("MediaSubtitle")
        bar.addWidget(self.title)
        bar.addStretch(1)

        fit_btn = QPushButton("适应窗口")
        fit_btn.setObjectName("GhostButton")
        fit_btn.clicked.connect(self._set_fit)

        orig_btn = QPushButton("原始大小")
        orig_btn.setObjectName("GhostButton")
        orig_btn.clicked.connect(self._set_original)

        bar.addWidget(fit_btn)
        bar.addWidget(orig_btn)
        root.addLayout(bar)

    def load(self, raw: bytes, actual_format: str, filename: str):
        pixmap = load_image_pixmap(raw)
        if pixmap is None:
            self.title.setText("图片加载失败")
            return
        self._pixmap = pixmap
        self.title.setText(f"{filename}   ({actual_format.upper()}, "
                           f"{pixmap.width()}×{pixmap.height()})")
        self._apply()

    def stop_and_clear(self):
        pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit_mode:
            self._apply()

    def _set_fit(self):
        self._fit_mode = True
        self._apply()

    def _set_original(self):
        self._fit_mode = False
        self._apply()

    def _apply(self):
        if self._pixmap is None:
            return
        if self._fit_mode:
            size = self.scroll.viewport().size()
            scaled = self._pixmap.scaled(
                size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
            self.image_label.resize(size)
        else:
            self.image_label.setPixmap(self._pixmap)
            self.image_label.resize(self._pixmap.size())