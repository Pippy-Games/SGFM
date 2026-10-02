"""Qt 绑定兼容层。

优先使用 PySide6（Qt6），不可用时回退到 PySide2（Qt5）。
所有 UI 代码都从这里导入 Qt 相关模块。

用法：
    from compat import QtCore, QtGui, QtWidgets, Qt, Signal, Slot
"""

import sys

QT_VERSION = None
IS_QT6 = False

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtCore import Qt, Signal, Slot, QThread, QObject, QTimer
    from PySide6.QtGui import (
        QIcon, QPixmap, QImage, QColor,
        QDragEnterEvent, QDropEvent,
    )
    from PySide6.QtWidgets import QApplication
    QT_VERSION = "PySide6"
    IS_QT6 = True

except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
        from PySide2.QtCore import Qt, Signal, Slot, QThread, QObject, QTimer
        from PySide2.QtGui import (
            QIcon, QPixmap, QImage, QColor,
            QDragEnterEvent, QDropEvent,
        )
        from PySide2.QtWidgets import QApplication
        QT_VERSION = "PySide2"
        IS_QT6 = False

    except ImportError:
        sys.stderr.write(
            "\n[错误] 未找到 PySide6 或 PySide2。\n"
            "请运行以下命令之一：\n"
            "  pip install PySide6   (Win10/11)\n"
            "  pip install PySide2   (Win7)\n\n"
        )
        raise


def exec_app(app):
    """Qt5 用 exec_()，Qt6 用 exec()。"""
    if hasattr(app, "exec"):
        return app.exec()
    return app.exec_()


__all__ = [
    "QtCore", "QtGui", "QtWidgets",
    "Qt", "Signal", "Slot", "QThread", "QObject", "QTimer",
    "QIcon", "QPixmap", "QImage", "QColor",
    "QDragEnterEvent", "QDropEvent",
    "QApplication",
    "QT_VERSION", "IS_QT6", "exec_app",
]