"""Creatures whose power and toughness continuously count battlefield objects."""

from .cards import CardDefinition, VariableCreatureStats, VariableStatKind
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility


KELDON_WARLORD = CardDefinition(
    name="Keldon Warlord",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{R}{R}"),
    rules_text=(
        "Power and toughness each equal the number of non-Wall creatures "
        "you control, including Keldon Warlord."
    ),
    colors=frozenset({Color.RED}),
    subtypes=("Lord",),
    variable_stats=VariableCreatureStats(
        VariableStatKind.CONTROLLED_NON_WALL_CREATURES
    ),
)

NIGHTMARE = CardDefinition(
    name="Nightmare",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{5}{B}"),
    rules_text=(
        "Flying. Power and toughness each equal the number of Swamps "
        "you control."
    ),
    colors=frozenset({Color.BLACK}),
    subtypes=("Nightmare",),
    abilities=frozenset({KeywordAbility.FLYING}),
    variable_stats=VariableCreatureStats(
        VariableStatKind.CONTROLLED_LAND_SUBTYPE,
        subtype="Swamp",
    ),
)

PLAGUE_RATS = CardDefinition(
    name="Plague Rats",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{B}"),
    rules_text=(
        "Power and toughness each equal the number of Rats in play, "
        "counting both sides."
    ),
    colors=frozenset({Color.BLACK}),
    subtypes=("Rats",),
    variable_stats=VariableCreatureStats(
        VariableStatKind.ALL_CREATURE_SUBTYPE,
        subtype="Rats",
    ),
)

VARIABLE_CREATURES = (KELDON_WARLORD, NIGHTMARE, PLAGUE_RATS)
