"""Beta's three Walls with no printed rules text."""

from .cards import CardDefinition
from .mana import ManaCost
from .types import CardType, Color


def _wall(
    name: str, cost: str, color: Color, toughness: int
) -> CardDefinition:
    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.CREATURE}),
        mana_cost=ManaCost.parse(cost),
        colors=frozenset({color}),
        subtypes=("Wall",),
        power=0,
        toughness=toughness,
    )


WALL_OF_ICE = _wall("Wall of Ice", "{2}{G}", Color.GREEN, 7)
WALL_OF_STONE = _wall("Wall of Stone", "{1}{R}{R}", Color.RED, 8)
WALL_OF_WOOD = _wall("Wall of Wood", "{G}", Color.GREEN, 3)

VANILLA_WALLS = (WALL_OF_ICE, WALL_OF_STONE, WALL_OF_WOOD)
