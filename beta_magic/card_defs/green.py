"""Supported green Beta cards, independent of implemented mechanic."""

from ..types import Color
from ._legacy import LEGACY_CARDS

GREEN_CARDS = tuple(card for card in LEGACY_CARDS if Color.GREEN in card.colors)
