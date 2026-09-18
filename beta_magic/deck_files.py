"""Validation and loading for portable Beta Magic deck files."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .card_defs.catalog import card_named
from .cards import CardDefinition


DECK_FORMAT = "beta-magic-deck"
DECK_VERSION = 1


@dataclass(frozen=True)
class LoadedDeck:
    name: str
    cards: tuple[CardDefinition, ...]


def deck_from_document(document: Any) -> LoadedDeck:
    """Validate a decoded deck document and resolve supported definitions."""

    if not isinstance(document, dict):
        raise ValueError("deck file must contain a JSON object")
    if document.get("format") != DECK_FORMAT:
        raise ValueError(f"deck file format must be {DECK_FORMAT!r}")
    if document.get("version") != DECK_VERSION:
        raise ValueError(f"unsupported deck file version: {document.get('version')!r}")
    name = document.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("deck file name must be a nonempty string")
    rows = document.get("cards")
    if not isinstance(rows, list) or not rows:
        raise ValueError("deck file must contain at least one card entry")

    seen: set[str] = set()
    cards: list[CardDefinition] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each deck card entry must be an object")
        card_name = row.get("name")
        count = row.get("count")
        if not isinstance(card_name, str) or not card_name:
            raise ValueError("each deck card entry needs a nonempty name")
        if card_name in seen:
            raise ValueError(f"duplicate deck card entry: {card_name}")
        if type(count) is not int or count < 1:
            raise ValueError(f"invalid count for {card_name}: {count!r}")
        try:
            definition = card_named(card_name)
        except KeyError as error:
            raise ValueError(str(error.args[0])) from error
        seen.add(card_name)
        cards.extend((definition,) * count)

    if len(cards) < 40:
        raise ValueError(
            f"saved decks must contain at least 40 cards; found {len(cards)}"
        )
    return LoadedDeck(name=name.strip(), cards=tuple(cards))


def load_deck_file(path: str | Path) -> LoadedDeck:
    """Read and validate one deck JSON file."""

    source = Path(path)
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {source}: {error.msg}") from error
    return deck_from_document(document)


__all__ = ["LoadedDeck", "deck_from_document", "load_deck_file"]
