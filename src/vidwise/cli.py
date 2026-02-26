"""vidwise CLI — extract knowledge from videos for LLMs."""

from __future__ import annotations

from pathlib import Path

import click

from vidwise import __version__
from vidwise.utils import check_dependency, format_output_dir


@click.command()
@click.argument("source")
@click.option(
    "--model", "-m",
    type=click.Choice(["tiny", "base", "small", "medium", "large"]),
    default="medium",
    show_default=True,
    help="Whisper model size (speed vs accuracy).",
)
@click.option(
    "--output-dir", "-o",
    type=click.Path(),
    default=None,
    help="Output directory (default: ./vidwise-<name>-<date>).",
)
@click.option(
    "--no-guide",
    is_flag=True,
    help="Skip AI guide generation (transcript + frames only).",
)
@click.option(
    "--provider", "-p",
    type=click.Choice(["auto", "claude", "openai"]),
    default="auto",
    show_default=True,
    help="AI provider for guide generation.",
)
@click.option(
    "--frame-interval",
    type=int,
    default=2,
    show_default=True,
    help="Seconds between frame captures.",
)
@click.option(
    "--frame-threshold",
    type=float,
    default=0.05,
    show_default=True,
    help="Pixel difference threshold for key frame selection (0.0-1.0).",
)
@click.version_option(version=__version__)
def main(
    source: str,
    model: str,
    output_dir: str | None,
    no_guide: bool,
    provider: str,
    frame_interval: int,
    frame_threshold: float,
) -> None:
    """Extract knowledge from VIDEO for LLMs.

    SOURCE can be a local file path or a URL (YouTube, Loom, etc.).

    \b
    Examples:
      vidwise recording.mp4
      vidwise https://youtube.com/watch?v=abc --model small
      vidwise https://loom.com/share/xyz --provider claude
    """
    from vidwise.downloader import acquire_video, is_url
    from vidwise.extractor import extract_all
    from vidwise.transcriber import transcribe

    # Check dependencies
    if not check_dependency("ffmpeg", "brew install ffmpeg"):
        raise SystemExit(1)
    if is_url(source) and not check_dependency("yt-dlp", "brew install yt-dlp"):
        raise SystemExit(1)

    # Resolve output directory
    if output_dir:
        out = Path(output_dir)
    else:
        out = format_output_dir(source)
    out.mkdir(parents=True, exist_ok=True)
    (out / "frames").mkdir(exist_ok=True)

    print(f"Output: {out}\n")

    # Step 1: Acquire video
    video_path = acquire_video(source, out)
    print(f"  Video: {video_path.name}\n")

    # Step 2: Extract audio + frames (parallel)
    audio_path, frame_paths = extract_all(video_path, out, interval=frame_interval)
    print()

    # Step 3: Transcribe
    transcript_result = transcribe(audio_path, out, model_size=model)
    print()

    # Step 4: Generate guide (optional)
    if not no_guide:
        from vidwise.guide import detect_provider, generate_guide

        ai_provider = detect_provider(provider)
        if ai_provider:
            generate_guide(
                ai_provider,
                frame_paths,
                transcript_result,
                out,
                frame_threshold=frame_threshold,
            )
            print()
        else:
            print(
                "No AI provider configured. Skipping guide generation.\n"
                "Set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable it,\n"
                "or use the Claude Code plugin for free AI-powered guides.\n"
            )

    # Summary
    print("Done! Output directory contents:")
    for f in sorted(out.iterdir()):
        if f.is_dir():
            count = len(list(f.iterdir()))
            print(f"  {f.name}/  ({count} files)")
        else:
            size = f.stat().st_size
            if size > 1024 * 1024:
                print(f"  {f.name}  ({size / 1024 / 1024:.1f} MB)")
            elif size > 1024:
                print(f"  {f.name}  ({size / 1024:.1f} KB)")
            else:
                print(f"  {f.name}  ({size} B)")


if __name__ == "__main__":
    main()
