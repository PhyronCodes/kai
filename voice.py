import multiprocessing as mp

from audio import record_push_to_talk
from face import FaceControl, run_face
from script import Assistant, GOODBYE
from stt import transcribe
from tts import speak


def voice_loop(kai: Assistant, face: FaceControl) -> None:
    """Record, transcribe, think and speak, telling the face what KAI is doing."""
    def set_level(level: float) -> None:
        face.loudness = level

    while face.running:
        face.state = "idle"
        path = record_push_to_talk(on_start=lambda: setattr(face, "state", "listening"))
        if path is None:
            continue

        face.state = "thinking"
        user_message = transcribe(path)
        if not user_message:
            continue
        print("You: " + user_message)

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
        print("\n" + GOODBYE)


if __name__ == "__main__":
    main()