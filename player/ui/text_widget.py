"""文本显示界面。"""

from compat import Qt, QtWidgets
from player.core.text_viewer import decode_text

(
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton,
) = (
    QtWidgets.QWidget, QtWidgets.QVBoxLayout, QtWidgets.QHBoxLayout,
    QtWidgets.QLabel, QtWidgets.QTextEdit, QtWidgets.QPushButton,
)


class TextWidget(QWidget):
    """文本查看页。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        bar = QHBoxLayout()
        self.title = QLabel("—")
        self.title.setObjectName("MediaSubtitle")
        bar.addWidget(self.title)
        bar.addStretch(1)

        copy_btn = QPushButton("复制全文")
        copy_btn.setObjectName("GhostButton")
        copy_btn.clicked.connect(self._copy_all)
        bar.addWidget(copy_btn)

        root.addLayout(bar)

        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setObjectName("TextEditor")
        root.addWidget(self.editor, 1)

    def load(self, raw: bytes, actual_format: str, filename: str):
        text = decode_text(raw)
        self.editor.setPlainText(text)
        lines = text.count('\n') + 1
        chars = len(text)
        self.title.setText(f"{filename}   ({chars} 字符, {lines} 行)")

    def stop_and_clear(self):
        self.editor.clear()

    def _copy_all(self):
        self.editor.selectAll()
        self.editor.copy()
        self.editor.moveCursor(QtGui.QTextCursor.Start) if False else None