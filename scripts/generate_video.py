"""Utility to generate a slideshow video from frames or from a prompt (using OpenAI images).

Usage examples:
- python scripts/generate_video.py --frames outputs/supplementary/frame_00.jpg outputs/supplementary/frame_01.jpg
- python scripts/generate_video.py --prompt "A minimalist ceramic mug on a wooden table" --n 4 --tts "A beautiful handcrafted mug"
"""
import argparse
import os
from app.openai_utils import generate_images
from app.video_utils import create_tts_audio, create_silent_audio, make_video_from_frames
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", nargs="*", help="Frame image paths")
    parser.add_argument("--prompt", type=str, help="Prompt to generate images via OpenAI")
    parser.add_argument("--n", type=int, default=4, help="Number of images to generate from prompt")
    parser.add_argument("--tts", type=str, default=None, help="Optional narration text")
    parser.add_argument("--fps", type=int, default=2)
    parser.add_argument("--out", type=str, default="outputs/videos")
    args = parser.parse_args()

    frames = args.frames or []
    if not frames and args.prompt:
        if not os.getenv("OPENAI_API_KEY"):
            print("OPENAI_API_KEY not set; cannot generate images")
            return
        frames = generate_images(args.prompt, n=args.n, outdir=os.path.join('outputs', 'images'))
    if not frames:
        print("No frames to build a video from")
        return

    os.makedirs(args.out, exist_ok=True)
    audio_path = None
    if args.tts:
        try:
            audio_path = os.path.join('outputs', 'audio', f"tts_{uuid.uuid4().hex[:8]}.mp3")
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            create_tts_audio(args.tts, audio_path)
        except Exception as e:
            print(f"TTS failed: {e}; trying silent audio")
            audio_path = os.path.join('outputs', 'audio', f"silent_{uuid.uuid4().hex[:8]}.mp3")
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            create_silent_audio(audio_path, duration=max(1, int(len(frames)/max(1, args.fps))))

    out_path = os.path.join(args.out, f"slideshow_{uuid.uuid4().hex[:8]}.mp4")
    final = make_video_from_frames(frames, out_path, fps=args.fps, audio_path=audio_path)
    print("Video generated:", final)


if __name__ == '__main__':
    main()
