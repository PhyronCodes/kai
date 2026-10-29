import multiprocessing as mp
import string
import sys
import time
from datetime import datetime

from audio import record_until_silence
from bar import run_bar
from face import FaceControl
from script import Assistant, GOODBYE
from stt import transcribe
from tasks import briefing
from tts import speak
from wake import WakeWord


BRIEFING_HOUR = 9      # the daily briefing happens at (or after) 9:00

QUIT_PHRASES = {"quit", "exit", "stop", "goodbye", "bye", "bye kai", "goodbye kai"}


def is_quit(message: str) -> bool:
    """True if the whole message is just a quit phrase, e.g. "Goodbye, KAI."
    Punctuation and capitals are ignored. A longer sentence that merely
    contains "stop" (like "stop reminding me") doesn't count."""
    cleaned = message.lower().translate(str.maketrans("", "", string.punctuation))
    return " ".join(cleaned.split()) in QUIT_PHRASES


class DailyBriefing:
    """Says what's due once a day: at startup, and at BRIEFING_HOUR if KAI is
    left running. Remembers the date of the last one so it never repeats."""

    def __init__(self, face: FaceControl, set_level) -> None:
        self.face = face
        self.set_level = set_level
        self.last_date = None

    def is_due(self) -> bool:
        now = datetime.now()
        return now.hour >= BRIEFING_HOUR and self.last_date != now.date()

    def give(self) -> None:
        """Speak the briefing (if anything is due) and mark today as done.
        A startup briefing before BRIEFING_HOUR doesn't count, so the 9:00
        one still happens later."""
        if datetime.now().hour >= BRIEFING_HOUR:
            self.last_date = datetime.now().date()
        text = briefing()
        if text is None:
            return
        print("KAI: " + text)
        self.face.state = "speaking"
        speak(text, on_level=self.set_level)
        self.face.state = "idle"


def voice_loop(kai: Assistant, face: FaceControl) -> None:
    """Record, transcribe, think and speak, telling the face what KAI is doing."""
    def set_level(level: float) -> None:
        face.loudness = level

    daily = DailyBriefing(face, set_level)
    daily.give()       # startup briefing
    wake = WakeWord()

    def briefing_if_due() -> bool:
        """Called while KAI waits for the wake word. True if it spoke."""
        if daily.is_due():
            daily.give()
            return True
        return False

    while face.running:
        face.state = "idle"
        print("Waiting for 'hey KAI' (or space)...")
        wake.wait(face, on_idle=briefing_if_due)

        # Listening: stops by itself when you go quiet, or early with space
        face.state = "listening"
        presses_at_start = face.space_presses
        path = record_until_silence(
            on_level=set_level,      # the bar reacts to your voice while you talk
            should_stop=lambda: face.space_presses != presses_at_start,
        )
        if path is None:
            continue

        face.state = "thinking"
        user_message = transcribe(path)
        if not user_message:
            continue
        print("You: " + user_message)

        if is_quit(user_message):
            face.state = "speaking"
            speak(GOODBYE, on_level=set_level)
            face.running = False      # closes the face and ends the loop
            break

        response = kai.ask(user_message)
        print("KAI: " + response)

        face.state = "speaking"
        speak(response, on_level=set_level)


def main() -> None:
    fullscreen = "--fullscreen" in sys.argv     # python voice.py --fullscreen
    kai = Assistant()
    face = FaceControl()

    # The face runs as its own process: a separate Python, so drawing the face
    # can never slow down recording or playback
    face_process = mp.Process(target=run_bar, args=(face, fullscreen), daemon=True)
    face_process.start()

    try:
        voice_loop(kai, face)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        face.running = False          # tells the face window to close
        face_process.join(timeout=2)
        print("\nKAI: " + GOODBYE)


if __name__ == "__main__":
    main()