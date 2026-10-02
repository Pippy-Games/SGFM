"""SGMF 文件解密 + 内容格式识别 + 分派。

流程：
    open_sgmf(path, password)
        ├─ read_sgmf_header()  校验 Magic/版本/类型
        ├─ read_sgmf_payload() 解密 + SHA-256 校验
        └─ detect_actual_format() 从原始字节的魔数判断真实格式
"""

from dataclasses import dataclass
from typing import Optional

from sgmf_core import (
    DecryptionError, InvalidFormatError, PayloadType,
    is_sgmf_file, read_sgmf_header, read_sgmf_payload,
)


# ---------- 内容魔数表 ----------
# (格式名, 匹配函数)
def _match_mp3(b: bytes) -> bool:
    if len(b) < 3:
        return False
    if b[:3] == b'ID3':
        return True
    # MPEG Audio Frame Sync: 0xFF 0xE0 mask
    if b[0] == 0xFF and (b[1] & 0xE0) == 0xE0:
        return True
    return False


def _match_ogg(b: bytes) -> bool:
    return b[:4] == b'OggS'


def _match_flac(b: bytes) -> bool:
    return b[:4] == b'fLaC'


def _match_wav(b: bytes) -> bool:
    return len(b) >= 12 and b[:4] == b'RIFF' and b[8:12] == b'WAVE'


def _match_mp4(b: bytes) -> bool:
    return len(b) >= 12 and b[4:8] == b'ftyp'


def _match_webm(b: bytes) -> bool:
    return b[:4] == b'\x1A\x45\xDF\xA3'


def _match_jpeg(b: bytes) -> bool:
    return b[:3] == b'\xFF\xD8\xFF'


def _match_png(b: bytes) -> bool:
    return b[:8] == b'\x89PNG\r\n\x1a\n'


def _match_gif(b: bytes) -> bool:
    return b[:6] in (b'GIF87a', b'GIF89a')


def _match_bmp(b: bytes) -> bool:
    return b[:2] == b'BM'


def _match_webp(b: bytes) -> bool:
    return len(b) >= 12 and b[:4] == b'RIFF' and b[8:12] == b'WEBP'


# 顺序很重要，先匹配更具体的
_MAGIC_TABLE = [
    # 音频
    ('mp3',  _match_mp3),
    ('ogg',  _match_ogg),
    ('flac', _match_flac),
    ('wav',  _match_wav),
    # 视频
    ('mp4',  _match_mp4),
    ('webm', _match_webm),
    ('ogg',  _match_ogg),   # ogv 也是 OggS
    # 图片
    ('jpeg', _match_jpeg),
    ('png',  _match_png),
    ('gif',  _match_gif),
    ('bmp',  _match_bmp),
    ('webp', _match_webp),
]


def detect_actual_format(raw: bytes) -> str:
    """从原始字节的魔数判断真实格式。

    Returns:
        格式名（如 'mp3' / 'mp4' / 'jpeg' / 'png'），未知返回 'bin'
    """
    if not raw:
        return 'bin'
    for name, matcher in _MAGIC_TABLE:
        try:
            if matcher(raw):
                return name
        except Exception:
            continue
    return 'bin'


@dataclass
class MediaInfo:
    """解密后的媒体信息。"""
    payload_type: PayloadType
    actual_format: str
    raw: bytes
    source_path: str

    @property
    def size(self) -> int:
        return len(self.raw)


# ---------- 主入口 ----------

def open_sgmf(filepath: str, password: str) -> MediaInfo:
    """打开 SGMF 文件：解密 + 识别真实格式。

    Raises:
        InvalidFormatError: 文件不是合法 SGMF / 校验失败
        DecryptionError:    密码错误
    """
    if not is_sgmf_file(filepath):
        raise InvalidFormatError("不是 SGMF 文件")

    header = read_sgmf_header(filepath)
    raw = read_sgmf_payload(filepath, password, verify=True)
    fmt = detect_actual_format(raw)

    return MediaInfo(
        payload_type=header.payload_type,
        actual_format=fmt,
        raw=raw,
        source_path=filepath,
    )