"""sgmf_core 功能自测。"""

import os
import tempfile
from sgmf_core import (
    PayloadType, convert_to_sgmf, read_sgmf_header, read_sgmf_payload,
    is_sgmf_file, format_size, DecryptionError, InvalidFormatError,
)


def test_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        # 构造一个假 MP3
        src = os.path.join(d, 'demo.mp3')
        original = b'FAKE_MP3_DATA_' * 100
        with open(src, 'wb') as f:
            f.write(original)

        # 转换
        out = convert_to_sgmf(src, 'p@ss123')
        assert os.path.exists(out), "输出文件不存在"
        assert out.endswith('.sgmic')

        # 检查文件识别
        assert is_sgmf_file(out)
        assert not is_sgmf_file(src)

        # 读取文件头
        header = read_sgmf_header(out)
        print(f"文件头: {header.to_dict()}")
        assert header.payload_type == PayloadType.AUDIO
        print(f"文件大小: {format_size(os.path.getsize(out))}")

        # 解密验证
        decrypted = read_sgmf_payload(out, 'p@ss123')
        assert decrypted == original, "往返数据不一致"

        # 错误密码必须失败
        try:
            read_sgmf_payload(out, 'wrong')
            raise AssertionError("错误密码应该失败")
        except DecryptionError:
            print("✓ 错误密码被正确拒绝")

        # 非 SGMF 文件必须失败
        try:
            read_sgmf_header(src)
            raise AssertionError("非 SGMF 文件不应通过")
        except InvalidFormatError:
            print("✓ 非 SGMF 文件被正确拒绝")

        print("✓ 所有测试通过")


if __name__ == '__main__':
    test_roundtrip()