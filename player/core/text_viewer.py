"""文本解码：自动探测编码。"""


# 尝试顺序：越靠前越优先
_ENCODINGS = ['utf-8-sig', 'utf-8', 'gb18030', 'big5', 'utf-16', 'latin-1']


def decode_text(raw: bytes) -> str:
    """把字节流解码为字符串。"""
    if not raw:
        return ''

    # UTF-8 BOM
    if raw[:3] == b'\xEF\xBB\xBF':
        try:
            return raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            pass

    # UTF-16 BOM
    if raw[:2] in (b'\xFF\xFE', b'\xFE\xFF'):
        try:
            return raw.decode('utf-16')
        except UnicodeDecodeError:
            pass

    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

    # 最后兜底
    return raw.decode('utf-8', errors='replace')