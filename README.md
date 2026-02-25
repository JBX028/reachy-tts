# Reachy Mini TTS

**Reachy Mini TTS** (`reachy-tts`) is a standalone command-line interface tool designed to make the Reachy Mini robot organically talk. By integrating with the OpenAI Text-to-Speech (TTS) API, this tool generates high-quality voices and processes the audio envelope in real-time to mimic natural head movements (wobbles and sways) that synchronize directly with the generated speech.

By default, the script will output audio to the `reSpeaker XVF3800` microphone array/speaker, but will gracefully fall back to the system default if it is disconnected or unavailable. 

> **⚠️ Note:** This script has been developed and tested **only on macOS**. Implementation and system dependencies (such as portaudio or ALSA) might differ significantly on other operating systems (like Linux or Windows).

## ✨ Features
- **Dynamic Head Movement:** Analyzes the amplitude envelope of the incoming PCM audio at 24kHz to dynamically calculate organic head and neck positioning offsets.
- **OpenAI Integration:** Select natively between various OpenAI models (`tts-1`) and voices (`alloy`, `fable`, `shimmer`, etc.).
- **Smart Speaker Routing:** Native targeting for Reachy's built-in reSpeaker or fallback speakers.
- **HTTP Webhook Mode:** Run the tool as a persistent FastAPI server, allowing integrations via POST requests instead of single CLI executions.
- **Interactive Web UI:** A premium, glassmorphic web interface to trigger TTS manually with live status updates.
- **Standalone Global CLI:** Can be symlinked as a native global utility that uses an encapsulated virtual environment.

---

## 🛠️ Prerequisites & Installation
Because this script uses `pyaudio` to buffer raw PCM audio to specific output devices, you must ensure the C-bindings for portaudio are installed on your OS.

### 1. Install System Dependencies (macOS example)
The tool relies on PortAudio for sound processing and, optionally, `SwitchAudioSource` for properly targeting volume changes to specific output devices (like the reSpeaker) so it does not affect your active headphones.
```bash
brew install portaudio switchaudio-osx
```

### 2. Set Up the Environment
Clone the repository and prepare the isolated virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install openai numpy pyaudio fastapi pydantic uvicorn reachy-mini
```

### 3. Make the Script Executable
Make sure the main script is executable:
```bash
chmod +x reachy-tts
```

*(Optional) Install Globally:*
To make the `reachy-tts` command accessible from anywhere on your machine, you can symlink the absolute path of the script into your machine's global bin directory:
```bash
sudo ln -s /absolute/path/to/reachy-experiments/reachy-tts/reachy-tts /usr/local/bin/reachy-tts
```
*(Make sure to update the shebang inside `reachy-tts` to point to the absolute path of your local `.venv/bin/python` if you do this!)*

---

## 🚀 Usage 

You can run `reachy-tts` from the command line. You must have an active OpenAI API key either provided as an argument or available globally as an environment variable (`OPENAI_API_KEY`).

```bash
# Basic usage (defaults to voice: alloy, model: tts-1)
reachy-tts "Bonjour, je suis Reachy et je bouge ma tête!"

# Passing an explicit API Key
reachy-tts "Testing, 1 2 3." --api-key sk-proj-xxxxx

# Using a different OpenAI voice
reachy-tts "It's alive!" --voice fable

# Overriding the target output speaker
reachy-tts "Testing on my headset." --speaker "AirPods"

# Temporarily forcing volume to 100%
reachy-tts "Attention please!" --volume 100
```

### 🌐 Running as an HTTP Webhook Server
If you want to plug `reachy-tts` into broader automation logic, you can start it as a persistent server:
```bash
reachy-tts --http --port 8000 --ui
```
This boots a FastAPI server listening on `http://0.0.0.0:8000` and exposes a premium web-based control panel at the root URL (`/`). You can then trigger the exact same text-to-speech functionality by using the UI or sending a standard POST request:
```bash
curl -X POST http://localhost:8000/tts \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello world over HTTP!", "voice": "echo", "volume": 90}'
```

### CLI Arguments Summary
| Argument | Description | Default |
|----------|-------------|---------|
| `text`   | **(Required)** The text you want Reachy to say. | N/A |
| `--voice`| The OpenAI voice to use (`alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`). | `alloy` |
| `--model`| The OpenAI underlying model to generate audio with. | `tts-1` |
| `--speaker`| The targeted name of the physical audio output device. | `reSpeaker XVF3800` |
| `--api-key`| Your OpenAI API string. Will fall back to the `OPENAI_API_KEY` environment variable. | N/A |
| `--http` | Launches a persistent FastAPI webhook server listening for TTS requests. | N/A |
| `--port` | Defines the specific port for the FastAPI server. | `8000` |
| `--ui`   | Exposes a clean and modern web UI for manual TTS triggering when in HTTP mode. | N/A |
| `--volume`| Temporary system volume (0-100). Restored automatically after speech. | N/A |
 
---
 
## ❓ Troubleshooting

### "Could not connect to the Reachy Mini daemon"
This tool requires the Reachy Mini daemon to be running in the background to handle motor communications. Ensure you have started the daemon before running `reachy-tts`.

## ⚙️ How it Works
1. **TTS Generation:** The text string is handed to the OpenAI API which begins buffering an incoming stream of raw PCM audio chunks.
2. **Audio Playback:** A background thread immediately starts streaming the incoming audio via PyAudio directly to your specific hardware device. 
3. **Envelope Tracking:** At the same time, the main thread extracts overlapping frames from the playing audio, checking the root mean square (RMS) amplitude and processing it through a Voice Activity Detection (VAD) smoother.
4. **Kinematics:** Sine wave algorithms calculate pitch, yaw, and roll modifiers alongside relative spatial movement, composing them as offsets via the Reachy SDK.

## 🏗️ Architecture
The project has recently been refactored into a scalable Python package:

- `reachy-tts`: The lightweight executable proxy that runs the CLI application.
- `reachy_tts/audio.py`: Native macOS audio routing (`SwitchAudioSource`, `osascript`) and generic stream buffering.
- `reachy_tts/kinematics.py`: Mathematics for audio envelope tracking and organic geometric head sway logic.
- `reachy_tts/server.py`: API Server, UI Template, and Pydantic routing.
- `reachy_tts/core.py`: The movement engine linking TTS buffering with robotic constraints.
- `reachy_tts/cli.py`: Isolated command-line options and execution parsing.
