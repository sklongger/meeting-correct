import sounddevice as sd
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult

from core.config import Config


class Callback(RecognitionCallback):
    def __init__(self):
        self.result_callback = None

    def on_event(self, result):
        sentence = result.get_sentence()
        if RecognitionResult.is_sentence_end(sentence):
            text = sentence.get("text", "").strip()
            if text and self.result_callback:
                self.result_callback(text)


def run_asr(callback_func):
    import dashscope

    dashscope.api_key = Config.QWEN_API_KEY

    callback = Callback()
    callback.result_callback = callback_func

    recognition = Recognition(
        model="paraformer-realtime-v2",
        format="pcm",
        sample_rate=16000,
        callback=callback,
    )

    print("开始录音... 按 Ctrl+C 停止")

    def audio_callback(indata, frames, time, status):
        recognition.send_audio_frame(indata.tobytes())

    recognition.start()

    with sd.InputStream(
        samplerate=16000,
        channels=1,
        dtype="int16",
        blocksize=3200,
        callback=audio_callback,
    ):
        sd.sleep(-1)
