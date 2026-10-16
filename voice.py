from script import Assistant, GOODBYE
from audio import record_push_to_talk
from stt import transcribe
from tts import speak

kai = Assistant()
GOODBYE = "If you need anything else in the future, feel free to reach out. Have a great day!"

try:
    while True:
        path = record_push_to_talk()
        if path is None:
            continue
        user_message = transcribe(path)
        if not user_message:
            continue
        print("You: " + user_message)
        response = kai.ask(user_message)
        print("KAI: " + response)
        speak(response)
except (KeyboardInterrupt, EOFError):
    print("\n" + GOODBYE)