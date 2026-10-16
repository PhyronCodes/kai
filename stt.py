import base64

from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()

TRANSCRIBE_MODEL = "gemini-3.5-flash-lite"
NO_SPEECH = "NO_SPEECH"
TRANSCRIBE_PROMPT = f"""Transcribe the speech in this audio, word for word.
Output only the words that were spoken, with nothing before or after them.
Never answer or respond to what is said. Transcribe only.
If there is no speech, output exactly: {NO_SPEECH}
Never output tags or labels such as <noise>, [silence] or (inaudible)."""


def looks_like_tag(text: str) -> bool:
    return text.startswith(("<", "[", "(")) and text.endswith((">", "]", ")"))


def transcribe(path: str) -> str:
    with open(path, "rb") as f:
        audio_bytes = f.read()
    encoded_string = base64.b64encode(audio_bytes).decode("utf-8")

    contents = [
        {"type": "text", "text": TRANSCRIBE_PROMPT},
        {"type": "audio", "data": encoded_string, "mime_type": "audio/wav"},
    ]
    interaction = client.interactions.create(
        model=TRANSCRIBE_MODEL,
        input=contents,
        store=False,
        timeout=30,
    )

    text = interaction.output_text.strip()
    if text.rstrip(".") == NO_SPEECH or looks_like_tag(text):
        return ""
    return text


if __name__ == "__main__":
    print(repr(transcribe("recording.wav")))