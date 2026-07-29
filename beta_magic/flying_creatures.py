"""Beta creatures whose only rules ability is Flying."""

from .cards import CardDefinition
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility


def _flyer(
    name: str,
    cost: str,
    color: Color,
    subtype: str,
    power: int,
    toughness: int,
) -> CardDefinition:
    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.CREATURE}),
        mana_cost=ManaCost.parse(cost),
        rules_text="Flying",
        colors=frozenset({color}),
        subtypes=(subtype,),
        power=power,
        toughness=toughness,
        abilities=frozenset({KeywordAbility.FLYING}),
    )


AIR_ELEMENTAL = _flyer("Air Elemental", "{3}{U}{U}", Color.BLUE, "Elemental", 4, 4)
MAHAMOTI_DJINN = _flyer("Mahamoti Djinn", "{4}{U}{U}", Color.BLUE, "Djinn", 5, 6)
PHANTOM_MONSTER = _flyer(
    "Phantom Monster", "{3}{U}", Color.BLUE, "Phantasm", 3, 3
)
ROC_OF_KHER_RIDGES = _flyer(
    "Roc of Kher Ridges", "{3}{R}", Color.RED, "Roc", 3, 3
)
SCRYB_SPRITES = _flyer("Scryb Sprites", "{G}", Color.GREEN, "Faeries", 1, 1)
WALL_OF_AIR = _flyer("Wall of Air", "{1}{U}{U}", Color.BLUE, "Wall", 1, 5)
WALL_OF_SWORDS = _flyer("Wall of Swords", "{3}{W}", Color.WHITE, "Wall", 3, 5)

FLYING_CREATURES = (
    AIR_ELEMENTAL,
    MAHAMOTI_DJINN,
    PHANTOM_MONSTER,
    ROC_OF_KHER_RIDGES,
    SCRYB_SPRITES,
    WALL_OF_AIR,
    WALL_OF_SWORDS,
)
