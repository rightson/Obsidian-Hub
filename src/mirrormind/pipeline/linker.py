"""Link related conversations via tag overlap (Jaccard similarity).

Produces ``[[wiki-link]]`` targets consumable by Obsidian/Logseq. Embedding
similarity replaces/augments this in milestone M2.
"""

from __future__ import annotations

MIN_SHARED_TAGS = 2
MAX_RELATED = 5


def related_map(tagged: dict[str, list[str]]) -> dict[str, list[str]]:
    """Map note-name → related note-names, given note-name → tags."""
    tag_sets = {name: set(tags) for name, tags in tagged.items()}
    result: dict[str, list[str]] = {}
    for name, tags in tag_sets.items():
        scored = []
        for other, other_tags in tag_sets.items():
            if other == name or not tags or not other_tags:
                continue
            shared = tags & other_tags
            if len(shared) >= MIN_SHARED_TAGS:
                jaccard = len(shared) / len(tags | other_tags)
                scored.append((jaccard, other))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        result[name] = [other for _, other in scored[:MAX_RELATED]]
    return result
