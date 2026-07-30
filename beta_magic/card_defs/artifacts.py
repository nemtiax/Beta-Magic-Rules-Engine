"""Supported Beta artifacts, including artifact creatures."""

from ..types import CardType
from ._legacy import LEGACY_CARDS

ARTIFACT_CARDS = tuple(
    card for card in LEGACY_CARDS if CardType.ARTIFACT in card.card_types
)
