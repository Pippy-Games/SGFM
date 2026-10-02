"""独立的密码设置对话框。

用途：
  - 用户未在主界面输入密码时弹出
  - 未来可从转换器命令行/脚本调用
  - 播放器也可复用同一模式（复刻到 player/ui/ 下）
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox,
)


class PasswordDialog(QDialog):
    """带确认输入的密码对话框。"""

    def __init__(self, parent=None,
                 title="设置密码",
                 hint="此密码用于加密文件，请务必牢记。丢失密码将无法恢复。"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(380)
        self._password = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(12)

        # 提示
        hint_label = QLabel(hint)
        hint_label.setWordWrap(True)
        hint_label.setObjectName("DialogHint")
        layout.addWidget(hint_label)

        # 密码
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.pwd_edit.setPlaceholderText("请输入密码（至少 4 位）")
        layout.addWidget(self.pwd_edit)

        # 确认
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        self.confirm_edit.setPlaceholderText("请再次输入确认")
        layout.addWidget(self.confirm_edit)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("GhostButton")
        cancel_btn.clicked.connect(self.reject)

        ok_btn = QPushButton("确定")
        ok_btn.setObjectName("PrimaryButton")
        ok_btn.clicked.connect(self._on_ok)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        # 回车确认
        self.pwd_edit.returnPressed.connect(
            lambda: self.confirm_edit.setFocus()
        )
        self.confirm_edit.returnPressed.connect(self._on_ok)

    def _on_ok(self):
        p1 = self.pwd_edit.text()
        p2 = self.confirm_edit.text()

        if len(p1) < 4:
            QMessageBox.warning(self, "密码太短", "密码至少需要 4 位。")
            self.pwd_edit.setFocus()
            return
        if p1 != p2:
            QMessageBox.warning(self, "密码不一致", "两次输入的密码不一致。")
            self.confirm_edit.clear()
            self.confirm_edit.setFocus()
            return

        self._password = p1
        self.accept()

    def get_password(self) -> str:
        return self._password

    @staticmethod
    def ask(parent=None) -> str:
        """便捷调用：返回密码，取消时返回空字符串。"""
        dlg = PasswordDialog(parent)
        if dlg.exec() == QDialog.Accepted:
            return dlg.get_password()
        return ""