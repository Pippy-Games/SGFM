"""转换器核心逻辑（无 UI 依赖）。"""
from .transcoder import ConvertResult, convert_file
from .batch import BatchWorker

__all__ = ['ConvertResult', 'convert_file', 'BatchWorker']