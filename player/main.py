"""SGMF 播放器 — 程序入口。"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore", message=".*Python 3.8.*",
                        category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*ffmpeg or avconv.*",
                        category=RuntimeWarning)

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _register_bundled_ffmpeg():
    import shutil
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, "tools", "ffmpeg", "bin"))
    candidates.append(os.path.join(_ROOT, "tools", "ffmpeg", "bin"))
    for bin_dir in candidates:
        exe = os.path.join(bin_dir, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if os.path.isfile(exe):
            if bin_dir not in os.environ.get("PATH", "").split(os.pathsep):
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            return bin_dir
    system = shutil.which("ffmpeg")
    return os.path.dirname(system) if system else None


_FFMPEG_DIR = _register_bundled_ffmpeg()


from compat import Qt, QApplication, QIcon, QTimer, QT_VERSION, IS_QT6, exec_app
from player.ui.main_window import MainWindow


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
        candidates.append(os.path.join(meipass, "player", "assets", "icon.ico"))
    candidates.append(os.path.join(_ROOT, "assets", "icon.ico"))
    candidates.append(os.path.join(_HERE, "assets", "icon.ico"))
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _parse_cli_file():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        return None
    candidate = args[0]
    if os.path.isfile(candidate):
        return os.path.abspath(candidate)
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
    print(f"[SGMF] FFmpeg:  {_FFMPEG_DIR or '未找到（音频解码可能失败）'}")

    # ---- 关键 1：AppUserModelID ----
    _set_app_user_model_id("SGMF.Player")

    _enable_high_dpi()

    app = QApplication(sys.argv)
    app.setApplicationName("SGMF 播放器")
    app.setApplicationDisplayName("SGMF 播放器")
    app.setOrganizationName("SGMF")

    # ---- 关键 2：QSS 必须先于 MainWindow ----
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
    if not require_auth(app_name="SGMF 播放器"):
        return 0

    # ---- 主窗口 ----
    window = MainWindow()
    if icon_path:
        window.setWindowIcon(QIcon(icon_path))
    if qss:
        window.setStyleSheet(qss)

    window.show()

    cli_file = _parse_cli_file()
    if cli_file:
        QTimer.singleShot(100, lambda: window._open_file(cli_file))

    return exec_app(app)


if __name__ == "__main__":
    sys.exit(main())