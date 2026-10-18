import multiprocessing as mp
import string
import time

from audio import record_push_to_talk
from face import FaceControl, run_face
from script import Assistant, GOODBYE
from stt import transcribe
from tts import speak


QUIT_PHRASES = {"quit", "exit", "stop", "goodbye", "bye", "bye kai", "goodbye kai"}


def is_quit(message: str) -> bool:
    """True if the whole message is just a quit phrase, e.g. "Goodbye, KAI."
    Punctuation and capitals are ignored. A longer sentence that merely
    contains "stop" (like "stop reminding me") doesn't count."""
    cleaned = message.lower().translate(str.maketrans("", "", string.punctuation))
    return " ".join(cleaned.split()) in QUIT_PHRASES


def wait_for_space(face: FaceControl, prompt: str) -> None:
    """Block until space is pressed in the face window (used instead of input)."""
    print(prompt.replace("Enter", "space"))
    presses_before = face.space_presses
    while face.space_presses == presses_before:
        if not face.running:
            raise EOFError        # window closed: main() shuts everything down
        time.sleep(0.02)


def voice_loop(kai: Assistant, face: FaceControl) -> None:
    """Record, transcribe, think and speak, telling the face what KAI is doing."""
    def set_level(level: float) -> None:
        face.loudness = level

    def wait(prompt: str = "") -> None:
        wait_for_space(face, prompt)

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
    face_process = mp.Process(target=run_face, args=(face,), daemon=True)
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