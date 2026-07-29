"""Beta creatures with simple activated utility abilities."""

from .cards import (
    ActivatedDestroyAbility,
    ActivatedPumpAbility,
    CardDefinition,
    TargetRequirement,
)
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility, Zone


DWARVEN_DEMOLITION_TEAM = CardDefinition(
    name="Dwarven Demolition Team",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{R}"),
    rules_text="Tap to destroy a Wall.",
    colors=frozenset({Color.RED}),
    subtypes=("Dwarves",),
    power=1,
    toughness=1,
    activated_abilities=(
        ActivatedDestroyAbility(
            TargetRequirement(
                zone=Zone.BATTLEFIELD,
                card_types=frozenset({CardType.CREATURE}),
                subtypes=frozenset({"Wall"}),
            )
        ),
    ),
)

GOBLIN_BALLOON_BRIGADE = CardDefinition(
    name="Goblin Balloon Brigade",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{R}"),
    rules_text="{R}: Goblin Balloon Brigade gains flying until end of turn.",
    colors=frozenset({Color.RED}),
    subtypes=("Goblins",),
    power=1,
    toughness=1,
    activated_abilities=(
        ActivatedPumpAbility(
            ManaCost.parse("{R}"),
            granted_abilities=frozenset({KeywordAbility.FLYING}),
        ),
    ),
)

ROYAL_ASSASSIN = CardDefinition(
    name="Royal Assassin",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{B}{B}"),
    rules_text="Tap to destroy any tapped creature.",
    colors=frozenset({Color.BLACK}),
    subtypes=("Assassin",),
    power=1,
    toughness=1,
    activated_abilities=(
        ActivatedDestroyAbility(
            TargetRequirement(
                zone=Zone.BATTLEFIELD,
                card_types=frozenset({CardType.CREATURE}),
                tapped_only=True,
            )
        ),
    ),
)

NORTHERN_PALADIN = CardDefinition(
    name="Northern Paladin",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{W}{W}"),
    rules_text="{W}{W} and tap: Destroy a black card in play.",
    colors=frozenset({Color.WHITE}),
    subtypes=("Paladin",),
    power=3,
    toughness=3,
    activated_abilities=(
        ActivatedDestroyAbility(
            TargetRequirement(
                zone=Zone.BATTLEFIELD,
                color=Color.BLACK,
            ),
            mana_cost=ManaCost.parse("{W}{W}"),
        ),
    ),
)

UTILITY_ABILITY_CREATURES = (
    DWARVEN_DEMOLITION_TEAM,
    GOBLIN_BALLOON_BRIGADE,
    ROYAL_ASSASSIN,
    NORTHERN_PALADIN,
)
