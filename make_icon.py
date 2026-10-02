"""生成 SGMF 图标文件。

运行：
    py -3.8 make_icon.py

产物：
    assets/icon.ico           主图标
    assets/icon_audio.ico     音频
    assets/icon_video.ico     视频
    assets/icon_text.ico      文本
    assets/icon_image.ico     图片
"""

import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)


def make_icon(text, bg_color="#7C5CFC", fg_color="#FFFFFF", size=256):
    """画一个圆角方形图标，中间一个字符。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆角方底
    margin = size // 16
    radius = size // 5
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=bg_color,
    )

    # 字符
    font = None
    for name in ("arialbd.ttf", "arial.ttf", "msyhbd.ttc", "msyh.ttc"):
        try:
            font = ImageFont.truetype(name, size // 2)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        ((size - tw) / 2 - bbox[0],
         (size - th) / 2 - bbox[1] - size // 25),
        text, fill=fg_color, font=font,
    )
    return img


def save_ico(img, path, sizes=(16, 24, 32, 48, 64, 128, 256)):
    img.save(path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"  [OK] {path}")


def main():
    print(f"生成图标到: {ASSETS}")

    # 主图标：SG 字母
    save_ico(make_icon("SG", "#7C5CFC"),
             os.path.join(ASSETS, "icon.ico"))

    # 类型图标
    save_ico(make_icon("♪", "#F9A825"),
             os.path.join(ASSETS, "icon_audio.ico"))
    save_ico(make_icon("▶", "#E53935"),
             os.path.join(ASSETS, "icon_video.ico"))
    save_ico(make_icon("T", "#43A047"),
             os.path.join(ASSETS, "icon_text.ico"))
    save_ico(make_icon("◨", "#1E88E5"),
             os.path.join(ASSETS, "icon_image.ico"))

    print("完成。")


if __name__ == "__main__":
    main()