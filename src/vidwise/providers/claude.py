"""Claude (Anthropic) AI provider for guide generation."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from vidwise.providers.base import GuideProvider

SYSTEM_PROMPT = """You are a video analysis expert. You receive frames from a video segment \
alongside the transcript text for that segment. Your job is to:

1. Describe what is visible in the key frames (UI, text, navigation, diagrams, people, etc.)
2. Correlate visual content with the narration/transcript
3. Identify which frames show meaningful visual changes

Return your analysis as JSON with this structure:
{
  "summary": "Brief 1-sentence summary of what happens in this segment",
  "key_frames": [
    {"filename": "frame_Xm00s.png", "description": "What this frame shows"}
  ],
  "narrative": "2-3 sentence description correlating visuals with transcript"
}

Only include the most informative frames — skip frames that show the same thing."""

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


class ClaudeGuideProvider(GuideProvider):
    """Generate guides using the Anthropic Claude API."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        import anthropic

        self.client = anthropic.Anthropic()
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
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": data,
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

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )

        return _parse_json_response(response.content[0].text)

    def generate_overview(self, batch_results: list[dict], full_transcript: str) -> dict:
        segments_summary = json.dumps(batch_results, indent=2)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=OVERVIEW_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"Segment analyses:\n{segments_summary}\n\n"
                    f"Full transcript:\n{full_transcript[:3000]}\n\n"
                    "Generate overview JSON."
                ),
            }],
        )

        return _parse_json_response(response.content[0].text)


def _parse_json_response(text: str) -> dict:
    """Parse JSON from an LLM response, handling markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (code fences)
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"summary": text, "key_frames": [], "narrative": text}
