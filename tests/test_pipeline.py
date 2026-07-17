from obsidianllmhub.model import Conversation, Message, slugify
from obsidianllmhub.pipeline import chunker, linker, markdown, tagger


def _conv(**kwargs):
    defaults = dict(
        id="abc-123",
        title="Test: a conversation",
        source="claude",
        created_at="2026-07-01T09:12:00+00:00",
        updated_at="2026-07-01T09:48:00+00:00",
        messages=[
            Message(role="user", text="What is Redis?"),
            Message(role="assistant", text="Redis is an in-memory data store.\n\n```python\nprint('hi')\n```"),
        ],
    )
    defaults.update(kwargs)
    return Conversation(**defaults)


def test_markdown_render_has_frontmatter_and_sections():
    md = markdown.render(_conv(), tags=["redis", "python"], related=["other-note"])
    assert md.startswith("---\n")
    assert 'title: "Test: a conversation"' in md
    assert "tags: [redis, python]" in md
    assert "## 🧑 User" in md
    assert "## 🤖 Assistant" in md
    assert "- [[other-note]]" in md


def test_markdown_render_is_deterministic():
    assert markdown.render(_conv()) == markdown.render(_conv())


def test_slugify():
    assert slugify("Designing a Rate Limiter") == "designing-a-rate-limiter"
    assert slugify('bad/chars:*?"<>|') == "badchars"
    assert slugify("   ") == "untitled"
    assert len(slugify("x" * 200)) <= 60


def test_chunker_respects_limit_and_boundaries():
    long_text = "para one. " * 50 + "\n\n" + "para two. " * 50
    conv = _conv(messages=[Message(role="user", text=long_text)] * 3)
    chunks = chunker.chunk(conv, max_chars=600)
    assert all(len(c["text"]) <= 600 for c in chunks)
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))
    joined = " ".join(c["text"] for c in chunks)
    assert "para one." in joined and "para two." in joined


def test_tagger_finds_code_language_and_keywords():
    text = "Redis redis redis is great for caching caching caching.\n```python\nx=1\n```"
    conv = _conv(messages=[Message(role="assistant", text=text)])
    tags = tagger.tags_for(conv)
    assert "python" in tags
    assert "redis" in tags


def test_linker_links_by_tag_overlap():
    tagged = {
        "a": ["redis", "python", "cache"],
        "b": ["redis", "python", "queue"],
        "c": ["cooking", "pasta"],
    }
    related = linker.related_map(tagged)
    assert related["a"] == ["b"]
    assert related["b"] == ["a"]
    assert related["c"] == []
