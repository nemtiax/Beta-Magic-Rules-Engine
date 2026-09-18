"""Portable deck-file serialization shared by the draft UI contract."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Iterable


DECK_FORMAT = "beta-magic-deck"
DECK_VERSION = 1


def build_deck_document(name: str, card_names: Iterable[str]) -> dict:
    """Build the versioned JSON-compatible representation of one deck."""

    if not isinstance(name, str) or not name.strip():
        raise ValueError("deck name must be a nonempty string")
    names = list(card_names)
    if any(not isinstance(card_name, str) or not card_name for card_name in names):
        raise ValueError("deck card names must be nonempty strings")
    counts = Counter(names)
    return {
        "format": DECK_FORMAT,
        "version": DECK_VERSION,
        "name": name.strip(),
        "cards": [
            {"name": card_name, "count": count}
            for card_name, count in sorted(counts.items())
        ],
    }


def save_deck_file(
    path: str | Path, name: str, card_names: Iterable[str]
) -> Path:
    """Write one deck as UTF-8 JSON and return its normalized path."""

    destination = Path(path)
    if not destination.suffix:
        destination = destination.with_suffix(".json")
    document = build_deck_document(name, card_names)
    destination.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return destination


__all__ = [
    "DECK_FORMAT",
    "DECK_VERSION",
    "build_deck_document",
    "save_deck_file",
]
