"""Structured damage descriptions and resolution incidents."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

from .types import Color


class DamageRecipientKind(str, Enum):
    CREATURE = "creature"
    PLAYER = "player"


class DamageIncidentKind(str, Enum):
    SINGLE_SOURCE = "single_source"
    FAST_EFFECT_BATCH = "fast_effect_batch"
    FIRST_STRIKE_COMBAT = "first_strike_combat"
    COMBAT = "combat"
    TIMED_EVENT = "timed_event"
    RULE_EVENT = "rule_event"


class DamageResolutionStep(str, Enum):
    ACCUMULATION = "accumulation"
    PREVENTION = "prevention"
    REDIRECTION = "redirection"
    REGENERATION = "regeneration"
    DEATH = "death"
    COMPLETE = "complete"


@dataclass(slots=True)
class DamagePacket:
    """Damage from one source to one recipient during a single incident."""

    amount: int
    recipient_kind: DamageRecipientKind
    recipient_id: UUID | str
    recipient_name: str
    source_name: str
    source_id: UUID | None = None
    source_controller_id: str | None = None
    colors: frozenset[Color] = field(default_factory=frozenset)
    combat: bool = False
    trample: bool = False
    first_strike: bool = False
    life_gain_player_id: str | None = None
    life_gain_cap: int | None = None
    prevented: int = 0
    life_loss_prevented: int = 0
    converted_life_loss: int = 0
    redirected: int = 0
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.amount < 1:
            raise ValueError("a damage packet must contain positive damage")
        if (
            self.prevented < 0
            or self.life_loss_prevented < 0
            or self.redirected < 0
            or self.prevented + self.redirected > self.amount
            or self.converted_life_loss < 0
        ):
            raise ValueError(
                "prevented and redirected damage must fit within the packet"
            )

    @property
    def remaining(self) -> int:
        return self.amount - self.prevented - self.redirected

    @property
    def resulting_life_loss(self) -> int:
        """Life lost by a player after loss-of-life prevention."""

        return max(
            0,
            self.remaining + self.converted_life_loss - self.life_loss_prevented,
        )


@dataclass(slots=True)
class DamageIncident:
    """All damage assigned simultaneously by one rule event or batch."""

    kind: DamageIncidentKind
    packets: list[DamagePacket] = field(default_factory=list)
    step: DamageResolutionStep = DamageResolutionStep.ACCUMULATION
    regenerated_card_ids: set[UUID] = field(default_factory=set)
    surviving_damage_triggers: dict[UUID, int] = field(default_factory=dict)
    redirected_packets: list[DamagePacket] = field(default_factory=list)
    life_gain_awarded_by_source: dict[UUID, int] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)

    @property
    def total_assigned(self) -> int:
        return sum(packet.amount for packet in self.packets)

    @property
    def total_remaining(self) -> int:
        return sum(packet.remaining for packet in self.packets)


@dataclass(slots=True)
class PlayerDamageRecord:
    """Unreversed damage actually applied to a player during this turn."""

    player_id: str
    amount: int
    source_key: str
    source_name: str
    source_id: UUID | None = None
    source_controller_id: str | None = None
    colors: frozenset[Color] = field(default_factory=frozenset)
    combat: bool = False
    reversed_amount: int = 0

    @property
    def remaining(self) -> int:
        return self.amount - self.reversed_amount
