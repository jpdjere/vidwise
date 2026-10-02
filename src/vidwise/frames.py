"""Smart frame selection — deduplicate near-identical frames using pixel diff."""

from __future__ import annotations

from pathlib import Path

from vidwise.utils import seconds_from_label


THUMBNAIL_SIZE = (128, 72)


def thumbnail(frame: Path):
    """Load a frame as a small RGB array, which is all the difference check needs."""
    import numpy as np
    from PIL import Image

    with Image.open(frame) as image:
        small = image.convert("RGB").resize(THUMBNAIL_SIZE)
    return np.asarray(small, dtype=np.uint8)


def thumbnail_difference(thumb_a, thumb_b) -> float:
    """Normalized pixel difference between two thumbnails: 0.0 (identical) to 1.0."""
    import numpy as np

    difference = np.abs(thumb_a.astype(np.int16) - thumb_b.astype(np.int16))
    return float(difference.mean() / 255.0)


def thumbnails_in_order(frames: list[Path], batch_size: int = 256):
    """Yield each frame's thumbnail in order, decoding a batch at a time across threads."""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor() as pool:
        for start in range(0, len(frames), batch_size):
            yield from pool.map(thumbnail, frames[start : start + batch_size])


def compute_frame_difference(frame_a: Path, frame_b: Path) -> float:
    """Compute normalized pixel difference between two frames.

    Returns a value between 0.0 (identical) and 1.0 (completely different).
    Uses small thumbnails for fast comparison.
    """
    return thumbnail_difference(thumbnail(frame_a), thumbnail(frame_b))


def select_key_frames(
    frame_paths: list[Path], threshold: float = 0.05
) -> list[Path]:
    """Select frames that show meaningful visual changes.

    Compares consecutive frames and keeps those where the pixel difference
    exceeds the threshold. Always keeps first and last frame.

    Args:
        frame_paths: Sorted list of all frame paths.
        threshold: Minimum pixel difference (0.0-1.0) to consider a frame "new".
                   Default 0.05 (5%) works well for most content.

    Returns:
        Filtered list of key frame paths.
    """
    if len(frame_paths) <= 2:
        return list(frame_paths)

    thumbnails = thumbnails_in_order(frame_paths)
    key_frames = [frame_paths[0]]
    last_kept = next(thumbnails)
    for frame, current in zip(frame_paths[1:], thumbnails):
        if thumbnail_difference(last_kept, current) > threshold:
            key_frames.append(frame)
            last_kept = current

    if frame_paths[-1] not in key_frames:
        key_frames.append(frame_paths[-1])

    return key_frames


def write_key_frame_index(key_frames: list[Path], output_dir: Path) -> Path:
    """Write key_frames.json: each key frame's time in seconds and its path.

    Paths are relative to output_dir, so the folder can be moved.
    Returns the path of the written file.
    """
    import json

    index = [
        {
            "seconds": seconds_from_label(frame.name),
            "path": str(frame.relative_to(output_dir)),
        }
        for frame in key_frames
    ]
    index_path = output_dir / "key_frames.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    return index_path


def batch_frames(key_frames: list[Path], max_per_batch: int = 10) -> list[list[Path]]:
    """Group key frames into batches for efficient API calls.

    Each batch represents a contiguous time segment.
    """
    return [
        key_frames[i : i + max_per_batch]
        for i in range(0, len(key_frames), max_per_batch)
    ]


def time_range_for_batch(batch: list[Path], interval: int = 2) -> str:
    """Get a human-readable time range for a batch of frames."""
    if not batch:
        return "0:00 - 0:00"

    start_s = seconds_from_label(batch[0].stem)
    end_s = seconds_from_label(batch[-1].stem) + interval

    def fmt(s: int) -> str:
        return f"{s // 60}:{s % 60:02d}"

    return f"{fmt(start_s)} - {fmt(end_s)}"
