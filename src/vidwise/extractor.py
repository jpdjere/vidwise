"""Audio and frame extraction using ffmpeg."""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from vidwise.utils import timestamp_label


def extract_audio(video_path: Path, output_dir: Path) -> Path:
    """Extract 16kHz mono WAV audio from video.

    Whisper expects 16kHz sample rate, mono channel.
    """
    audio_path = output_dir / "audio.wav"
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
        "-y",
    ]

    print("Extracting audio...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error extracting audio:\n{result.stderr}", file=sys.stderr)
        raise SystemExit(1)

    return audio_path


def extract_frames(
    video_path: Path, output_dir: Path, interval: int = 2
) -> list[Path]:
    """Extract frames at the specified interval (seconds).

    Frames are saved as frame_0m00s.png, frame_0m02s.png, etc.
    Returns sorted list of frame paths.
    """
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    # Extract with sequential numbering first
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vf", f"fps=1/{interval}",
        str(frames_dir / "frame_%04d.png"),
        "-y",
    ]

    print(f"Extracting frames (every {interval}s)...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error extracting frames:\n{result.stderr}", file=sys.stderr)
        raise SystemExit(1)

    # Rename to timestamp-based names
    raw_frames = sorted(frames_dir.glob("frame_*.png"))
    renamed = []
    for i, frame in enumerate(raw_frames):
        seconds = i * interval
        new_name = frames_dir / f"frame_{timestamp_label(seconds)}.png"
        frame.rename(new_name)
        renamed.append(new_name)

    print(f"  Extracted {len(renamed)} frames")
    return renamed


def extract_all(
    video_path: Path, output_dir: Path, interval: int = 2
) -> tuple[Path, list[Path]]:
    """Run audio and frame extraction in parallel.

    Returns (audio_path, list_of_frame_paths).
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        audio_future = pool.submit(extract_audio, video_path, output_dir)
        frames_future = pool.submit(extract_frames, video_path, output_dir, interval)
        return audio_future.result(), frames_future.result()
