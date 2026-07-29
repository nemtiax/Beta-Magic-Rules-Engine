"""Beta creatures whose only rules ability is Trample."""

from .cards import CardDefinition
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility


WAR_MAMMOTH = CardDefinition(
    name="War Mammoth",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{G}"),
    rules_text="Trample",
    colors=frozenset({Color.GREEN}),
    subtypes=("Mammoth",),
    power=3,
    toughness=3,
    abilities=frozenset({KeywordAbility.TRAMPLE}),
)

TRAMPLE_CREATURES = (WAR_MAMMOTH,)
