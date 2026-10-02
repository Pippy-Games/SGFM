"""SGMF 转换器 — 程序入口。"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore", message=".*Python 3.8.*",
                        category=DeprecationWarning)

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from compat import Qt, QApplication, QIcon, QT_VERSION, IS_QT6, exec_app
from converter.ui.main_window import MainWindow


def _set_app_user_model_id(app_id: str):
    """Windows 任务栏图标必须设置 AppUserModelID 才生效。"""
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def _load_stylesheet() -> str:
    qss_path = os.path.join(_HERE, "ui", "styles.qss")
    if os.path.isfile(qss_path):
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""
    return ""


def _find_icon():
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, "assets", "icon.ico"))
        candidates.append(os.path.join(meipass, "converter", "assets", "icon.ico"))
    candidates.append(os.path.join(_ROOT, "assets", "icon.ico"))
    candidates.append(os.path.join(_HERE, "assets", "icon.ico"))
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _enable_high_dpi():
    if IS_QT6:
        if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except Exception:
        pass


def main() -> int:
    print(f"[SGMF] Qt 绑定: {QT_VERSION}")

    # ---- 关键 1：AppUserModelID，必须最早设置 ----
    _set_app_user_model_id("SGMF.Converter")

    _enable_high_dpi()

    app = QApplication(sys.argv)
    app.setApplicationName("SGMF 转换器")
    app.setApplicationDisplayName("SGMF 转换器")
    app.setOrganizationName("SGMF")

    # ---- 关键 2：QSS 必须在 MainWindow 之前应用 ----
    qss = _load_stylesheet()
    print(f"[SGMF] styles.qss 长度: {len(qss)}")
    if qss:
        app.setStyleSheet(qss)

    # ---- 图标 ----
    icon_path = _find_icon()
    if icon_path:
        print(f"[SGMF] 图标: {icon_path}")
        app.setWindowIcon(QIcon(icon_path))
    else:
        print("[SGMF] 未找到图标文件")

    # ---- 启动验证 ----
    from common.startup_auth import require_auth
    if not require_auth(app_name="SGMF 转换器"):
        return 0

    # ---- 主窗口 ----
    window = MainWindow()
    if icon_path:
        window.setWindowIcon(QIcon(icon_path))

    # 再次兜底：确保窗口本身也带上 QSS
    if qss:
        window.setStyleSheet(qss)

    window.show()
    return exec_app(app)


if __name__ == "__main__":
    sys.exit(main())