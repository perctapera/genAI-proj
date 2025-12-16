import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def create_tts_audio(text: str, out_path: str):
    """Create a TTS WAV/MP3 using pyttsx3 if available. Raises RuntimeError if not available or fails."""
    try:
        import pyttsx3
    except Exception as e:
        raise RuntimeError("pyttsx3 not available") from e
    engine = pyttsx3.init()
    # try to set a reasonable rate
    try:
        engine.setProperty('rate', 150)
    except Exception:
        pass
    # save to file
    tmp_mp3 = out_path
    engine.save_to_file(text, tmp_mp3)
    engine.runAndWait()
    if not os.path.exists(tmp_mp3):
        raise RuntimeError("TTS generation failed: output file not created")
    return tmp_mp3


def create_silent_audio(out_path: str, duration: int = 1):
    """Use ffmpeg to generate a silent audio file of a given duration in seconds."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t",
        str(duration),
        out_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found on PATH; cannot create silent audio")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg silent audio generation failed: {e.stderr.decode(errors='ignore')}")
    return out_path


def make_video_from_frames(frames: list, out_path: str, fps: int = 2, audio_path: str | None = None):
    """Create a slideshow video from ordered image frame paths. Optionally add audio (will be trimmed to video length)."""
    # frames are paths; copy them into a temporary dir with sequential frame_000.jpg names
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as tmp:
        for i, src in enumerate(frames):
            dst = os.path.join(tmp, f"frame_{i:03d}.jpg")
            shutil.copy(src, dst)
        # create raw video
        tmp_pattern = os.path.join(tmp, "frame_%03d.jpg")
        raw_video = out_path
        cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i", tmp_pattern, "-c:v", "libx264", "-pix_fmt", "yuv420p", raw_video]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except FileNotFoundError:
            raise RuntimeError("ffmpeg not found on PATH; please install ffmpeg to enable video generation")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg failed: {e.stderr.decode(errors='ignore')}")
        if audio_path:
            final_out = os.path.splitext(out_path)[0] + "_with_audio.mp4"
            cmd2 = ["ffmpeg", "-y", "-i", raw_video, "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-shortest", final_out]
            try:
                subprocess.run(cmd2, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"ffmpeg merging audio failed: {e.stderr.decode(errors='ignore')}")
            return final_out
        return raw_video
