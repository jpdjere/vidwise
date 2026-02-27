---
name: video-analysis
description: |
  Knowledge about vidwise and video-to-LLM-knowledge extraction.
  Activates when users discuss video transcription, whisper, frame extraction,
  making videos AI-readable, or feeding video content to LLMs.
version: 0.1.0
---

# Video Analysis with vidwise

## Overview

vidwise makes videos AI-readable. LLMs can't watch videos — vidwise bridges that gap by extracting timestamped transcripts and key frames into structured markdown that any LLM can consume as context.

## When to Use

- User mentions video transcription or whisper
- User wants to extract knowledge from a video
- User wants to make a video understandable to an AI/LLM
- User asks about vidwise, frame extraction, or video analysis
- User has a Loom, YouTube, or other video they want to process

## Quick Reference

```bash
# Install
pipx install vidwise

# Basic usage
vidwise recording.mp4
vidwise https://youtube.com/watch?v=abc --model small
vidwise https://loom.com/share/xyz --no-guide

# In Claude Code (no API key needed for guide)
/vidwise:vidwise recording.mp4
/vidwise:vidwise https://loom.com/share/xyz
```

## Output Structure

```
vidwise-<name>-<date>/
├── video.<ext>         # Source video
├── audio.wav           # Extracted 16kHz mono audio
├── transcript.txt      # Plain text transcript
├── transcript.srt      # Timestamped SRT subtitles
├── transcript.json     # Full Whisper output with segments
├── frames/             # PNG frames named by timestamp
│   ├── frame_0m00s.png
│   ├── frame_0m02s.png
│   └── ...
└── guide.md            # Visual guide (if AI provider available)
```

## Whisper Model Sizes

| Model  | Speed    | Quality     | Best For          |
|--------|----------|-------------|-------------------|
| tiny   | Fastest  | Basic       | Quick tests       |
| base   | Fast     | Good        | Short videos      |
| small  | Moderate | Better      | Videos >30 min    |
| medium | Slow     | Recommended | Default           |
| large  | Slowest  | Best        | Critical accuracy |

## Use Cases

- **Bug reports:** Feed Loom recording output to Claude → it "sees" the bug
- **Tutorials:** Absorb knowledge from video courses into LLM context
- **Meetings:** Extract decisions and action items with visual context
- **Talks:** Turn conference presentations into searchable knowledge
- **Onboarding:** Make training videos queryable by AI

## Dependencies

- **Required:** Python 3.10+, ffmpeg
- **Optional:** yt-dlp (for URL downloads)
- **Bundled:** openai-whisper (installed with vidwise)
