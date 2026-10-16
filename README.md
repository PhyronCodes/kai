# KAI — Knowledge & Automation Interface

KAI is a voice-controlled desk assistant I'm building from scratch in Python. You talk to it, it answers out loud, and it remembers the conversation. The long-term goal is a small physical device that sits on my desk, helps me stay organised, and eventually moves its head to look at me.

## What it does now

- **Push-to-talk recording**: press Enter, speak, press Enter. Silent recordings are skipped using an RMS loudness check, before anything is sent to the cloud.
- **Speech-to-text** with Gemini, with output validation so tags like `<noise>` or a model trying to *answer* instead of transcribe never reach the assistant.
- **Conversation with memory**: the full history is managed client-side (`store=False`), trimmed at exchange boundaries to stay within limits, and rolled back cleanly if an API call fails.
- **Personality and honesty rules** in the system prompt, with the live date and time injected on every request.
- **Spoken replies** with [Piper](https://github.com/OHF-Voice/piper1-gpl), a neural text-to-speech engine that runs locally.
- **Fault tolerance**: timeouts and API errors (no Wi-Fi, bad key, rate limits) produce a spoken apology instead of a crash.
- **A face**: a rotating 3D sphere of blue dots with depth shading, drawn with perspective projection in `pygame`. Being turned into a full face.

## Project structure

| File | Job |
| --- | --- |
| `voice.py` | The voice loop: record → transcribe → think → speak |
| `script.py` | The `Assistant` class (conversation, memory, system prompt). Run it directly for a typed chat |
| `audio.py` | Microphone recording and silence detection |
| `stt.py` | Speech-to-text |
| `tts.py` | Text-to-speech with Piper |
| `face.py` | The dot-sphere face |

Each file has one job, so a provider can be swapped (for example a local speech model instead of the cloud) by changing a single file.

## Running it

1. Create and activate a virtual environment, then install the packages:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Download a Piper voice into a `voices` folder:
   ```
   python -m piper.download_voices en_GB-alan-medium --download-dir voices
   ```
3. Create a `.env` file with a Gemini API key (free from Google AI Studio):
   ```
   GEMINI_API_KEY=your-key-here
   ```
4. Run the voice assistant with `python voice.py`, the typed version with `python script.py`, or the face with `python face.py`.

## Next steps

- Move KAI onto a dedicated Linux machine and start it automatically on boot
- Finish the face and make it react to KAI's state: idle, listening, thinking, speaking
- Calendar and to-do tools via function calling, so KAI can answer "what's on tomorrow?" and add tasks
- A wake word, so it listens hands-free
- A pan-tilt head with a camera, so KAI turns to face whoever is speaking