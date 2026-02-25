import os
import sys
import argparse
from openai import OpenAI
from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose
import uvicorn

from reachy_tts.core import _execute_tts_movement
from reachy_tts.server import app
import reachy_tts.server as server_module

def main():
    parser = argparse.ArgumentParser(description="Reachy TTS CLI Tool")
    parser.add_argument("text", type=str, nargs="?", help="Text for Reachy to say (ignored if --http is used)")
    parser.add_argument("--voice", type=str, default="alloy", help="OpenAI voice (alloy, echo, fable, onyx, nova, shimmer) (default: alloy)")
    parser.add_argument("--model", type=str, default="tts-1", help="OpenAI TTS model (default: tts-1)")
    parser.add_argument("--api-key", type=str, help="OpenAI API Key (fallback to OPENAI_API_KEY env var)")
    parser.add_argument("--speaker", type=str, default="reSpeaker XVF3800", help="Target speaker name (default: reSpeaker XVF3800)")
    parser.add_argument("--http", action="store_true", help="Start an HTTP server instead of running directly")
    parser.add_argument("--port", type=int, default=8000, help="Port for the HTTP server (default: 8000)")
    parser.add_argument("--ui", action="store_true", help="Expose a simple web UI in HTTP mode (at '/')")
    parser.add_argument("--volume", type=int, help="Temporary system volume (0-100). Restored after speech.")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OpenAI API key must be provided via --api-key argument or OPENAI_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)
        
    client = OpenAI(api_key=api_key)

    try:
        reachy = ReachyMini(media_backend="default")
        neutral_head_pose = create_head_pose(0, 0, 0, 0, 0, 0, degrees=True)
        reachy.goto_target(head=neutral_head_pose, antennas=[0.0, 0.0], duration=0.5, body_yaw=0.0)
    except ConnectionError:
        print("\n❌ Error: Could not connect to the Reachy Mini daemon.", file=sys.stderr)
        print("Please ensure the daemon is running in the background and try again.\n", file=sys.stderr)
        sys.exit(1)

    if args.http:
        server_module._GLOBAL_REACHY = reachy
        server_module._GLOBAL_OPENAI = client
        server_module._GLOBAL_SPEAKER = args.speaker
        server_module._UI_ENABLED = args.ui
        print(f"Starting FastAPI server on port {args.port}...")
        if args.ui:
            print(f"UI exposed at http://localhost:{args.port}/")
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        if not args.text:
            print("Error: 'text' positional argument is required unless running in --http mode.", file=sys.stderr)
            sys.exit(1)
        _execute_tts_movement(reachy, client, args.text, args.voice, args.model, args.speaker, args.volume)
