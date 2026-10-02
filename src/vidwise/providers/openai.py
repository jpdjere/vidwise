"""OpenAI API provider for guide generation."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from vidwise.providers.base import GuideProvider

SYSTEM_PROMPT = """You are a video analysis expert. You receive frames from a video segment \
alongside the transcript text for that segment. Your job is to:

1. Describe what is visible in the key frames (UI, text, navigation, diagrams, people, etc.)
2. **Transcribe all visible text verbatim**: code, terminal commands and output, error messages, \
file contents, URLs, configuration values, slide text, and any other readable text
3. Correlate visual content with the narration/transcript
4. Identify which frames show meaningful visual changes

Readers must be able to copy, run, and edit what was on screen from the guide alone. \
Never paraphrase or summarize code, commands, or config. Mark unreadable text as [unreadable] \
instead of guessing.

Capture rules by screen type:
- Code editors/IDEs: the entire visible buffer verbatim, in a fenced block with a language hint. \
Put the file path from the tab or breadcrumb as a first-line comment. Note any unsaved/modified \
marker and the cursor or selection when the narrator points at it. For diff views, mark removed \
lines with - and added lines with +. If the same file changes across frames, show each state.
- Terminals: commands and output verbatim in a fenced block, including the prompt line and any \
exit status.
- Errors, stack traces, logs: verbatim in a fenced block, never shortened.
- Diagrams: describe the structure and transcribe every node and edge label; for architecture \
diagrams, give the direction of each arrow.
- Browser screens: the URL, visible state, table values, and form field contents.
- Slides/documents: the full visible slide or section verbatim.
- Chat panels: each sender name and message text.
- Plain UI labels, menus, headings: plain text, not code blocks.

If a screen stays the same across frames, transcribe it once in the first frame showing it. \
If it changes, capture each distinct state.

Return your analysis as JSON with this structure:
{
  "summary": "Brief 1-sentence summary of what happens in this segment",
  "key_frames": [
    {
      "filename": "frame_Xm00s.png",
      "description": "What this frame shows",
      "extracted_text": "Everything readable in this frame, verbatim. Use ```lang blocks for code/commands/errors, with the file path as a first-line comment when known."
    }
  ],
  "narrative": "2-3 sentence description correlating visuals with transcript"
}

Only include the most informative frames — skip frames that show the same thing. \
Keep summary, description, and narrative short, but never shorten extracted_text."""

OVERVIEW_PROMPT = """Based on the following segment analyses of a video, generate:
1. A descriptive title for the video content
2. A 2-3 sentence overview
3. 3-5 key takeaways as bullet points

Return as JSON:
{
  "title": "Descriptive Title",
  "overview": "2-3 sentence summary of the entire video",
  "key_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"]
}"""


class OpenAIGuideProvider(GuideProvider):
    """Generate guides using the OpenAI API."""

    def __init__(self, model: str = "gpt-4o"):
        import openai

        self.client = openai.OpenAI()
        self.model = model

    def analyze_batch(
        self,
        frame_paths: list[Path],
        transcript_text: str,
        time_range: str,
    ) -> dict:
        content = []

        # Add frames as images
        for frame in frame_paths:
            data = base64.standard_b64encode(frame.read_bytes()).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{data}",
                    "detail": "low",
                },
            })

        # Add transcript text
        content.append({
            "type": "text",
            "text": (
                f"Time range: {time_range}\n\n"
                f"Transcript:\n{transcript_text}\n\n"
                f"Frame filenames: {', '.join(f.name for f in frame_paths)}\n\n"
                "Analyze these frames and transcript. Return JSON only."
            ),
        })

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
        )

        return _parse_json_response(response.choices[0].message.content)

    def generate_overview(self, batch_results: list[dict], full_transcript: str) -> dict:
        segments_summary = json.dumps(batch_results, indent=2)

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": OVERVIEW_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Segment analyses:\n{segments_summary}\n\n"
                        f"Full transcript:\n{full_transcript[:3000]}\n\n"
                        "Generate overview JSON."
                    ),
                },
            ],
        )

        return _parse_json_response(response.choices[0].message.content)


def _parse_json_response(text: str) -> dict:
    """Parse JSON from an LLM response, handling markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"summary": text, "key_frames": [], "narrative": text}
