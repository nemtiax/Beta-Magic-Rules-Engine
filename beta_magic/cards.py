"""Static card definitions and mutable physical card instances.

Ability and effect descriptions are re-exported here for compatibility.
New code may import them directly from :mod:`beta_magic.abilities` and
:mod:`beta_magic.effects`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from .abilities import (
    ActivatedAbility,
    ActivatedDamageAbility,
    ActivatedDestroyAbility,
    ActivatedDrawAbility,
    ActivatedManaAbility,
    ActivatedPreventDamageAbility,
    ActivatedPumpAbility,
    ActivatedRegenerationAbility,
    ActivatedTapAbility,
    BatchActivatedAbility,
    TargetedActivatedAbility,
    TargetRequirement,
)
from .effects import (
    ContinuousEffect,
    CreatureBuff,
    DamageEffect,
    DestroyAllEffect,
    DestroyTargetsEffect,
    DrawCardsEffect,
    EffectRecipient,
    EffectScope,
    GainLifeEffect,
    GlobalDamageEffect,
    MoveTargetsEffect,
    RegenerateTargetsEffect,
    SpellEffect,
    TemporaryPumpEffect,
    UpkeepCostEffect,
    UpkeepDamageEffect,
    UpkeepDamageRecipient,
    UpkeepEffect,
    UpkeepFailure,
    VariableCreatureStats,
    VariableStatKind,
)
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility, Zone


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
    prevention_amount: int = 0

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
        if self.prevention_amount < 0:
            raise ValueError("damage prevention cannot be negative")

    @property
    def is_permanent(self) -> bool:
        return bool(
            self.card_types
            & {
                CardType.ARTIFACT,
                CardType.CREATURE,
                CardType.ENCHANTMENT,
                CardType.LAND,
            }
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


__all__ = [
    "Card",
    "CardDefinition",
    "ActivatedAbility",
    "ActivatedDamageAbility",
    "ActivatedDestroyAbility",
    "ActivatedDrawAbility",
    "ActivatedManaAbility",
    "ActivatedPreventDamageAbility",
    "ActivatedPumpAbility",
    "ActivatedRegenerationAbility",
    "ActivatedTapAbility",
    "BatchActivatedAbility",
    "TargetedActivatedAbility",
    "TargetRequirement",
    "ContinuousEffect",
    "CreatureBuff",
    "DamageEffect",
    "DestroyAllEffect",
    "DestroyTargetsEffect",
    "DrawCardsEffect",
    "EffectRecipient",
    "EffectScope",
    "GainLifeEffect",
    "GlobalDamageEffect",
    "MoveTargetsEffect",
    "RegenerateTargetsEffect",
    "SpellEffect",
    "TemporaryPumpEffect",
    "UpkeepCostEffect",
    "UpkeepDamageEffect",
    "UpkeepDamageRecipient",
    "UpkeepEffect",
    "UpkeepFailure",
    "VariableCreatureStats",
    "VariableStatKind",
]
