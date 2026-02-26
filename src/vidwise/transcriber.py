"""Whisper transcription — local speech-to-text."""

from __future__ import annotations

import json
from pathlib import Path


def transcribe(audio_path: Path, output_dir: Path, model_size: str = "medium") -> dict:
    """Run Whisper transcription on an audio file.

    Saves .txt, .srt, and .json outputs to output_dir.
    Returns the Whisper result dict (with 'segments' and 'text').
    """
    import whisper

    print(f"Loading Whisper model '{model_size}'...")
    model = whisper.load_model(model_size)

    print("Transcribing audio (this may take a while)...")
    result = model.transcribe(str(audio_path), language="en")

    # Save plain text
    txt_path = output_dir / "transcript.txt"
    txt_path.write_text(result["text"].strip() + "\n")

    # Save SRT
    srt_path = output_dir / "transcript.srt"
    srt_path.write_text(_format_srt(result["segments"]))

    # Save JSON (full result)
    json_path = output_dir / "transcript.json"
    json_path.write_text(json.dumps(result, indent=2, default=str))

    segment_count = len(result.get("segments", []))
    print(f"  Transcription complete: {segment_count} segments")
    return result


def _format_srt(segments: list[dict]) -> str:
    """Convert Whisper segments to SRT subtitle format."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_timestamp_srt(seg["start"])
        end = _format_timestamp_srt(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def _format_timestamp_srt(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def segments_for_timerange(
    segments: list[dict], start_s: float, end_s: float
) -> list[dict]:
    """Filter transcript segments that overlap with a time range."""
    return [
        seg for seg in segments
        if seg["end"] > start_s and seg["start"] < end_s
    ]


def segments_to_text(segments: list[dict]) -> str:
    """Join a list of segments into plain text."""
    return " ".join(seg["text"].strip() for seg in segments)
