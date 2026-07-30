"""Supported black Beta cards, independent of implemented mechanic."""

from ..types import Color
from ._legacy import LEGACY_CARDS

BLACK_CARDS = tuple(card for card in LEGACY_CARDS if Color.BLACK in card.colors)
