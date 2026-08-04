"""Short-lived rules events that condition historical activated abilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

from .types import Color


class RuleEventKind(str, Enum):
    SPELL_CAST = "spell_cast"
    CREATURE_DEATH = "creature_death"
    LAND_ENTERED = "land_entered"
    LAND_LOST = "land_lost"
    PERMANENT_TAPPED = "permanent_tapped"
    COMBAT_PLAYER_DAMAGED = "combat_player_damaged"


@dataclass(frozen=True, slots=True)
class RuleEventOpportunity:
    """An event that one or more permanents may catch exactly once."""

    kind: RuleEventKind
    label: str
    spell_id: UUID | None = None
    spell_colors: frozenset[Color] = field(default_factory=frozenset)
    card_id: UUID | None = None
    damage: int = 0
    life_gain: int = 0
    source_id: UUID | None = None
    source_name: str | None = None
    source_controller_id: str | None = None
    affected_player_id: str | None = None
    damage_colors: frozenset[Color] = field(default_factory=frozenset)
    random_discard: int = 0
    id: UUID = field(default_factory=uuid4)


__all__ = ["RuleEventKind", "RuleEventOpportunity"]
