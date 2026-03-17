import base64
import json
import time
import threading
import numpy as np
import sounddevice as sd
import websocket
from core.config import Config
from core.asr.vad import init_vad

# 最大帧长度 262144 字节，base64 编码增加 33%
# 安全起见，每次发送不超过 1 秒音频 (32000 samples * 2 bytes = 64KB)
MAX_CHUNK_SAMPLES = 16000  # 1 秒


def run_asr(callback_func, vad_model_path: str = "models/silero_vad.onnx"):
    api_key = Config.QWEN_API_KEY
    url = f"wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen3-asr-flash-realtime"
    print(f"开始录音... 按 Ctrl+C 停止")

    vad, window_size = init_vad(vad_model_path, sample_rate=16000)
    print(f"[VAD] 已加载：{vad_model_path}, window_size={window_size}")

    def on_open(ws):
        event = {
            "event_id": "event_123",
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "input_audio_format": "pcm",
                "sample_rate": 16000,
                "input_audio_transcription": {"language": "zh"},
                "turn_detection": {"type": "none"},
            },
        }
        ws.send(json.dumps(event))
        print("[ASR] 会话已初始化")

    def on_message(ws, message):
        try:
            data = json.loads(message)
            event_type = data.get("type")
            if event_type == "conversation.item.input_audio_transcription.completed":
                transcript = data.get("transcript", "").strip()
                if transcript:
                    print(f"[ASR] {transcript}")
                    callback_func(transcript)
        except json.JSONDecodeError:
            pass

    def on_error(ws, error):
        print(f"WebSocket 错误：{error}")

    def on_close(ws, code, reason):
        print(f"连接关闭：{code} - {reason}")

    def send_audio_chunks(ws, audio_int16):
        """将音频分块发送，避免超过 WebSocket 帧限制"""
        for i in range(0, len(audio_int16), MAX_CHUNK_SAMPLES):
            chunk = audio_int16[i : i + MAX_CHUNK_SAMPLES]
            audio_b64 = base64.b64encode(chunk.tobytes()).decode("utf-8")
            event = {
                "event_id": f"event_{int(time.time() * 1000)}_{i}",
                "type": "input_audio_buffer.append",
                "audio": audio_b64,
            }
            try:
                ws.send(json.dumps(event))
            except Exception as e:
                print(f"[发送错误] {e}")
                return False
        return True

    def audio_callback(indata, frames, time_info, status):
        nonlocal audio_buffer
        if ws and ws.sock and ws.sock.connected:
            samples = indata.astype(np.float32) / 32768.0
            samples = samples.reshape(-1)
            audio_buffer = np.concatenate([audio_buffer, samples])

            while len(audio_buffer) >= window_size:
                vad.accept_waveform(audio_buffer[:window_size])
                audio_buffer = audio_buffer[window_size:]

            if not vad.empty():
                vad_samples = vad.front.samples
                vad.pop()
                # vad_samples 可能是 list，需要转换为 numpy array
                if isinstance(vad_samples, list):
                    vad_samples = np.array(vad_samples, dtype=np.float32)
                # 转换为 int16 PCM 格式
                vad_samples_int16 = (vad_samples * 32768.0).astype(np.int16)

                # 分块发送音频
                if send_audio_chunks(ws, vad_samples_int16):
                    # 提交音频缓冲区，触发识别
                    try:
                        ws.send(
                            json.dumps(
                                {
                                    "event_id": f"event_commit_{int(time.time() * 1000)}",
                                    "type": "input_audio_buffer.commit",
                                }
                            )
                        )
                    except Exception:
                        pass

    audio_buffer = np.array([], dtype=np.float32)

    headers = [f"Authorization: Bearer {api_key}", "OpenAI-Beta: realtime=v1"]
    ws = websocket.WebSocketApp(
        url,
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    threading.Thread(target=lambda: ws.run_forever(), daemon=True).start()
    time.sleep(1)

    with sd.InputStream(
        samplerate=16000,
        channels=1,
        dtype="int16",
        blocksize=3200,
        callback=audio_callback,
    ):
        try:
            sd.sleep(-1)
        except KeyboardInterrupt:
            print("\n停止录音...")
        finally:
            if ws and ws.sock and ws.sock.connected:
                ws.send(json.dumps({"event_id": "event_987", "type": "session.finish"}))
                time.sleep(0.5)
                ws.close()
