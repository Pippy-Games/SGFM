"""SGMF 文件格式核心库。

统一导出所有公共 API，供转换器、播放器、测试直接调用。

用法示例：

    from sgmf_core import (
        write_sgmf_file, read_sgmf_payload,
        convert_to_sgmf, PayloadType,
    )

    # 加密
    convert_to_sgmf('song.mp3', 'mypassword')
    # → 生成 song.sgmic

    # 解密
    raw = read_sgmf_payload('song.sgmic', 'mypassword')
"""

from .constants import (
    ALL_SGMF_EXTS,
    BLOCK_BITS,
    EXT_TO_TYPE,
    HEADER_SIZE,
    HEADER_STRUCT,
    IV_LENGTH,
    KEY_LENGTH,
    MAGIC,
    PBKDF2_ITERATIONS,
    PayloadType,
    SALT_LENGTH,
    TYPE_TO_EXT,
    VERSION,
)
from .crypto import (
    DecryptionError,
    decrypt_payload,
    derive_key,
    encrypt_payload,
)
from .format import (
    InvalidFormatError,
    SgmfHeader,
    convert_to_sgmf,
    extract_to_file,
    get_original_type,
    is_sgmf_file,
    read_sgmf_header,
    read_sgmf_payload,
    write_sgmf_file,
)
from .utils import (
    change_extension,
    compute_sha256,
    ensure_dir,
    format_size,
    get_extension,
    verify_hash,
)

__version__ = "0.1.0"

__all__ = [
    # constants
    'MAGIC', 'VERSION', 'HEADER_SIZE', 'HEADER_STRUCT',
    'PayloadType', 'EXT_TO_TYPE', 'TYPE_TO_EXT', 'ALL_SGMF_EXTS',
    'PBKDF2_ITERATIONS', 'KEY_LENGTH', 'SALT_LENGTH',
    'IV_LENGTH', 'BLOCK_BITS',
    # crypto
    'derive_key', 'encrypt_payload', 'decrypt_payload', 'DecryptionError',
    # format
    'SgmfHeader', 'InvalidFormatError',
    'write_sgmf_file', 'convert_to_sgmf',
    'read_sgmf_header', 'read_sgmf_payload',
    'extract_to_file', 'is_sgmf_file', 'get_original_type',
    # utils
    'compute_sha256', 'verify_hash', 'format_size',
    'get_extension', 'change_extension', 'ensure_dir',
]