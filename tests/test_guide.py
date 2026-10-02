from vidwise.guide import (
    _assemble_html,
    _assemble_markdown,
    collect_captured_code,
    split_extracted_text,
)


def test_split_plain_text_is_one_code_block():
    assert split_extracted_text("npm install\nnpm test") == [
        {"kind": "code", "lang": "", "body": "npm install\nnpm test"}
    ]


def test_split_empty_text():
    assert split_extracted_text("") == []
    assert split_extracted_text("\n  \n") == []


def test_split_mixed_text_and_fences():
    text = "Settings > API keys\n```bash\nexport KEY=abc\n```\nSaved\n```python\nprint(1)\n```"
    assert split_extracted_text(text) == [
        {"kind": "text", "lang": "", "body": "Settings > API keys"},
        {"kind": "code", "lang": "bash", "body": "export KEY=abc"},
        {"kind": "text", "lang": "", "body": "Saved"},
        {"kind": "code", "lang": "python", "body": "print(1)"},
    ]


def test_split_unclosed_fence_runs_to_end():
    assert split_extracted_text("```ts\nconst a = 1;") == [
        {"kind": "code", "lang": "ts", "body": "const a = 1;"}
    ]


def test_collect_captured_code_dedupes_and_keeps_order():
    batches = [
        {"key_frames": [
            {"filename": "frame_0m02s.png", "extracted_text": "```bash\nls\n```"},
            {"filename": "frame_0m04s.png", "extracted_text": "Just a label\n```bash\nls\n```"},
        ]},
        {"key_frames": [{"filename": "frame_1m30s.png", "extracted_text": "```py\nx = 1\n```"}]},
    ]
    assert collect_captured_code(batches) == [
        {"filename": "frame_0m02s.png", "lang": "bash", "body": "ls"},
        {"filename": "frame_1m30s.png", "lang": "py", "body": "x = 1"},
    ]


BATCHES = [
    {
        "summary": "Install the CLI",
        "narrative": "The narrator installs it.",
        "key_frames": [
            {
                "filename": "frame_1m30s.png",
                "description": "Terminal",
                "extracted_text": "```bash\n$ pip install vidwise\n```",
            }
        ],
    }
]
OVERVIEW = {"title": "Demo", "overview": "A demo.", "key_takeaways": ["It works"]}


def test_markdown_has_captured_section_and_no_double_fences():
    md = _assemble_markdown(OVERVIEW, BATCHES)
    assert "## Captured Code and Commands" in md
    assert "*At 1:30 (`frame_1m30s.png`)*" in md
    assert md.count("```bash\n$ pip install vidwise\n```") == 2
    assert "``````" not in md


def test_markdown_without_code_has_no_captured_section():
    batches = [{"summary": "Talk", "key_frames": [{"filename": "frame_0m00s.png", "description": "A face"}]}]
    assert "Captured Code" not in _assemble_markdown(OVERVIEW, batches)


def test_html_renders_fences_as_code_not_literal_backticks():
    html = _assemble_html(OVERVIEW, BATCHES)
    assert '<pre><code class="language-bash">$ pip install vidwise</code></pre>' in html
    assert "```" not in html
    assert "<h2>Captured Code and Commands</h2>" in html
