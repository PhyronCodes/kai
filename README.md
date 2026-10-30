# KAI — Knowledge & Automation Interface

KAI is a hands-free desk assistant I built from scratch in Python. Say "hey KAI", ask a question or tell it something to do, and it answers out loud while a full-width waveform display shows what it's doing. It manages my to-do list, tells me what's due each morning, and starts by itself when the machine powers on.

It currently runs on a 2012 Sony Vaio that I wiped and set up with Xubuntu as a dedicated device. The end goal is a small desk box with a bar-shaped screen across the front.

## What it does

- **Wake word, fully offline.** It listens for "hey KAI" using [Vosk](https://alphacephei.com/vosk/) restricted to a tiny grammar, so it costs nothing and needs no internet while waiting. To cut false triggers from background audio, the grammar includes sound-alike "decoy" words, partial results have to hold steady for several chunks, and final results need a minimum per-word confidence.
- **Automatic end of speech.** Recording stops by itself after a short silence (RMS loudness per 0.1 s chunk), with a timeout if nobody speaks and a hard cap on length.
- **Speech-to-text** with Gemini, with output validation so tags like `<noise>`, or a model trying to *answer* instead of transcribe, never reach the assistant.
- **Conversation with memory.** The history is managed client-side (`store=False`), trimmed only at user-turn boundaries so a tool call is never separated from its result, and fully rolled back if any request in a turn fails.
- **To-do list via function calling.** Gemini is given four tools (`add_task`, `list_tasks`, `complete_task`, `delete_task`) and decides when to call them; the assistant loop runs them, sends the results back, and repeats until there's a text answer. Tasks have due dates and are stored as JSON.
- **Daily briefing.** At startup and at 9:00 each day, KAI says what's due today and what's overdue, built locally so it can't hallucinate a task.
- **Spoken replies** with [Piper](https://github.com/OHF-Voice/piper1-gpl), a neural text-to-speech engine that runs locally.
- **Waveform display.** A full-width bar of dotted columns drawn with `pygame` and `numpy`. Each state (idle, listening, thinking, speaking) has its own look that the display eases between; while listening it follows the microphone level, and while speaking it follows KAI's own voice.
- **Runs as a device.** Autologin plus an autostart entry launch KAI full screen at boot, wait for the network, log to `kai.log`, and restart it automatically if it ever crashes.

## Design notes

- **The display runs in its own process.** Drawing and audio originally shared one Python process, and the drawing loop starved the audio callbacks of the GIL, so playback crackled. Moving the display into a separate process (sharing state through `multiprocessing.Value`) fixed it, and also keeps the window on its own main thread, which macOS requires.
- **Each file has one job**, so a provider can be swapped (for example a local model instead of the cloud) by changing a single file.
- **Works on Mac and Linux from the same code.** If Vosk isn't available (it has no Apple Silicon build), the wake word falls back to the space bar.

## Project structure

| File | Job |
| --- | --- |
| `voice.py` | The main loop: wake → listen → transcribe → think → speak, plus the daily briefing |
| `script.py` | The `Assistant` class: conversation, memory, system prompt and the tool-calling loop. Run it directly for a typed chat |
| `tasks.py` | The to-do list: storage, the four task functions, their tool descriptions, and the briefing text |
| `wake.py` | The "hey KAI" wake word |
| `audio.py` | Microphone recording, silence detection and loudness levels |
| `stt.py` | Speech-to-text |
| `tts.py` | Text-to-speech with Piper, reporting loudness for the display |
| `bar.py` | The waveform display |
| `face.py` | Shared state between processes (`FaceControl`), and an earlier 3D dot-sphere face |
| `start_kai.sh`, `kai.desktop` | Launcher and autostart entry for running KAI as a device |

## Running it

1. Create a virtual environment and install the packages:
   ```
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```
   On Linux you may also need PortAudio: `sudo apt install libportaudio2`.
2. Download a Piper voice into `voices/`:
   ```
   mkdir -p voices && cd voices
   wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx
   wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json
   cd ..
   ```
3. For the wake word (Linux), download the small English Vosk model into `models/`:
   ```
   mkdir -p models && cd models
   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   unzip vosk-model-small-en-us-0.15.zip
   cd ..
   ```
4. Create a `.env` file with a Gemini API key (free from Google AI Studio):
   ```
   GEMINI_API_KEY=your-key-here
   ```
5. Run it:
   - `.venv/bin/python voice.py` for the full voice assistant in a window
   - `.venv/bin/python voice.py --fullscreen` for device mode (Esc quits)
   - `.venv/bin/python script.py` for a typed chat
6. To start it at boot on Xubuntu, make `start_kai.sh` executable and copy `kai.desktop` into `~/.config/autostart/`.

## Next steps

- The enclosure: a low box with a 7.9" bar display across the front, designed in CAD
- Google Calendar tools, using the same function-calling pattern as the to-do list
- Tap-to-talk on the touchscreen
- Running the language model locally, so KAI works fully offline