"""SGMF 容器读写。

- write_sgmf_file()     原始字节 → 加密 SGMF 文件
- convert_to_sgmf()     普通文件 → SGMF 文件
- read_sgmf_header()    读取文件头（不解密）
- read_sgmf_payload()   读取并解密（返回 bytes）
- extract_to_file()     解密并写入普通文件
- is_sgmf_file()        快速判断是否为 SGMF 文件
"""

import os
from dataclasses import dataclass
from typing import Optional, Union

from .constants import (
    ALL_SGMF_EXTS, EXT_TO_TYPE, HEADER_SIZE, HEADER_STRUCT,
    MAGIC, TYPE_TO_EXT, VERSION, PayloadType,
)
from .crypto import decrypt_payload, encrypt_payload
from .utils import compute_sha256, get_extension, verify_hash


class InvalidFormatError(Exception):
    """文件不是合法的 SGMF 容器。"""
    pass


@dataclass(frozen=True)
class SgmfHeader:
    """SGMF 文件头信息。"""
    version: int
    payload_type: PayloadType
    flags: int
    digest: bytes
    iv: bytes
    salt: bytes
    encrypted_size: int

    @property
    def original_ext(self) -> str:
        """对应 SGMF 的扩展名。"""
        return TYPE_TO_EXT[self.payload_type]

    def to_dict(self) -> dict:
        return {
            'version': self.version,
            'type': int(self.payload_type),
            'type_name': self.payload_type.name,
            'flags': self.flags,
            'hash': self.digest.hex(),
            'iv': self.iv.hex(),
            'salt': self.salt.hex(),
            'encrypted_size': self.encrypted_size,
        }


# ============================== 写入 ==============================

def write_sgmf_file(output_path: str,
                    raw_data: bytes,
                    payload_type: Union[PayloadType, int],
                    password: str,
                    flags: int = 0) -> None:
    """加密并写出 SGMF 文件。

    Args:
        output_path: 输出路径
        raw_data: 原始文件字节
        payload_type: PayloadType 或对应的 int
        password: 密码
        flags: 预留标志位
    """
    if not isinstance(payload_type, PayloadType):
        try:
            payload_type = PayloadType(payload_type)
        except ValueError as e:
            raise ValueError(f"无效的 PayloadType: {payload_type}") from e

    if not isinstance(raw_data, (bytes, bytearray, memoryview)):
        raise TypeError("raw_data 必须是 bytes-like")
    raw_data = bytes(raw_data)

    # 1. 原始数据 SHA-256
    digest = compute_sha256(raw_data)

    # 2. 加密
    encrypted, iv, salt = encrypt_payload(raw_data, password)

    # 3. 打包头部
    header = HEADER_STRUCT.pack(
        MAGIC,
        VERSION,
        int(payload_type),
        flags & 0xFF,
        digest,
        iv,
        salt,
        len(encrypted),
    )
    if len(header) != HEADER_SIZE:
        raise RuntimeError("内部错误：文件头长度异常")

    # 4. 原子写入（先写临时文件，成功后 rename）
    dirpath = os.path.dirname(os.path.abspath(output_path)) or '.'
    if not os.path.isdir(dirpath):
        os.makedirs(dirpath, exist_ok=True)

    tmp_path = output_path + '.tmp'
    try:
        with open(tmp_path, 'wb') as f:
            f.write(header)
            f.write(encrypted)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, output_path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def convert_to_sgmf(source_path: str,
                    password: str,
                    output_path: Optional[str] = None) -> str:
    """从普通文件转换到 SGMF 文件。

    Returns:
        输出文件路径
    """
    ext = get_extension(source_path)
    if ext not in EXT_TO_TYPE:
        raise ValueError(f"不支持的源文件格式: {ext}")

    payload_type = EXT_TO_TYPE[ext]

    with open(source_path, 'rb') as f:
        raw = f.read()

    if output_path is None:
        base, _ = os.path.splitext(source_path)
        output_path = base + TYPE_TO_EXT[payload_type]

    write_sgmf_file(output_path, raw, payload_type, password)
    return output_path


# ============================== 读取 ==============================

def is_sgmf_file(filepath: str) -> bool:
    """快速检查文件头前 4 字节是否为 Magic。"""
    try:
        with open(filepath, 'rb') as f:
            return f.read(4) == MAGIC
    except OSError:
        return False


def read_sgmf_header(filepath: str) -> SgmfHeader:
    """只读取文件头，不解密载荷。"""
    with open(filepath, 'rb') as f:
        raw = f.read(HEADER_SIZE)
        if len(raw) < HEADER_SIZE:
            raise InvalidFormatError("文件过小，不是合法的 SGMF 文件")

        magic, version, ptype, flags, digest, iv, salt, enc_size = \
            HEADER_STRUCT.unpack(raw)

        if magic != MAGIC:
            raise InvalidFormatError(
                f"无效的 Magic Number: {magic!r}，期望 {MAGIC!r}"
            )
        if version != VERSION:
            raise InvalidFormatError(f"不支持的版本号: {version}")
        try:
            payload_type = PayloadType(ptype)
        except ValueError as e:
            raise InvalidFormatError(f"未知的 PayloadType: {ptype}") from e

        # 校验文件大小与声明一致
        actual_size = os.path.getsize(filepath)
        expected_size = HEADER_SIZE + enc_size
        if actual_size != expected_size:
            raise InvalidFormatError(
                f"文件大小不匹配: 期望 {expected_size} 字节, "
                f"实际 {actual_size} 字节"
            )

        return SgmfHeader(
            version=version,
            payload_type=payload_type,
            flags=flags,
            digest=digest,
            iv=iv,
            salt=salt,
            encrypted_size=enc_size,
        )


def read_sgmf_payload(filepath: str,
                      password: str,
                      verify: bool = True) -> bytes:
    """读取并解密 SGMF 文件。

    Args:
        filepath: SGMF 文件路径
        password: 密码
        verify: 是否用文件头中的 SHA-256 校验解密结果

    Returns:
        原始文件字节

    Raises:
        InvalidFormatError: 格式错误 / 校验失败
        DecryptionError: 密码错误
    """
    header = read_sgmf_header(filepath)

    with open(filepath, 'rb') as f:
        f.seek(HEADER_SIZE)
        encrypted = f.read(header.encrypted_size)
        if len(encrypted) != header.encrypted_size:
            raise InvalidFormatError("加密载荷被截断")

    raw = decrypt_payload(encrypted, password, header.iv, header.salt)

    if verify and not verify_hash(raw, header.digest):
        raise InvalidFormatError("SHA-256 校验失败：内容已被篡改")

    return raw


def extract_to_file(filepath: str,
                    password: str,
                    output_path: str,
                    verify: bool = True) -> str:
    """解密并写入到普通文件。"""
    raw = read_sgmf_payload(filepath, password, verify=verify)
    with open(output_path, 'wb') as f:
        f.write(raw)
    return output_path


def get_original_type(filepath: str) -> PayloadType:
    """获取 SGMF 文件内封装的原始内容类型。"""
    return read_sgmf_header(filepath).payload_type