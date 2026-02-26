"""Smart frame selection — deduplicate near-identical frames using pixel diff."""

from __future__ import annotations

from pathlib import Path

from vidwise.utils import seconds_from_label


def compute_frame_difference(frame_a: Path, frame_b: Path) -> float:
    """Compute normalized pixel difference between two frames.

    Returns a value between 0.0 (identical) and 1.0 (completely different).
    Uses small thumbnails for fast comparison.
    """
    from PIL import Image
    import numpy as np

    size = (128, 72)  # Small thumbnail for speed
    img_a = np.array(Image.open(frame_a).convert("RGB").resize(size), dtype=np.float32)
    img_b = np.array(Image.open(frame_b).convert("RGB").resize(size), dtype=np.float32)

    diff = np.abs(img_a - img_b).mean() / 255.0
    return float(diff)


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

    key_frames = [frame_paths[0]]
    for frame in frame_paths[1:]:
        diff = compute_frame_difference(key_frames[-1], frame)
        if diff > threshold:
            key_frames.append(frame)

    if frame_paths[-1] not in key_frames:
        key_frames.append(frame_paths[-1])

    return key_frames


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
