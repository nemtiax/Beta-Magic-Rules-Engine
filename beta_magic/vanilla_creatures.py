"""The fifteen non-Wall creatures in Beta with no printed rules text."""

from .cards import CardDefinition
from .mana import ManaCost
from .types import CardType, Color


def _creature(
    name: str,
    cost: str,
    color: Color | None,
    subtype: str,
    power: int,
    toughness: int,
    *,
    artifact: bool = False,
) -> CardDefinition:
    card_types = {CardType.CREATURE}
    if artifact:
        card_types.add(CardType.ARTIFACT)
    return CardDefinition(
        name=name,
        card_types=frozenset(card_types),
        mana_cost=ManaCost.parse(cost),
        colors=frozenset({color}) if color is not None else frozenset(),
        subtypes=(subtype,),
        power=power,
        toughness=toughness,
    )


PEARLED_UNICORN = _creature("Pearled Unicorn", "{2}{W}", Color.WHITE, "Unicorn", 2, 2)
SAVANNAH_LIONS = _creature("Savannah Lions", "{W}", Color.WHITE, "Lions", 2, 1)
MERFOLK_OF_THE_PEARL_TRIDENT = _creature(
    "Merfolk of the Pearl Trident", "{U}", Color.BLUE, "Merfolk", 1, 1
)
WATER_ELEMENTAL = _creature(
    "Water Elemental", "{3}{U}{U}", Color.BLUE, "Elemental", 5, 4
)
SCATHE_ZOMBIES = _creature("Scathe Zombies", "{2}{B}", Color.BLACK, "Zombies", 2, 2)
EARTH_ELEMENTAL = _creature(
    "Earth Elemental", "{3}{R}{R}", Color.RED, "Elemental", 4, 5
)
FIRE_ELEMENTAL = _creature(
    "Fire Elemental", "{3}{R}{R}", Color.RED, "Elemental", 5, 4
)
GRAY_OGRE = _creature("Gray Ogre", "{2}{R}", Color.RED, "Ogre", 2, 2)
HILL_GIANT = _creature("Hill Giant", "{3}{R}", Color.RED, "Giant", 3, 3)
HURLOON_MINOTAUR = _creature(
    "Hurloon Minotaur", "{1}{R}{R}", Color.RED, "Minotaur", 2, 3
)
MONSS_GOBLIN_RAIDERS = _creature(
    "Mons's Goblin Raiders", "{R}", Color.RED, "Goblins", 1, 1
)
CRAW_WURM = _creature("Craw Wurm", "{4}{G}{G}", Color.GREEN, "Wurm", 6, 4)
GRIZZLY_BEARS = _creature("Grizzly Bears", "{1}{G}", Color.GREEN, "Bears", 2, 2)
IRONROOT_TREEFOLK = _creature(
    "Ironroot Treefolk", "{4}{G}", Color.GREEN, "Treefolk", 3, 5
)
OBSIANUS_GOLEM = _creature(
    "Obsianus Golem", "{6}", None, "Golem", 4, 6, artifact=True
)

VANILLA_CREATURES = (
    PEARLED_UNICORN,
    SAVANNAH_LIONS,
    MERFOLK_OF_THE_PEARL_TRIDENT,
    WATER_ELEMENTAL,
    SCATHE_ZOMBIES,
    EARTH_ELEMENTAL,
    FIRE_ELEMENTAL,
    GRAY_OGRE,
    HILL_GIANT,
    HURLOON_MINOTAUR,
    MONSS_GOBLIN_RAIDERS,
    CRAW_WURM,
    GRIZZLY_BEARS,
    IRONROOT_TREEFOLK,
    OBSIANUS_GOLEM,
)
