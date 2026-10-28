import sounddevice as sd
import numpy as np
import wave

SAMPLE_RATE = 16000
NUM_CHANNELS = 1
SAMPLE_TYPE = "int16"
SAMPLE_WIDTH_BYTES = 2
SILENCE_THRESHOLD = 300
MIC_FULL_SCALE = 2500     # a mic RMS this high or above counts as "fully loud" (speech is ~1300)


def rms(audio) -> float:
    return float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))


def save_wav(audio, path: str) -> str:
    with wave.open(path, "wb") as f:
        f.setnchannels(NUM_CHANNELS)
        f.setsampwidth(SAMPLE_WIDTH_BYTES)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(audio.tobytes())
    return path


def record_fixed(seconds: float, path: str = "recording.wav") -> str:
    samples = int(SAMPLE_RATE * seconds)
    audio = sd.rec(samples, samplerate=SAMPLE_RATE, channels=NUM_CHANNELS, dtype=SAMPLE_TYPE)
    sd.wait()
    return save_wav(audio, path)


def record_push_to_talk(path: str = "recording.wav", on_start=None, wait=input,
                        on_level=None) -> str | None:
    """Record between two key presses.

    `wait` is whatever blocks until the key press: input (Enter in the
    terminal) by default, or voice.py's wait_for_space (space in the face window).
    `on_level`, if given, is called with the mic loudness (0 to 1) for every
    chunk of audio, so the display can react to your voice live.
    """
    chunks = []

    def callback(indata, frames, time, status):
        if status:
            print(status)
        chunks.append(indata.copy())
        if on_level is not None:
            on_level(min(1.0, rms(indata) / MIC_FULL_SCALE))

    wait("Press Enter to start recording...")
    if on_start is not None:
        on_start()
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=NUM_CHANNELS,
        dtype=SAMPLE_TYPE,
        callback=callback,
    ):
        wait("Recording... press Enter to stop.")
    if on_level is not None:
        on_level(0.0)          # recording over: back to silence

    if not chunks:
        return None

    audio = np.concatenate(chunks)
    level = rms(audio)
    print(f"[debug] RMS: {level:.0f}")
    if level < SILENCE_THRESHOLD:
        return None
    return save_wav(audio, path)


if __name__ == "__main__":
    record_push_to_talk()