"""视频播放：python-vlc 封装。

策略：解密后的字节流写入临时文件，交给 VLC 播放，关闭时删除。
"""

import os
import sys
import tempfile
from typing import Optional

from compat import QObject, QTimer, Signal

try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    vlc = None
    VLC_AVAILABLE = False


class VideoPlayer(QObject):
    """异步视频播放器。

    信号：
        position_changed(int pos_ms, int total_ms)
        state_changed(str state)
        error_occurred(str msg)
    """

    position_changed = Signal(int, int)
    state_changed    = Signal(str)
    error_occurred   = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._instance = None
        self._player = None
        self._tmp_path: Optional[str] = None
        self._video_frame = None

        if VLC_AVAILABLE:
            try:
                self._instance = vlc.Instance("--quiet")
                self._player = self._instance.media_player_new()
                self._player.event_manager().event_attach(
                    vlc.EventType.MediaPlayerEndReached,
                    self._on_end_reached,
                )
            except Exception as e:
                self.error_occurred.emit(f"VLC 初始化失败: {e}")
                self._player = None

        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._emit_position)

    @staticmethod
    def is_available() -> bool:
        return VLC_AVAILABLE and vlc is not None

    # ---------- 窗口绑定 ----------
    def attach_widget(self, widget):
        """把 VLC 输出绑定到 QWidget（一般是 QFrame）。"""
        self._video_frame = widget
        if self._player is None:
            return
        try:
            if sys.platform.startswith('win'):
                self._player.set_hwnd(int(widget.winId()))
            elif sys.platform == 'darwin':
                self._player.set_nsobject(int(widget.winId()))
            else:
                self._player.set_xwindow(int(widget.winId()))
        except Exception as e:
            self.error_occurred.emit(f"绑定视频输出失败: {e}")

    # ---------- 加载 ----------
    def load(self, raw: bytes, suffix: str = '.mp4') -> bool:
        if self._player is None:
            self.error_occurred.emit("VLC 未安装或初始化失败")
            return False

        self.stop()
        self._cleanup_tmp()

        try:
            fd, path = tempfile.mkstemp(prefix='sgmf_', suffix=suffix)
            with os.fdopen(fd, 'wb') as f:
                f.write(raw)
            self._tmp_path = path
        except OSError as e:
            self.error_occurred.emit(f"写临时文件失败: {e}")
            return False

        try:
            media = self._instance.media_new(self._tmp_path)
            self._player.set_media(media)
        except Exception as e:
            self.error_occurred.emit(f"加载媒体失败: {e}")
            return False

        # 如果已经绑定了窗口，重新绑定一次
        if self._video_frame is not None:
            self.attach_widget(self._video_frame)
        return True

    # ---------- 控制 ----------
    def play(self):
        if self._player is None:
            return
        try:
            self._player.play()
            self._timer.start()
            self.state_changed.emit('playing')
        except Exception as e:
            self.error_occurred.emit(f"播放失败: {e}")

    def pause(self):
        if self._player is None:
            return
        try:
            self._player.pause()
            self._timer.stop()
            self.state_changed.emit('paused')
        except Exception:
            pass

    def toggle_pause(self):
        if self._player is None:
            return
        if self._player.is_playing():
            self.pause()
        else:
            self.play()

    def stop(self):
        if self._player is None:
            return
        try:
            self._player.stop()
        except Exception:
            pass
        self._timer.stop()
        self.state_changed.emit('stopped')

    def seek(self, ms: int):
        if self._player is None:
            return
        try:
            self._player.set_time(int(ms))
        except Exception:
            pass

    def set_volume(self, vol: float):
        """vol: 0.0 ~ 1.0"""
        if self._player is None:
            return
        try:
            self._player.audio_set_volume(int(max(0.0, min(1.0, vol)) * 100))
        except Exception:
            pass

    # ---------- 属性 ----------
    @property
    def duration_ms(self) -> int:
        if self._player is None:
            return 0
        try:
            return max(0, self._player.get_length() or 0)
        except Exception:
            return 0

    @property
    def position_ms(self) -> int:
        if self._player is None:
            return 0
        try:
            return max(0, self._player.get_time() or 0)
        except Exception:
            return 0

    # ---------- 内部 ----------
    def _emit_position(self):
        self.position_changed.emit(self.position_ms, self.duration_ms)

    def _on_end_reached(self, event):
        self._timer.stop()
        self.state_changed.emit('stopped')

    def _cleanup_tmp(self):
        if self._tmp_path and os.path.exists(self._tmp_path):
            try:
                os.unlink(self._tmp_path)
            except OSError:
                pass
        self._tmp_path = None

    def shutdown(self):
        """窗口关闭时调用。"""
        self.stop()
        self._cleanup_tmp()
        if self._player is not None:
            try:
                self._player.release()
            except Exception:
                pass
            self._player = None
        if self._instance is not None:
            try:
                self._instance.release()
            except Exception:
                pass
            self._instance = None