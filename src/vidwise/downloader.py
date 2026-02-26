"""Video acquisition — download from URL or copy local file."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def is_url(source: str) -> bool:
    """Check if source is a URL."""
    return source.startswith(("http://", "https://"))


def download_video(source: str, output_dir: Path) -> Path:
    """Download video from URL using yt-dlp.

    Returns the path to the downloaded video file.
    """
    if shutil.which("yt-dlp") is None:
        print(
            "Error: yt-dlp is required for URL downloads.\n"
            "Install it: brew install yt-dlp  (or)  pip install yt-dlp",
            file=sys.stderr,
        )
        raise SystemExit(1)

    output_template = str(output_dir / "video.%(ext)s")
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-o", output_template,
        source,
    ]

    print(f"Downloading video from {source}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error downloading video:\n{result.stderr}", file=sys.stderr)
        raise SystemExit(1)

    # Find the downloaded file (extension varies)
    video_files = list(output_dir.glob("video.*"))
    video_files = [f for f in video_files if f.suffix not in (".wav", ".srt", ".txt", ".json")]
    if not video_files:
        print("Error: no video file found after download.", file=sys.stderr)
        raise SystemExit(1)

    return video_files[0]


def copy_local_video(source: str, output_dir: Path) -> Path:
    """Copy a local video file into the output directory.

    Returns the path to the copied video file.
    """
    src = Path(source).expanduser().resolve()
    if not src.exists():
        print(f"Error: file not found: {src}", file=sys.stderr)
        raise SystemExit(1)

    dst = output_dir / f"video{src.suffix}"
    shutil.copy2(src, dst)
    return dst


def acquire_video(source: str, output_dir: Path) -> Path:
    """Acquire video from source (URL or local file).

    Returns the path to the video file inside output_dir.
    """
    if is_url(source):
        return download_video(source, output_dir)
    else:
        return copy_local_video(source, output_dir)
