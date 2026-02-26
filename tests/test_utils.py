from vidwise.utils import timestamp_label, seconds_from_label
from vidwise.downloader import is_url


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
