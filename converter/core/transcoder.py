"""单文件转换逻辑：普通文件 → SGMF 加密容器。

设计要点：
  - 保持原始字节不变，仅做加密封装（无损、无需转码）
  - 播放器解密后根据文件头自动识别真实格式（MP3/FLAC/WAV...）
  - 所有异常统一转为 ConvertResult，不向上抛
"""

import os
from dataclasses import dataclass
from typing import Optional

from sgmf_core import (
    EXT_TO_TYPE, TYPE_TO_EXT, PayloadType, write_sgmf_file,
)


@dataclass
class ConvertResult:
    """单次转换的结果。"""
    ok: bool
    source: str
    output: Optional[str] = None
    error: Optional[str] = None
    source_size: int = 0
    output_size: int = 0


def convert_file(source_path: str,
                 password: str,
                 output_dir: Optional[str] = None,
                 overwrite: bool = True) -> ConvertResult:
    """把一个普通文件加密转换为 SGMF 文件。

    Args:
        source_path: 源文件完整路径
        password:    加密密码（非空）
        output_dir:  输出目录；None 表示与源文件同目录
        overwrite:   目标已存在时是否覆盖

    Returns:
        ConvertResult
    """
    try:
        # ---------- 参数校验 ----------
        if not source_path or not os.path.isfile(source_path):
            return ConvertResult(False, source_path, error="源文件不存在")

        if not password or len(password) < 4:
            return ConvertResult(False, source_path, error="密码至少 4 位")

        ext = os.path.splitext(source_path)[1].lower()
        if ext not in EXT_TO_TYPE:
            return ConvertResult(False, source_path,
                                 error=f"不支持的格式: {ext or '(无扩展名)'}")

        ptype = EXT_TO_TYPE[ext]
        out_ext = TYPE_TO_EXT[ptype]

        # ---------- 计算输出路径 ----------
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            base = os.path.splitext(os.path.basename(source_path))[0]
            output_path = os.path.join(output_dir, base + out_ext)
        else:
            base = os.path.splitext(source_path)[0]
            output_path = base + out_ext

        # 防止输出覆盖源文件（理论上不会，因为扩展名不同）
        if os.path.abspath(output_path) == os.path.abspath(source_path):
            return ConvertResult(False, source_path, error="输出路径与源文件相同")

        if not overwrite and os.path.exists(output_path):
            return ConvertResult(
                False, source_path,
                error=f"已存在: {os.path.basename(output_path)}"
            )

        # ---------- 读取源文件 ----------
        source_size = os.path.getsize(source_path)
        if source_size == 0:
            return ConvertResult(False, source_path, error="源文件为空")

        with open(source_path, 'rb') as f:
            raw = f.read()

        # ---------- 加密写入 ----------
        write_sgmf_file(output_path, raw, ptype, password)

        output_size = os.path.getsize(output_path)
        return ConvertResult(
            True, source_path,
            output=output_path,
            source_size=source_size,
            output_size=output_size,
        )

    except PermissionError as e:
        return ConvertResult(False, source_path,
                             error=f"权限不足: {e.filename}")
    except OSError as e:
        return ConvertResult(False, source_path, error=f"IO 错误: {e}")
    except Exception as e:
        return ConvertResult(False, source_path,
                             error=f"{type(e).__name__}: {e}")