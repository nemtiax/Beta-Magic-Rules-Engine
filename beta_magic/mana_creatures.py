"""Beta creatures whose only special rules are activated mana abilities."""

from .cards import ActivatedManaAbility, CardDefinition
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility


LLANOWAR_ELVES = CardDefinition(
    name="Llanowar Elves",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{G}"),
    rules_text="Tap to add {G} to your mana pool.",
    colors=frozenset({Color.GREEN}),
    subtypes=("Mana Elves",),
    power=1,
    toughness=1,
    activated_abilities=(ActivatedManaAbility(Color.GREEN),),
)

BIRDS_OF_PARADISE = CardDefinition(
    name="Birds of Paradise",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{G}"),
    rules_text="Flying. Tap to add one mana of any color to your mana pool.",
    colors=frozenset({Color.GREEN}),
    subtypes=("Mana Birds",),
    power=0,
    toughness=1,
    abilities=frozenset({KeywordAbility.FLYING}),
    activated_abilities=tuple(
        ActivatedManaAbility(color)
        for color in (
            Color.WHITE,
            Color.BLUE,
            Color.BLACK,
            Color.RED,
            Color.GREEN,
        )
    ),
)

MANA_CREATURES = (LLANOWAR_ELVES, BIRDS_OF_PARADISE)
