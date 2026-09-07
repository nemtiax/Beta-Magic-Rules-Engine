"""Offline Beta catalog and deliberately hand-authored Limited evaluations."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
import json
import re
import unicodedata

COLORS = "WUBRG"


def normalize_name(name: str) -> str:
    if not isinstance(name, str):
        raise TypeError("Card names must be strings")
    name = unicodedata.normalize("NFKC", name).replace("’", "'").replace("‘", "'")
    return " ".join(name.split()).casefold()


@dataclass(frozen=True)
class Card:
    name: str
    mana_cost: str
    mana_value: float
    colors: tuple[str, ...]
    type_line: str
    power: str | None
    toughness: str | None
    keywords: tuple[str, ...]
    produced_mana: tuple[str, ...]
    rules_text: str
    rarity: str
    source: str
    rating: float
    tags: frozenset[str]
    note: str

    def has(self, tag: str) -> bool:
        return tag in self.tags

    @property
    def pips(self) -> int:
        return len(re.findall(r"\{[WUBRG]\}", self.mana_cost))

    @property
    def is_land(self) -> bool:
        return "Land" in self.type_line.split(" — ")[0]

    @property
    def is_creature(self) -> bool:
        return "Creature" in self.type_line.split(" — ")[0]

    @property
    def is_artifact(self) -> bool:
        return "Artifact" in self.type_line.split(" — ")[0]

    @property
    def is_enchantment(self) -> bool:
        return "Enchantment" in self.type_line.split(" — ")[0]

    @property
    def curve_cost(self) -> float:
        """Practical deployment cost; X spells must not look like one-drops."""
        return {
            "Fireball": 5, "Disintegrate": 5, "Earthquake": 4, "Hurricane": 4,
            "Braingeyser": 5, "Drain Life": 5, "Spell Blast": 3, "Power Sink": 3,
            "Howl from Beyond": 3, "Stream of Life": 4, "Mind Twist": 4,
            "Guardian Angel": 3, "Rock Hydra": 6, "Volcanic Eruption": 6,
            "Animate Dead": 4,
        }.get(self.name, self.mana_value)

    @property
    def combat_power(self) -> float:
        overrides = {
            "Clone": 4, "Vesuvan Doppelganger": 4, "Clockwork Beast": 7,
            "Rock Hydra": 4, "Nightmare": 4, "Gaea's Liege": 4,
            "Plague Rats": 1, "Frozen Shade": 2, "Keldon Warlord": 3,
            "Jade Statue": 3, "The Hive": 1, "Animate Dead": 3,
            "Control Magic": 3,
        }
        if self.name in overrides:
            return float(overrides[self.name])
        try:
            return float(self.power or 0)
        except ValueError:
            return 0.0

    @property
    def attacks(self) -> bool:
        return self.has("body") and not self.has("defender") and self.combat_power > 0


class CardCatalog:
    def __init__(self) -> None:
        root = files("beta_draft").joinpath("data")
        payload = json.loads(root.joinpath("cards.json").read_text(encoding="utf-8"))
        ratings = {}
        for line in root.joinpath("ratings.tsv").read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            name, rating, tags, note = line.split("|", 3)
            if name in ratings:
                raise ValueError(f"Duplicate evaluation: {name}")
            ratings[name] = (float(rating), frozenset(tags.split(",")), note)
        names = {row["name"] for row in payload["cards"]}
        if len(payload["cards"]) != 292 or len(names) != 292 or names != set(ratings):
            raise ValueError(f"Incomplete Beta catalog; missing={names - ratings.keys()}, "
                             f"extra={ratings.keys() - names}")
        self._cards = {}
        for row in payload["cards"]:
            row = dict(row)
            for key in ("colors", "keywords", "produced_mana"):
                row[key] = tuple(row[key])
            rating, tags, note = ratings[row["name"]]
            card = Card(**row, rating=rating, tags=tags, note=note)
            self._cards[normalize_name(card.name)] = card

    def get(self, name: str) -> Card:
        try:
            return self._cards[normalize_name(name)]
        except KeyError:
            raise ValueError(f"Unknown Beta card: {name!r}") from None

    def __iter__(self):
        return iter(self._cards.values())

    def __len__(self) -> int:
        return len(self._cards)


@lru_cache(maxsize=1)
def default_catalog() -> CardCatalog:
    return CardCatalog()
