"""Static card definitions and mutable physical card instances."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

from .mana import ManaCost
from .types import CardType, Color, KeywordAbility, Zone


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
    | DestroyTargetsEffect
    | DestroyAllEffect
    | MoveTargetsEffect
)


@dataclass(frozen=True, slots=True)
class ActivatedManaAbility:
    """A permanent ability whose cost taps its source to produce one mana."""

    color: Color
    amount: int = 1
    tap_cost: bool = True
    sacrifice_source: bool = False

    def __post_init__(self) -> None:
        if self.amount < 1:
            raise ValueError("a mana ability must produce at least one mana")

    @property
    def label(self) -> str:
        return f"Add {self.color.value * self.amount}"


@dataclass(frozen=True, slots=True)
class ActivatedPumpAbility:
    """A paid ability that temporarily modifies its source or attached creature."""

    mana_cost: ManaCost
    power: int = 0
    toughness: int = 0
    affects_attached_creature: bool = False
    safe_activations_per_turn: int | None = None

    @property
    def label(self) -> str:
        subject = (
            "Enchanted creature gets "
            if self.affects_attached_creature
            else ""
        )
        return (
            f"Pay {self.mana_cost.compact}: {subject}"
            f"{self.power:+d}/{self.toughness:+d} until end of turn"
        )


ActivatedAbility = ActivatedManaAbility | ActivatedPumpAbility


@dataclass(frozen=True, slots=True)
class ContinuousEffect:
    """A declarative characteristic modifier supplied by a permanent."""

    scope: EffectScope = EffectScope.ALL_CREATURES
    power: int = 0
    toughness: int = 0
    granted_abilities: frozenset[KeywordAbility] = field(default_factory=frozenset)
    color: Color | None = None
    subtype: str | None = None
    exclude_source: bool = False
    controller_only: bool = False
    attacking_only: bool = False


# Compatibility name for extensions built against the earlier stat-only model.
CreatureBuff = ContinuousEffect


@dataclass(frozen=True, slots=True)
class TargetRequirement:
    """A declarative requirement for one or more card targets."""

    zone: Zone | None = None
    card_types: frozenset[CardType] = field(default_factory=frozenset)
    any_card_types: frozenset[CardType] = field(default_factory=frozenset)
    players: bool = False
    blocking_only: bool = False
    owner_only: bool = False
    count: int = 1

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError("a target requirement must require at least one target")

        if self.zone is None and not self.players:
            raise ValueError("a target requirement must accept cards or players")
        if self.blocking_only and self.zone is not Zone.BATTLEFIELD:
            raise ValueError("a blocking target must be on the battlefield")

    def accepts_card(self, card: Card) -> bool:
        return (
            self.zone is not None
            and card.zone is self.zone
            and self.card_types.issubset(card.definition.card_types)
            and (
                not self.any_card_types
                or bool(self.any_card_types & card.definition.card_types)
            )
        )

    def accepts(self, card: Card) -> bool:
        """Compatibility alias for card-target checks."""

        return self.accepts_card(card)


@dataclass(frozen=True, slots=True)
class CardDefinition:
    """The characteristics shared by every copy of a printed card."""

    name: str
    card_types: frozenset[CardType]
    mana_cost: ManaCost = field(default_factory=ManaCost)
    rules_text: str = ""
    colors: frozenset[Color] = field(default_factory=frozenset)
    subtypes: tuple[str, ...] = ()
    power: int | None = None
    toughness: int | None = None
    variable_stats: VariableCreatureStats | None = None
    produces_mana: Color | None = None
    activated_abilities: tuple[ActivatedAbility, ...] = ()
    supertypes: tuple[str, ...] = ()
    abilities: frozenset[KeywordAbility] = field(default_factory=frozenset)
    continuous_effects: tuple[ContinuousEffect, ...] = ()
    target_requirement: TargetRequirement | None = None
    spell_effects: tuple[SpellEffect, ...] = ()
    upkeep_effects: tuple[UpkeepEffect, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a card must have a name")
        if not self.card_types:
            raise ValueError("a card must have at least one card type")
        has_one_stat = (self.power is None) != (self.toughness is None)
        if has_one_stat:
            raise ValueError("power and toughness must be specified together")
        if self.power is not None and CardType.CREATURE not in self.card_types:
            raise ValueError("only creatures can have power and toughness")
        if (
            self.variable_stats is not None
            and CardType.CREATURE not in self.card_types
        ):
            raise ValueError("only creatures can have variable stats")
        if self.variable_stats is not None and self.power is not None:
            raise ValueError("variable stats cannot also have printed numeric stats")
        if self.produces_mana is not None and CardType.LAND not in self.card_types:
            raise ValueError("only lands can have an intrinsic mana ability")
        if self.activated_abilities and not self.is_permanent:
            raise ValueError("only permanents can have activated abilities")
        if (
            any(
                isinstance(ability, ActivatedPumpAbility)
                and ability.affects_attached_creature
                for ability in self.activated_abilities
            )
            and self.target_requirement is None
        ):
            raise ValueError("an attached pump ability must define its target requirement")
        if self.continuous_effects and not self.is_permanent:
            raise ValueError("only permanents can supply continuous effects")
        if (
            any(
                effect.scope is EffectScope.ATTACHED_CARD
                for effect in self.continuous_effects
            )
            and self.target_requirement is None
        ):
            raise ValueError("an attached effect must define its target requirement")
        if self.spell_effects and not self.card_types & {
            CardType.INSTANT,
            CardType.SORCERY,
        }:
            raise ValueError("only instants and sorceries can have spell effects")
        if self.upkeep_effects and not self.is_permanent:
            raise ValueError("only permanents can supply upkeep effects")

    @property
    def is_permanent(self) -> bool:
        return bool(
            self.card_types
            & {CardType.ARTIFACT, CardType.CREATURE, CardType.ENCHANTMENT, CardType.LAND}
        )

    @property
    def is_basic_land(self) -> bool:
        return CardType.LAND in self.card_types and "Basic" in self.supertypes

    @property
    def creature_buffs(self) -> tuple[ContinuousEffect, ...]:
        """Compatibility view of global stat effects."""

        return tuple(
            effect
            for effect in self.continuous_effects
            if effect.scope is EffectScope.ALL_CREATURES
            and not effect.granted_abilities
        )

    @property
    def enchanted_creature_buff(self) -> ContinuousEffect | None:
        """Compatibility view of the first attached stat effect."""

        return next(
            (
                effect
                for effect in self.continuous_effects
                if effect.scope is EffectScope.ATTACHED_CARD
                and not effect.granted_abilities
            ),
            None,
        )


@dataclass(slots=True, eq=False)
class Card:
    """One physical copy of a card as it moves through a game."""

    definition: CardDefinition
    owner_id: str
    controller_id: str | None = None
    zone: Zone = Zone.LIBRARY
    tapped: bool = False
    damage: int = 0
    entered_battlefield_turn: int | None = None
    enchanted_card_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.owner_id:
            raise ValueError("a card must have an owner")
        if self.controller_id is None:
            self.controller_id = self.owner_id
        if self.damage < 0:
            raise ValueError("damage cannot be negative")
        if self.zone is not Zone.BATTLEFIELD and self.tapped:
            raise ValueError("only a permanent on the battlefield can be tapped")

    @property
    def name(self) -> str:
        return self.definition.name

    def __hash__(self) -> int:
        return hash(self.id)
