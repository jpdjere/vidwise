"""Shared utilities for vidwise."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def check_dependency(name: str, install_hint: str) -> bool:
    """Check if an external CLI tool is available on PATH."""
    if shutil.which(name) is None:
        print(f"Error: '{name}' not found. Install it: {install_hint}", file=sys.stderr)
        return False
    return True


def timestamp_label(seconds: int) -> str:
    """Convert seconds to a human-readable timestamp label like '2m30s'."""
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}m{secs:02d}s"


def seconds_from_label(label: str) -> int | None:
    """Parse a timestamp label like '2m30s' back to seconds."""
    import re

    match = re.search(r"(\d+)m(\d+)s", label)
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


def derive_output_name(source: str) -> str:
    """Derive a short name from a video source (URL or file path)."""
    if source.startswith(("http://", "https://")):
        # Extract something usable from URL
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(source)
        # YouTube: use video ID
        if "youtube.com" in parsed.hostname or "youtu.be" in parsed.hostname:
            qs = parse_qs(parsed.query)
            if "v" in qs:
                return qs["v"][0][:11]
        # Loom: use share ID
        if "loom.com" in parsed.hostname:
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2:
                return parts[-1][:12]
        # Generic: use last path segment
        last = parsed.path.strip("/").split("/")[-1]
        return last[:20] if last else "video"
    else:
        return Path(source).stem[:20]


def format_output_dir(source: str, base_dir: Path | None = None) -> Path:
    """Create the output directory path for a given source."""
    from datetime import date

    name = derive_output_name(source)
    dirname = f"vidwise-{name}-{date.today().isoformat()}"
    if base_dir:
        return base_dir / dirname
    return Path.cwd() / dirname
