"""视频播放界面：全屏 + 浮动控制栏 + 自动隐藏光标。"""

from compat import Qt, QtCore, QtGui, QtWidgets, Signal, QTimer
from player.core.video_player import VideoPlayer

(
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QFrame,
) = (
    QtWidgets.QWidget, QtWidgets.QVBoxLayout, QtWidgets.QHBoxLayout,
    QtWidgets.QLabel, QtWidgets.QPushButton, QtWidgets.QSlider,
    QtWidgets.QFrame,
)


def _fmt_time(ms: int) -> str:
    s = max(0, ms) // 1000
    return f"{s // 60:02d}:{s % 60:02d}"


# ============================================================
# 全屏窗口（带浮动控制栏）
# ============================================================
class FullscreenWindow(QWidget):
    """独立全屏窗口，浮动的控制栏，自动隐藏光标。"""

    closed          = Signal()
    play_toggled    = Signal()
    stop_requested  = Signal()
    seek_requested  = Signal(int)   # 0~1000
    volume_changed  = Signal(int)   # 0~100

    IDLE_MS         = 3000          # 3 秒不动
    POLL_INTERVAL   = 120           # 光标轮询间隔(ms)
    CTRL_MARGIN     = 24            # 控制栏距边缘

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

        # ---- 强制黑色背景（比 stylesheet 可靠）----
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor("black"))
        self.setPalette(pal)
        self.setStyleSheet("background-color: black;")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # ---- 浮动控制栏 ----
        self._ctrl = self._build_ctrl_bar()
        self._ctrl.setParent(self)
        self._ctrl.hide()
        self._ctrl.raise_()

        # 半透明效果
        self._ctrl_opacity = QtWidgets.QGraphicsOpacityEffect(self._ctrl)
        self._ctrl.setGraphicsEffect(self._ctrl_opacity)
        self._ctrl_opacity.setOpacity(0.0)
        self._fade_target = 0.0
        self._fade_anim = QtCore.QPropertyAnimation(
            self._ctrl_opacity, b"opacity", self
        )
        self._fade_anim.setDuration(180)

        # ---- 光标轮询（VLC 可能吞鼠标事件，用全局光标位置兜底）----
        self._last_cursor_pos = None
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(self.POLL_INTERVAL)
        self._poll_timer.timeout.connect(self._poll_cursor)
        self._poll_timer.start()

        # ---- 空闲计时 ----
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setInterval(self.IDLE_MS)
        self._idle_timer.timeout.connect(self._on_idle)

        self._cursor_hidden = False

    # ------------------------------------------------------------
    # 控制栏 UI
    # ------------------------------------------------------------
    def _build_ctrl_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("FullscreenCtrl")
        bar.setStyleSheet("""
            QFrame#FullscreenCtrl {
                background-color: rgba(20, 20, 30, 210);
                border-radius: 10px;
            }
            QFrame#FullscreenCtrl QLabel {
                color: #CDD6F4;
                background: transparent;
            }
            QFrame#FullscreenCtrl QPushButton {
                background-color: transparent;
                border: none;
                color: #CDD6F4;
                padding: 6px 8px;
                font-size: 14px;
                border-radius: 6px;
            }
            QFrame#FullscreenCtrl QPushButton:hover {
                background-color: rgba(124, 92, 252, 160);
                color: white;
            }
            QFrame#FullscreenCtrl QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255,255,255,70);
                border-radius: 2px;
            }
            QFrame#FullscreenCtrl QSlider::sub-page:horizontal {
                background: #7C5CFC;
                border-radius: 2px;
            }
            QFrame#FullscreenCtrl QSlider::handle:horizontal {
                background: white;
                width: 12px;
                height: 12px;
                margin: -5px 0;
                border-radius: 6px;
            }
        """)

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(8)

        self._play_btn = QPushButton("⏸")
        self._play_btn.setFixedWidth(36)
        self._play_btn.setToolTip("播放 / 暂停")
        self._play_btn.clicked.connect(self.play_toggled.emit)

        self._stop_btn = QPushButton("■")
        self._stop_btn.setFixedWidth(36)
        self._stop_btn.setToolTip("停止")
        self._stop_btn.clicked.connect(self.stop_requested.emit)

        self._time_label = QLabel("00:00 / 00:00")
        self._time_label.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 12px;"
        )

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setValue(0)
        self._dragging = False
        self._slider.sliderPressed.connect(self._on_slider_press)
        self._slider.sliderReleased.connect(self._on_slider_release)

        vol_icon = QLabel("🔊")

        self._vol_slider = QSlider(Qt.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(80)
        self._vol_slider.setFixedWidth(90)
        self._vol_slider.valueChanged.connect(self.volume_changed.emit)

        self._exit_btn = QPushButton("✕ 退出")
        self._exit_btn.setFixedWidth(72)
        self._exit_btn.setToolTip("退出全屏 (ESC)")
        self._exit_btn.clicked.connect(self.closed.emit)

        lay.addWidget(self._play_btn)
        lay.addWidget(self._stop_btn)
        lay.addWidget(self._time_label)
        lay.addWidget(self._slider, 1)
        lay.addWidget(vol_icon)
        lay.addWidget(self._vol_slider)
        lay.addWidget(self._exit_btn)

        return bar

    # ------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------
    def attach(self, widget: QWidget):
        """把视频画面收进来。"""
        widget.setParent(self)
        widget.setMouseTracking(True)
        self._layout.addWidget(widget)
        widget.show()
        self._ctrl.raise_()

    def release(self, widget: QWidget):
        """释放视频画面。"""
        self._layout.removeWidget(widget)
        widget.setParent(None)

    def update_position(self, pos_ms: int, total_ms: int):
        if not self._dragging and total_ms > 0:
            self._slider.setValue(int(pos_ms / total_ms * 1000))
        self._time_label.setText(f"{_fmt_time(pos_ms)} / {_fmt_time(total_ms)}")

    def update_state(self, state: str):
        self._play_btn.setText("⏸" if state == "playing" else "▶")

    def update_volume(self, vol_0_100: int):
        self._vol_slider.blockSignals(True)
        self._vol_slider.setValue(vol_0_100)
        self._vol_slider.blockSignals(False)

    # ------------------------------------------------------------
    # 光标 / 空闲检测
    # ------------------------------------------------------------
    def _poll_cursor(self):
        pos = QtGui.QCursor.pos()
        if self._last_cursor_pos is None:
            self._last_cursor_pos = pos
            return
        if pos != self._last_cursor_pos:
            self._last_cursor_pos = pos
            self._show_ctrl()
            self._show_cursor()
            self._idle_timer.start()

    def _on_idle(self):
        self._hide_ctrl()
        self._hide_cursor()

    def _show_ctrl(self):
        if self._ctrl.isVisible() and self._fade_target >= 0.99:
            return
        self._fade_target = 1.0
        self._ctrl.show()
        self._ctrl.raise_()
        self._reposition_ctrl()
        self._animate_opacity(1.0)

    def _hide_ctrl(self):
        if not self._ctrl.isVisible() or self._fade_target <= 0.01:
            return
        self._fade_target = 0.0
        self._animate_opacity(0.0)

    def _animate_opacity(self, target: float):
        self._fade_anim.stop()
        try:
            self._fade_anim.finished.disconnect()
        except Exception:
            pass
        self._fade_anim.setStartValue(float(self._ctrl_opacity.opacity()))
        self._fade_anim.setEndValue(float(target))
        self._fade_anim.finished.connect(self._on_fade_done)
        self._fade_anim.start()

    def _on_fade_done(self):
        try:
            self._fade_anim.finished.disconnect()
        except Exception:
            pass
        if self._fade_target <= 0.01:
            self._ctrl.hide()

    def _show_cursor(self):
        if self._cursor_hidden:
            self.unsetCursor()
            self._cursor_hidden = False

    def _hide_cursor(self):
        if not self._cursor_hidden:
            self.setCursor(Qt.BlankCursor)
            self._cursor_hidden = True

    def _reposition_ctrl(self):
        m = self.CTRL_MARGIN
        h = self._ctrl.sizeHint().height()
        w = max(400, self.width() - m * 2)
        self._ctrl.setGeometry(m, self.height() - h - m, w, h)

    # ------------------------------------------------------------
    # 滑块
    # ------------------------------------------------------------
    def _on_slider_press(self):
        self._dragging = True
        self._idle_timer.stop()

    def _on_slider_release(self):
        self._dragging = False
        self.seek_requested.emit(self._slider.value())
        self._idle_timer.start()

    # ------------------------------------------------------------
    # Qt 事件
    # ------------------------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_ctrl()

    def showEvent(self, event):
        super().showEvent(event)
        # 进入时先显示控制栏 3 秒
        QTimer.singleShot(50, self._show_ctrl)
        self._idle_timer.start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.closed.emit()
            event.accept()
            return
        if event.key() == Qt.Key_Space:
            self.play_toggled.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._poll_timer.stop()
        self._idle_timer.stop()
        self._show_cursor()
        self.closed.emit()
        event.accept()


# ============================================================
# 视频播放页
# ============================================================
class VideoWidget(QWidget):
    """视频播放页（含全屏）。"""

    request_stop = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = VideoPlayer(self)
        self.player.position_changed.connect(self._on_position)
        self.player.state_changed.connect(self._on_state)
        self.player.error_occurred.connect(self._on_error)

        self._dragging = False
        self._fullscreen = False
        self._fs_window = None

        self._build_ui()

    # ------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        self._root_layout = root

        # ---- 视频画面 ----
        self.video_frame = QFrame()
        self.video_frame.setObjectName("VideoFrame")
        self.video_frame.setStyleSheet("background-color: black;")
        self.video_frame.setMinimumHeight(360)
        self.video_frame.setMouseTracking(True)
        self.video_frame.mouseDoubleClickEvent = self._on_video_double_click
        root.addWidget(self.video_frame, 1)

        # ---- 控制面板（全屏时隐藏）----
        self.ctrl_panel = self._build_ctrl_panel()
        root.addWidget(self.ctrl_panel)

    def _build_ctrl_panel(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # 标题
        self.title = QLabel("—")
        self.title.setObjectName("MediaSubtitle")
        lay.addWidget(self.title)

        # 进度条
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderPressed.connect(lambda: setattr(self, '_dragging', True))
        self.slider.sliderReleased.connect(self._on_seek_release)
        lay.addWidget(self.slider)

        # 按钮行
        ctrl = QHBoxLayout()

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("TimeLabel")
        ctrl.addWidget(self.time_label)
        ctrl.addStretch(1)

        self.play_btn = QPushButton("⏸ 暂停")
        self.play_btn.setObjectName("PrimaryButton")
        self.play_btn.setFixedWidth(100)
        self.play_btn.clicked.connect(self.player.toggle_pause)

        self.stop_btn = QPushButton("■ 停止")
        self.stop_btn.setObjectName("GhostButton")
        self.stop_btn.setFixedWidth(90)
        self.stop_btn.clicked.connect(self.player.stop)

        self.fullscreen_btn = QPushButton("⛶ 全屏")
        self.fullscreen_btn.setObjectName("GhostButton")
        self.fullscreen_btn.setFixedWidth(90)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)

        ctrl.addWidget(self.play_btn)
        ctrl.addWidget(self.stop_btn)
        ctrl.addWidget(self.fullscreen_btn)

        vol_label = QLabel("音量")
        vol_label.setObjectName("FieldLabel")
        ctrl.addWidget(vol_label)

        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(120)
        self.vol_slider.valueChanged.connect(
            lambda v: self.player.set_volume(v / 100.0)
        )
        ctrl.addWidget(self.vol_slider)

        lay.addLayout(ctrl)
        return panel

    # ------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------
    def load(self, raw: bytes, actual_format: str, filename: str):
        if not VideoPlayer.is_available():
            self.title.setText("未检测到 VLC，无法播放视频。请安装 VLC 后重试。")
            return

        if self._fullscreen:
            self._exit_fullscreen()

        suffix = '.' + actual_format if actual_format != 'bin' else '.mp4'
        if not self.player.load(raw, suffix=suffix):
            return

        self.title.setText(filename)
        self.player.attach_widget(self.video_frame)
        self.player.set_volume(self.vol_slider.value() / 100.0)
        self.player.play()

    def stop_and_clear(self):
        if self._fullscreen:
            self._exit_fullscreen()
        self.player.stop()

    def shutdown(self):
        if self._fullscreen:
            self._exit_fullscreen()
        self.player.shutdown()

    # ------------------------------------------------------------
    # 全屏切换
    # ------------------------------------------------------------
    def toggle_fullscreen(self):
        if self._fullscreen:
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    def _enter_fullscreen(self):
        if self._fullscreen:
            return

        # 1. 记住播放状态，暂停 VLC 释放 HWND 绑定
        was_playing = self.player.state == 'playing'
        self.player.stop()

        # 2. 隐藏本地控制面板
        self.ctrl_panel.hide()

        # 3. 从原布局移除视频画面（不 setParent(None)，避免句柄销毁）
        self._root_layout.removeWidget(self.video_frame)

        # 4. 创建全屏窗口
        self._fs_window = FullscreenWindow(self.window())

        # 5. 连接信号
        self._fs_window.closed.connect(self._exit_fullscreen)
        self._fs_window.play_toggled.connect(self.player.toggle_pause)
        self._fs_window.stop_requested.connect(self.player.stop)
        self._fs_window.seek_requested.connect(self._on_fs_seek)
        self._fs_window.volume_changed.connect(self._on_fs_volume)

        # 6. 把画面挂进去（内部会 setParent 到 FullscreenWindow）
        self._fs_window.attach(self.video_frame)
        self.video_frame.show()

        # 7. 同步状态
        self._fs_window.update_volume(self.vol_slider.value())
        self._fs_window.update_state('playing' if was_playing else 'paused')

        # 8. 显示全屏
        self._fs_window.showFullScreen()
        self._fs_window.raise_()
        self._fs_window.activateWindow()
        self._fs_window.setFocus()

        # 9. 等窗口彻底就位后重新绑定 VLC 并恢复播放
        def _rebind():
            QtWidgets.QApplication.processEvents()
            self.player.attach_widget(self.video_frame)
            if was_playing:
                self.player.play()

        QTimer.singleShot(300, _rebind)

        self._fullscreen = True
        self.fullscreen_btn.setText("⛶ 退出")

    def _exit_fullscreen(self):
        if not self._fullscreen:
            return
        self._fullscreen = False

        # 1. 记住播放状态，暂停
        was_playing = self.player.state == 'playing'
        self.player.stop()

        # 2. 从全屏窗口移出视频画面
        if self._fs_window is not None:
            try:
                self._fs_window.release(self.video_frame)
            except Exception:
                pass
            try:
                self._fs_window.close()
            except Exception:
                pass
            self._fs_window.deleteLater()
            self._fs_window = None

        # 3. 放回原布局
        self._root_layout.insertWidget(0, self.video_frame)
        self.video_frame.show()

        # 4. 显示本地控制面板
        self.ctrl_panel.show()

        # 5. 重新绑定 VLC
        def _rebind():
            QtWidgets.QApplication.processEvents()
            self.player.attach_widget(self.video_frame)
            if was_playing:
                self.player.play()

        QTimer.singleShot(300, _rebind)

        self.fullscreen_btn.setText("⛶ 全屏")

    def _on_video_double_click(self, event):
        self.toggle_fullscreen()
        event.accept()

    def _on_fs_seek(self, value_0_1000: int):
        total = self.player.duration_ms
        if total > 0:
            self.player.seek(int(value_0_1000 / 1000 * total))

    def _on_fs_volume(self, vol_0_100: int):
        self.player.set_volume(vol_0_100 / 100.0)
        self.vol_slider.blockSignals(True)
        self.vol_slider.setValue(vol_0_100)
        self.vol_slider.blockSignals(False)

    # ------------------------------------------------------------
    # 状态同步
    # ------------------------------------------------------------
    def _on_state(self, state: str):
        if state == 'playing':
            self.play_btn.setText("⏸ 暂停")
        else:
            self.play_btn.setText("▶ 播放")
        if self._fs_window is not None:
            self._fs_window.update_state(state)

    def _on_position(self, pos_ms: int, total_ms: int):
        if not self._dragging and total_ms > 0:
            self.slider.setValue(int(pos_ms / total_ms * 1000))
        self.time_label.setText(f"{_fmt_time(pos_ms)} / {_fmt_time(total_ms)}")
        if self._fs_window is not None:
            self._fs_window.update_position(pos_ms, total_ms)

    def _on_seek_release(self):
        self._dragging = False
        total = self.player.duration_ms
        if total > 0:
            target = int(self.slider.value() / 1000 * total)
            self.player.seek(target)

    def _on_error(self, msg: str):
        self.title.setText(f"错误: {msg}")