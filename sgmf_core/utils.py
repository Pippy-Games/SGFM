"""通用工具函数：哈希、路径、格式化。"""

import hashlib
import os


def compute_sha256(data: bytes) -> bytes:
    """计算 SHA-256 摘要（32 字节）。"""
    return hashlib.sha256(data).digest()


def verify_hash(data: bytes, expected_digest: bytes) -> bool:
    """常量时间比较 SHA-256 摘要。"""
    if len(expected_digest) != 32:
        return False
    return hashlib.sha256(data).digest() == expected_digest


def format_size(num_bytes: int) -> str:
    """人类可读的文件大小。"""
    units = ('B', 'KB', 'MB', 'GB', 'TB')
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == 'B':
                return f"{int(size)} B"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def get_extension(path: str) -> str:
    """返回小写扩展名（含点）。"""
    return os.path.splitext(path)[1].lower()


def change_extension(path: str, new_ext: str) -> str:
    """替换扩展名。"""
    if new_ext and not new_ext.startswith('.'):
        new_ext = '.' + new_ext
    base, _ = os.path.splitext(path)
    return base + new_ext


def ensure_dir(path: str) -> None:
    """确保文件所在目录存在。"""
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)