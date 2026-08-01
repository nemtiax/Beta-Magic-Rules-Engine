"""Target requirements and declarative activated-ability descriptions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .mana import ManaCost
from .types import CardType, Color, KeywordAbility, Zone

if TYPE_CHECKING:
    from .cards import Card


@dataclass(frozen=True, slots=True)
class TargetRequirement:
    """A declarative requirement for one or more card targets."""

    zone: Zone | None = None
    additional_zones: frozenset[Zone] = field(default_factory=frozenset)
    card_types: frozenset[CardType] = field(default_factory=frozenset)
    any_card_types: frozenset[CardType] = field(default_factory=frozenset)
    excluded_card_types: frozenset[CardType] = field(default_factory=frozenset)
    players: bool = False
    opponent_only: bool = False
    blocking_only: bool = False
    tapped_only: bool = False
    color: Color | None = None
    excluded_colors: frozenset[Color] = field(default_factory=frozenset)
    subtypes: frozenset[str] = field(default_factory=frozenset)
    owner_only: bool = False
    controller_only: bool = False
    maximum_power: int | None = None
    count: int = 1

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError("a target requirement must require at least one target")
        if self.zone is None and not self.additional_zones and not self.players:
            raise ValueError("a target requirement must accept cards or players")
        if self.blocking_only and self.zone is not Zone.BATTLEFIELD:
            raise ValueError("a blocking target must be on the battlefield")
        if self.owner_only and self.controller_only:
            raise ValueError("a target cannot require both owner and controller")
        if self.opponent_only and not self.players:
            raise ValueError("an opponent-only target must accept players")

    def accepts_card(
        self,
        card: Card,
        *,
        check_tapped: bool = True,
        current_colors: frozenset[Color] | None = None,
        current_card_types: frozenset[CardType] | None = None,
    ) -> bool:
        return (
            (self.zone is not None or self.additional_zones)
            and card.zone in (
                self.additional_zones
                | (frozenset({self.zone}) if self.zone is not None else frozenset())
            )
            and self.card_types.issubset(
                card.definition.card_types
                if current_card_types is None
                else current_card_types
            )
            and not (
                self.excluded_card_types
                & (
                    card.definition.card_types
                    if current_card_types is None
                    else current_card_types
                )
            )
            and (not check_tapped or not self.tapped_only or card.tapped)
            and (
                self.color is None
                or self.color
                in (
                    card.definition.colors
                    if current_colors is None
                    else current_colors
                )
            )
            and not (
                self.excluded_colors
                & (
                    card.definition.colors
                    if current_colors is None
                    else current_colors
                )
            )
            and (
                not self.subtypes
                or bool(self.subtypes & set(card.definition.subtypes))
            )
            and (
                not self.any_card_types
                or bool(
                    self.any_card_types
                    & (
                        card.definition.card_types
                        if current_card_types is None
                        else current_card_types
                    )
                )
            )
        )

    def accepts(self, card: Card) -> bool:
        """Compatibility alias for card-target checks."""

        return self.accepts_card(card)


@dataclass(frozen=True, slots=True)
class ActivatedManaAbility:
    """A permanent ability whose cost taps its source to produce mana."""

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
    """A paid ability that temporarily modifies its source or attachment."""

    mana_cost: ManaCost
    power: int = 0
    toughness: int = 0
    granted_abilities: frozenset[KeywordAbility] = field(default_factory=frozenset)
    affects_attached_creature: bool = False
    safe_activations_per_turn: int | None = None

    @property
    def label(self) -> str:
        subject = (
            "Enchanted creature gets "
            if self.affects_attached_creature
            else ""
        )
        effect = (
            "/".join(ability.value for ability in self.granted_abilities)
            if self.granted_abilities
            else f"{self.power:+d}/{self.toughness:+d}"
        )
        return f"Pay {self.mana_cost.compact}: {subject}{effect} until end of turn"


@dataclass(frozen=True, slots=True)
class ActivatedDamageAbility:
    """A targeted fast effect that deals damage."""

    damage: int
    target_requirement: TargetRequirement
    controller_damage: int = 0
    tap_cost: bool = True
    mana_cost: ManaCost = field(default_factory=ManaCost)

    def __post_init__(self) -> None:
        if self.damage < 1:
            raise ValueError("an activated damage ability must deal damage")

    @property
    def label(self) -> str:
        suffix = (
            f" and {self.controller_damage} damage to you"
            if self.controller_damage
            else ""
        )
        cost = (
            f"Pay {self.mana_cost.compact} and tap"
            if self.mana_cost.mana_value
            else "Tap"
        )
        return f"{cost}: Deal {self.damage} damage to any target{suffix}"


@dataclass(frozen=True, slots=True)
class ActivatedDestroyAbility:
    target_requirement: TargetRequirement
    mana_cost: ManaCost = field(default_factory=ManaCost)
    tap_cost: bool = True
    regeneration_allowed: bool = True

    @property
    def label(self) -> str:
        cost = (
            f"Pay {self.mana_cost.compact} and tap"
            if self.mana_cost.mana_value
            else "Tap"
        )
        return f"{cost}: Destroy target permanent"


@dataclass(frozen=True, slots=True)
class ActivatedTapAbility:
    target_requirement: TargetRequirement
    mana_cost: ManaCost = field(default_factory=ManaCost)
    tap_cost: bool = True

    @property
    def label(self) -> str:
        return f"Pay {self.mana_cost.compact} and tap: Tap target permanent"


@dataclass(frozen=True, slots=True)
class ActivatedUnblockableAbility:
    """A targeted fast effect that makes a creature unblockable this turn."""

    target_requirement: TargetRequirement
    tap_cost: bool = True
    mana_cost: ManaCost = field(default_factory=ManaCost)

    @property
    def label(self) -> str:
        return "Tap: Target creature is unblockable this turn"


@dataclass(frozen=True, slots=True)
class ActivatedTemporaryAbility:
    """Grant a target an ability temporarily, with an optional delayed cost."""

    target_requirement: TargetRequirement
    granted_abilities: frozenset[KeywordAbility] = field(default_factory=frozenset)
    mana_cost: ManaCost = field(default_factory=ManaCost)
    tap_cost: bool = True
    toughness_less_than_source_power: bool = False
    destroy_at_end_of_turn: bool = False

    @property
    def label(self) -> str:
        abilities = ", ".join(
            ability.value for ability in self.granted_abilities
        )
        return f"Tap: Target creature gains {abilities} until end of turn"


@dataclass(frozen=True, slots=True)
class ActivatedDrawAbility:
    mana_cost: ManaCost
    amount: int = 1
    tap_cost: bool = True

    @property
    def label(self) -> str:
        return f"Pay {self.mana_cost.compact} and tap: Draw {self.amount} card"


@dataclass(frozen=True, slots=True)
class ActivatedDiscardAbility:
    """A targeted fast effect that makes an opponent choose discards."""

    mana_cost: ManaCost
    amount: int = 1
    tap_cost: bool = True
    target_requirement: TargetRequirement = field(
        default_factory=lambda: TargetRequirement(players=True, opponent_only=True)
    )

    @property
    def label(self) -> str:
        return f"Pay {self.mana_cost.compact} and tap: Opponent discards a card"


@dataclass(frozen=True, slots=True)
class ActivatedExtraTurnAbility:
    """Tap a permanent to grant its controller an additional turn."""

    tap_cost: bool = True
    mana_cost: ManaCost = field(default_factory=ManaCost)

    @property
    def label(self) -> str:
        return "Tap: Take an additional turn after this one"


@dataclass(frozen=True, slots=True)
class ActivatedUntapAbility:
    """Pay mana to untap the source as a fast effect."""

    mana_cost: ManaCost
    tap_cost: bool = False

    @property
    def label(self) -> str:
        return f"Pay {self.mana_cost.compact}: Untap"


@dataclass(frozen=True, slots=True)
class ActivatedAnimationAbility:
    """Temporarily make an artifact a creature for the current combat."""

    mana_cost: ManaCost
    power: int
    toughness: int
    once_per_turn: bool = True

    @property
    def label(self) -> str:
        return (
            f"Pay {self.mana_cost.compact}: Become a {self.power}/"
            f"{self.toughness} artifact creature for this combat"
        )


@dataclass(frozen=True, slots=True)
class ActivatedEventLifeGainAbility:
    """Gain life by paying during a matching spell-cast or death event."""

    mana_cost: ManaCost
    spell_color: Color | None = None
    creature_death: bool = False
    amount: int = 1

    def __post_init__(self) -> None:
        if (self.spell_color is None) == (not self.creature_death):
            raise ValueError(
                "event life gain must match either a spell color or creature death"
            )
        if self.amount < 1:
            raise ValueError("event life gain must be positive")

    @property
    def label(self) -> str:
        event = (
            "a creature death"
            if self.creature_death
            else f"a {self.spell_color.name.lower()} spell being cast"
        )
        return (
            f"Pay {self.mana_cost.compact}: Gain {self.amount} life "
            f"for {event}"
        )


@dataclass(frozen=True, slots=True)
class ActivatedPreventDamageAbility:
    amount: int | None = None
    mana_cost: ManaCost = field(default_factory=ManaCost)
    tap_cost: bool = True
    source_color: Color | None = None
    controller_only: bool = False

    def __post_init__(self) -> None:
        if self.amount is not None and self.amount < 1:
            raise ValueError("a prevention ability must prevent positive damage")

    @property
    def label(self) -> str:
        cost_parts = []
        if self.mana_cost.mana_value:
            cost_parts.append(f"Pay {self.mana_cost.compact}")
        if self.tap_cost:
            cost_parts.append("tap")
        cost = " and ".join(cost_parts).capitalize()
        amount = "all" if self.amount is None else str(self.amount)
        color = (
            f" from one {self.source_color.name.lower()} source"
            if self.source_color is not None
            else " to any target"
        )
        return f"{cost}: Prevent {amount} damage{color}"


@dataclass(frozen=True, slots=True)
class ActivatedRedirectDamageAbility:
    """Redirect a selected damage packet during the FAQ redirection step."""

    mana_cost: ManaCost = field(default_factory=ManaCost)
    source_only: bool = False
    bidirectional_with_owner: bool = False
    any_amount: bool = False
    owner_activates: bool = False

    @property
    def label(self) -> str:
        cost = (
            f"Pay {self.mana_cost.compact}: "
            if self.mana_cost.mana_value
            else ""
        )
        if self.bidirectional_with_owner:
            return (
                f"{cost}Redirect damage between this creature and its owner"
            )
        return f"{cost}Redirect all damage to a creature to you"


@dataclass(frozen=True, slots=True)
class ActivatedRegenerationAbility:
    mana_cost: ManaCost
    affects_attached_creature: bool = False

    @property
    def label(self) -> str:
        return f"Pay {self.mana_cost.compact}: Regenerate"


TargetedActivatedAbility = (
    ActivatedDamageAbility
    | ActivatedDestroyAbility
    | ActivatedTapAbility
    | ActivatedUnblockableAbility
    | ActivatedTemporaryAbility
    | ActivatedDiscardAbility
)
BatchActivatedAbility = (
    TargetedActivatedAbility
    | ActivatedPumpAbility
    | ActivatedDrawAbility
    | ActivatedDiscardAbility
    | ActivatedExtraTurnAbility
    | ActivatedUntapAbility
    | ActivatedEventLifeGainAbility
    | ActivatedAnimationAbility
)
ActivatedAbility = (
    ActivatedManaAbility
    | ActivatedPumpAbility
    | ActivatedDamageAbility
    | ActivatedDestroyAbility
    | ActivatedTapAbility
    | ActivatedUnblockableAbility
    | ActivatedTemporaryAbility
    | ActivatedDrawAbility
    | ActivatedExtraTurnAbility
    | ActivatedUntapAbility
    | ActivatedEventLifeGainAbility
    | ActivatedAnimationAbility
    | ActivatedPreventDamageAbility
    | ActivatedRedirectDamageAbility
    | ActivatedRegenerationAbility
)


__all__ = [
    "TargetRequirement",
    "ActivatedManaAbility",
    "ActivatedPumpAbility",
    "ActivatedDamageAbility",
    "ActivatedDestroyAbility",
    "ActivatedTapAbility",
    "ActivatedUnblockableAbility",
    "ActivatedTemporaryAbility",
    "ActivatedDrawAbility",
    "ActivatedDiscardAbility",
    "ActivatedExtraTurnAbility",
    "ActivatedUntapAbility",
    "ActivatedEventLifeGainAbility",
    "ActivatedAnimationAbility",
    "ActivatedPreventDamageAbility",
    "ActivatedRedirectDamageAbility",
    "ActivatedRegenerationAbility",
    "TargetedActivatedAbility",
    "BatchActivatedAbility",
    "ActivatedAbility",
]
