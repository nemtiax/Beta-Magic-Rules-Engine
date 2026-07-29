"""Beta creatures whose only special rule is a landwalk ability."""

from .cards import CardDefinition
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility


BOG_WRAITH = CardDefinition(
    name="Bog Wraith",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{B}"),
    rules_text="Swampwalk",
    colors=frozenset({Color.BLACK}),
    subtypes=("Wraith",),
    power=3,
    toughness=3,
    abilities=frozenset({KeywordAbility.SWAMPWALK}),
)

SHANODIN_DRYADS = CardDefinition(
    name="Shanodin Dryads",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{G}"),
    rules_text="Forestwalk",
    colors=frozenset({Color.GREEN}),
    subtypes=("Nymph", "Dryad"),
    power=1,
    toughness=1,
    abilities=frozenset({KeywordAbility.FORESTWALK}),
)

LANDWALK_CREATURES = (BOG_WRAITH, SHANODIN_DRYADS)
