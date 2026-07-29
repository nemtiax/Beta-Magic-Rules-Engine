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
    prevented: int = 0
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.amount < 1:
            raise ValueError("a damage packet must contain positive damage")
        if not 0 <= self.prevented <= self.amount:
            raise ValueError("prevented damage must fit within the packet")

    @property
    def remaining(self) -> int:
        return self.amount - self.prevented


@dataclass(slots=True)
class DamageIncident:
    """All damage assigned simultaneously by one rule event or batch."""

    kind: DamageIncidentKind
    packets: list[DamagePacket] = field(default_factory=list)
    step: DamageResolutionStep = DamageResolutionStep.ACCUMULATION
    regenerated_card_ids: set[UUID] = field(default_factory=set)
    id: UUID = field(default_factory=uuid4)

    @property
    def total_assigned(self) -> int:
        return sum(packet.amount for packet in self.packets)

    @property
    def total_remaining(self) -> int:
        return sum(packet.remaining for packet in self.packets)
