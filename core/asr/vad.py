"""
VAD (Voice Activity Detector) 模块

使用 sherpa-onnx 实现本地语音活动检测

安装: uv pip install sherpa-onnx
"""

import numpy as np

try:
    import sherpa_onnx

    SHERPA_ONNX_AVAILABLE = True
except ImportError:
    SHERPA_ONNX_AVAILABLE = False
    print("警告：sherpa-onnx 未安装，VAD 功能不可用")
    print("安装：uv pip install sherpa-onnx")


def init_vad(model_path: str, sample_rate: int = 16000):
    """
    初始化 VAD (Voice Activity Detector)

    Args:
        model_path: Silero VAD 模型路径 (.onnx)
        sample_rate: 采样率

    Returns:
        vad: VoiceActivityDetector 实例
        window_size: 每次需要输入的样本数

    Raises:
        ImportError: 如果 sherpa-onnx 未安装
    """
    if not SHERPA_ONNX_AVAILABLE:
        raise ImportError("sherpa-onnx 未安装，请先安装：uv pip install sherpa-onnx")

    vad_config = sherpa_onnx.VadModelConfig()
    vad_config.silero_vad.model = model_path
    vad_config.silero_vad.min_silence_duration = 0.25
    vad_config.silero_vad.min_speech_duration = 0.25
    vad_config.silero_vad.threshold = 0.6
    vad_config.sample_rate = sample_rate

    if not vad_config.validate():
        raise ValueError("Invalid VAD config")

    window_size = vad_config.silero_vad.window_size
    vad = sherpa_onnx.VoiceActivityDetector(vad_config, buffer_size_in_seconds=100)

    return vad, window_size


def process_audio_with_vad(vad, audio_data, window_size):
    """
    将音频数据送入 VAD 处理

    Args:
        vad: VoiceActivityDetector 实例
        audio_data: 音频数据 (numpy array, float32)
        window_size: 窗口大小

    Returns:
        segments: 检测到的语音片段列表
        buffer: 剩余未处理的音频数据
    """
    if not SHERPA_ONNX_AVAILABLE:
        raise ImportError("sherpa-onnx 未安装")

    buffer = audio_data

    while len(buffer) >= window_size:
        vad.accept_waveform(buffer[:window_size])
        buffer = buffer[window_size:]

    segments = []
    while not vad.empty():
        vad_samples = vad.front.samples
        vad.pop()
        segments.append(vad_samples)

    return segments, buffer
