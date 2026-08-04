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
    ActivatedAnimationAbility,
    ActivatedDestroyAbility,
    ActivatedDestroyAllAbility,
    ActivatedDrawAbility,
    ActivatedDiscardAbility,
    ActivatedAttackRequirementAbility,
    ActivatedLandTypeAbility,
    ActivatedExtraTurnAbility,
    ActivatedEventLifeGainAbility,
    ActivatedManaAbility,
    ActivatedPreventDamageAbility,
    ActivatedRedirectDamageAbility,
    ActivatedPumpAbility,
    ActivatedRegenerationAbility,
    ActivatedTapAbility,
    ActivatedTemporaryAbility,
    ActivatedUntapAbility,
    ActivatedInterruptUntapAbility,
    ActivatedUnblockableAbility,
    BatchActivatedAbility,
    TargetedActivatedAbility,
    TargetRequirement,
)
from .effects import (
    ContinuousEffect,
    CounterTargetSpellEffect,
    ChangeTargetColorEffect,
    CreatureBuff,
    DamageEffect,
    DestroyAllEffect,
    DestroyTargetsEffect,
    DrawCardsEffect,
    DrawPhaseEffect,
    DiscardCardsEffect,
    ShuffleHandAndGraveyardEffect,
    SirensCallEffect,
    ExtraTurnEffect,
    LandEventDamageEffect,
    AttachedEventDamageEffect,
    EffectRecipient,
    EffectScope,
    GainLifeEffect,
    GlobalDamageEffect,
    LandhomeRequirement,
    LandTypeEffect,
    MoveTargetsEffect,
    PermanentTappedEffect,
    OptionalUpkeepPaymentEffect,
    SetTappedEffect,
    AddManaEffect,
    CombatDestructionEffect,
    RegenerateTargetsEffect,
    SpellEffect,
    TemporaryPumpEffect,
    UpkeepCostEffect,
    UpkeepDamageEffect,
    UpkeepDamageRecipient,
    UpkeepEffect,
    UpkeepFailure,
    UpkeepBenefit,
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
    landhome: LandhomeRequirement | None = None
    land_type_effects: tuple[LandTypeEffect, ...] = ()
    produces_mana: Color | None = None
    activated_abilities: tuple[ActivatedAbility, ...] = ()
    supertypes: tuple[str, ...] = ()
    abilities: frozenset[KeywordAbility] = field(default_factory=frozenset)
    continuous_effects: tuple[ContinuousEffect, ...] = ()
    target_requirement: TargetRequirement | None = None
    spell_effects: tuple[SpellEffect, ...] = ()
    upkeep_effects: tuple[UpkeepEffect, ...] = ()
    draw_phase_effects: tuple[DrawPhaseEffect, ...] = ()
    land_event_effects: tuple[LandEventDamageEffect, ...] = ()
    attached_event_damage_effects: tuple[AttachedEventDamageEffect, ...] = ()
    permanent_tapped_effects: tuple[PermanentTappedEffect, ...] = ()
    prevention_amount: int = 0
    casting_modes: tuple[str, ...] = ()
    casting_mode_target_zones: tuple[Zone, ...] = ()
    maximum_blocked_power: int | None = None
    maximum_attackers_blocked: int = 1
    must_attack_if_able: bool = False
    cannot_be_blocked_by_subtypes: frozenset[str] = field(default_factory=frozenset)
    combat_destruction_effects: tuple[CombatDestructionEffect, ...] = ()
    redirects_unblocked_combat_damage: bool = False
    combat_player_damage_random_discard: int = 0
    grows_after_surviving_damage: bool = False
    owner_life_loss_on_death_divisor: int | None = None
    enters_tapped: bool = False
    untaps_normally: bool = True
    may_skip_turn_to_untap: bool = False
    taps_attached_on_entry: bool = False

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
        if (
            self.landhome is not None
            and CardType.CREATURE not in self.card_types
        ):
            raise ValueError("only creatures can have landhome requirements")
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
        if self.land_type_effects and not self.is_permanent:
            raise ValueError("only permanents can change land types")
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
            CardType.INTERRUPT,
            CardType.SORCERY,
        }:
            raise ValueError(
                "only instants, interrupts, and sorceries can have spell effects"
            )
        if self.upkeep_effects and not self.is_permanent:
            raise ValueError("only permanents can supply upkeep effects")
        if self.draw_phase_effects and not self.is_permanent:
            raise ValueError("only permanents can supply draw-phase effects")
        if self.land_event_effects and not self.is_permanent:
            raise ValueError("only permanents can supply land-event effects")
        if self.attached_event_damage_effects and self.target_requirement is None:
            raise ValueError("attached-event effects require an attachment target")
        if self.taps_attached_on_entry and self.target_requirement is None:
            raise ValueError("tapping an attachment target requires a target")
        if self.prevention_amount < 0:
            raise ValueError("damage prevention cannot be negative")
        if len(set(self.casting_modes)) != len(self.casting_modes):
            raise ValueError("casting modes must be unique")
        if any(not mode.strip() for mode in self.casting_modes):
            raise ValueError("casting modes cannot be empty")
        if self.casting_mode_target_zones and len(
            self.casting_mode_target_zones
        ) != len(self.casting_modes):
            raise ValueError(
                "casting-mode target zones must align with casting modes"
            )
        if (
            self.maximum_blocked_power is not None
            and CardType.CREATURE not in self.card_types
        ):
            raise ValueError("only creatures can restrict what they block")
        if self.maximum_attackers_blocked < 1:
            raise ValueError("a creature must be able to block at least one attacker")
        if (
            self.maximum_attackers_blocked != 1
            and CardType.CREATURE not in self.card_types
        ):
            raise ValueError("only creatures can block additional attackers")
        if self.must_attack_if_able and CardType.CREATURE not in self.card_types:
            raise ValueError("only creatures can be required to attack")
        if (
            self.combat_destruction_effects
            and CardType.CREATURE not in self.card_types
        ):
            raise ValueError("only creatures can have combat destruction effects")
        if (
            self.redirects_unblocked_combat_damage
            and CardType.CREATURE not in self.card_types
        ):
            raise ValueError("only creatures can receive redirected combat damage")
        if (
            self.owner_life_loss_on_death_divisor is not None
            and self.owner_life_loss_on_death_divisor < 1
        ):
            raise ValueError("death life-loss divisor must be positive")

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
    battlefield_entry_sequence: int | None = None
    base_controller_id: str | None = None
    controller_at_turn_start_id: str | None = None
    enchanted_card_id: UUID | None = None
    chosen_land_subtype: str | None = None
    color_override: Color | None = None
    plus_one_counters: int = 0
    summoned_turn: int | None = None
    land_type_marks: dict[UUID, tuple[str, int]] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.owner_id:
            raise ValueError("a card must have an owner")
        if self.controller_id is None:
            self.controller_id = self.owner_id
        if self.base_controller_id is None:
            self.base_controller_id = self.controller_id
        if self.damage < 0:
            raise ValueError("damage cannot be negative")
        if self.plus_one_counters < 0:
            raise ValueError("+1/+1 counters cannot be negative")
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
    "ActivatedAnimationAbility",
    "ActivatedDestroyAbility",
    "ActivatedDestroyAllAbility",
    "ActivatedDrawAbility",
    "ActivatedExtraTurnAbility",
    "ActivatedEventLifeGainAbility",
    "ActivatedManaAbility",
    "ActivatedPreventDamageAbility",
    "ActivatedRedirectDamageAbility",
    "ActivatedPumpAbility",
    "ActivatedRegenerationAbility",
    "ActivatedTapAbility",
    "ActivatedTemporaryAbility",
    "ActivatedUntapAbility",
    "ActivatedInterruptUntapAbility",
    "ActivatedUnblockableAbility",
    "BatchActivatedAbility",
    "TargetedActivatedAbility",
    "TargetRequirement",
    "ContinuousEffect",
    "CounterTargetSpellEffect",
    "ChangeTargetColorEffect",
    "CreatureBuff",
    "DamageEffect",
    "DestroyAllEffect",
    "DestroyTargetsEffect",
    "DrawCardsEffect",
    "DrawPhaseEffect",
    "ExtraTurnEffect",
    "LandEventDamageEffect",
    "AttachedEventDamageEffect",
    "EffectRecipient",
    "EffectScope",
    "GainLifeEffect",
    "GlobalDamageEffect",
    "LandhomeRequirement",
    "LandTypeEffect",
    "MoveTargetsEffect",
    "OptionalUpkeepPaymentEffect",
    "SetTappedEffect",
    "AddManaEffect",
    "CombatDestructionEffect",
    "RegenerateTargetsEffect",
    "SpellEffect",
    "TemporaryPumpEffect",
    "UpkeepCostEffect",
    "UpkeepDamageEffect",
    "UpkeepDamageRecipient",
    "UpkeepEffect",
    "UpkeepFailure",
    "UpkeepBenefit",
    "VariableCreatureStats",
    "VariableStatKind",
]
