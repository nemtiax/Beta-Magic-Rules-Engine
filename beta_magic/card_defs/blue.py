"""Supported blue Beta cards, independent of implemented mechanic."""

from ..types import Color
from ._legacy import LEGACY_CARDS

BLUE_CARDS = tuple(card for card in LEGACY_CARDS if Color.BLUE in card.colors)
