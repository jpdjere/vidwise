"""Abstract base class for AI guide generation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class GuideProvider(ABC):
    """Abstract base for AI providers that analyze frames and generate guides."""

    @abstractmethod
    def analyze_batch(
        self,
        frame_paths: list[Path],
        transcript_text: str,
        time_range: str,
    ) -> dict:
        """Analyze a batch of frames with corresponding transcript.

        Args:
            frame_paths: Paths to frame images in this batch.
            transcript_text: The transcript text for this time range.
            time_range: Human-readable time range (e.g., "0:30 - 1:00").

        Returns:
            {
                "summary": str,
                "key_frames": [
                    {"filename": str, "description": str}
                ],
                "narrative": str,
            }
        """

    @abstractmethod
    def generate_overview(self, batch_results: list[dict], full_transcript: str) -> dict:
        """Generate title and overview from all batch results.

        Returns:
            {
                "title": str,
                "overview": str,
                "key_takeaways": [str],
            }
        """
