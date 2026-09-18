"""Authoritative catalog access for supported Beta cards.

Printed definitions are organized by color and card type in sibling modules.
This package surface deliberately exposes only the assembled catalog.
"""

from .catalog import ALL_CARDS, CARDS_BY_NAME, card_named

__all__ = ["ALL_CARDS", "CARDS_BY_NAME", "card_named"]
