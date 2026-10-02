"""启动密码验证。

固定密码：sg123（用 SHA-256 哈希比对，避免明文硬编码）
"""

import hashlib

from compat import Qt, QtWidgets

(
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox,
) = (
    QtWidgets.QDialog, QtWidgets.QVBoxLayout, QtWidgets.QHBoxLayout,
    QtWidgets.QLabel, QtWidgets.QLineEdit,
    QtWidgets.QPushButton, QtWidgets.QMessageBox,
)


# 启动密码的 SHA-256（对应明文 "sg123"）
_AUTH_HASH = hashlib.sha256("sg123".encode("utf-8")).digest()


def check_password(pwd: str) -> bool:
    return hashlib.sha256(pwd.encode("utf-8")).digest() == _AUTH_HASH


class StartupAuthDialog(QDialog):
    """启动验证对话框。"""

    def __init__(self, parent=None, app_name="SGMF"):
        super().__init__(parent)
        self.setWindowTitle(f"{app_name} — 启动验证")
        self.setModal(True)
        self.setFixedSize(360, 200)
        # 去掉标题栏的问号按钮
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(14)

        title = QLabel(f"欢迎使用 {app_name}")
        title.setObjectName("AuthTitle")
        title.setAlignment(Qt.AlignCenter)

        hint = QLabel("请输入启动密码")
        hint.setObjectName("AuthHint")
        hint.setAlignment(Qt.AlignCenter)

        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.pwd_edit.setPlaceholderText("启动密码")
        self.pwd_edit.setAlignment(Qt.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        ok_btn = QPushButton("进入")
        ok_btn.setObjectName("PrimaryButton")
        ok_btn.setFixedWidth(100)
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(ok_btn)
        btn_row.addStretch(1)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.pwd_edit)
        layout.addLayout(btn_row)

        self.pwd_edit.returnPressed.connect(self._on_ok)
        self.pwd_edit.setFocus()

    def _on_ok(self):
        if check_password(self.pwd_edit.text()):
            self.accept()
        else:
            QMessageBox.warning(self, "密码错误", "启动密码不正确。")
            self.pwd_edit.clear()
            self.pwd_edit.setFocus()


def require_auth(parent=None, app_name="SGMF") -> bool:
    """弹出启动验证。返回 True 表示通过。"""
    dlg = StartupAuthDialog(parent, app_name)
    return dlg.exec() == QDialog.Accepted