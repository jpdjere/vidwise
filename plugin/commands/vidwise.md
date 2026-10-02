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

Split the video into segments of ~30 seconds each. For each segment, launch a **vidwise:frame-analyzer** subagent in parallel (fall back to general-purpose if that agent type is unavailable, and pass it the capture rules below). Each subagent:

- Receives the time range, corresponding SRT transcript lines, and frame paths
- Uses the **Read** tool to view each frame image (Claude Code is multimodal)
- Describes what is visible: UI elements, text on screen, navigation, diagrams, people, slides
- **Transcribes all visible text verbatim**: code, terminal commands and output, error messages, file contents, URLs, configuration values. Never paraphrase code; a reader must be able to copy and edit it from the guide.
- Returns: segment summary, key frames with descriptions AND extracted text, and correlated narrative

Launch ALL segment subagents in a single message for maximum parallelism.

**Capture rules** (the frame-analyzer agent has the full version):

- **Code editors / IDEs:** the entire visible buffer verbatim, with the file path from the tab or breadcrumb as a first-line comment, the language, any unsaved or modified marker, and the cursor or selection when it matters. Diff views get both sides marked with `-` and `+`. If the same file changes across frames, show the progression.
- **Terminals:** commands and output verbatim, with the prompt line and any exit status.
- **Errors, stack traces, logs:** verbatim, never shortened.
- **Diagrams:** structure plus every node and edge label verbatim; arrow direction for architecture diagrams.
- **Browser screens:** URL, visible state, table values, form field contents.
- **Slides / documents:** the full visible slide or section verbatim.
- **Chat panels:** sender name and message text.
- **Repeated screens:** transcribe once with the time range it was visible. **Changing screens:** capture each distinct state.
- Unreadable text is marked `[unreadable]`, never guessed.

### 6. Assemble guide.md

Using the subagent results, write `<output_dir>/guide.md` with:

1. **Title** — descriptive title inferred from the video content
2. **Overview** — 2-3 sentence summary
3. **Captured code and commands** — only if anything was shown on screen. Every verbatim code snapshot, terminal command, config file, and error collected in one place, each in a fenced block with the file path as a first-line comment and the timestamp it appeared. This is the section a reader (or an LLM) uses to pick up the work without watching the video.
4. **Step-by-step sections** — for each logical step/topic:
   - Descriptive heading
   - Key frame(s) embedded: `![Description](frames/frame_XmYYs.png)`
   - Clear explanation correlating visuals with transcript
   - Callouts or tips from the narration
   - The verbatim code, commands, or text shown during this step
5. **Key Takeaways** — bullet point summary

**Guide style — content-type-aware formatting:**
- **Tutorials/demos:** Numbered step-by-step instructions with actual commands/code in fenced code blocks (```bash, ```python, etc.). The user should be able to follow the guide without watching the video.
- **Meetings/talks:** Extract decisions, action items, and any text shown on screen (slides, whiteboards). Summarize key discussion points.
- **Bug reports:** Extract error messages and stack traces verbatim as code blocks. Include reproduction steps if shown.
- **Presentations:** Extract slide text, key bullet points, and diagrams. Organize by slide/topic.

**Rendering extracted text:**
- Code, commands, terminal output, config → fenced code blocks with language hint
- Error messages, stack traces, logs → fenced code blocks
- UI labels, headings → inline text
- If the subagent returned extracted text for a key frame, render it as a code block after the frame image
- Copy extracted text exactly as the subagent returned it. Do not shorten, tidy, or summarize code while assembling the guide.

**General guidelines:**
- Use relative paths for images (`frames/frame_1m30s.png`)
- Only include frames showing meaningful visual changes
- Group by logical steps, not raw timestamps
- Write in clear instructional language

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
