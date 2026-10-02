"""播放器主窗口。"""

import os

from compat import Qt, QtWidgets, Signal, QApplication
from sgmf_core import (
    ALL_SGMF_EXTS, DecryptionError, InvalidFormatError,
    PayloadType, format_size, is_sgmf_file,
)

from player.core.dispatcher import MediaInfo, open_sgmf
from player.ui.audio_widget import AudioWidget
from player.ui.video_widget import VideoWidget
from player.ui.image_widget import ImageWidget
from player.ui.text_widget import TextWidget
from player.ui.password_dialog import PasswordDialog

(
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QStackedWidget,
    QFileDialog, QMessageBox,
) = (
    QtWidgets.QMainWindow, QtWidgets.QWidget, QtWidgets.QVBoxLayout,
    QtWidgets.QHBoxLayout, QtWidgets.QLabel, QtWidgets.QLineEdit,
    QtWidgets.QPushButton, QtWidgets.QFrame, QtWidgets.QStackedWidget,
    QtWidgets.QFileDialog, QtWidgets.QMessageBox,
)


# ============================================================
# 拖入区
# ============================================================
class DropArea(QFrame):
    files_dropped = Signal(list)
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("DropArea")
        self.setMinimumHeight(150)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("dragActive", False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(4)

        icon = QLabel("▶")
        icon.setObjectName("DropIcon")
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("拖入 SGMF 文件到此处播放")
        title.setObjectName("DropTitle")
        title.setAlignment(Qt.AlignCenter)

        hint = QLabel(
            "支持 .sgmic / .sgpim / .sgwb / .sgtp\n"
            "点击本区域也可选择文件"
        )
        hint.setObjectName("DropHint")
        hint.setAlignment(Qt.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(hint)

    def _set_drag_active(self, active: bool):
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_drag_active(True)

    def dragLeaveEvent(self, event):
        self._set_drag_active(False)

    def dropEvent(self, event):
        self._set_drag_active(False)
        paths = []
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p and os.path.isfile(p):
                paths.append(p)
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):

    PAGE_WELCOME = 0
    PAGE_AUDIO   = 1
    PAGE_VIDEO   = 2
    PAGE_IMAGE   = 3
    PAGE_TEXT    = 4

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SGMF 播放器")
        self.resize(900, 700)
        self.setMinimumSize(720, 520)

        # ---- 兜底：直接加载 QSS ----
        self._apply_stylesheet()

        self._current_path = ""
        self._build_ui()
        self._switch_page(self.PAGE_WELCOME)

    def _apply_stylesheet(self):
        """从模块目录加载 styles.qss 并应用。"""
        qss_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "styles.qss",
        )
        if not os.path.isfile(qss_path):
            print(f"[SGMF] styles.qss 未找到: {qss_path}")
            return
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                qss = f.read()
            print(f"[SGMF] MainWindow 加载 QSS: {len(qss)} 字符")
            app = QApplication.instance()
            if app is not None:
                app.setStyleSheet(qss)
            self.setStyleSheet(qss)
        except Exception as e:
            print(f"[SGMF] QSS 加载失败: {e}")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ---------- 顶部 ----------
        top = QHBoxLayout()

        title = QLabel("SGMF 播放器")
        title.setObjectName("AppTitle")
        top.addWidget(title)
        top.addStretch(1)

        pwd_label = QLabel("密码：")
        pwd_label.setObjectName("FieldLabel")
        top.addWidget(pwd_label)

        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.pwd_edit.setPlaceholderText("留空则打开时询问")
        self.pwd_edit.setFixedWidth(180)
        self.pwd_edit.setText("sg123")
        top.addWidget(self.pwd_edit)

        root.addLayout(top)

        # ---------- 打开按钮行 ----------
        bar = QHBoxLayout()

        open_btn = QPushButton("打开文件")
        open_btn.setObjectName("PrimaryButton")
        open_btn.clicked.connect(self._pick_file)
        bar.addWidget(open_btn)

        bar.addStretch(1)

        self.file_label = QLabel("未加载文件")
        self.file_label.setObjectName("MediaSubtitle")
        bar.addWidget(self.file_label)

        root.addLayout(bar)

        # ---------- 页面栈 ----------
        self.stack = QStackedWidget()

        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self._on_files_dropped)
        self.drop_area.clicked.connect(self._pick_file)
        self.stack.addWidget(self.drop_area)

        self.audio_widget = AudioWidget()
        self.video_widget = VideoWidget()
        self.image_widget = ImageWidget()
        self.text_widget  = TextWidget()

        self.stack.addWidget(self.audio_widget)
        self.stack.addWidget(self.video_widget)
        self.stack.addWidget(self.image_widget)
        self.stack.addWidget(self.text_widget)

        root.addWidget(self.stack, 1)

        # ---------- 返回 ----------
        back_row = QHBoxLayout()
        back_row.addStretch(1)

        self.back_btn = QPushButton("← 返回")
        self.back_btn.setObjectName("GhostButton")
        self.back_btn.clicked.connect(self._on_back)
        back_row.addWidget(self.back_btn)

        root.addLayout(back_row)

    # ------------------------------------------------------------
    # 打开流程
    # ------------------------------------------------------------
    def _pick_file(self):
        exts = " ".join(f"*{e}" for e in ALL_SGMF_EXTS)
        path, _ = QFileDialog.getOpenFileName(
            self, "打开 SGMF 文件", "",
            f"SGMF 文件 ({exts});;所有文件 (*.*)",
        )
        if path:
            self._open_file(path)

    def _on_files_dropped(self, paths):
        if not paths:
            return
        self._open_file(paths[0])

    def _open_file(self, path: str):
        if not is_sgmf_file(path):
            QMessageBox.warning(
                self, "不是 SGMF 文件",
                f"{os.path.basename(path)}\n\n"
                "该文件不是 SGMF 格式，无法打开。\n"
                "请先用 SGMF 转换器将其转换。"
            )
            return

        password = self.pwd_edit.text()
        if not password:
            password = PasswordDialog.ask(self, os.path.basename(path))
            if not password:
                return

        try:
            info = open_sgmf(path, password)
        except DecryptionError:
            QMessageBox.critical(
                self, "密码错误",
                "解密失败，请检查密码是否正确。"
            )
            return
        except InvalidFormatError as e:
            QMessageBox.critical(self, "文件错误", str(e))
            return
        except Exception as e:
            QMessageBox.critical(
                self, "打开失败",
                f"{type(e).__name__}: {e}"
            )
            return

        self._stop_current()
        self._current_path = path
        self.file_label.setText(
            f"{os.path.basename(path)}   ({format_size(info.size)})"
        )
        self._dispatch(info)

    def _dispatch(self, info: MediaInfo):
        name = os.path.basename(info.source_path)

        if info.payload_type == PayloadType.AUDIO:
            self._switch_page(self.PAGE_AUDIO)
            self.audio_widget.load(info.raw, info.actual_format, name)

        elif info.payload_type == PayloadType.VIDEO:
            self._switch_page(self.PAGE_VIDEO)
            self.video_widget.load(info.raw, info.actual_format, name)

        elif info.payload_type == PayloadType.IMAGE:
            self._switch_page(self.PAGE_IMAGE)
            self.image_widget.load(info.raw, info.actual_format, name)

        elif info.payload_type == PayloadType.TEXT:
            self._switch_page(self.PAGE_TEXT)
            self.text_widget.load(info.raw, info.actual_format, name)

        else:
            QMessageBox.warning(
                self, "未知类型",
                f"不支持的 PayloadType: {info.payload_type}"
            )
            self._switch_page(self.PAGE_WELCOME)

    # ------------------------------------------------------------
    # 页面切换
    # ------------------------------------------------------------
    def _switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        self.back_btn.setVisible(index != self.PAGE_WELCOME)

    def _on_back(self):
        self._stop_current()
        self.file_label.setText("未加载文件")
        self._current_path = ""
        self._switch_page(self.PAGE_WELCOME)

    def _stop_current(self):
        for w in (self.audio_widget, self.video_widget,
                  self.image_widget, self.text_widget):
            try:
                w.stop_and_clear()
            except Exception:
                pass

    # ------------------------------------------------------------
    # 键盘事件
    # ------------------------------------------------------------
    def keyPressEvent(self, event):
        if (hasattr(self, "video_widget")
                and getattr(self.video_widget, "_fullscreen", False)):
            if event.key() == Qt.Key_Escape:
                self.video_widget._exit_fullscreen()
                event.accept()
                return
        super().keyPressEvent(event)

    # ------------------------------------------------------------
    # 关闭
    # ------------------------------------------------------------
    def closeEvent(self, event):
        try:
            self.video_widget.shutdown()
        except Exception:
            pass
        try:
            self.audio_widget.stop_and_clear()
        except Exception:
            pass
        event.accept()