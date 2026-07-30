"""Supported white Beta cards, independent of implemented mechanic."""

from ..types import Color
from ._legacy import LEGACY_CARDS

WHITE_CARDS = tuple(card for card in LEGACY_CARDS if Color.WHITE in card.colors)
