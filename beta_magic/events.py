"""Structured outcomes emitted by rules-engine actions."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from .types import Zone


@dataclass(frozen=True, slots=True)
class CardMovedEvent:
    card_id: UUID
    card_name: str
    source: Zone
    destination: Zone


@dataclass(frozen=True, slots=True)
class SpellCastEvent:
    card_id: UUID
    card_name: str
    caster_id: str
    target_ids: tuple[UUID, ...] = ()
    target_player_ids: tuple[str, ...] = ()
    target_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DamageEvent:
    amount: int
    source: str
    player_id: str | None = None
    card_id: UUID | None = None
    card_name: str | None = None


@dataclass(frozen=True, slots=True)
class ManaBurnEvent:
    player_id: str
    amount: int


GameEvent = CardMovedEvent | SpellCastEvent | DamageEvent | ManaBurnEvent
