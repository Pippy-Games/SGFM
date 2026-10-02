"""播放器密码输入对话框。"""

from compat import Qt, QtWidgets

(
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox,
) = (
    QtWidgets.QDialog, QtWidgets.QVBoxLayout, QtWidgets.QHBoxLayout,
    QtWidgets.QLabel, QtWidgets.QLineEdit,
    QtWidgets.QPushButton, QtWidgets.QMessageBox,
)


class PasswordDialog(QDialog):
    """输入密码解锁 SGMF 文件。"""

    def __init__(self, parent=None, filename=""):
        super().__init__(parent)
        self.setWindowTitle("需要密码")
        self.setModal(True)
        self.setMinimumWidth(360)
        self._password = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(12)

        tip = QLabel(
            f"<b>{filename}</b><br><br>"
            "该文件已加密，请输入密码以播放。"
        )
        tip.setWordWrap(True)
        tip.setObjectName("DialogHint")
        layout.addWidget(tip)

        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.pwd_edit.setPlaceholderText("请输入密码")
        layout.addWidget(self.pwd_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("GhostButton")
        cancel_btn.clicked.connect(self.reject)

        ok_btn = QPushButton("打开")
        ok_btn.setObjectName("PrimaryButton")
        ok_btn.clicked.connect(self._on_ok)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        self.pwd_edit.returnPressed.connect(self._on_ok)
        self.pwd_edit.setFocus()

    def _on_ok(self):
        p = self.pwd_edit.text()
        if not p:
            QMessageBox.warning(self, "提示", "密码不能为空。")
            return
        self._password = p
        self.accept()

    def get_password(self) -> str:
        return self._password

    @staticmethod
    def ask(parent=None, filename="") -> str:
        dlg = PasswordDialog(parent, filename)
        if dlg.exec() == QDialog.Accepted:
            return dlg.get_password()
        return ""