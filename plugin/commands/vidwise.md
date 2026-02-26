---
description: Extract knowledge from a video (local file or URL) — transcript, frames, and visual guide
argument-hint: <source> [--model tiny|base|small|medium|large]
---

# vidwise — Make any video AI-readable

Extract a timestamped transcript, key frames, and a visual markdown guide from any video.
Uses the `vidwise` CLI for extraction and Claude Code's native multimodal AI for guide generation — no API key needed.

**Input:** `$ARGUMENTS` — a local file path or URL. Optionally add `--model tiny|base|small|medium|large` (default: medium).

## Instructions

### 1. Check vidwise CLI is installed

```bash
which vidwise
```

If not found, tell the user:
```
vidwise CLI not found. Install it:
  pipx install vidwise
  # or: pip install vidwise
```

Also check ffmpeg. If the source is a URL, check yt-dlp too.

### 2. Parse arguments

Extract the source (first argument) and optional `--model` flag from `$ARGUMENTS`.
Default model: `medium`. For videos >30 min, suggest `small` or `tiny`.

### 3. Run vidwise CLI for extraction

Always pass `--no-guide` because this plugin handles guide generation natively via Claude Code:

```bash
vidwise "<source>" --model <model> --no-guide
```

This produces an output directory with:
- `video.<ext>` — source video
- `audio.wav` — extracted audio
- `transcript.txt` / `transcript.srt` / `transcript.json` — transcript
- `frames/` — frames every 2 seconds, named by timestamp

Note the output directory path from vidwise's output.

### 4. Read transcript and list frames

Read the `.srt` file from the output directory. List all frames in the `frames/` subdirectory.

### 5. Analyze with parallel subagents

Split the video into segments of ~30 seconds each. For each segment, launch a **Task** subagent (general-purpose type) in parallel that:

- Receives the time range, corresponding SRT transcript lines, and frame paths
- Uses the **Read** tool to view each frame image (Claude Code is multimodal)
- Describes what is visible: UI elements, text on screen, navigation, diagrams, people, slides
- Returns: segment summary, key frames (most informative only), and correlated narrative

Launch ALL segment subagents in a single message for maximum parallelism.

### 6. Assemble guide.md

Using the subagent results, write `<output_dir>/guide.md` with:

1. **Title** — descriptive title inferred from the video content
2. **Overview** — 2-3 sentence summary
3. **Step-by-step sections** — for each logical step/topic:
   - Descriptive heading
   - Key frame(s) embedded: `![Description](frames/frame_XmYYs.png)`
   - Clear explanation correlating visuals with transcript
   - Callouts or tips from the narration
4. **Key Takeaways** — bullet point summary

**Guidelines:**
- Use relative paths for images (`frames/frame_1m30s.png`)
- Only include frames showing meaningful visual changes
- Group by logical steps, not raw timestamps
- Write in clear instructional language
- For demos/walkthroughs → step-by-step instructions
- For talks/presentations → summary with key slides
- For bug reports → problem description with visual evidence

### 7. Present results

Tell the user:
1. Output directory path and contents
2. Display the guide content
3. Mention they can feed `guide.md` to any LLM for instant video knowledge

## Notes

- **Model sizes:** tiny (fastest), base, small, medium (recommended), large (best accuracy)
- First run downloads the Whisper model weights (one-time)
- For videos >1hr, use `small` or `tiny` model
- The guide uses relative image paths — it's a self-contained, portable artifact
