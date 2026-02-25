import json
import threading
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from reachy_tts.core import _execute_tts_movement

app = FastAPI(title="Reachy TTS HTTP Server")

_GLOBAL_REACHY = None
_GLOBAL_OPENAI = None
_GLOBAL_SPEAKER = None
_UI_ENABLED = False
_TTS_LOCK = threading.Lock()

VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reachy TTS Control</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0f172a;
            --panel: rgba(30, 41, 59, 0.7);
            --accent: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --border: rgba(255, 255, 255, 0.1);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
        }

        body {
            background-color: var(--bg);
            color: var(--text);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            overflow: hidden;
            background-image: 
                radial-gradient(circle at 20% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 80% 80%, rgba(168, 85, 247, 0.15) 0%, transparent 40%);
        }

        .container {
            width: 100%;
            max-width: 500px;
            padding: 2rem;
            background: var(--panel);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 24px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        h1 {
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            background: var(--accent);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
        }

        p.subtitle {
            color: var(--text-dim);
            text-align: center;
            margin-bottom: 2rem;
            font-weight: 300;
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        label {
            display: block;
            margin-bottom: 0.5rem;
            color: var(--text-dim);
            font-size: 0.875rem;
            font-weight: 400;
        }

        textarea {
            width: 100%;
            padding: 1rem;
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text);
            font-size: 1rem;
            resize: none;
            transition: all 0.3s ease;
            outline: none;
        }

        textarea:focus {
            border-color: #6366f1;
            box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
        }

        select {
            width: 100%;
            padding: 0.75rem 1rem;
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text);
            font-size: 1rem;
            appearance: none;
            cursor: pointer;
            outline: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 1rem center;
            background-size: 1.25rem;
        }

        select:focus {
            border-color: #6366f1;
        }

        button {
            width: 100%;
            padding: 1rem;
            background: var(--accent);
            border: none;
            border-radius: 12px;
            color: white;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            margin-top: 1rem;
            position: relative;
            overflow: hidden;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.4);
            filter: brightness(1.1);
        }

        button:active {
            transform: translateY(0);
        }

        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .status {
            margin-top: 1rem;
            text-align: center;
            font-size: 0.875rem;
            min-height: 1.25rem;
            transition: color 0.3s ease;
        }

        .status.success { color: #10b981; }
        .status.error { color: #f43f5e; }
        .status.loading { color: var(--text-dim); }

        /* Micro-animations */
        .loading-dots:after {
            content: '.';
            animation: dots 1.5s steps(5, end) infinite;
        }
        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60% { content: '...'; }
            80%, 100% { content: ''; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Reachy TTS</h1>
        <p class="subtitle">Enter text to make Reachy speak</p>
        
        <div class="form-group">
            <label for="text">Message</label>
            <textarea id="text" rows="4" placeholder="What should I say?"></textarea>
        </div>

        <div class="form-group">
            <label for="voice">Voice</label>
            <select id="voice">
                <!-- Generated by JS -->
            </select>
        </div>

        <div class="form-group">
            <label for="volume">Volume: <span id="volValue">80</span>%</label>
            <input type="range" id="volume" min="0" max="100" value="80" style="width: 100%; accent-color: #6366f1;">
        </div>

        <button id="submitBtn">Speak Now</button>
        <div id="status" class="status"></div>
    </div>

    <script>
        const voices = %s;
        const voiceSelect = document.getElementById('voice');
        const submitBtn = document.getElementById('submitBtn');
        const textInput = document.getElementById('text');
        const statusDiv = document.getElementById('status');
        const volInput = document.getElementById('volume');
        const volValue = document.getElementById('volValue');

        volInput.addEventListener('input', (e) => {
            volValue.textContent = e.target.value;
        });

        voices.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v;
            opt.textContent = v.charAt(0).toUpperCase() + v.slice(1);
            voiceSelect.appendChild(opt);
        });

        submitBtn.addEventListener('click', async () => {
            const text = textInput.value.trim();
            if (!text) {
                showStatus('Please enter some text.', 'error');
                return;
            }

            setLoading(true);
            try {
                const response = await fetch('/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        voice: voiceSelect.value,
                        volume: parseInt(document.getElementById('volume').value)
                    })
                });

                const data = await response.json();
                if (response.ok) {
                    showStatus('Speech completed successfully.', 'success');
                } else {
                    showStatus(data.detail || 'An error occurred.', 'error');
                }
            } catch (err) {
                showStatus('Server connection failed.', 'error');
            } finally {
                setLoading(false);
            }
        });

        function showStatus(msg, type) {
            statusDiv.textContent = msg;
            statusDiv.className = 'status ' + type;
        }

        function setLoading(isLoading) {
            submitBtn.disabled = isLoading;
            if (isLoading) {
                submitBtn.textContent = 'Processing...';
                showStatus('Generating audio', 'loading');
                statusDiv.classList.add('loading-dots');
            } else {
                submitBtn.textContent = 'Speak Now';
                statusDiv.classList.remove('loading-dots');
            }
        }
    </script>
</body>
</html>
"""

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "alloy"
    model: Optional[str] = "tts-1"
    speaker: Optional[str] = None
    volume: Optional[int] = None

@app.get("/", response_class=HTMLResponse)
def ui_index():
    if not _UI_ENABLED:
        raise HTTPException(status_code=404, detail="UI is not enabled.")
    return UI_HTML.replace('%s', json.dumps(VOICES))

@app.post("/tts")
def tts_endpoint(req: TTSRequest):
    if not _GLOBAL_REACHY or not _GLOBAL_OPENAI:
        raise HTTPException(status_code=503, detail="TTS service is not fully initialized.")
        
    with _TTS_LOCK:
        try:
            target_speaker = req.speaker if req.speaker else _GLOBAL_SPEAKER
            _execute_tts_movement(
                _GLOBAL_REACHY, 
                _GLOBAL_OPENAI, 
                req.text, 
                req.voice, 
                req.model, 
                target_speaker,
                req.volume
            )
            return {"status": "success", "message": "TTS completed."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
