"""Read-only plans for resolving one 1993 fast-effect batch.

The engine still commits batch members through the established resolution
code.  These data structures provide the stable planning boundary needed to
classify noncommuting effects before any of them changes game state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from .cards import Card
from .casting import AbilityOnStack, SpellOnStack
from .effects import ExileTargetsEffect

if TYPE_CHECKING:
    from .game import PlayerState


class BatchIntentKind(str, Enum):
    """The broad source of a planned batch operation."""

    PERMANENT_ENTRY = "permanent_entry"
    SPELL_EFFECT = "spell_effect"
    ACTIVATED_ABILITY = "activated_ability"


class BatchConflictKind(str, Enum):
    """A noncommuting state change recognized by the batch planner."""

    DESTINATION = "destination"
    TAPPED_STATE = "tapped_state"
    POWER = "power"
    HAND_LIBRARY = "hand_library"
    LAND_TYPE = "land_type"
    TURN_SEQUENCE = "turn_sequence"
    SWORDS_READ = "swords_read"
    AURA_ENTRY = "aura_entry"
    COPY_ENTRY = "copy_entry"
    CHARACTERISTICS = "characteristics"


@dataclass(frozen=True, slots=True)
class BatchLegalitySnapshot:
    """Target and source legality frozen before a batch changes game state."""

    spells: dict[UUID, bool]
    spell_targets: dict[UUID, tuple[Card | PlayerState, ...]]
    abilities: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class BatchEffectIntent:
    """One declarative operation announced as part of a batch.

    ``operation`` remains the existing spell-effect or activated-ability
    object.  A later paradox pass can normalize it into read/write footprints
    without coupling this planning layer to every effect class today.
    """

    kind: BatchIntentKind
    source: Card
    controller_id: str
    decision_maker_id: str
    targets: tuple[Card | PlayerState, ...]
    operation: object
    declaration_sequence: int
    operation_index: int = 0


@dataclass(frozen=True, slots=True)
class BatchConflict:
    """An ordering choice between noncommuting planned intents."""

    intent_indexes: tuple[int, ...]
    chooser_id: str
    reason: str
    kind: BatchConflictKind
    target_ids: tuple[UUID, ...] = ()
    affected_player_ids: tuple[str, ...] = ()


@dataclass(slots=True)
class PendingBatchConflictChoice:
    """The last effect's caster or controller orders a paradox first-to-last."""

    conflict: BatchConflict
    intent_indexes_first_to_last: list[int]


@dataclass(frozen=True, slots=True)
class BatchCharacteristicSnapshot:
    """Characteristic-dependent values observed by one ordered effect."""

    target_ids: tuple[UUID, ...] = ()
    toughness_by_target: tuple[tuple[UUID, int], ...] = ()
    balance_lands: tuple[tuple[str, tuple[UUID, ...]], ...] = ()
    balance_creatures: tuple[tuple[str, tuple[UUID, ...]], ...] = ()


@dataclass(slots=True)
class BatchConsequences:
    """Zone-changing results deferred until every batch member is applied."""

    destruction: list[tuple[Card, bool]] = field(default_factory=list)
    regeneration: list[Card] = field(default_factory=list)
    exile: list[tuple[Card, ExileTargetsEffect, int | None, str | None]] = field(
        default_factory=list
    )


@dataclass(slots=True)
class BatchResolutionPlan:
    """Everything frozen before a fast-effect batch begins committing."""

    cards: tuple[Card, ...]
    spells: tuple[SpellOnStack, ...]
    abilities: tuple[AbilityOnStack, ...]
    legality: BatchLegalitySnapshot
    caught_event_ids: frozenset[UUID]
    intents: tuple[BatchEffectIntent, ...]
    consequences: BatchConsequences = field(default_factory=BatchConsequences)
    destination_orders: dict[UUID, tuple[int, ...]] = field(default_factory=dict)
    tapped_state_orders: dict[UUID, tuple[int, ...]] = field(default_factory=dict)
    power_modifier_orders: list[tuple[int, ...]] = field(default_factory=list)
    hand_library_orders: list[tuple[int, ...]] = field(default_factory=list)
    land_type_orders: list[tuple[int, ...]] = field(default_factory=list)
    turn_sequence_orders: list[tuple[int, ...]] = field(default_factory=list)
    swords_read_orders: list[tuple[int, ...]] = field(default_factory=list)
    swords_power_snapshots: dict[tuple[int, UUID], int] = field(
        default_factory=dict
    )
    swords_controller_snapshots: dict[tuple[int, UUID], str] = field(
        default_factory=dict
    )
    aura_entry_orders: list[tuple[int, ...]] = field(default_factory=list)
    pending_aura_entry_intents: list[int] = field(default_factory=list)
    copy_entry_orders: list[tuple[int, ...]] = field(default_factory=list)
    pending_copy_entry_intents: list[int] = field(default_factory=list)
    characteristic_orders: list[tuple[int, ...]] = field(default_factory=list)
    characteristic_snapshots: dict[int, BatchCharacteristicSnapshot] = field(
        default_factory=dict
    )
    zone_results_applied: bool = False
    pending_hand_library_intents: list[int] = field(default_factory=list)
    commanded_spell_priority_player_index: int | None = None
    commanded_spell_interruptible_id: UUID | None = None
    base_effects_applied: bool = False
    finalized: bool = False


__all__ = [
    "BatchConflict",
    "BatchConflictKind",
    "BatchCharacteristicSnapshot",
    "BatchConsequences",
    "BatchEffectIntent",
    "BatchIntentKind",
    "BatchLegalitySnapshot",
    "PendingBatchConflictChoice",
    "BatchResolutionPlan",
]
