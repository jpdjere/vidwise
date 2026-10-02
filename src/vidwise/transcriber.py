"""Whisper transcription — local speech-to-text.

Supports two backends:
- faster-whisper (lighter, ~200MB, 3-4x faster) — used if installed
- openai-whisper (default, ~2GB, Apple Metal GPU support) — fallback
"""

from __future__ import annotations

import json
from pathlib import Path


def _use_faster_whisper() -> bool:
    """Check if faster-whisper is available."""
    try:
        import faster_whisper  # noqa: F401

        return True
    except ImportError:
        return False


def whisper_language(language: str) -> str | None:
    """Translate the ``--language`` option into Whisper's ``language`` argument.

    ``"auto"`` becomes None, which makes Whisper detect the spoken language.
    """
    return None if language == "auto" else language


def transcribe(
    audio_path: Path,
    output_dir: Path,
    model_size: str = "medium",
    language: str = "en",
    word_timestamps: bool = False,
) -> dict:
    """Run Whisper transcription on an audio file.

    Saves .txt, .srt, and .json outputs to output_dir.
    Returns a result dict with 'segments' list and 'text' string. With
    word_timestamps, each segment also has a 'words' list of
    {'word', 'start', 'end'}.
    """
    if _use_faster_whisper():
        result = _transcribe_faster(audio_path, model_size, language, word_timestamps)
    else:
        result = _transcribe_openai(audio_path, model_size, language, word_timestamps)

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


def _transcribe_openai(
    audio_path: Path, model_size: str, language: str, word_timestamps: bool
) -> dict:
    """Transcribe using openai-whisper (PyTorch backend)."""
    import whisper

    print(f"Loading Whisper model '{model_size}' (openai-whisper)...")
    model = whisper.load_model(model_size)

    print("Transcribing audio (this may take a while)...")
    result = model.transcribe(
        str(audio_path),
        language=whisper_language(language),
        word_timestamps=word_timestamps,
    )
    return result


def _transcribe_faster(
    audio_path: Path, model_size: str, language: str, word_timestamps: bool
) -> dict:
    """Transcribe using faster-whisper (CTranslate2 backend)."""
    from faster_whisper import WhisperModel

    print(f"Loading Whisper model '{model_size}' (faster-whisper)...")
    model = WhisperModel(model_size, device="auto", compute_type="default")

    print("Transcribing audio (this may take a while)...")
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=whisper_language(language),
        word_timestamps=word_timestamps,
    )

    # Convert faster-whisper segments to the same format as openai-whisper
    segments = []
    full_text_parts = []
    for seg in segments_iter:
        segment = {
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
        }
        if word_timestamps and seg.words:
            segment["words"] = [
                {"word": word.word, "start": word.start, "end": word.end}
                for word in seg.words
            ]
        segments.append(segment)
        full_text_parts.append(seg.text.strip())

    return {
        "text": " ".join(full_text_parts),
        "segments": segments,
        "language": info.language,
    }


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
