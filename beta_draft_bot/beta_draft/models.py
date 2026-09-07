from __future__ import annotations

from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class DraftConfig:
    total_picks: int = 45
    pack_size: int = 15
    table_size: int = 8
    allow_ante: bool = False
    allow_dexterity: bool = False
    chaos_orb_hit_rate: float = 0.75
    banned_cards: tuple[str, ...] = ()

    def __post_init__(self):
        for key in ("total_picks", "pack_size", "table_size"):
            value = getattr(self, key)
            if type(value) is not int or value < 1:
                raise ValueError(f"{key} must be a positive integer")
        for key in ("allow_ante", "allow_dexterity"):
            if type(getattr(self, key)) is not bool:
                raise ValueError(f"{key} must be a boolean")
        if (type(self.chaos_orb_hit_rate) not in (int, float)
                or not math.isfinite(self.chaos_orb_hit_rate)
                or not 0 <= self.chaos_orb_hit_rate <= 1):
            raise ValueError("chaos_orb_hit_rate must be between 0 and 1")
        if isinstance(self.banned_cards, str) or not isinstance(self.banned_cards, (tuple, list)):
            raise ValueError("banned_cards must be a list or tuple of card names")
        if any(not isinstance(name, str) for name in self.banned_cards):
            raise ValueError("banned_cards must contain card names")
        object.__setattr__(self, "banned_cards", tuple(self.banned_cards))


@dataclass(frozen=True)
class DraftContext:
    """One-based round and pick; pack_id identifies a physical pack across a wheel."""
    pack_number: int
    pick_number: int
    pack_id: str | None = None

    def __post_init__(self):
        for key in ("pack_number", "pick_number"):
            if type(getattr(self, key)) is not int or getattr(self, key) < 1:
                raise ValueError(f"{key} must be a positive integer")
        if self.pack_id is not None and (not isinstance(self.pack_id, str) or not self.pack_id):
            raise ValueError("pack_id must be a nonempty string or null")


@dataclass(frozen=True)
class ColorPlan:
    colors: tuple[str, ...]
    weight: float


@dataclass(frozen=True)
class PickEvaluation:
    card: str
    index: int
    score: float
    eligible: bool
    components: dict[str, float]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        result = asdict(self)
        result["reasons"] = list(self.reasons)
        return result
