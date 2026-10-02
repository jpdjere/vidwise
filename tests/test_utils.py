from vidwise.downloader import is_url
from vidwise.utils import seconds_from_label, timestamp_label


def test_timestamp_label_seconds_only():
    assert timestamp_label(0) == "0m00s"
    assert timestamp_label(5) == "0m05s"
    assert timestamp_label(59) == "0m59s"


def test_timestamp_label_with_minutes():
    assert timestamp_label(60) == "1m00s"
    assert timestamp_label(90) == "1m30s"
    assert timestamp_label(754) == "12m34s"


def test_seconds_from_label():
    assert seconds_from_label("frame_0m00s.png") == 0
    assert seconds_from_label("frame_1m30s.png") == 90
    assert seconds_from_label("frame_12m34s.png") == 754


def test_seconds_from_label_no_match():
    assert seconds_from_label("random.png") is None


def test_is_url():
    assert is_url("https://youtube.com/watch?v=abc") is True
    assert is_url("http://loom.com/share/xyz") is True
    assert is_url("/path/to/video.mp4") is False
    assert is_url("video.mp4") is False


def test_whisper_language_auto_means_detect():
    from vidwise.transcriber import whisper_language

    assert whisper_language("auto") is None
    assert whisper_language("es") == "es"


def test_write_key_frame_index(tmp_path):
    import json

    from vidwise.frames import write_key_frame_index

    frames = tmp_path / "frames"
    frames.mkdir()
    key_frames = [frames / "frame_0m00s.png", frames / "frame_1m30s.png"]
    index_path = write_key_frame_index(key_frames, tmp_path)
    assert index_path == tmp_path / "key_frames.json"
    assert json.loads(index_path.read_text()) == [
        {"seconds": 0, "path": "frames/frame_0m00s.png"},
        {"seconds": 90, "path": "frames/frame_1m30s.png"},
    ]


def test_select_key_frames_keeps_changes_against_the_last_kept_frame(tmp_path):
    from PIL import Image

    from vidwise.frames import select_key_frames

    colors = ["white", "white", "black", "black", "white", "gray", "gray"]
    frames = []
    for second, color in enumerate(colors):
        path = tmp_path / f"frame_0m{second:02d}s.png"
        Image.new("RGB", (64, 36), color).save(path)
        frames.append(path)

    kept = select_key_frames(frames, threshold=0.05)
    assert [path.name for path in kept] == [
        "frame_0m00s.png", "frame_0m02s.png", "frame_0m04s.png", "frame_0m05s.png", "frame_0m06s.png",
    ]
