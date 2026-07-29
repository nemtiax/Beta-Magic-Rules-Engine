"""Regeneration-only resolution state for ordinary destroy effects."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class DestructionResolutionStep(str, Enum):
    WAITING = "waiting"
    REGENERATION = "regeneration"
    COMPLETE = "complete"


@dataclass(slots=True)
class DestructionTarget:
    card_id: UUID
    card_name: str
    regeneration_allowed: bool = True


@dataclass(slots=True)
class DestructionIncident:
    """Permanents simultaneously facing an ordinary destroy effect."""

    targets: list[DestructionTarget]
    step: DestructionResolutionStep = DestructionResolutionStep.WAITING
    regenerated_card_ids: set[UUID] = field(default_factory=set)
    id: UUID = field(default_factory=uuid4)
