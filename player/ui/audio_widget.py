"""音频播放界面。"""

from compat import Qt, QtWidgets, Signal
from player.core.audio_player import AudioPlayer

(
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider,
) = (
    QtWidgets.QWidget, QtWidgets.QVBoxLayout, QtWidgets.QHBoxLayout,
    QtWidgets.QLabel, QtWidgets.QPushButton, QtWidgets.QSlider,
)


def _fmt_time(ms: int) -> str:
    s = max(0, ms) // 1000
    return f"{s // 60:02d}:{s % 60:02d}"


class AudioWidget(QWidget):
    """音频播放页。"""

    request_stop = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = AudioPlayer(self)
        self.player.position_changed.connect(self._on_position)
        self.player.state_changed.connect(self._on_state)
        self.player.error_occurred.connect(self._on_error)
        self._dragging = False
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(20)
        root.addStretch(1)

        # 图标
        icon = QLabel("♪")
        icon.setObjectName("MediaIcon")
        icon.setAlignment(Qt.AlignCenter)
        root.addWidget(icon)

        # 文件名
        self.title = QLabel("—")
        self.title.setObjectName("MediaTitle")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setWordWrap(True)
        root.addWidget(self.title)

        # 格式
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("MediaSubtitle")
        self.subtitle.setAlignment(Qt.AlignCenter)
        root.addWidget(self.subtitle)

        root.addSpacing(10)

        # 进度
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderPressed.connect(lambda: setattr(self, '_dragging', True))
        self.slider.sliderReleased.connect(self._on_seek_release)
        root.addWidget(self.slider)

        time_row = QHBoxLayout()
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("TimeLabel")
        time_row.addWidget(self.time_label)
        time_row.addStretch(1)
        root.addLayout(time_row)

        # 控制按钮
        ctrl = QHBoxLayout()
        ctrl.addStretch(1)

        self.play_btn = QPushButton("▶ 播放")
        self.play_btn.setObjectName("PrimaryButton")
        self.play_btn.setFixedWidth(120)
        self.play_btn.clicked.connect(self._toggle_play)

        self.stop_btn = QPushButton("■ 停止")
        self.stop_btn.setObjectName("GhostButton")
        self.stop_btn.setFixedWidth(100)
        self.stop_btn.clicked.connect(self.player.stop)

        ctrl.addWidget(self.play_btn)
        ctrl.addWidget(self.stop_btn)
        ctrl.addStretch(1)
        root.addLayout(ctrl)

        # 音量
        vol_row = QHBoxLayout()
        vol_row.addStretch(1)
        vol_label = QLabel("音量")
        vol_label.setObjectName("FieldLabel")
        vol_row.addWidget(vol_label)

        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(180)
        self.vol_slider.valueChanged.connect(
            lambda v: self.player.set_volume(v / 100.0)
        )
        vol_row.addWidget(self.vol_slider)
        vol_row.addStretch(1)
        root.addLayout(vol_row)

        root.addStretch(2)

    # ---------- 外部调用 ----------
    def load(self, raw: bytes, actual_format: str, filename: str):
        if not self.player.load(raw, actual_format):
            return
        self.title.setText(filename)
        self.subtitle.setText(f"格式: {actual_format.upper()}")
        self.play_btn.setText("▶ 播放")
        self.player.set_volume(self.vol_slider.value() / 100.0)
        self.player.play()

    def stop_and_clear(self):
        self.player.stop()

    # ---------- 内部 ----------
    def _toggle_play(self):
        if self.player.state == 'playing':
            self.player.pause()
        else:
            self.player.play()

    def _on_state(self, state: str):
        if state == 'playing':
            self.play_btn.setText("⏸ 暂停")
        else:
            self.play_btn.setText("▶ 播放")

    def _on_position(self, pos_ms: int, total_ms: int):
        if not self._dragging and total_ms > 0:
            self.slider.setValue(int(pos_ms / total_ms * 1000))
        self.time_label.setText(f"{_fmt_time(pos_ms)} / {_fmt_time(total_ms)}")

    def _on_seek_release(self):
        self._dragging = False
        total = self.player.duration_ms
        if total > 0:
            target = int(self.slider.value() / 1000 * total)
            self.player.seek(target)

    def _on_error(self, msg: str):
        self.subtitle.setText(f"错误: {msg}")