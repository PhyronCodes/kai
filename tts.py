import sounddevice as sd
from piper import PiperVoice

VOICE_PATH = "voices/en_GB-alan-medium.onnx"

voice = PiperVoice.load(VOICE_PATH)


def speak(text: str) -> None:
    for chunk in voice.synthesize(text):
        sd.play(chunk.audio_int16_array, chunk.sample_rate)
        sd.wait()


if __name__ == "__main__":
    speak('Hello Tomás, I am KAI. I\'d say "maybe"; it depends.')