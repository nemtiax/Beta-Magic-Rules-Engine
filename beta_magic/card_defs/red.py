"""Supported red Beta cards, independent of implemented mechanic."""

from ..types import Color
from ._legacy import LEGACY_CARDS

RED_CARDS = tuple(card for card in LEGACY_CARDS if Color.RED in card.colors)
