import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def create_tts_audio(text: str, out_path: str):
    """Create a TTS WAV/MP3 using pyttsx3 if available."""
    try:
        import pyttsx3
    except Exception as e:
        raise RuntimeError("pyttsx3 not available") from e
    
    try:
        engine = pyttsx3.init()
        # Set properties
        try:
            engine.setProperty('rate', 150)
        except Exception:
            pass
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        # Save to file
        engine.save_to_file(text, out_path)
        engine.runAndWait()
        
        if not os.path.exists(out_path):
            raise RuntimeError("TTS generation failed: output file not created")
        return out_path
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise


def create_silent_audio(out_path: str, duration: int = 1):
    """Use ffmpeg to generate a silent audio file of a given duration in seconds."""
    # Ensure output directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t",
        str(duration),
        out_path,
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.debug(f"FFmpeg output: {result.stdout}")
        return out_path
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found on PATH; cannot create silent audio")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        raise RuntimeError(f"ffmpeg silent audio generation failed: {e.stderr}")


def make_video_from_frames(frames: list, out_path: str, fps: int = 2, audio_path: str | None = None):
    """Create a slideshow video from ordered image frame paths."""
    import tempfile
    import shutil
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with tempfile.TemporaryDirectory() as tmp:
        # Copy/convert frames with sequential names (re-encode to standard JPEG to avoid codec issues)
        for i, src in enumerate(frames):
            if not os.path.exists(src):
                logger.error(f"Frame not found: {src}")
                continue

            dst = os.path.join(tmp, f"frame_{i:03d}.jpg")
            # Prefer re-encoding via PIL to ensure consistent JPEG format and color mode
            try:
                from PIL import Image
                img = Image.open(src)
                # Convert to RGB if needed (e.g., PNG with alpha)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(dst, "JPEG", quality=85)
                logger.debug(f"Saved frame {i} as {dst} (size={img.size}, mode={img.mode})")
            except Exception as e:
                logger.warning(f"PIL re-encode failed for {src}: {e}; falling back to simple copy")
                try:
                    shutil.copy(src, dst)
                except Exception as e2:
                    logger.error(f"Failed to copy frame {src}: {e2}")
        
        # Check if we have any frames
        frame_files = sorted([f for f in os.listdir(tmp) if f.startswith('frame_') and f.endswith('.jpg')])
        if not frame_files:
            raise RuntimeError("No valid frames found for video creation")
        
        # Create video from frames
        tmp_pattern = os.path.join(tmp, "frame_%03d.jpg")
        
        if audio_path and os.path.exists(audio_path):
            # Create video with audio
            intermediate_video = os.path.join(tmp, "temp_video.mp4")
            
            # First create video without audio
            cmd1 = [
                "ffmpeg",
                "-y",
                "-framerate", str(fps),
                "-i", tmp_pattern,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "fast",
                intermediate_video
            ]
            
            # Then merge with audio
            cmd2 = [
                "ffmpeg",
                "-y",
                "-i", intermediate_video,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                out_path
            ]
            
            try:
                logger.info("Creating video without audio...")
                subprocess.run(cmd1, check=True, capture_output=True, text=True)
                
                logger.info("Merging with audio...")
                subprocess.run(cmd2, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg error: {e.stderr}")
                raise RuntimeError(f"Video creation failed: {e.stderr}")
        else:
            # Create video without audio
            cmd = [
                "ffmpeg",
                "-y",
                "-framerate", str(fps),
                "-i", tmp_pattern,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "fast",
                out_path
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg error: {e.stderr}")
                raise RuntimeError(f"Video creation failed: {e.stderr}")
    
    if not os.path.exists(out_path):
        raise RuntimeError(f"Video file was not created: {out_path}")
    
    return out_path