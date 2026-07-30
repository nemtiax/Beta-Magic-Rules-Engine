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
    card_types: frozenset[CardType] = field(default_factory=frozenset)
    any_card_types: frozenset[CardType] = field(default_factory=frozenset)
    players: bool = False
    blocking_only: bool = False
    tapped_only: bool = False
    color: Color | None = None
    subtypes: frozenset[str] = field(default_factory=frozenset)
    owner_only: bool = False
    count: int = 1

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError("a target requirement must require at least one target")
        if self.zone is None and not self.players:
            raise ValueError("a target requirement must accept cards or players")
        if self.blocking_only and self.zone is not Zone.BATTLEFIELD:
            raise ValueError("a blocking target must be on the battlefield")

    def accepts_card(self, card: Card, *, check_tapped: bool = True) -> bool:
        return (
            self.zone is not None
            and card.zone is self.zone
            and self.card_types.issubset(card.definition.card_types)
            and (not check_tapped or not self.tapped_only or card.tapped)
            and (self.color is None or self.color in card.definition.colors)
            and (
                not self.subtypes
                or bool(self.subtypes & set(card.definition.subtypes))
            )
            and (
                not self.any_card_types
                or bool(self.any_card_types & card.definition.card_types)
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
class ActivatedDrawAbility:
    mana_cost: ManaCost
    amount: int = 1
    tap_cost: bool = True

    @property
    def label(self) -> str:
        return f"Pay {self.mana_cost.compact} and tap: Draw {self.amount} card"


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
class ActivatedRegenerationAbility:
    mana_cost: ManaCost
    affects_attached_creature: bool = False

    @property
    def label(self) -> str:
        return f"Pay {self.mana_cost.compact}: Regenerate"


TargetedActivatedAbility = (
    ActivatedDamageAbility | ActivatedDestroyAbility | ActivatedTapAbility
)
BatchActivatedAbility = (
    TargetedActivatedAbility | ActivatedPumpAbility | ActivatedDrawAbility
)
ActivatedAbility = (
    ActivatedManaAbility
    | ActivatedPumpAbility
    | ActivatedDamageAbility
    | ActivatedDestroyAbility
    | ActivatedTapAbility
    | ActivatedDrawAbility
    | ActivatedPreventDamageAbility
    | ActivatedRegenerationAbility
)


__all__ = [
    "TargetRequirement",
    "ActivatedManaAbility",
    "ActivatedPumpAbility",
    "ActivatedDamageAbility",
    "ActivatedDestroyAbility",
    "ActivatedTapAbility",
    "ActivatedDrawAbility",
    "ActivatedPreventDamageAbility",
    "ActivatedRegenerationAbility",
    "TargetedActivatedAbility",
    "BatchActivatedAbility",
    "ActivatedAbility",
]
