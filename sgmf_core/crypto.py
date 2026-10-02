"""AES-256-CBC + PBKDF2-HMAC-SHA256 加解密模块。

设计原则：
  - 每次加密使用全新的随机 Salt 和 IV
  - 密钥由 PBKDF2 从密码 + Salt 派生，不做持久化
  - 密码错误时通过 PKCS7 反填充失败识别
"""

import os
from typing import Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .constants import (
    BLOCK_BITS, IV_LENGTH, KEY_LENGTH,
    PBKDF2_ITERATIONS, SALT_LENGTH,
)


class DecryptionError(Exception):
    """解密失败：密码错误或文件被篡改。"""
    pass


def _to_bytes(password) -> bytes:
    """统一把密码转为 bytes。"""
    if isinstance(password, bytes):
        pw = password
    elif isinstance(password, str):
        pw = password.encode('utf-8')
    else:
        raise TypeError(f"密码类型不支持: {type(password).__name__}")
    if not pw:
        raise ValueError("密码不能为空")
    return pw


def derive_key(password, salt: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256 派生 32 字节 AES 密钥。"""
    if len(salt) != SALT_LENGTH:
        raise ValueError(f"Salt 长度必须为 {SALT_LENGTH} 字节")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend(),
    )
    return kdf.derive(_to_bytes(password))


def encrypt_payload(data: bytes, password) -> Tuple[bytes, bytes, bytes]:
    """AES-256-CBC 加密。

    返回:
        (encrypted, iv, salt)
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data 必须是 bytes-like")

    salt = os.urandom(SALT_LENGTH)
    iv = os.urandom(IV_LENGTH)
    key = derive_key(password, salt)

    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend(),
    )
    encryptor = cipher.encryptor()

    padder = padding.PKCS7(BLOCK_BITS).padder()
    padded = padder.update(bytes(data)) + padder.finalize()

    encrypted = encryptor.update(padded) + encryptor.finalize()
    return encrypted, iv, salt


def decrypt_payload(encrypted: bytes, password,
                    iv: bytes, salt: bytes) -> bytes:
    """AES-256-CBC 解密。

    Raises:
        DecryptionError: 密码错误或数据损坏
        ValueError: 参数长度错误
    """
    if len(iv) != IV_LENGTH:
        raise ValueError(f"IV 长度必须为 {IV_LENGTH} 字节")
    if len(salt) != SALT_LENGTH:
        raise ValueError(f"Salt 长度必须为 {SALT_LENGTH} 字节")
    if not encrypted:
        raise ValueError("加密载荷为空")
    if len(encrypted) % 16 != 0:
        raise ValueError("加密载荷长度不是 16 的倍数")

    key = derive_key(password, salt)
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend(),
    )
    decryptor = cipher.decryptor()

    try:
        padded = decryptor.update(encrypted) + decryptor.finalize()
        unpadder = padding.PKCS7(BLOCK_BITS).unpadder()
        return unpadder.update(padded) + unpadder.finalize()
    except ValueError as e:
        # PKCS7 反填充失败 → 大概率是密码错误
        raise DecryptionError("密码错误或文件已损坏") from e