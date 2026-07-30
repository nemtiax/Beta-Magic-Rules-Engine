"""Authoritative registry of every currently supported Beta card."""

from __future__ import annotations

from types import MappingProxyType

from ..cards import CardDefinition
from .artifacts import ARTIFACT_CARDS
from .black import BLACK_CARDS
from .blue import BLUE_CARDS
from .green import GREEN_CARDS
from .lands import LAND_CARDS
from .red import RED_CARDS
from .white import WHITE_CARDS


_PRINTED_GROUPS: tuple[tuple[CardDefinition, ...], ...] = (
    WHITE_CARDS,
    BLUE_CARDS,
    BLACK_CARDS,
    RED_CARDS,
    GREEN_CARDS,
    ARTIFACT_CARDS,
    LAND_CARDS,
)


def _build_catalog() -> tuple[CardDefinition, ...]:
    cards_by_name: dict[str, CardDefinition] = {}
    for group in _PRINTED_GROUPS:
        for card in group:
            existing = cards_by_name.setdefault(card.name, card)
            if existing is not card:
                raise RuntimeError(
                    f"conflicting definitions for supported card: {card.name}"
                )

    return tuple(sorted(cards_by_name.values(), key=lambda card: card.name))


ALL_CARDS = _build_catalog()
CARDS_BY_NAME = MappingProxyType({card.name: card for card in ALL_CARDS})


def card_named(name: str) -> CardDefinition:
    """Return a supported card definition by its printed name."""

    try:
        return CARDS_BY_NAME[name]
    except KeyError as error:
        raise KeyError(f"unsupported Beta card: {name}") from error
