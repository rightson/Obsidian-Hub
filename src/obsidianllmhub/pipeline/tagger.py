"""Heuristic, offline tagging.

Two signals in the MVP:
  1. languages of fenced code blocks (```python → tag "python")
  2. frequent meaningful keywords across the conversation text

LLM-powered semantic tagging is a planned optional enricher (see
docs/DESIGN.md, milestone M2).
"""

from __future__ import annotations

import re
from collections import Counter

from obsidianllmhub.model import Conversation

_CODE_FENCE = re.compile(r"^```([A-Za-z0-9_+#-]+)", re.MULTILINE)
_WORD = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{3,}")

_STOPWORDS = frozenset(
    """
    that this with have from your what when will would could should there
    their about which they them then than because those these here also
    just like want need make made using used uses each other some more
    most much many very where were does doesn only into over under after
    before between such being been both same how why can you the and for
    not are but has had its it's let lets look looks see way well still
    might may must shall upon out our own too any all say said use two
    first thing things example without however actually really something
    code file line function return value data case work works working
    yes sure okay thanks thank help please here's don't can't want
    """.split()
)


def tags_for(conv: Conversation, max_tags: int = 8) -> list[str]:
    text = "\n".join(m.text for m in conv.messages)

    code_langs = {lang.lower() for lang in _CODE_FENCE.findall(text)}

    prose = _CODE_FENCE.sub("", text)
    words = [w.lower() for w in _WORD.findall(prose)]
    counts = Counter(w for w in words if w not in _STOPWORDS)
    title_words = {w.lower() for w in _WORD.findall(conv.title)}
    for word in list(counts):
        if word in title_words:
            counts[word] += 3  # title words are strong topic signals
    keywords = [w for w, n in counts.most_common(max_tags * 2) if n >= 3]

    tags = sorted(code_langs) + [k for k in keywords if k not in code_langs]
    return tags[:max_tags]
