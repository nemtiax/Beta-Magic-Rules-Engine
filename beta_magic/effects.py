"""Declarative descriptions of continuous, spell, and upkeep effects."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from .mana import ManaCost
from .types import CardType, Color, KeywordAbility, Zone

if TYPE_CHECKING:
    from .cards import Card


class EffectScope(str, Enum):
    ALL_CREATURES = "all_creatures"
    ATTACHED_CARD = "attached_card"


class EffectRecipient(str, Enum):
    TARGET = "target"
    CASTER = "caster"


class UpkeepDamageRecipient(str, Enum):
    ACTIVE_PLAYER = "active_player"
    ATTACHED_PERMANENT_CONTROLLER = "attached_permanent_controller"


class UpkeepFailure(str, Enum):
    DESTROY_SOURCE = "destroy_source"
    DAMAGE_CONTROLLER = "damage_controller"


class VariableStatKind(str, Enum):
    CONTROLLED_NON_WALL_CREATURES = "controlled_non_wall_creatures"
    CONTROLLED_LAND_SUBTYPE = "controlled_land_subtype"
    ALL_CREATURE_SUBTYPE = "all_creature_subtype"


@dataclass(frozen=True, slots=True)
class VariableCreatureStats:
    """A creature's base power and toughness derived from battlefield objects."""

    kind: VariableStatKind
    subtype: str | None = None

    def __post_init__(self) -> None:
        needs_subtype = self.kind in {
            VariableStatKind.CONTROLLED_LAND_SUBTYPE,
            VariableStatKind.ALL_CREATURE_SUBTYPE,
        }
        if needs_subtype != (self.subtype is not None):
            raise ValueError("variable stat subtype does not match its counting rule")


@dataclass(frozen=True, slots=True)
class DamageEffect:
    amount: int
    recipient: EffectRecipient = EffectRecipient.TARGET

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("damage cannot be negative")


@dataclass(frozen=True, slots=True)
class TemporaryPumpEffect:
    """Modify targeted creatures until the current turn ends."""

    power: int = 0
    toughness: int = 0
    power_per_x: int = 0
    toughness_per_x: int = 0
    granted_abilities: frozenset[KeywordAbility] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class RegenerateTargetsEffect:
    """Regenerate the spell's creature targets in the current incident."""


@dataclass(frozen=True, slots=True)
class GainLifeEffect:
    """Give targeted players life based on the spell's declared X value."""

    amount: int = 0
    amount_per_x: int = 0

    def __post_init__(self) -> None:
        if self.amount < 0 or self.amount_per_x < 0:
            raise ValueError("life gain cannot be negative")


@dataclass(frozen=True, slots=True)
class DrawCardsEffect:
    """Make targeted players draw a number of cards based on X."""

    amount: int = 0
    amount_per_x: int = 0


@dataclass(frozen=True, slots=True)
class GlobalDamageEffect:
    """Deal X-scaled damage to all players and selected creatures."""

    amount: int = 0
    amount_per_x: int = 0
    creatures_with_flying: bool | None = None
    damage_players: bool = True


@dataclass(frozen=True, slots=True)
class UpkeepDamageEffect:
    """Deal damage to the active player during each player's upkeep."""

    amount: int
    recipient: UpkeepDamageRecipient = UpkeepDamageRecipient.ACTIVE_PLAYER

    def __post_init__(self) -> None:
        if self.amount < 1:
            raise ValueError("upkeep damage must be positive")


@dataclass(frozen=True, slots=True)
class UpkeepCostEffect:
    """An optional mana payment with a consequence for declining."""

    mana_cost: ManaCost
    failure: UpkeepFailure = UpkeepFailure.DESTROY_SOURCE
    damage: int = 0

    def __post_init__(self) -> None:
        if self.failure is UpkeepFailure.DAMAGE_CONTROLLER and self.damage < 1:
            raise ValueError("a damaging upkeep failure must deal positive damage")
        if self.failure is UpkeepFailure.DESTROY_SOURCE and self.damage:
            raise ValueError("source-destruction upkeep cannot also deal damage")


UpkeepEffect = UpkeepDamageEffect | UpkeepCostEffect


@dataclass(frozen=True, slots=True)
class DestroyTargetsEffect:
    """Move the spell's permanent targets to their owners' graveyards."""

    regeneration_allowed: bool = True


@dataclass(frozen=True, slots=True)
class MoveTargetsEffect:
    """Move targeted cards to another zone."""

    destination: Zone
    under_caster_control: bool = False

    def __post_init__(self) -> None:
        if self.destination in {Zone.LIBRARY, Zone.STACK}:
            raise ValueError("unsupported destination for a targeted zone move")
        if self.under_caster_control and self.destination is not Zone.BATTLEFIELD:
            raise ValueError("caster control only applies to battlefield moves")


@dataclass(frozen=True, slots=True)
class DestroyAllEffect:
    """Move all battlefield permanents matching any listed type."""

    card_types: frozenset[CardType]
    subtypes: frozenset[str] = field(default_factory=frozenset)
    regeneration_allowed: bool = True

    def __post_init__(self) -> None:
        if not self.card_types:
            raise ValueError("a global destruction effect must name a card type")

    def matches(self, card: Card) -> bool:
        return bool(
            self.card_types & card.definition.card_types
            and (
                not self.subtypes
                or self.subtypes & set(card.definition.subtypes)
            )
        )


SpellEffect = (
    DamageEffect
    | TemporaryPumpEffect
    | RegenerateTargetsEffect
    | GainLifeEffect
    | DrawCardsEffect
    | GlobalDamageEffect
    | DestroyTargetsEffect
    | DestroyAllEffect
    | MoveTargetsEffect
)


@dataclass(frozen=True, slots=True)
class ContinuousEffect:
    """A declarative characteristic modifier supplied by a permanent."""

    scope: EffectScope = EffectScope.ALL_CREATURES
    power: int = 0
    toughness: int = 0
    granted_abilities: frozenset[KeywordAbility] = field(default_factory=frozenset)
    granted_regeneration_cost: ManaCost | None = None
    color: Color | None = None
    subtype: str | None = None
    exclude_source: bool = False
    source_only: bool = False
    controller_only: bool = False
    attacking_only: bool = False
    untapped_only: bool = False
    nonattacking_only: bool = False
    controller_has_land_subtype: str | None = None


# Compatibility name for extensions built against the earlier stat-only model.
CreatureBuff = ContinuousEffect


__all__ = [
    "EffectScope",
    "EffectRecipient",
    "UpkeepDamageRecipient",
    "UpkeepFailure",
    "VariableStatKind",
    "VariableCreatureStats",
    "DamageEffect",
    "TemporaryPumpEffect",
    "RegenerateTargetsEffect",
    "GainLifeEffect",
    "DrawCardsEffect",
    "GlobalDamageEffect",
    "UpkeepDamageEffect",
    "UpkeepCostEffect",
    "UpkeepEffect",
    "DestroyTargetsEffect",
    "MoveTargetsEffect",
    "DestroyAllEffect",
    "SpellEffect",
    "ContinuousEffect",
    "CreatureBuff",
]
