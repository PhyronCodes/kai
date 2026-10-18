import time
from typing import Callable

import numpy as np
import sounddevice as sd
from piper import PiperVoice

VOICE_PATH = "voices/en_GB-alan-medium.onnx"
LEVEL_STEP = 1 / 30        # check the loudness 30 times a second, like the face
LEVEL_FULL_SCALE = 6000    # an RMS this high or above counts as "fully loud"

voice = PiperVoice.load(VOICE_PATH)


def speak(text: str, on_level: Callable[[float], None] | None = None) -> None:
    """Say the text out loud. If on_level is given, it is called about 30 times
    a second with how loud the voice is right now (0-1), to drive the mouth."""
    for chunk in voice.synthesize(text):
        audio = chunk.audio_int16_array
        rate = chunk.sample_rate
        # latency="high" gives a bigger audio buffer, so playback survives
        # brief pauses while the face is being drawn on the other thread
        sd.play(audio, rate, latency="high")

        if on_level is not None:
            step = int(rate * LEVEL_STEP)
            start = time.perf_counter()
            for i in range(0, len(audio), step):
                window = audio[i:i + step].astype(np.float64)
                rms = np.sqrt(np.mean(window ** 2))
                on_level(min(rms / LEVEL_FULL_SCALE, 1.0))
                # wait until this window's moment in the audio, so mouth and voice stay in sync
                target_time = start + (i + step) / rate
                time.sleep(max(0.0, target_time - time.perf_counter()))
            on_level(0.0)

        sd.wait()


if __name__ == "__main__":
    speak('Hello Tomás, I am KAI. I\'d say "maybe"; it depends.')