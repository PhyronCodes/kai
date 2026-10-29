"""Wake word: waits until someone says "hey KAI" (or presses space).

Uses Vosk, an offline speech recogniser, restricted to a tiny grammar of
wake phrases. Anything else it hears comes out as [unk], so it is quick
and can listen all day without using the internet.

If Vosk or its model isn't installed (e.g. on the Mac), it falls back to
waiting for the space bar only, so KAI still works everywhere.
"""
import json
import os
import queue

import sounddevice as sd

try:
    from vosk import KaldiRecognizer, Model, SetLogLevel
    SetLogLevel(-1)                    # hide Vosk's startup log spam
except ImportError:
    Model = None

MODEL_PATH = "models/vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
CHUNK = 2000                           # an eighth of a second of audio

# Everything Vosk is allowed to recognise. Single "kai"/"kay" are in the grammar
# so they don't get mistaken for "hey kai", but on their own they don't wake KAI.
GRAMMAR_WORDS = ["hey kai", "hey kay", "kay kai", "okay kai", "hi kai", "kai", "kay"]
WAKE_PAIRS = {("hey", "kai"), ("hey", "kay"), ("kay", "kai"), ("okay", "kai"), ("hi", "kai")}


def is_wake(text: str) -> bool:
    """True if two neighbouring words form a wake phrase, e.g. "hey kai"."""
    words = text.split()
    return any((a, b) in WAKE_PAIRS for a, b in zip(words, words[1:]))


class WakeWord:
    def __init__(self) -> None:
        self.model = None
        if Model is not None and os.path.isdir(MODEL_PATH):
            self.model = Model(MODEL_PATH)        # load once: it takes a second
        print("Wake word:", "on (say 'hey KAI')" if self.model else "off (space only)")

    def wait(self, face, on_idle=None) -> str:
        """Block until "hey KAI" is heard or space is pressed.
        Returns "wake" or "space". on_idle() is called regularly; if it returns
        True (it spoke, e.g. the daily briefing), anything heard meanwhile is ignored."""
        if self.model is None:
            return self._wait_space_only(face, on_idle)

        recogniser = KaldiRecognizer(self.model, SAMPLE_RATE, json.dumps(GRAMMAR_WORDS + ["[unk]"]))
        chunks: queue.Queue[bytes] = queue.Queue()

        def callback(indata, frames, time, status):
            chunks.put(bytes(indata))

        presses_before = face.space_presses
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=CHUNK,
                               dtype="int16", channels=1, callback=callback):
            while True:
                if not face.running:
                    raise EOFError
                if face.space_presses != presses_before:
                    return "space"
                if on_idle is not None and on_idle():
                    # KAI just spoke: forget what the mic heard during that
                    recogniser.Reset()
                    while not chunks.empty():
                        chunks.get_nowait()
                    presses_before = face.space_presses
                    continue

                try:
                    data = chunks.get(timeout=0.1)
                except queue.Empty:
                    continue

                # Check partial results too, so KAI wakes as soon as the phrase
                # is said, without waiting for you to stop talking
                if recogniser.AcceptWaveform(data):
                    text = json.loads(recogniser.Result())["text"]
                else:
                    text = json.loads(recogniser.PartialResult())["partial"]
                if is_wake(text):
                    return "wake"

    def _wait_space_only(self, face, on_idle=None) -> str:
        import time
        presses_before = face.space_presses
        while face.space_presses == presses_before:
            if not face.running:
                raise EOFError
            if on_idle is not None and on_idle():
                presses_before = face.space_presses
            time.sleep(0.02)
        return "space"