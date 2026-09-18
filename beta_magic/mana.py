"""Mana-related immutable value objects."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable
from uuid import UUID

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

    def scaled(self, multiplier: int) -> ManaCost:
        """Repeat every symbol in this cost a fixed number of times."""

        if multiplier < 0:
            raise ValueError("mana-cost multiplier cannot be negative")
        return ManaCost(*(amount * multiplier for amount in self.amounts))

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


@dataclass(frozen=True, slots=True)
class ManaAllocation:
    """A color-by-color quantity of mana produced, spent, or retained."""

    white: int = 0
    blue: int = 0
    black: int = 0
    red: int = 0
    green: int = 0
    colorless: int = 0

    def __post_init__(self) -> None:
        if any(value < 0 for value in self.amounts):
            raise ValueError("mana allocations cannot contain negative amounts")

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

    @classmethod
    def from_amounts(cls, amounts: Iterable[int]) -> ManaAllocation:
        values = tuple(amounts)
        if len(values) != len(Color):
            raise ValueError("a mana allocation needs one amount per color")
        return cls(*values)


@dataclass(frozen=True, slots=True)
class LandManaActivation:
    """One currently available mana mode of one controlled land."""

    land_id: UUID
    land_name: str
    ability_index: int
    production: ManaAllocation


@dataclass(frozen=True, slots=True)
class LandManaPaymentPlan:
    """A validated set of land activations and the resulting mana payment."""

    activations: tuple[LandManaActivation, ...]
    production: ManaAllocation
    spending: ManaAllocation
    excess_production: int

    @property
    def exact(self) -> bool:
        """Whether every unit produced by the selected lands can be spent."""

        return self.excess_production == 0


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

    @classmethod
    def from_amounts(cls, amounts: Iterable[int]) -> ManaPool:
        values = tuple(amounts)
        if len(values) != len(Color):
            raise ValueError("a mana pool needs one amount per color")
        return cls(*values)

    def add(self, color: Color, amount: int = 1) -> None:
        if amount < 0:
            raise ValueError("cannot add a negative amount of mana")
        field_name = _POOL_FIELDS[color]
        setattr(self, field_name, getattr(self, field_name) + amount)

    def _payment_plan(
        self,
        cost: ManaCost,
        substitutions: tuple[tuple[Color, Color], ...] = (),
    ) -> dict[Color, int] | None:
        """Return mana spent by source color, including allowed substitutions."""

        available = {color: self.amount(color) for color in Color}
        spent = {color: 0 for color in Color}
        requirements = {
            Color.WHITE: cost.white,
            Color.BLUE: cost.blue,
            Color.BLACK: cost.black,
            Color.RED: cost.red,
            Color.GREEN: cost.green,
        }
        for color, required in requirements.items():
            exact = min(required, available[color])
            available[color] -= exact
            spent[color] += exact
            requirements[color] -= exact
        for paid_as, required in requirements.items():
            for source, accepted_as in substitutions:
                if accepted_as is not paid_as or not required:
                    continue
                substituted = min(required, available[source])
                available[source] -= substituted
                spent[source] += substituted
                required -= substituted
            if required:
                return None
        remaining = cost.generic
        for color in (
            Color.COLORLESS,
            Color.WHITE,
            Color.BLUE,
            Color.BLACK,
            Color.RED,
            Color.GREEN,
        ):
            generic = min(remaining, available[color])
            available[color] -= generic
            spent[color] += generic
            remaining -= generic
            if not remaining:
                break
        return None if remaining else spent

    def payment_plans(
        self,
        cost: ManaCost,
        substitutions: tuple[tuple[Color, Color], ...] = (),
    ) -> tuple[ManaAllocation, ...]:
        """Return every color allocation that can pay ``cost``.

        Ordinary payments retain their deterministic historical behavior via
        :meth:`pay`.  Effects which give another player control over payment
        decisions need the full set so they can distinguish, for example,
        spending red rather than green mana on a generic cost.
        """

        colors = tuple(Color)
        color_indexes = {color: index for index, color in enumerate(colors)}
        initial_available = self.amounts
        initial_spent = (0,) * len(colors)
        states = {(initial_available, initial_spent)}

        def allocations(
            required: int,
            source_indexes: tuple[int, ...],
            available: tuple[int, ...],
        ) -> tuple[tuple[int, ...], ...]:
            results: list[tuple[int, ...]] = []

            def visit(position: int, remaining: int, chosen: list[int]) -> None:
                if position == len(source_indexes):
                    if remaining == 0:
                        result = [0] * len(colors)
                        for source_index, amount in zip(source_indexes, chosen):
                            result[source_index] = amount
                        results.append(tuple(result))
                    return
                source_index = source_indexes[position]
                maximum = min(remaining, available[source_index])
                for amount in range(maximum + 1):
                    chosen.append(amount)
                    visit(position + 1, remaining - amount, chosen)
                    chosen.pop()

            visit(0, required, [])
            return tuple(results)

        colored_requirements = (
            (Color.WHITE, cost.white),
            (Color.BLUE, cost.blue),
            (Color.BLACK, cost.black),
            (Color.RED, cost.red),
            (Color.GREEN, cost.green),
        )
        for paid_as, required in colored_requirements:
            if not required:
                continue
            eligible = [paid_as]
            eligible.extend(
                source
                for source, accepted_as in substitutions
                if accepted_as is paid_as and source not in eligible
            )
            source_indexes = tuple(color_indexes[color] for color in eligible)
            next_states: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()
            for available, spent in states:
                for allocated in allocations(required, source_indexes, available):
                    next_states.add(
                        (
                            tuple(
                                amount - used
                                for amount, used in zip(available, allocated)
                            ),
                            tuple(
                                amount + used
                                for amount, used in zip(spent, allocated)
                            ),
                        )
                    )
            states = next_states
            if not states:
                return ()

        generic_indexes = tuple(
            color_indexes[color]
            for color in (
                Color.COLORLESS,
                Color.WHITE,
                Color.BLUE,
                Color.BLACK,
                Color.RED,
                Color.GREEN,
            )
        )
        final_spending: set[tuple[int, ...]] = set()
        for available, spent in states:
            for allocated in allocations(cost.generic, generic_indexes, available):
                final_spending.add(
                    tuple(
                        amount + used
                        for amount, used in zip(spent, allocated)
                    )
                )
        return tuple(
            ManaAllocation.from_amounts(amounts)
            for amounts in sorted(final_spending)
        )

    def pay_allocation(self, allocation: ManaAllocation) -> None:
        """Spend an already selected, color-specific payment allocation."""

        if any(
            amount > self.amount(color)
            for color, amount in zip(Color, allocation.amounts)
        ):
            raise ValueError("mana pool cannot pay the selected allocation")
        for color, amount in zip(Color, allocation.amounts):
            field_name = _POOL_FIELDS[color]
            setattr(self, field_name, getattr(self, field_name) - amount)

    def can_pay(
        self,
        cost: ManaCost,
        substitutions: tuple[tuple[Color, Color], ...] = (),
    ) -> bool:
        """Whether this pool can satisfy all colored and generic requirements."""

        return self._payment_plan(cost, substitutions) is not None

    def pay(
        self,
        cost: ManaCost,
        substitutions: tuple[tuple[Color, Color], ...] = (),
    ) -> None:
        """Pay a cost atomically, using colorless mana for generic mana first."""

        plan = self._payment_plan(cost, substitutions)
        if plan is None:
            raise ValueError(f"mana pool cannot pay {cost}")
        for color, amount in plan.items():
            field_name = _POOL_FIELDS[color]
            setattr(self, field_name, getattr(self, field_name) - amount)

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
