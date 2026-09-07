"""Historical Limited Edition Beta booster and starter collation."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import random
from typing import Protocol, Sequence, TypeVar


_T = TypeVar("_T")


class _Sampler(Protocol):
    def sample(self, population: Sequence[_T], k: int) -> list[_T]: ...


CARD_DATA = Path(__file__).resolve().parents[1] / "cards" / "LEB.json"
BASIC_LAND_NAMES = frozenset(
    {"Plains", "Island", "Swamp", "Mountain", "Forest"}
)


@dataclass(frozen=True)
class BetaPrintSheets:
    """Canonical names in the three 121-slot Beta rarity sheets."""

    rare: tuple[str, ...]
    uncommon: tuple[str, ...]
    common: tuple[str, ...]

    def __post_init__(self) -> None:
        for rarity in ("rare", "uncommon", "common"):
            sheet = getattr(self, rarity)
            if len(sheet) != 121:
                raise ValueError(
                    f"Beta {rarity} sheet must contain 121 slots, got {len(sheet)}"
                )

    def for_rarity(self, rarity: str) -> tuple[str, ...]:
        if rarity not in {"rare", "uncommon", "common"}:
            raise ValueError(f"Unknown Beta sheet rarity: {rarity!r}")
        return getattr(self, rarity)


def _sheet_names(
    sheet: dict,
    names_by_uuid: dict[str, str],
) -> tuple[str, ...]:
    names = []
    for card_id, weight in sheet.get("cards", {}).items():
        if card_id not in names_by_uuid:
            raise ValueError(f"Beta sheet references unknown card UUID {card_id}")
        if type(weight) is not int or weight < 1:
            raise ValueError(f"Beta sheet has invalid weight {weight!r}")
        names.extend([names_by_uuid[card_id]] * weight)
    return tuple(names)


@lru_cache(maxsize=1)
def build_beta_print_sheets(path: Path = CARD_DATA) -> BetaPrintSheets:
    """Load the authoritative sheet slots from the repository's MTGJSON data."""

    payload = json.loads(path.read_text(encoding="utf-8"))["data"]
    names_by_uuid = {card["uuid"]: card["name"] for card in payload["cards"]}
    booster_sheets = payload["booster"]["default"]["sheets"]
    sheets = BetaPrintSheets(
        rare=_sheet_names(booster_sheets["rare"], names_by_uuid),
        uncommon=_sheet_names(booster_sheets["uncommon"], names_by_uuid),
        common=_sheet_names(booster_sheets["common"], names_by_uuid),
    )

    # MTGJSON names the starter versions separately because those products may
    # contain repeated card names. For Beta, they are the same physical sheets.
    starter_sheets = payload["booster"]["starter"]["sheets"]
    starter = BetaPrintSheets(
        rare=_sheet_names(starter_sheets["rare"], names_by_uuid),
        uncommon=_sheet_names(
            starter_sheets["uncommonWithDuplicates"], names_by_uuid
        ),
        common=_sheet_names(
            starter_sheets["commonWithDuplicates"], names_by_uuid
        ),
    )
    if starter != sheets:
        raise ValueError("Beta booster and starter products use different sheets")
    return sheets


class _BetaSealedGenerator:
    def __init__(
        self,
        *,
        sheets: BetaPrintSheets | None = None,
        rng: _Sampler | None = None,
        available_names: set[str] | frozenset[str] | None = None,
    ) -> None:
        self.sheets = build_beta_print_sheets() if sheets is None else sheets
        self.rng = random.Random() if rng is None else rng
        self.available_names = (
            None if available_names is None else frozenset(available_names)
        )

    def _draw(self, rarity: str, count: int) -> list[str]:
        sheet = self.sheets.for_rarity(rarity)
        if self.available_names is not None:
            sheet = tuple(name for name in sheet if name in self.available_names)
        if len(sheet) < count:
            raise ValueError(
                f"Beta {rarity} sheet has only {len(sheet)} available slots; "
                f"cannot draw {count}"
            )
        return self.rng.sample(sheet, count)


class BetaBoosterGenerator(_BetaSealedGenerator):
    """Generate 15-card boosters: one rare, three uncommons, eleven commons."""

    def generate_pack(self) -> tuple[str, ...]:
        return tuple(
            self._draw("rare", 1)
            + self._draw("uncommon", 3)
            + self._draw("common", 11)
        )


class BetaStarterGenerator(_BetaSealedGenerator):
    """Generate 60-card starters: two rares, 13 uncommons, 45 commons."""

    def generate_starter(self) -> tuple[str, ...]:
        return tuple(
            self._draw("rare", 2)
            + self._draw("uncommon", 13)
            + self._draw("common", 45)
        )


def generate_beta_booster(
    *,
    rng: _Sampler | None = None,
    available_names: set[str] | frozenset[str] | None = None,
) -> tuple[str, ...]:
    return BetaBoosterGenerator(
        rng=rng, available_names=available_names
    ).generate_pack()


def generate_beta_starter(
    *,
    rng: _Sampler | None = None,
    available_names: set[str] | frozenset[str] | None = None,
) -> tuple[str, ...]:
    return BetaStarterGenerator(
        rng=rng, available_names=available_names
    ).generate_starter()


__all__ = [
    "BASIC_LAND_NAMES",
    "BetaBoosterGenerator",
    "BetaPrintSheets",
    "BetaStarterGenerator",
    "build_beta_print_sheets",
    "generate_beta_booster",
    "generate_beta_starter",
]
