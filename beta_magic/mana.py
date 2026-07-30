"""Mana-related immutable value objects."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .types import Color

_SYMBOL_RE = re.compile(r"\{([^{}]+)\}")
_COLORED_SYMBOLS = {color.value: color for color in Color if color is not Color.COLORLESS}


@dataclass(frozen=True, slots=True)
class ManaCost:
    """A Beta-era mana cost.

    The object stores generic and colored requirements separately and supports
    the notation used by the supplied card reference, such as ``{2}{U}{U}``.
    A blank string represents no mana cost (normally a land).
    """

    generic: int = 0
    white: int = 0
    blue: int = 0
    black: int = 0
    red: int = 0
    green: int = 0
    x_symbols: int = 0

    def __post_init__(self) -> None:
        if any(value < 0 for value in self.amounts):
            raise ValueError("mana amounts cannot be negative")

    @property
    def amounts(self) -> tuple[int, ...]:
        return (
            self.generic,
            self.white,
            self.blue,
            self.black,
            self.red,
            self.green,
            self.x_symbols,
        )

    @property
    def mana_value(self) -> int:
        return sum(self.amounts[:-1])

    def colored(self, color: Color) -> int:
        fields = {
            Color.WHITE: self.white,
            Color.BLUE: self.blue,
            Color.BLACK: self.black,
            Color.RED: self.red,
            Color.GREEN: self.green,
            Color.COLORLESS: 0,
        }
        return fields[color]

    @classmethod
    def parse(cls, notation: str) -> ManaCost:
        notation = notation.strip().upper()
        if not notation:
            return cls()
        symbols = _SYMBOL_RE.findall(notation)
        if "".join(f"{{{symbol}}}" for symbol in symbols) != notation:
            raise ValueError(f"invalid mana cost: {notation!r}")

        generic = 0
        counts_x = 0
        counts = {color: 0 for color in _COLORED_SYMBOLS.values()}
        for symbol in symbols:
            if symbol.isdecimal():
                generic += int(symbol)
            elif symbol in _COLORED_SYMBOLS:
                counts[_COLORED_SYMBOLS[symbol]] += 1
            elif symbol == "X":
                counts_x += 1
            else:
                raise ValueError(f"unsupported mana symbol: {{{symbol}}}")
        return cls(
            generic=generic,
            white=counts[Color.WHITE],
            blue=counts[Color.BLUE],
            black=counts[Color.BLACK],
            red=counts[Color.RED],
            green=counts[Color.GREEN],
            x_symbols=counts_x,
        )

    def with_x(self, x_value: int) -> ManaCost:
        if x_value < 0:
            raise ValueError("X cannot be negative")
        return ManaCost(
            generic=self.generic + self.x_symbols * x_value,
            white=self.white,
            blue=self.blue,
            black=self.black,
            red=self.red,
            green=self.green,
        )

    @classmethod
    def from_symbols(cls, symbols: Iterable[str]) -> ManaCost:
        return cls.parse("".join(f"{{{symbol}}}" for symbol in symbols))

    def __str__(self) -> str:
        symbols: list[str] = []
        if self.generic:
            symbols.append(str(self.generic))
        symbols.extend("X" for _ in range(self.x_symbols))
        for symbol, count in (
            ("W", self.white),
            ("U", self.blue),
            ("B", self.black),
            ("R", self.red),
            ("G", self.green),
        ):
            symbols.extend(symbol for _ in range(count))
        return "".join(f"{{{symbol}}}" for symbol in symbols)

    @property
    def compact(self) -> str:
        """Card-face notation without braces, such as ``1UU``."""

        symbols: list[str] = []
        if self.generic:
            symbols.append(str(self.generic))
        symbols.extend("X" for _ in range(self.x_symbols))
        symbols.extend("W" for _ in range(self.white))
        symbols.extend("U" for _ in range(self.blue))
        symbols.extend("B" for _ in range(self.black))
        symbols.extend("R" for _ in range(self.red))
        symbols.extend("G" for _ in range(self.green))
        return "".join(symbols)


@dataclass(slots=True)
class ManaPool:
    """Mana currently available to a player."""

    white: int = 0
    blue: int = 0
    black: int = 0
    red: int = 0
    green: int = 0
    colorless: int = 0

    def __post_init__(self) -> None:
        if any(value < 0 for value in self.amounts):
            raise ValueError("mana amounts cannot be negative")

    @property
    def amounts(self) -> tuple[int, ...]:
        return (
            self.white,
            self.blue,
            self.black,
            self.red,
            self.green,
            self.colorless,
        )

    @property
    def total(self) -> int:
        return sum(self.amounts)

    def amount(self, color: Color) -> int:
        return getattr(self, _POOL_FIELDS[color])

    def add(self, color: Color, amount: int = 1) -> None:
        if amount < 0:
            raise ValueError("cannot add a negative amount of mana")
        field_name = _POOL_FIELDS[color]
        setattr(self, field_name, getattr(self, field_name) + amount)

    def can_pay(self, cost: ManaCost) -> bool:
        """Whether this pool can satisfy all colored and generic requirements."""

        colored_requirements = (
            (Color.WHITE, cost.white),
            (Color.BLUE, cost.blue),
            (Color.BLACK, cost.black),
            (Color.RED, cost.red),
            (Color.GREEN, cost.green),
        )
        if any(self.amount(color) < required for color, required in colored_requirements):
            return False
        return self.total >= cost.mana_value

    def pay(self, cost: ManaCost) -> None:
        """Pay a cost atomically, using colorless mana for generic mana first."""

        if not self.can_pay(cost):
            raise ValueError(f"mana pool cannot pay {cost}")

        for color, required in (
            (Color.WHITE, cost.white),
            (Color.BLUE, cost.blue),
            (Color.BLACK, cost.black),
            (Color.RED, cost.red),
            (Color.GREEN, cost.green),
        ):
            field_name = _POOL_FIELDS[color]
            setattr(self, field_name, getattr(self, field_name) - required)

        remaining = cost.generic
        for color in (
            Color.COLORLESS,
            Color.WHITE,
            Color.BLUE,
            Color.BLACK,
            Color.RED,
            Color.GREEN,
        ):
            field_name = _POOL_FIELDS[color]
            spent = min(remaining, getattr(self, field_name))
            setattr(self, field_name, getattr(self, field_name) - spent)
            remaining -= spent
            if not remaining:
                break

    def empty(self) -> int:
        """Remove and return the number of unspent mana."""

        total = self.total
        for field_name in _POOL_FIELDS.values():
            setattr(self, field_name, 0)
        return total


_POOL_FIELDS = {
    Color.WHITE: "white",
    Color.BLUE: "blue",
    Color.BLACK: "black",
    Color.RED: "red",
    Color.GREEN: "green",
    Color.COLORLESS: "colorless",
}
