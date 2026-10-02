"""SGMF 文件格式常量定义。

文件头布局（共 76 字节，小端序）：
    偏移   长度   字段
    0x00   4      Magic Number  b'SGMF'
    0x04   2      Version       uint16
    0x06   1      PayloadType   uint8
    0x07   1      Flags         uint8
    0x08   32     原始 SHA-256   bytes
    0x28   16     AES IV        bytes
    0x38   16     PBKDF2 Salt   bytes
    0x48   4      EncryptedSize uint32
    0x4C   N      Encrypted Payload (AES-256-CBC, PKCS7)
"""

import struct
from enum import IntEnum


# ============ 魔数与版本 ============
MAGIC = b'SGMF'
VERSION = 1


# ============ 文件头二进制结构 ============
# <   : 小端序
# 4s  : Magic (4 字节)
# H   : Version (uint16)
# B   : PayloadType (uint8)
# B   : Flags (uint8)
# 32s : SHA-256 digest (32 字节)
# 16s : IV (16 字节)
# 16s : Salt (16 字节)
# I   : Encrypted payload size (uint32)
HEADER_STRUCT = struct.Struct('<4sHBB32s16s16sI')
HEADER_SIZE = HEADER_STRUCT.size  # 76


# ============ Payload 类型 ============
class PayloadType(IntEnum):
    """内容类型枚举。"""
    AUDIO = 0x01
    VIDEO = 0x02
    TEXT  = 0x03
    IMAGE = 0x04


# ============ 扩展名 ↔ 类型映射 ============
# 源文件扩展名（小写）→ PayloadType
EXT_TO_TYPE = {
    '.mp3':  PayloadType.AUDIO,
    '.ogg':  PayloadType.AUDIO,
    '.flac': PayloadType.AUDIO,
    '.wav':  PayloadType.AUDIO,
    '.mp4':  PayloadType.VIDEO,
    '.txt':  PayloadType.TEXT,
    '.jpg':  PayloadType.IMAGE,
    '.jpeg': PayloadType.IMAGE,
    '.png':  PayloadType.IMAGE,
}

# PayloadType → 输出扩展名
TYPE_TO_EXT = {
    PayloadType.AUDIO: '.sgmic',
    PayloadType.VIDEO: '.sgpim',
    PayloadType.TEXT:  '.sgwb',
    PayloadType.IMAGE: '.sgtp',
}

# 所有合法 SGMF 扩展名
ALL_SGMF_EXTS = tuple(TYPE_TO_EXT.values())

# 预设加密参数
PBKDF2_ITERATIONS = 100_000
KEY_LENGTH        = 32    # AES-256
SALT_LENGTH       = 16
IV_LENGTH         = 16
BLOCK_BITS        = 128   # PKCS7 块大小