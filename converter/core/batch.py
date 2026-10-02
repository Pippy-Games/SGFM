"""后台批量转换工作线程。

使用 QThread + QObject 的标准模式：
    worker = BatchWorker(files, password)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)

所有信号在主线程（GUI 线程）中接收，可直接操作 UI。
"""

import os
import traceback
from typing import List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from .transcoder import convert_file


class BatchWorker(QObject):
    """批量转换任务。

    信号：
        progress(int index, int total, str filepath)
            每开始处理一个文件前发出

        file_done(int row, str status, str message)
            status 为 'ok' 或 'failed'

        finished(int success, int fail, str output_dir)
            全部完成时发出一次
    """

    progress  = Signal(int, int, str)
    file_done = Signal(int, str, str)
    finished  = Signal(int, int, str)

    def __init__(self,
                 files: List[Tuple[int, str]],
                 password: str,
                 output_dir: Optional[str] = None,
                 overwrite: bool = True):
        """
        Args:
            files: [(表格行号, 文件路径), ...]
            password: 加密密码
            output_dir: 统一输出目录；None 表示各自与源文件同目录
            overwrite: 是否覆盖已存在的目标
        """
        super().__init__()
        self.files = list(files)
        self.password = password
        self.output_dir = output_dir
        self.overwrite = overwrite
        self._cancelled = False

    def cancel(self):
        """请求取消（在下一个文件前生效）。"""
        self._cancelled = True

    def run(self):
        """由 QThread.started 信号触发，在工作线程中执行。"""
        total = len(self.files)
        success = 0
        fail = 0
        last_dir = self.output_dir or ""

        try:
            for idx, (row, filepath) in enumerate(self.files):
                if self._cancelled:
                    break

                self.progress.emit(idx, total, filepath)

                try:
                    result = convert_file(
                        filepath,
                        self.password,
                        output_dir=self.output_dir,
                        overwrite=self.overwrite,
                    )
                except Exception as e:
                    # convert_file 理论上不会抛异常，这里是双保险
                    result = None
                    err_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
                    fail += 1
                    self.file_done.emit(row, "failed", err_msg)
                    continue

                if result.ok:
                    success += 1
                    self.file_done.emit(row, "ok", result.output or "")
                    if not last_dir and result.output:
                        last_dir = os.path.dirname(result.output)
                else:
                    fail += 1
                    self.file_done.emit(row, "failed", result.error or "未知错误")

        except Exception as e:
            # 极端情况：整个批次崩了
            err = f"批处理异常: {type(e).__name__}: {e}"
            for row, _ in self.files:
                self.file_done.emit(row, "failed", err)
            fail = total
            success = 0

        self.finished.emit(success, fail, last_dir or "—")