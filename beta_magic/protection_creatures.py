"""Beta creatures whose protection follows the contemporary FAQ."""

from .cards import CardDefinition
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility


WHITE_KNIGHT = CardDefinition(
    name="White Knight",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{W}{W}"),
    rules_text="Protection from black, first strike",
    colors=frozenset({Color.WHITE}),
    subtypes=("Knight",),
    power=2,
    toughness=2,
    abilities=frozenset(
        {
            KeywordAbility.FIRST_STRIKE,
            KeywordAbility.PROTECTION_FROM_BLACK,
        }
    ),
)

BLACK_KNIGHT = CardDefinition(
    name="Black Knight",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{B}{B}"),
    rules_text="Protection from white, first strike",
    colors=frozenset({Color.BLACK}),
    subtypes=("Knight",),
    power=2,
    toughness=2,
    abilities=frozenset(
        {
            KeywordAbility.FIRST_STRIKE,
            KeywordAbility.PROTECTION_FROM_WHITE,
        }
    ),
)

PROTECTION_CREATURES = (WHITE_KNIGHT, BLACK_KNIGHT)
