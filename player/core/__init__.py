"""播放器核心逻辑（无 UI 依赖）。"""

from .dispatcher import MediaInfo, open_sgmf, detect_actual_format
from .audio_player import AudioPlayer
from .image_viewer import load_image_pixmap
from .text_viewer import decode_text

__all__ = [
    'MediaInfo', 'open_sgmf', 'detect_actual_format',
    'AudioPlayer',
    'load_image_pixmap',
    'decode_text',
]