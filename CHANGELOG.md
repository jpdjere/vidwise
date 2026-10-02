# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `--language` option: a language code, or `auto` to detect it (default stays `en`)
- `--word-timestamps` flag: per-word timing in `transcript.json`
- `key_frames.json`: the selected key frames and their times, written on every run, including `--no-guide`

### Fixed

- Declare `numpy` and `pillow`, which key frame selection needs

## [0.1.0] - 2026-02-26

### Added

- Core CLI with `vidwise <source>` command
- Whisper-powered transcription (`.txt`, `.srt`, `.json` outputs)
- Frame extraction every N seconds with timestamp-based naming
- Smart key frame selection via pixel-difference analysis
- URL support via yt-dlp (YouTube, Loom, 1000+ sites)
- AI-powered visual guide generation (Claude and OpenAI providers)
- Claude Code plugin with `/vidwise` slash command
- Parallel frame analysis via Claude Code subagents (no API key needed)
