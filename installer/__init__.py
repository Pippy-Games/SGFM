"""SGMF 文件关联注册模块。

提供四个扩展名与 SGMF 播放器的关联：
    .sgmic → SGMF.Audio
    .sgpim → SGMF.Video
    .sgwb  → SGMF.Text
    .sgtp  → SGMF.Image

全部操作在 HKCU（当前用户），无需管理员权限。
"""

from .register import (
    EXTENSIONS,
    PROG_IDS,
    FileAssociationError,
    check_associations,
    get_registered_player,
    register_all,
    register_one,
    unregister_all,
    unregister_one,
)

__all__ = [
    'EXTENSIONS',
    'PROG_IDS',
    'FileAssociationError',
    'register_one',
    'register_all',
    'unregister_one',
    'unregister_all',
    'check_associations',
    'get_registered_player',
]

__version__ = "0.1.0"