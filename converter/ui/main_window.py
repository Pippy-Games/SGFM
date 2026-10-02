"""转换器主窗口。"""

import os
from compat import Qt, QtWidgets, Signal, QColor, QApplication
from sgmf_core import EXT_TO_TYPE, TYPE_TO_EXT, format_size
from converter.core.batch import BatchWorker

(
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QProgressBar, QFileDialog, QMessageBox, QHeaderView,
    QAbstractItemView, QFrame,
) = (
    QtWidgets.QMainWindow, QtWidgets.QWidget,
    QtWidgets.QVBoxLayout, QtWidgets.QHBoxLayout, QtWidgets.QLabel,
    QtWidgets.QLineEdit, QtWidgets.QPushButton,
    QtWidgets.QTableWidget, QtWidgets.QTableWidgetItem,
    QtWidgets.QProgressBar, QtWidgets.QFileDialog, QtWidgets.QMessageBox,
    QtWidgets.QHeaderView, QtWidgets.QAbstractItemView, QtWidgets.QFrame,
)


# ============================================================
# 拖入区
# ============================================================
class DropArea(QFrame):
    files_dropped = Signal(list)
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("DropArea")
        self.setMinimumHeight(140)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("dragActive", False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(4)

        icon = QLabel("⬇")
        icon.setObjectName("DropIcon")
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("拖入文件或文件夹到此处")
        title.setObjectName("DropTitle")
        title.setAlignment(Qt.AlignCenter)

        hint = QLabel(
            "支持  mp3 / ogg / flac / wav / mp4 / txt / jpg / png\n"
            "可拖入文件夹（自动递归扫描）"
        )
        hint.setObjectName("DropHint")
        hint.setAlignment(Qt.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(hint)

    def _set_drag_active(self, active: bool):
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_drag_active(True)

    def dragLeaveEvent(self, event):
        self._set_drag_active(False)

    def dropEvent(self, event):
        self._set_drag_active(False)
        paths = []
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p and os.path.exists(p):
                paths.append(p)
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SGMF 转换器")
        self.resize(860, 720)
        self.setMinimumSize(680, 540)

        # ---- 兜底：直接加载 QSS ----
        self._apply_stylesheet()

        self._worker = None
        self._thread = None

        self._build_ui()
        self._update_convert_button()

    def _apply_stylesheet(self):
        """从模块目录加载 styles.qss 并应用。"""
        qss_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "styles.qss",
        )
        if not os.path.isfile(qss_path):
            print(f"[SGMF] styles.qss 未找到: {qss_path}")
            return
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                qss = f.read()
            print(f"[SGMF] MainWindow 加载 QSS: {len(qss)} 字符")
            app = QApplication.instance()
            if app is not None:
                app.setStyleSheet(qss)
            self.setStyleSheet(qss)
        except Exception as e:
            print(f"[SGMF] QSS 加载失败: {e}")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("SGMF 转换器")
        title.setObjectName("AppTitle")

        subtitle = QLabel(
            "把普通文件加密为 .sgmic / .sgpim / .sgwb / .sgtp 专用格式"
        )
        subtitle.setObjectName("AppSubtitle")

        root.addWidget(title)
        root.addWidget(subtitle)

        # ---------- 密码行 ----------
        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(8)

        pwd_label = QLabel("密码：")
        pwd_label.setObjectName("FieldLabel")
        pwd_label.setFixedWidth(60)

        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.pwd_edit.setPlaceholderText("至少 4 位，转换前必须设置")
        self.pwd_edit.textChanged.connect(self._update_convert_button)
        self.pwd_edit.setText("sg123")

        self.show_pwd_btn = QPushButton("显示")
        self.show_pwd_btn.setObjectName("IconButton")
        self.show_pwd_btn.setCheckable(True)
        self.show_pwd_btn.setFixedWidth(56)
        self.show_pwd_btn.toggled.connect(self._toggle_pwd_visibility)

        pwd_row.addWidget(pwd_label)
        pwd_row.addWidget(self.pwd_edit, 1)
        pwd_row.addWidget(self.show_pwd_btn)
        root.addLayout(pwd_row)

        # ---------- 输出目录行 ----------
        out_row = QHBoxLayout()
        out_row.setSpacing(8)

        out_label = QLabel("输出：")
        out_label.setObjectName("FieldLabel")
        out_label.setFixedWidth(60)

        self.out_edit = QLineEdit()
        self.out_edit.setPlaceholderText("留空表示与源文件同目录")

        self.out_btn = QPushButton("浏览")
        self.out_btn.setObjectName("GhostButton")
        self.out_btn.setFixedWidth(56)
        self.out_btn.clicked.connect(self._pick_output_dir)

        out_row.addWidget(out_label)
        out_row.addWidget(self.out_edit, 1)
        out_row.addWidget(self.out_btn)
        root.addLayout(out_row)

        # ---------- 拖入区 ----------
        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self._on_files_added)
        self.drop_area.clicked.connect(self._pick_files)
        root.addWidget(self.drop_area)

        # ---------- 文件列表标题 ----------
        list_header = QHBoxLayout()
        list_title = QLabel("待转换文件")
        list_title.setObjectName("SectionTitle")

        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.setObjectName("GhostButton")
        self.clear_btn.clicked.connect(self._clear_files)

        list_header.addWidget(list_title)
        list_header.addStretch(1)
        list_header.addWidget(self.clear_btn)
        root.addLayout(list_header)

        # ---------- 表格 ----------
        self.file_table = QTableWidget(0, 4)
        self.file_table.setHorizontalHeaderLabels(
            ["文件名", "类型", "大小", "状态"]
        )
        hh = self.file_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setShowGrid(False)
        self.file_table.setWordWrap(False)
        self.file_table.setColumnWidth(1, 80)
        self.file_table.setColumnWidth(2, 90)
        self.file_table.setColumnWidth(3, 90)
        root.addWidget(self.file_table, 1)

        # ---------- 进度条 ----------
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("就绪")
        root.addWidget(self.progress)

        # ---------- 底部按钮 ----------
        action_row = QHBoxLayout()

        self.select_btn = QPushButton("选择文件")
        self.select_btn.setObjectName("GhostButton")
        self.select_btn.clicked.connect(self._pick_files)

        self.select_dir_btn = QPushButton("选择文件夹")
        self.select_dir_btn.setObjectName("GhostButton")
        self.select_dir_btn.clicked.connect(self._pick_folder)

        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.setObjectName("PrimaryButton")
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self._start_convert)

        action_row.addWidget(self.select_btn)
        action_row.addWidget(self.select_dir_btn)
        action_row.addStretch(1)
        action_row.addWidget(self.convert_btn)
        root.addLayout(action_row)

    # ------------------------------------------------------------
    # 密码 / 目录
    # ------------------------------------------------------------
    def _toggle_pwd_visibility(self, checked: bool):
        self.pwd_edit.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password
        )
        self.show_pwd_btn.setText("隐藏" if checked else "显示")

    def _pick_output_dir(self):
        d = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.out_edit.text() or ""
        )
        if d:
            self.out_edit.setText(d)

    def _pick_files(self):
        exts = " ".join(f"*{e}" for e in EXT_TO_TYPE.keys())
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要转换的文件", "",
            f"支持的文件 ({exts});;所有文件 (*.*)",
        )
        if files:
            self._on_files_added(files)

    def _pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹（递归扫描）")
        if d:
            self._on_files_added([d])

    # ------------------------------------------------------------
    # 文件列表管理
    # ------------------------------------------------------------
    def _on_files_added(self, paths):
        # ---- 展开文件夹 ----
        expanded = []
        for p in paths:
            if os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for f in files:
                        expanded.append(os.path.join(root, f))
            else:
                expanded.append(p)

        existing = set()
        for i in range(self.file_table.rowCount()):
            it = self.file_table.item(i, 0)
            if it:
                existing.add(it.data(Qt.UserRole))

        added = 0
        skipped = []
        for p in expanded:
            if p in existing:
                continue
            ext = os.path.splitext(p)[1].lower()
            if ext not in EXT_TO_TYPE:
                skipped.append(os.path.basename(p))
                continue
            self._add_file_row(p, ext)
            added += 1

        if skipped and added == 0:
            preview = "\n".join(skipped[:10])
            if len(skipped) > 10:
                preview += f"\n… 共 {len(skipped)} 个文件"
            QMessageBox.information(
                self, "部分文件已跳过",
                f"以下文件格式不支持：\n\n{preview}"
            )

        self._update_convert_button()

    def _add_file_row(self, filepath: str, ext: str):
        row = self.file_table.rowCount()
        self.file_table.insertRow(row)

        name_item = QTableWidgetItem(os.path.basename(filepath))
        name_item.setData(Qt.UserRole, filepath)
        name_item.setToolTip(filepath)

        ptype = EXT_TO_TYPE[ext]
        type_item = QTableWidgetItem(TYPE_TO_EXT[ptype])
        type_item.setTextAlignment(Qt.AlignCenter)

        try:
            size_str = format_size(os.path.getsize(filepath))
        except OSError:
            size_str = "—"
        size_item = QTableWidgetItem(size_str)
        size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        status_item = QTableWidgetItem("待转换")
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setData(Qt.UserRole, "pending")

        self.file_table.setItem(row, 0, name_item)
        self.file_table.setItem(row, 1, type_item)
        self.file_table.setItem(row, 2, size_item)
        self.file_table.setItem(row, 3, status_item)

    def _clear_files(self):
        if self._thread is not None:
            return
        self.file_table.setRowCount(0)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("就绪")
        self._update_convert_button()

    def _update_convert_button(self):
        has_files = self.file_table.rowCount() > 0
        has_pwd = len(self.pwd_edit.text()) >= 4
        busy = self._thread is not None
        self.convert_btn.setEnabled(has_files and has_pwd and not busy)

    # ------------------------------------------------------------
    # 转换流程
    # ------------------------------------------------------------
    def _start_convert(self):
        if self._thread is not None:
            return

        password = self.pwd_edit.text()
        if len(password) < 4:
            QMessageBox.warning(self, "密码太短", "密码至少需要 4 位。")
            return

        output_dir = self.out_edit.text().strip() or None
        if output_dir and not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                QMessageBox.critical(self, "无法创建目录", str(e))
                return

        files = []
        for row in range(self.file_table.rowCount()):
            item = self.file_table.item(row, 0)
            if item:
                files.append((row, item.data(Qt.UserRole)))

        if not files:
            return

        for row, _ in files:
            status_item = self.file_table.item(row, 3)
            if status_item:
                status_item.setText("等待中…")
                status_item.setForeground(QColor("#7F849C"))
                status_item.setToolTip("")

        self._set_busy(True)
        self.progress.setRange(0, len(files))
        self.progress.setValue(0)
        self.progress.setFormat(f"0 / {len(files)}")

        from compat import QThread
        self._thread = QThread(self)
        self._worker = BatchWorker(files, password, output_dir=output_dir)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.finished.connect(self._on_finished)
        self._thread.start()

    def _set_busy(self, busy: bool):
        self.select_btn.setEnabled(not busy)
        self.select_dir_btn.setEnabled(not busy)
        self.clear_btn.setEnabled(not busy)
        self.pwd_edit.setEnabled(not busy)
        self.out_edit.setEnabled(not busy)
        self.out_btn.setEnabled(not busy)
        self.drop_area.setEnabled(not busy)
        self._update_convert_button()

    def _on_progress(self, index: int, total: int, filepath: str):
        self.progress.setValue(index)
        self.progress.setFormat(
            f"{index}/{total}  {os.path.basename(filepath)}"
        )

    def _on_file_done(self, row: int, status: str, message: str):
        status_item = self.file_table.item(row, 3)
        if status_item is None:
            return
        if status == "ok":
            status_item.setText("✓ 完成")
            status_item.setForeground(QColor("#A6E3A1"))
            status_item.setData(Qt.UserRole, "ok")
            status_item.setToolTip(message)
        else:
            status_item.setText("✗ 失败")
            status_item.setForeground(QColor("#F38BA8"))
            status_item.setData(Qt.UserRole, "failed")
            status_item.setToolTip(message)

    def _on_finished(self, success: int, fail: int, output_dir: str):
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
        self._thread = None
        self._worker = None

        self.progress.setValue(self.progress.maximum())
        self.progress.setFormat(f"完成：成功 {success} / 失败 {fail}")
        self._set_busy(False)

        if fail == 0:
            icon = QMessageBox.Information
            title = "转换完成"
        elif success == 0:
            icon = QMessageBox.Critical
            title = "转换失败"
        else:
            icon = QMessageBox.Warning
            title = "部分完成"

        msg = QMessageBox(self)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(f"成功 {success} 个，失败 {fail} 个。")
        if fail > 0:
            msg.setInformativeText("失败原因可将鼠标悬停在对应行的状态列查看。")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    def closeEvent(self, event):
        if self._thread is not None:
            ret = QMessageBox.question(
                self, "正在转换",
                "有转换任务正在进行，确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                event.ignore()
                return
            if self._worker:
                self._worker.cancel()
            self._thread.quit()
            self._thread.wait(3000)
        event.accept()