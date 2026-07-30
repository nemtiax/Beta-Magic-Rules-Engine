"""Supported Beta lands."""

from ..types import CardType
from ._legacy import LEGACY_CARDS

LAND_CARDS = tuple(
    card for card in LEGACY_CARDS if CardType.LAND in card.card_types
)
