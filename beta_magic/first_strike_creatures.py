"""Beta creatures whose only rules ability is First Strike."""

from .cards import CardDefinition
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility


ELVISH_ARCHERS = CardDefinition(
    name="Elvish Archers",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{G}"),
    rules_text="First strike",
    colors=frozenset({Color.GREEN}),
    subtypes=("Elves",),
    power=2,
    toughness=1,
    abilities=frozenset({KeywordAbility.FIRST_STRIKE}),
)

FIRST_STRIKE_CREATURES = (ELVISH_ARCHERS,)
