"""音频播放引擎：pydub 解码 + sounddevice 输出。

支持 MP3 / OGG / FLAC / WAV。
"""

import io
import threading
from typing import Optional

import numpy as np
import sounddevice as sd
from pydub import AudioSegment

from compat import QObject, QTimer, Signal


class AudioPlayer(QObject):
    """异步音频播放器。

    信号：
        position_changed(int pos_ms, int total_ms)
        state_changed(str state)   'stopped' | 'playing' | 'paused'
        error_occurred(str msg)
    """

    position_changed = Signal(int, int)
    state_changed    = Signal(str)
    error_occurred   = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._samples: Optional[np.ndarray] = None
        self._rate = 44100
        self._channels = 2
        self._pos = 0
        self._total_frames = 0
        self._volume = 1.0
        self._stream: Optional[sd.OutputStream] = None
        self._lock = threading.Lock()
        self._state = 'stopped'

        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._emit_position)

    # ---------- 加载 ----------
    def load(self, raw: bytes, fmt_hint: Optional[str] = None) -> bool:
        """从字节流加载音频。返回是否成功。"""
        self.stop()
        try:
            seg = AudioSegment.from_file(io.BytesIO(raw), format=fmt_hint)
        except Exception as e:
            self.error_occurred.emit(f"解码失败: {e}")
            return False

        samples = np.array(seg.get_array_of_samples())

        # 归一化到 float32
        if seg.sample_width == 2:
            samples = samples.astype(np.float32) / 32768.0
        elif seg.sample_width == 1:
            samples = (samples.astype(np.float32) - 128.0) / 128.0
        elif seg.sample_width == 4:
            samples = samples.astype(np.float32) / 2147483648.0
        else:
            samples = samples.astype(np.float32)

        if seg.channels == 2:
            samples = samples.reshape(-1, 2)

        self._samples = samples
        self._rate = seg.frame_rate
        self._channels = seg.channels
        self._total_frames = len(samples)
        self._pos = 0
        return True

    # ---------- 播放控制 ----------
    def play(self):
        if self._samples is None:
            return
        if self._state == 'playing':
            return

        if self._stream is None:
            try:
                self._stream = sd.OutputStream(
                    samplerate=self._rate,
                    channels=self._channels,
                    dtype='float32',
                    callback=self._callback,
                    finished_callback=self._on_stream_finished,
                )
                self._stream.start()
            except Exception as e:
                self.error_occurred.emit(f"音频设备打开失败: {e}")
                self._stream = None
                return

        self._state = 'playing'
        self._timer.start()
        self.state_changed.emit('playing')

    def pause(self):
        if self._state != 'playing':
            return
        self._state = 'paused'
        self._timer.stop()
        self.state_changed.emit('paused')
        self._emit_position()

    def stop(self):
        was_active = self._state != 'stopped'
        self._state = 'stopped'
        self._timer.stop()

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        self._pos = 0
        self._emit_position()
        if was_active:
            self.state_changed.emit('stopped')

    def seek(self, ms: int):
        if self._samples is None:
            return
        with self._lock:
            frame = int(ms * self._rate / 1000)
            self._pos = max(0, min(frame, self._total_frames - 1))
        self._emit_position()

    def set_volume(self, vol: float):
        """vol: 0.0 ~ 1.0"""
        self._volume = max(0.0, min(1.0, vol))

    # ---------- 属性 ----------
    @property
    def state(self) -> str:
        return self._state

    @property
    def duration_ms(self) -> int:
        if self._rate == 0:
            return 0
        return int(self._total_frames * 1000 / self._rate)

    @property
    def position_ms(self) -> int:
        if self._rate == 0:
            return 0
        return int(self._pos * 1000 / self._rate)

    # ---------- 内部 ----------
    def _callback(self, outdata, frames, time_info, status):
        if status:
            pass
        with self._lock:
            if self._state != 'playing' or self._samples is None:
                outdata.fill(0)
                return
            end = min(self._pos + frames, self._total_frames)
            n = end - self._pos
            if n > 0:
                chunk = self._samples[self._pos:end] * self._volume
                outdata[:n] = chunk
                if n < frames:
                    outdata[n:] = 0
                self._pos = end
            else:
                outdata.fill(0)

    def _on_stream_finished(self):
        # 自然播放结束
        if self._pos >= self._total_frames:
            self._state = 'stopped'
            self._pos = 0
            self._timer.stop()
            self._emit_position()
            self.state_changed.emit('stopped')

    def _emit_position(self):
        self.position_changed.emit(self.position_ms, self.duration_ms)