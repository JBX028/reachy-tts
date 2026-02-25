import subprocess
import shutil
import sys
from typing import Optional

def _get_macos_volume() -> int:
    """Get the current macOS system volume (0-100)."""
    try:
        res = subprocess.check_output(["osascript", "-e", "output volume of (get volume settings)"])
        return int(res.strip())
    except Exception:
        return 50

def _set_macos_volume(volume: int):
    """Set the macOS system volume (0-100)."""
    try:
        subprocess.run(["osascript", "-e", f"set volume output volume {volume}"], check=True)
    except Exception as e:
        print(f"Warning: Could not set volume: {e}", file=sys.stderr)

def _try_switch_audio_source(device_name: str) -> Optional[str]:
    """Attempts to switch the macOS default audio output to the target device using SwitchAudioSource."""
    if not shutil.which("SwitchAudioSource"):
        return None
    try:
        prev_device = subprocess.check_output(["SwitchAudioSource", "-c", "-t", "output"]).decode().strip()
        if prev_device != device_name:
            subprocess.run(
                ["SwitchAudioSource", "-t", "output", "-s", device_name], 
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return prev_device
    except Exception:
        pass
    return None

def _restore_audio_source(device_name: str):
    """Restores the previous audio device."""
    if not shutil.which("SwitchAudioSource") or not device_name:
        return
    try:
        subprocess.run(
            ["SwitchAudioSource", "-t", "output", "-s", device_name],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

def play_audio_thread(stream, pcm_data):
    """Play the synthesized audio byte sequence to the speaker."""
    stream.write(pcm_data)
