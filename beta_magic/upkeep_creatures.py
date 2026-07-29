"""Creatures with optional mana payments during upkeep."""

from .cards import CardDefinition, UpkeepCostEffect, UpkeepFailure
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility


PHANTASMAL_FORCES = CardDefinition(
    name="Phantasmal Forces",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{U}"),
    rules_text=(
        "Flying. During your upkeep, pay {U} or destroy Phantasmal Forces."
    ),
    colors=frozenset({Color.BLUE}),
    subtypes=("Illusion",),
    power=4,
    toughness=1,
    abilities=frozenset({KeywordAbility.FLYING}),
    upkeep_effects=(UpkeepCostEffect(ManaCost.parse("{U}")),),
)

FORCE_OF_NATURE = CardDefinition(
    name="Force of Nature",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{G}{G}{G}{G}"),
    rules_text=(
        "Trample. During your upkeep, pay {G}{G}{G}{G} or "
        "Force of Nature deals 8 damage to you."
    ),
    colors=frozenset({Color.GREEN}),
    subtypes=("Elemental",),
    power=8,
    toughness=8,
    abilities=frozenset({KeywordAbility.TRAMPLE}),
    upkeep_effects=(
        UpkeepCostEffect(
            ManaCost.parse("{G}{G}{G}{G}"),
            failure=UpkeepFailure.DAMAGE_CONTROLLER,
            damage=8,
        ),
    ),
)

UPKEEP_CREATURES = (PHANTASMAL_FORCES, FORCE_OF_NATURE)
