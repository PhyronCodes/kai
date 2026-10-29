"""Wake word test: listens to the mic and prints what Vosk hears.

Vosk is an offline speech recogniser. Instead of letting it hear any word,
we give it a tiny "grammar": the only phrases it is allowed to recognise.
Anything else comes out as [unk] (unknown). That makes it fast and makes
it a keyword spotter rather than a full transcriber.

Run it, say the candidate phrases and some normal sentences, and watch
what gets printed. Ctrl+C to stop.
"""
import json
import queue

import sounddevice as sd
from vosk import KaldiRecognizer, Model

MODEL_PATH = "models/vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
CHUNK = 4000            # samples per chunk: a quarter of a second

# The phrases Vosk may recognise. Any word Vosk doesn't know gets reported
# at startup as "missing in vocabulary", which tells us which spellings work.
CANDIDATES = ["hey kai", "hey kay", "okay kai", "hi kai", "kai", "kay"]
GRAMMAR = json.dumps(CANDIDATES + ["[unk]"])


def main() -> None:
    model = Model(MODEL_PATH)
    recogniser = KaldiRecognizer(model, SAMPLE_RATE, GRAMMAR)
    chunks: queue.Queue[bytes] = queue.Queue()

    def callback(indata, frames, time, status):
        chunks.put(bytes(indata))      # hand the audio to the main thread

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=CHUNK,
                           dtype="int16", channels=1, callback=callback):
        print("Listening... say 'hey KAI' and some normal sentences. Ctrl+C to stop.")
        while True:
            data = chunks.get()
            if recogniser.AcceptWaveform(data):          # end of an utterance
                text = json.loads(recogniser.Result())["text"]
                if text and text != "[unk]":
                    print("HEARD:", text)
            else:                                        # still mid-utterance
                partial = json.loads(recogniser.PartialResult())["partial"]
                if partial and partial != "[unk]":
                    print("  partial:", partial)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")