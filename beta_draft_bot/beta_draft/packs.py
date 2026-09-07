"""Historically weighted Limited Edition Beta booster generation."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import random
from typing import Protocol, Sequence, TypeVar

from .cards import Card, CardCatalog, default_catalog


_T = TypeVar("_T")


class _Sampler(Protocol):
    def sample(self, population: Sequence[_T], k: int) -> list[_T]: ...


BASIC_LAND_NAMES = frozenset(
    {"Plains", "Island", "Swamp", "Mountain", "Forest"}
)
_COLORS = "WUBRG"

# Each tuple describes physical slots on the corresponding 121-card print
# sheet. Repeated names are deliberately retained rather than converted to
# probabilities, so pack construction can sample sheet positions directly.
BASIC_LAND_SLOTS = {
    "rare": ("Island",) * 4,
    "uncommon": (
        ("Plains",) * 6
        + ("Island",) * 2
        + ("Swamp",) * 6
        + ("Mountain",) * 6
        + ("Forest",) * 6
    ),
    "common": (
        ("Plains",) * 8
        + ("Island",) * 10
        + ("Swamp",) * 9
        + ("Mountain",) * 10
        + ("Forest",) * 9
    ),
}


@dataclass(frozen=True)
class BetaPrintSheets:
    """The three 121-slot sheets used to collate a Beta booster."""

    rare: tuple[Card, ...]
    uncommon: tuple[Card, ...]
    common: tuple[Card, ...]

    def __post_init__(self) -> None:
        for rarity in ("rare", "uncommon", "common"):
            sheet = getattr(self, rarity)
            if len(sheet) != 121:
                raise ValueError(
                    f"Beta {rarity} sheet must contain 121 slots, got {len(sheet)}"
                )

    def for_rarity(self, rarity: str) -> tuple[Card, ...]:
        if rarity == "rare":
            return self.rare
        if rarity == "uncommon":
            return self.uncommon
        if rarity == "common":
            return self.common
        raise ValueError(f"Unknown Beta sheet rarity: {rarity!r}")


def build_beta_print_sheets(
    catalog: CardCatalog | None = None,
) -> BetaPrintSheets:
    """Build the historical sheets from catalog rarity data and land slots."""

    catalog = default_catalog() if catalog is None else catalog
    cards = tuple(catalog)
    by_name = {card.name: card for card in cards}
    if not BASIC_LAND_NAMES <= by_name.keys():
        missing = sorted(BASIC_LAND_NAMES - by_name.keys())
        raise ValueError(f"Beta catalog is missing basic lands: {missing}")

    sheets: dict[str, tuple[Card, ...]] = {}
    expected_nonbasic_counts = {"rare": 117, "uncommon": 95, "common": 75}
    for rarity in ("rare", "uncommon", "common"):
        nonbasics = tuple(
            card
            for card in cards
            if card.rarity == rarity and card.name not in BASIC_LAND_NAMES
        )
        expected = expected_nonbasic_counts[rarity]
        if len(nonbasics) != expected:
            raise ValueError(
                f"Beta catalog must contain {expected} nonbasic {rarity}s, "
                f"got {len(nonbasics)}"
            )
        land_slots = tuple(by_name[name] for name in BASIC_LAND_SLOTS[rarity])
        sheets[rarity] = nonbasics + land_slots

    return BetaPrintSheets(**sheets)


def _common_color(card: Card) -> str | None:
    """Return the one color represented by a colored Beta common."""

    if card.name in BASIC_LAND_NAMES or len(card.colors) != 1:
        return None
    return card.colors[0] if card.colors[0] in _COLORS else None


def _balance_common_colors(
    selected: Sequence[Card],
    common_pool: Sequence[Card],
    rng: _Sampler,
) -> list[Card]:
    """Minimally repair an eleven-common selection to represent every color.

    Commons in colors represented more than once are replaced first. Colorless
    cards and basic lands are touched only when fewer than five colored commons
    were selected, which preserves the ordinary basic-land count whenever the
    original selection has enough colored cards to cover all five colors.
    """

    result = list(selected)
    represented = {_common_color(card) for card in result}
    missing = [color for color in _COLORS if color not in represented]
    for missing_color in rng.sample(missing, len(missing)):
        counts = Counter(
            color for card in result if (color := _common_color(card)) is not None
        )
        donors = [
            index
            for index, card in enumerate(result)
            if (color := _common_color(card)) is not None and counts[color] > 1
        ]
        if not donors:
            donors = [
                index for index, card in enumerate(result)
                if _common_color(card) is None
            ]
        if not donors:
            raise ValueError("cannot color-balance this common selection")
        replacements = [
            card for card in common_pool if _common_color(card) == missing_color
        ]
        if not replacements:
            raise ValueError(
                f"common pool has no card representing {missing_color}"
            )
        result[rng.sample(donors, 1)[0]] = rng.sample(replacements, 1)[0]
    return result


class BetaBoosterGenerator:
    """Open 15-card Beta packs from the historical rarity sheets.

    A pack contains one rare-sheet card, three uncommon-sheet cards, and
    eleven common-sheet cards. Slots are sampled without replacement within
    each sheet for a single pack. Separate packs use fresh virtual sheets.
    """

    def __init__(
        self,
        catalog: CardCatalog | None = None,
        *,
        rng: _Sampler | None = None,
        color_balanced: bool = False,
    ) -> None:
        if type(color_balanced) is not bool:
            raise TypeError("color_balanced must be a boolean")
        self.sheets = build_beta_print_sheets(catalog)
        self.rng = random.Random() if rng is None else rng
        self.color_balanced = color_balanced

    def generate_pack(self) -> tuple[Card, ...]:
        """Return rare, uncommon, then common sheet selections."""

        rare = self.rng.sample(self.sheets.rare, 1)
        uncommons = self.rng.sample(self.sheets.uncommon, 3)
        commons = self.rng.sample(self.sheets.common, 11)
        if self.color_balanced:
            commons = _balance_common_colors(
                commons, self.sheets.common, self.rng
            )
        return tuple(rare + uncommons + commons)


class NoBasicLandBetaBoosterGenerator:
    """Open Beta-card packs after removing basics from all three sheets.

    The rarity structure remains one rare, three uncommons, and eleven
    commons. Nonbasic lands remain eligible according to their printed rarity.
    """

    def __init__(
        self,
        catalog: CardCatalog | None = None,
        *,
        rng: _Sampler | None = None,
        color_balanced: bool = False,
    ) -> None:
        if type(color_balanced) is not bool:
            raise TypeError("color_balanced must be a boolean")
        historical = build_beta_print_sheets(catalog)
        self.rare_pool = tuple(
            card for card in historical.rare if card.name not in BASIC_LAND_NAMES
        )
        self.uncommon_pool = tuple(
            card
            for card in historical.uncommon
            if card.name not in BASIC_LAND_NAMES
        )
        self.common_pool = tuple(
            card for card in historical.common if card.name not in BASIC_LAND_NAMES
        )
        self.rng = random.Random() if rng is None else rng
        self.color_balanced = color_balanced

    def generate_pack(self) -> tuple[Card, ...]:
        """Return one rare, three uncommons, and eleven commons."""

        rare = self.rng.sample(self.rare_pool, 1)
        uncommons = self.rng.sample(self.uncommon_pool, 3)
        commons = self.rng.sample(self.common_pool, 11)
        if self.color_balanced:
            commons = _balance_common_colors(
                commons, self.common_pool, self.rng
            )
        return tuple(rare + uncommons + commons)


def generate_beta_pack(
    *,
    catalog: CardCatalog | None = None,
    rng: _Sampler | None = None,
    color_balanced: bool = False,
) -> tuple[Card, ...]:
    """Convenience function for opening one independently generated pack."""

    return BetaBoosterGenerator(
        catalog, rng=rng, color_balanced=color_balanced
    ).generate_pack()


def generate_no_basic_land_beta_pack(
    *,
    catalog: CardCatalog | None = None,
    rng: _Sampler | None = None,
    color_balanced: bool = False,
) -> tuple[Card, ...]:
    """Convenience function for one Beta pack containing no basic lands."""

    return NoBasicLandBetaBoosterGenerator(
        catalog, rng=rng, color_balanced=color_balanced
    ).generate_pack()


def basic_land_counts(sheet: Sequence[Card]) -> Counter[str]:
    """Return basic-land slot counts, useful for inspection and validation."""

    return Counter(card.name for card in sheet if card.name in BASIC_LAND_NAMES)


__all__ = [
    "BASIC_LAND_NAMES",
    "BASIC_LAND_SLOTS",
    "BetaBoosterGenerator",
    "BetaPrintSheets",
    "NoBasicLandBetaBoosterGenerator",
    "basic_land_counts",
    "build_beta_print_sheets",
    "generate_beta_pack",
    "generate_no_basic_land_beta_pack",
]
