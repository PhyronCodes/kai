import time
import wave

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
NUM_CHANNELS = 1
SAMPLE_TYPE = "int16"
SAMPLE_WIDTH_BYTES = 2
SILENCE_THRESHOLD = 300
SILENCE_SECONDS = 1.2     # stop recording after this long without speech
NO_SPEECH_TIMEOUT = 5     # give up if nobody starts talking within this long
MAX_SECONDS = 20          # never record longer than this
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


def record_until_silence(path: str = "recording.wav", on_level=None,
                         should_stop=None) -> str | None:
    """Record until you stop talking. Used after the wake word, since there's
    no second key press to end the recording.

    Each small chunk of audio is checked: louder than SILENCE_THRESHOLD counts as
    speech. Recording stops once you've spoken and then gone quiet for
    SILENCE_SECONDS, or when should_stop() returns True (e.g. space pressed).
    Returns None if you never said anything."""
    chunks = []
    heard = {"speech": False, "last_loud": time.monotonic()}

    def callback(indata, frames, time_info, status):
        if status:
            print(status)
        chunks.append(indata.copy())
        level = rms(indata)
        if on_level is not None:
            on_level(min(1.0, level / MIC_FULL_SCALE))
        if level >= SILENCE_THRESHOLD:
            heard["speech"] = True
            heard["last_loud"] = time.monotonic()

    start = time.monotonic()
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=NUM_CHANNELS, dtype=SAMPLE_TYPE,
                        blocksize=SAMPLE_RATE // 10, callback=callback):   # 0.1 s chunks
        while True:
            time.sleep(0.05)
            now = time.monotonic()
            if should_stop is not None and should_stop():
                break
            if heard["speech"] and now - heard["last_loud"] > SILENCE_SECONDS:
                break                     # you've finished talking
            if not heard["speech"] and now - start > NO_SPEECH_TIMEOUT:
                break                     # woken by mistake, or you changed your mind
            if now - start > MAX_SECONDS:
                break

    if on_level is not None:
        on_level(0.0)
    if not heard["speech"] or not chunks:
        return None
    audio = np.concatenate(chunks)
    print(f"[debug] RMS: {rms(audio):.0f}, {len(audio) / SAMPLE_RATE:.1f} s")
    return save_wav(audio, path)


if __name__ == "__main__":
    record_push_to_talk()