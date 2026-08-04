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


class UpkeepBenefit(str, Enum):
    GAIN_LIFE = "gain_life"
    UNTAP_ATTACHED = "untap_attached"


class VariableStatKind(str, Enum):
    CONTROLLED_NON_WALL_CREATURES = "controlled_non_wall_creatures"
    CONTROLLED_LAND_SUBTYPE = "controlled_land_subtype"
    ALL_CREATURE_SUBTYPE = "all_creature_subtype"
    ATTACKING_DEFENDER_LAND_SUBTYPE = "attacking_defender_land_subtype"


@dataclass(frozen=True, slots=True)
class VariableCreatureStats:
    """A creature's base power and toughness derived from battlefield objects."""

    kind: VariableStatKind
    subtype: str | None = None

    def __post_init__(self) -> None:
        needs_subtype = self.kind in {
            VariableStatKind.CONTROLLED_LAND_SUBTYPE,
            VariableStatKind.ALL_CREATURE_SUBTYPE,
            VariableStatKind.ATTACKING_DEFENDER_LAND_SUBTYPE,
        }
        if needs_subtype != (self.subtype is not None):
            raise ValueError("variable stat subtype does not match its counting rule")


@dataclass(frozen=True, slots=True)
class LandhomeRequirement:
    """Printed land subtype required both at home and for attacking."""

    land_subtype: str

    def __post_init__(self) -> None:
        if not self.land_subtype.strip():
            raise ValueError("a landhome requirement must name a land subtype")


@dataclass(frozen=True, slots=True)
class AttachedLandTypeEffect:
    """Replace an enchanted land's types with one basic land type."""

    replacement_subtype: str | None = None
    chosen_basic_subtype: bool = False

    def __post_init__(self) -> None:
        if (
            self.replacement_subtype is not None
        ) == self.chosen_basic_subtype:
            raise ValueError(
                "an attached land-type effect needs a fixed or chosen subtype"
            )


@dataclass(frozen=True, slots=True)
class GlobalLandTypeConversion:
    """Continuously replace one current land subtype with another."""

    source_subtype: str
    replacement_subtype: str

    def __post_init__(self) -> None:
        if not self.source_subtype.strip() or not self.replacement_subtype.strip():
            raise ValueError("land conversion subtypes cannot be blank")
        if self.source_subtype == self.replacement_subtype:
            raise ValueError("land conversion must change the subtype")


LandTypeEffect = AttachedLandTypeEffect | GlobalLandTypeConversion


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
class DiscardCardsEffect:
    """Make targeted players discard, optionally at random."""

    amount: int = 0
    amount_per_x: int = 0
    random: bool = False


@dataclass(frozen=True, slots=True)
class ShuffleHandAndGraveyardEffect:
    """Recycle each player's hand and graveyard, then draw a new hand."""

    draw_count: int = 7

    def __post_init__(self) -> None:
        if self.draw_count < 0:
            raise ValueError("a replacement hand size cannot be negative")


@dataclass(frozen=True, slots=True)
class SirensCallEffect:
    """Apply Beta Siren's Call to the active player's current creatures."""


@dataclass(frozen=True, slots=True)
class ExtraTurnEffect:
    """Give the spell's caster another turn immediately after this one."""


@dataclass(frozen=True, slots=True)
class LandEventDamageEffect:
    """Damage a player when they put a land in play or lose one."""

    amount: int
    land_enters: bool = False
    land_lost: bool = False

    def __post_init__(self) -> None:
        if self.amount < 1:
            raise ValueError("land-event damage must be positive")
        if self.land_enters == self.land_lost:
            raise ValueError("a land-event effect needs exactly one event")


@dataclass(frozen=True, slots=True)
class AttachedEventDamageEffect:
    """Damage the attached permanent's controller after a matching event."""

    amount: int = 0
    amount_from_toughness: bool = False
    when_tapped: bool = False
    when_destroyed: bool = False

    def __post_init__(self) -> None:
        if self.when_tapped == self.when_destroyed:
            raise ValueError("an attached event needs exactly one trigger")
        if self.amount_from_toughness == bool(self.amount):
            raise ValueError("attached-event damage needs fixed or toughness damage")


@dataclass(frozen=True, slots=True)
class PermanentTappedEffect:
    """Create an effect whenever a matching permanent becomes tapped."""

    damage: int = 0
    life_gain: int = 0
    land_subtype: str | None = None
    opponent_controlled_only: bool = False

    def __post_init__(self) -> None:
        if bool(self.damage) == bool(self.life_gain):
            raise ValueError("a tap event must damage or gain life")
        if self.damage < 0 or self.life_gain < 0:
            raise ValueError("tap-event amounts cannot be negative")


@dataclass(frozen=True, slots=True)
class CounterTargetSpellEffect:
    """Counter the targeted spell during its interrupt window."""

    x_equals_target_cost: bool = False


@dataclass(frozen=True, slots=True)
class ChangeTargetColorEffect:
    """Permanently replace a spell or permanent's color."""

    color: Color

    def __post_init__(self) -> None:
        if self.color is Color.COLORLESS:
            raise ValueError("a Lace must choose one of the five colors")


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
    controller_upkeep_only: bool = False
    source_tapped: bool | None = None

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


@dataclass(frozen=True, slots=True)
class OptionalUpkeepPaymentEffect:
    """A once-per-upkeep payment that grants a benefit when it resolves."""

    mana_cost: ManaCost
    benefit: UpkeepBenefit
    amount: int = 0
    attached_permanent_controller: bool = False
    require_all_matching_attachments: bool = False

    def __post_init__(self) -> None:
        if self.benefit is UpkeepBenefit.GAIN_LIFE and self.amount < 1:
            raise ValueError("life-gain upkeep benefits must be positive")
        if self.benefit is UpkeepBenefit.UNTAP_ATTACHED and self.amount:
            raise ValueError("untap upkeep benefits do not use an amount")


UpkeepEffect = UpkeepDamageEffect | UpkeepCostEffect | OptionalUpkeepPaymentEffect


@dataclass(frozen=True, slots=True)
class DrawPhaseEffect:
    """Draw additional cards during every player's Draw phase."""

    amount: int = 1

    def __post_init__(self) -> None:
        if self.amount < 1:
            raise ValueError("an additional draw amount must be positive")


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
class SetTappedEffect:
    """Tap or untap each targeted permanent, as chosen while casting."""


@dataclass(frozen=True, slots=True)
class AddManaEffect:
    """Add mana to the resolving spell's caster's mana pool."""

    color: Color
    amount: int

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("a mana effect must add a positive amount")


@dataclass(frozen=True, slots=True)
class CombatDestructionEffect:
    """Destroy creatures paired in combat with this creature at combat's end."""

    spare_blocking_walls: bool = True


@dataclass(frozen=True, slots=True)
class DestroyAllEffect:
    """Move all battlefield permanents matching any listed type."""

    card_types: frozenset[CardType]
    subtypes: frozenset[str] = field(default_factory=frozenset)
    regeneration_allowed: bool = True

    def __post_init__(self) -> None:
        if not self.card_types:
            raise ValueError("a global destruction effect must name a card type")

    def matches(
        self,
        card: Card,
        *,
        current_card_types: frozenset[CardType] | None = None,
        current_subtypes: tuple[str, ...] | None = None,
    ) -> bool:
        card_types = (
            card.definition.card_types
            if current_card_types is None
            else current_card_types
        )
        return bool(
            self.card_types & card_types
            and (
                not self.subtypes
                or self.subtypes
                & set(
                    card.definition.subtypes
                    if current_subtypes is None
                    else current_subtypes
                )
            )
        )


SpellEffect = (
    DamageEffect
    | TemporaryPumpEffect
    | RegenerateTargetsEffect
    | GainLifeEffect
    | DrawCardsEffect
    | DiscardCardsEffect
    | ShuffleHandAndGraveyardEffect
    | SirensCallEffect
    | ExtraTurnEffect
    | CounterTargetSpellEffect
    | ChangeTargetColorEffect
    | GlobalDamageEffect
    | DestroyTargetsEffect
    | DestroyAllEffect
    | MoveTargetsEffect
    | SetTappedEffect
    | AddManaEffect
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
    land_subtype: str | None = None
    exclude_source: bool = False
    source_only: bool = False
    controller_only: bool = False
    attacking_only: bool = False
    untapped_only: bool = False
    nonattacking_only: bool = False
    controller_has_land_subtype: str | None = None
    controls_attached_card: bool = False
    granted_card_types: frozenset[CardType] = field(default_factory=frozenset)
    base_stats_from_mana_value: bool = False
    base_power: int | None = None
    base_toughness: int | None = None
    wall_can_attack: bool = False
    blocking_subtype: str | None = None
    blocking_allowed_colors: frozenset[Color] = field(default_factory=frozenset)
    blocking_allowed_card_types: frozenset[CardType] = field(
        default_factory=frozenset
    )
    unblockable: bool = False
    prevents_untap: bool = False
    counted_controller_land_subtype: str | None = None
    power_per_count: int = 0
    toughness_per_count: int = 0
    count_divisor: int = 1
    round_toughness_up: bool = False

    def __post_init__(self) -> None:
        if (self.base_power is None) != (self.base_toughness is None):
            raise ValueError("base power and toughness must be supplied together")
        if (
            self.controls_attached_card
            and self.scope is not EffectScope.ATTACHED_CARD
        ):
            raise ValueError(
                "a control-changing effect must apply to its attached card"
            )
        if self.count_divisor < 1:
            raise ValueError("a dynamic continuous-effect divisor must be positive")
        has_count_scaling = bool(self.power_per_count or self.toughness_per_count)
        if has_count_scaling != (self.counted_controller_land_subtype is not None):
            raise ValueError(
                "count-scaled bonuses must name a controller land subtype"
            )
        if (
            self.counted_controller_land_subtype is not None
            and not self.counted_controller_land_subtype.strip()
        ):
            raise ValueError("a counted controller land subtype cannot be empty")
        if self.round_toughness_up and not self.toughness_per_count:
            raise ValueError("toughness rounding requires a scaled toughness bonus")


# Compatibility name for extensions built against the earlier stat-only model.
CreatureBuff = ContinuousEffect


__all__ = [
    "EffectScope",
    "EffectRecipient",
    "UpkeepDamageRecipient",
    "UpkeepFailure",
    "UpkeepBenefit",
    "VariableStatKind",
    "VariableCreatureStats",
    "LandhomeRequirement",
    "AttachedLandTypeEffect",
    "GlobalLandTypeConversion",
    "LandTypeEffect",
    "DamageEffect",
    "TemporaryPumpEffect",
    "RegenerateTargetsEffect",
    "GainLifeEffect",
    "DrawCardsEffect",
    "DiscardCardsEffect",
    "ShuffleHandAndGraveyardEffect",
    "SirensCallEffect",
    "ExtraTurnEffect",
    "LandEventDamageEffect",
    "AttachedEventDamageEffect",
    "PermanentTappedEffect",
    "CounterTargetSpellEffect",
    "ChangeTargetColorEffect",
    "GlobalDamageEffect",
    "UpkeepDamageEffect",
    "UpkeepCostEffect",
    "OptionalUpkeepPaymentEffect",
    "DrawPhaseEffect",
    "UpkeepEffect",
    "DestroyTargetsEffect",
    "MoveTargetsEffect",
    "SetTappedEffect",
    "AddManaEffect",
    "CombatDestructionEffect",
    "DestroyAllEffect",
    "SpellEffect",
    "ContinuousEffect",
    "CreatureBuff",
]
