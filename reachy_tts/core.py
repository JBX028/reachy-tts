import sys
import time
import threading
from typing import Optional
import pyaudio
import numpy as np

from reachy_mini.utils import create_head_pose
from reachy_mini.utils.interpolation import compose_world_offset

from reachy_tts.audio import (
    _get_macos_volume, 
    _set_macos_volume, 
    _try_switch_audio_source, 
    _restore_audio_source, 
    play_audio_thread
)
from reachy_tts.kinematics import SwayRollRT, HOP_MS

def _execute_tts_movement(reachy, client, text: str, voice: str, model: str, speaker: Optional[str], volume: Optional[int] = None):
    p = pyaudio.PyAudio()

    device_index = None
    target_device_name = None
    
    if speaker:
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                if info.get("maxOutputChannels", 0) > 0 and speaker.lower() in info.get("name", "").lower():
                    device_index = i
                    target_device_name = info.get("name")
                    break
            except Exception:
                pass

    original_device = None
    original_volume = None

    if volume is not None:
        if target_device_name:
            original_device = _try_switch_audio_source(target_device_name)
        
        original_volume = _get_macos_volume()
        target_display = target_device_name if target_device_name else "default system speaker"
        print(f"Temporarily setting volume of '{target_display}' to {volume}% (original: {original_volume}%)...")
        _set_macos_volume(volume)

    try:
        neutral_head_pose = create_head_pose(0, 0, 0, 0, 0, 0, degrees=True)
        
        print("Zeroing position...")
        reachy.goto_target(head=neutral_head_pose, antennas=[0.0, 0.0], duration=1.0, body_yaw=0.0)
        time.sleep(1.0)
        
        print(f"Generating OpenAI TTS for voice: {voice}...")
        audio_response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            response_format="pcm"
        )

        # Decode and buffer full audio 
        # (OpenAI TTS-1 PCM streams natively at 24kHz, 16bit, mono)
        OPENAI_SR = 24000
        pcm_bytes = b"".join([chunk for chunk in audio_response.iter_bytes(chunk_size=4096)])
        pcm_array = np.frombuffer(pcm_bytes, dtype=np.int16)

        # Initialize PyAudio
        if device_index is not None:
            print(f"Playing audio through speaker: {p.get_device_info_by_index(device_index)['name']}")
        else:
            if speaker:
                print(f"Warning: Could not find a speaker matching '{speaker}'. Falling back to system default.", file=sys.stderr)

        stream_kwargs = {
            "format": pyaudio.paInt16,
            "channels": 1,
            "rate": OPENAI_SR,
            "output": True
        }
        if device_index is not None:
            stream_kwargs["output_device_index"] = device_index

        stream = p.open(**stream_kwargs)

        # Start audio background thread while the main thread updates robotic movements
        playback_thr = threading.Thread(target=play_audio_thread, args=(stream, pcm_bytes))
        playback_thr.start()

        # Reachy movement control loop
        sway = SwayRollRT()
        
        # 50ms chunks aligned exactly with the hop interval (50ms @ 24kHz = 1200 frames)
        frames_per_hop = int(OPENAI_SR * (HOP_MS / 1000.0)) 
        
        print(f"Speaking: '{text.strip()}'")
        for i in range(0, len(pcm_array), frames_per_hop):
            loop_start = time.time()
            
            chunk = pcm_array[i : i + frames_per_hop]
            results = sway.feed(chunk, OPENAI_SR)
            
            if results:
                r = results[-1]  # Take latest smoothed interpolation interval
                
                # Format movement offsets exactly simulating reachy_mini_conversation_app secondary poses
                secondary_head_pose = create_head_pose(
                    x=r["x_mm"] / 1000.0, 
                    y=r["y_mm"] / 1000.0, 
                    z=r["z_mm"] / 1000.0,
                    roll=r["roll_rad"],
                    pitch=r["pitch_rad"],
                    yaw=r["yaw_rad"],
                    degrees=False, mm=False
                )
                
                # Merge with neutral head position and fire update
                combined_head = compose_world_offset(neutral_head_pose, secondary_head_pose)
                reachy.set_target(head=combined_head, antennas=[0.0, 0.0], body_yaw=0.0)
            
            # Compensate loop sleep interval (aiming to match Hop precisely)
            elapsed = time.time() - loop_start
            sleep_time = max(0.0, (HOP_MS / 1000.0) - elapsed)
            time.sleep(sleep_time)

        # Cleanup safely
        playback_thr.join()
        stream.stop_stream()
        stream.close()
        p.terminate()

        print("Returning to neutral...")
        reachy.goto_target(head=neutral_head_pose, antennas=[0.0, 0.0], duration=1.0, body_yaw=0.0)
    finally:
        if original_volume is not None:
            print(f"Restoring volume to {original_volume}%...")
            _set_macos_volume(original_volume)
        if original_device is not None:
            _restore_audio_source(original_device)
