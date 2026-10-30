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

# Everything Vosk is allowed to recognise. With only a few words, Vosk forces
# ANY speech into the closest one, so a video saying "hey guys" could come out
# as "hey kai". DECOYS are common sound-alikes: they give that speech somewhere
# else to land. They never wake KAI; they just soak up near misses.
WAKE_WORDS = ["hey kai", "hey kay", "kay kai", "kai", "kay"]
DECOYS = [
    "hey", "okay", "hi", "high", "guy", "guys", "sky", "buy", "by", "bye",
    "cry", "try", "eye", "my", "why", "pay", "day", "say", "way", "they",
    "key", "car", "cake", "case", "kind", "kite", "night", "right", "like",
]
GRAMMAR_WORDS = WAKE_WORDS + DECOYS
WAKE_PAIRS = {("hey", "kai"), ("hey", "kay"), ("kay", "kai")}

# Two extra checks before KAI wakes:
STABLE_PARTIALS = 3      # a partial result must say "hey kai" this many chunks in a row (~0.4 s)
MIN_CONFIDENCE = 0.80    # a final result's wake words must be at least this confident (0 to 1)


def is_wake(text: str) -> bool:
    """True if two neighbouring words form a wake phrase, e.g. "hey kai"."""
    words = text.split()
    return any((a, b) in WAKE_PAIRS for a, b in zip(words, words[1:]))


def confident_wake(result: dict) -> bool:
    """For a final result: a wake pair whose words are both confident enough.
    result["result"] lists each word with Vosk's confidence, e.g.
    [{"word": "hey", "conf": 0.97}, {"word": "kai", "conf": 0.91}]"""
    words = result.get("result", [])
    for first, second in zip(words, words[1:]):
        if ((first["word"], second["word"]) in WAKE_PAIRS
                and min(first["conf"], second["conf"]) >= MIN_CONFIDENCE):
            return True
    return False


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
        recogniser.SetWords(True)              # include per-word confidence in final results
        stable = 0                             # how many partials in a row said "hey kai"
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
                    stable = 0
                    continue

                try:
                    data = chunks.get(timeout=0.1)
                except queue.Empty:
                    continue

                if recogniser.AcceptWaveform(data):
                    # End of an utterance: check the words AND their confidence
                    result = json.loads(recogniser.Result())
                    stable = 0
                    if confident_wake(result):
                        print(f"[debug] woke on: {result['text']!r}")
                        return "wake"
                else:
                    # Mid-utterance: wake early only if "hey kai" holds steady,
                    # so a one-chunk guess from background noise doesn't count
                    partial = json.loads(recogniser.PartialResult())["partial"]
                    stable = stable + 1 if is_wake(partial) else 0
                    if stable >= STABLE_PARTIALS:
                        print(f"[debug] woke on: {partial!r} (partial)")
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