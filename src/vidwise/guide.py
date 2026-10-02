"""Guide generation — orchestrates AI analysis and assembles markdown."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from vidwise.frames import batch_frames, select_key_frames, time_range_for_batch
from vidwise.providers.base import GuideProvider
from vidwise.transcriber import segments_for_timerange, segments_to_text
from vidwise.utils import seconds_from_label


def detect_provider(preferred: str = "auto") -> GuideProvider | None:
    """Detect available AI provider based on env vars and preference.

    Returns None if no provider is available.
    """
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if preferred == "claude" or (preferred == "auto" and anthropic_key):
        if not anthropic_key:
            print("Error: ANTHROPIC_API_KEY not set.", file=sys.stderr)
            return None
        from vidwise.providers.claude import ClaudeGuideProvider

        return ClaudeGuideProvider()

    if preferred == "openai" or (preferred == "auto" and openai_key):
        if not openai_key:
            print("Error: OPENAI_API_KEY not set.", file=sys.stderr)
            return None
        from vidwise.providers.openai import OpenAIGuideProvider

        return OpenAIGuideProvider()

    return None


def generate_guide(
    provider: GuideProvider,
    frame_paths: list[Path],
    transcript_result: dict,
    output_dir: Path,
    frame_threshold: float = 0.05,
) -> Path:
    """Generate a visual markdown guide from frames and transcript.

    1. Select key frames (skip near-identical ones)
    2. Batch key frames for efficient API calls
    3. Analyze each batch with the AI provider
    4. Generate overview
    5. Assemble and write guide.md

    Returns path to the generated guide.md.
    """
    segments = transcript_result.get("segments", [])
    full_text = transcript_result.get("text", "")

    # Step 1: Key frame selection
    print("Selecting key frames...")
    key_frames = select_key_frames(frame_paths, threshold=frame_threshold)
    print(f"  {len(key_frames)} key frames selected from {len(frame_paths)} total")

    # Step 2: Batch
    batches = batch_frames(key_frames, max_per_batch=10)

    # Step 3: Analyze each batch
    print(f"Analyzing {len(batches)} segment(s)...")
    batch_results = []
    for i, batch in enumerate(batches):
        time_range = time_range_for_batch(batch)
        start_s = seconds_from_label(batch[0].stem)
        end_s = seconds_from_label(batch[-1].stem) + 2
        transcript_text = segments_to_text(
            segments_for_timerange(segments, start_s, end_s)
        )
        print(f"  Analyzing segment {i + 1}/{len(batches)}: {time_range}")
        result = provider.analyze_batch(batch, transcript_text, time_range)
        batch_results.append(result)

    # Step 4: Generate overview
    print("Generating overview...")
    overview = provider.generate_overview(batch_results, full_text)

    # Step 5: Assemble markdown and HTML
    guide_content = _assemble_markdown(overview, batch_results)
    guide_path = output_dir / "guide.md"
    guide_path.write_text(guide_content)

    html_content = _assemble_html(overview, batch_results)
    html_path = output_dir / "guide.html"
    html_path.write_text(html_content)

    print(f"  Guide written to {guide_path}")
    print(f"  HTML guide written to {html_path}")
    return guide_path


def split_extracted_text(text: str) -> list[dict]:
    """Split a frame's extracted text into code blocks and plain text.

    Fenced blocks (```lang ... ```) become ``{"kind": "code", "lang": ..., "body": ...}``.
    Everything outside a fence becomes ``{"kind": "text", "lang": "", "body": ...}``.
    Text with no fences at all is treated as one unlabelled code block, since it is
    raw screen content. An unclosed fence runs to the end of the text.
    """
    if "```" not in text:
        body = text.strip("\n")
        return [{"kind": "code", "lang": "", "body": body}] if body.strip() else []

    parts: list[dict] = []
    buffer: list[str] = []
    lang = ""
    in_code = False

    def flush(kind: str) -> None:
        body = "\n".join(buffer).strip("\n")
        if body.strip():
            parts.append({"kind": kind, "lang": lang if kind == "code" else "", "body": body})
        buffer.clear()

    for line in text.splitlines():
        if line.strip().startswith("```"):
            if in_code:
                flush("code")
                lang = ""
            else:
                flush("text")
                lang = line.strip()[3:].strip()
            in_code = not in_code
            continue
        buffer.append(line)

    flush("code" if in_code else "text")
    return parts


def collect_captured_code(batch_results: list[dict]) -> list[dict]:
    """Collect every code block from every key frame, in video order.

    Each item is ``{"filename": ..., "lang": ..., "body": ...}``. Identical blocks
    are kept once, at the first frame they appeared in.
    """
    captured: list[dict] = []
    seen: set[str] = set()
    for result in batch_results:
        for kf in result.get("key_frames", []):
            for part in split_extracted_text(kf.get("extracted_text", "")):
                if part["kind"] != "code" or part["body"] in seen:
                    continue
                seen.add(part["body"])
                captured.append({"filename": kf.get("filename", ""), "lang": part["lang"], "body": part["body"]})
    return captured


def _frame_time(filename: str) -> str:
    """Turn ``frame_1m30s.png`` into ``1:30``, or return the filename unchanged."""
    seconds = seconds_from_label(filename) if filename else None
    if seconds is None:
        return filename
    return f"{seconds // 60}:{seconds % 60:02d}"


def _assemble_markdown(overview: dict, batch_results: list[dict]) -> str:
    """Build the final markdown guide string."""
    lines = []

    # Title
    title = overview.get("title", "Video Guide")
    lines.append(f"# {title}\n")

    # Overview
    lines.append("## Overview\n")
    lines.append(overview.get("overview", "") + "\n")

    captured = collect_captured_code(batch_results)
    if captured:
        lines.append("## Captured Code and Commands\n")
        lines.append("Everything shown on screen as code, commands, config, or errors, in the order it appeared.\n")
        for item in captured:
            if item["filename"]:
                lines.append(f"*At {_frame_time(item['filename'])} (`{item['filename']}`)*\n")
            lines.append(f"```{item['lang']}\n{item['body']}\n```\n")

    lines.append("---\n")

    # Sections from batch results
    for result in batch_results:
        summary = result.get("summary", "")
        narrative = result.get("narrative", "")
        key_frames = result.get("key_frames", [])

        if summary:
            lines.append(f"### {summary}\n")

        for kf in key_frames:
            filename = kf.get("filename", "")
            description = kf.get("description", "")
            extracted_text = kf.get("extracted_text", "")
            if filename:
                lines.append(f"![{description}](frames/{filename})\n")
            if description:
                lines.append(f"{description}\n")
            for part in split_extracted_text(extracted_text):
                if part["kind"] == "code":
                    lines.append(f"```{part['lang']}\n{part['body']}\n```\n")
                else:
                    lines.append(f"{part['body']}\n")

        if narrative:
            lines.append(f"{narrative}\n")

        lines.append("---\n")

    # Key takeaways
    takeaways = overview.get("key_takeaways", [])
    if takeaways:
        lines.append("## Key Takeaways\n")
        for t in takeaways:
            lines.append(f"- {t}")
        lines.append("")

    return "\n".join(lines)


def _html_escape(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _html_code_block(lang: str, body: str) -> str:
    """Render one code block as escaped ``<pre><code>`` HTML."""
    css_class = f' class="language-{_html_escape(lang)}"' if lang else ""
    return f"<pre><code{css_class}>{_html_escape(body)}</code></pre>"


def _assemble_html(overview: dict, batch_results: list[dict]) -> str:
    """Build a self-contained HTML guide with embedded dark theme."""
    title = _html_escape(overview.get("title", "Video Guide"))
    overview_text = _html_escape(overview.get("overview", ""))

    parts = []
    parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 860px; margin: 0 auto; padding: 40px 24px; background: #0d1117; color: #e6edf3; line-height: 1.6; }}
  h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 12px; font-size: 28px; }}
  h2 {{ color: #79c0ff; margin-top: 32px; font-size: 20px; }}
  h3 {{ color: #d2a8ff; margin-top: 24px; font-size: 17px; }}
  img {{ max-width: 100%; border-radius: 8px; margin: 12px 0; border: 1px solid #30363d; }}
  hr {{ border: none; border-top: 1px solid #21262d; margin: 28px 0; }}
  ul {{ padding-left: 24px; }}
  li {{ margin: 4px 0; }}
  p {{ margin: 8px 0; }}
  pre {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; overflow-x: auto; font-size: 14px; line-height: 1.45; }}
  code {{ font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; }}
  .badge {{ display: inline-block; background: #1f6feb; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; margin-bottom: 16px; }}
</style>
</head>
<body>

<h1>{title}</h1>
<span class="badge">Generated by vidwise</span>

<h2>Overview</h2>
<p>{overview_text}</p>
""")

    captured = collect_captured_code(batch_results)
    if captured:
        parts.append("<h2>Captured Code and Commands</h2>")
        for item in captured:
            if item["filename"]:
                parts.append(f"<p><em>At {_frame_time(item['filename'])}</em></p>")
            parts.append(_html_code_block(item["lang"], item["body"]))

    parts.append("<hr>")

    for result in batch_results:
        summary = result.get("summary", "")
        narrative = result.get("narrative", "")
        key_frames = result.get("key_frames", [])

        if summary:
            parts.append(f"<h3>{_html_escape(summary)}</h3>")

        for kf in key_frames:
            filename = kf.get("filename", "")
            description = kf.get("description", "")
            extracted_text = kf.get("extracted_text", "")
            if filename:
                alt = _html_escape(description) if description else ""
                parts.append(f'<img src="frames/{filename}" alt="{alt}">')
            if description:
                parts.append(f"<p>{_html_escape(description)}</p>")
            for part in split_extracted_text(extracted_text):
                if part["kind"] == "code":
                    parts.append(_html_code_block(part["lang"], part["body"]))
                else:
                    parts.append(f"<p>{_html_escape(part['body']).replace(chr(10), '<br>')}</p>")

        if narrative:
            parts.append(f"<p>{_html_escape(narrative)}</p>")

        parts.append("<hr>")

    takeaways = overview.get("key_takeaways", [])
    if takeaways:
        parts.append("<h2>Key Takeaways</h2>\n<ul>")
        for t in takeaways:
            parts.append(f"  <li>{_html_escape(t)}</li>")
        parts.append("</ul>")

    parts.append("\n</body>\n</html>")

    return "\n".join(parts)
