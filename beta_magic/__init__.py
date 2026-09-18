"""Public rules-engine façade for Beta Magic.

Card definitions, ability descriptions, and effect descriptions live in their
own modules rather than being mirrored into the package root.
"""

from .card_defs import ALL_CARDS, CARDS_BY_NAME, card_named
from .cards import Card, CardDefinition
from .damage import (
    DamageIncident,
    DamageIncidentKind,
    DamagePacket,
    DamageRecipientKind,
    DamageResolutionStep,
    PlayerDamageRecord,
)
from .destruction import (
    DestructionIncident,
    DestructionResolutionStep,
    DestructionTarget,
)
from .events import (
    CardMovedEvent,
    DamageEvent,
    GameEvent,
    ManaBurnEvent,
    SpellCastEvent,
)
from .game import AnteAward, CombatState, GameState, PendingCast, PlayerState
from .mana import (
    LandManaActivation,
    LandManaPaymentPlan,
    ManaAllocation,
    ManaCost,
    ManaPool,
)
from .rule_events import RuleEventKind, RuleEventOpportunity
from .turn_flow import PendingTimedEvent
from .types import (
    BASIC_LAND_SUBTYPES,
    CardType,
    Color,
    CombatStep,
    FaceDownReason,
    GameStatus,
    KeywordAbility,
    RiverSide,
    TurnPhase,
    Zone,
)

__all__ = [
    "ALL_CARDS",
    "AnteAward",
    "BASIC_LAND_SUBTYPES",
    "CARDS_BY_NAME",
    "Card",
    "CardDefinition",
    "CardMovedEvent",
    "CardType",
    "Color",
    "CombatState",
    "CombatStep",
    "DamageEvent",
    "DamageIncident",
    "DamageIncidentKind",
    "DamagePacket",
    "DamageRecipientKind",
    "DamageResolutionStep",
    "DestructionIncident",
    "DestructionResolutionStep",
    "DestructionTarget",
    "FaceDownReason",
    "GameEvent",
    "GameState",
    "GameStatus",
    "KeywordAbility",
    "LandManaActivation",
    "LandManaPaymentPlan",
    "ManaAllocation",
    "ManaBurnEvent",
    "ManaCost",
    "ManaPool",
    "PendingCast",
    "PendingTimedEvent",
    "PlayerDamageRecord",
    "PlayerState",
    "RiverSide",
    "RuleEventKind",
    "RuleEventOpportunity",
    "SpellCastEvent",
    "TurnPhase",
    "Zone",
    "card_named",
]
