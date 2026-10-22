import multiprocessing as mp
import string
import time
from datetime import datetime

from audio import record_push_to_talk
from bar import run_bar
from face import FaceControl
from script import Assistant, GOODBYE
from stt import transcribe
from tasks import briefing
from tts import speak


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


def wait_for_space(face: FaceControl, prompt: str, daily: DailyBriefing | None = None) -> None:
    """Block until space is pressed in the face window (used instead of input).
    While KAI is idle, this is also where the daily briefing gets its chance."""
    print(prompt.replace("Enter", "space"))
    presses_before = face.space_presses
    while face.space_presses == presses_before:
        if not face.running:
            raise EOFError        # window closed: main() shuts everything down
        if daily is not None and face.state == "idle" and daily.is_due():
            daily.give()
            presses_before = face.space_presses   # ignore presses during the briefing
        time.sleep(0.02)


def voice_loop(kai: Assistant, face: FaceControl) -> None:
    """Record, transcribe, think and speak, telling the face what KAI is doing."""
    def set_level(level: float) -> None:
        face.loudness = level

    daily = DailyBriefing(face, set_level)
    daily.give()       # startup briefing

    def wait(prompt: str = "") -> None:
        # face.state is "idle" only while waiting to start, never mid-recording,
        # so the briefing can't interrupt you while you're talking
        wait_for_space(face, prompt, daily)

    while face.running:
        face.state = "idle"
        path = record_push_to_talk(
            on_start=lambda: setattr(face, "state", "listening"),
            wait=wait,
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
    kai = Assistant()
    face = FaceControl()

    # The face runs as its own process: a separate Python, so drawing the face
    # can never slow down recording or playback
    face_process = mp.Process(target=run_bar, args=(face,), daemon=True)
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