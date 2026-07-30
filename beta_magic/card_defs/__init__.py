"""Authoritative printed-characteristic definitions for supported cards."""

from .artifacts import *
from .black import *
from .blue import *
from .catalog import ALL_CARDS, CARDS_BY_NAME, card_named
from .green import *
from .groups import *
from .lands import *
from .red import *
from .white import *

__all__ = ["ALL_CARDS", "CARDS_BY_NAME", "card_named"] + sorted(
    name for name in globals() if name.isupper()
)
