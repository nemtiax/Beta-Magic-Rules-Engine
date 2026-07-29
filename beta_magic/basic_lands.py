"""Definitions of Limited Edition Beta's five basic lands."""

from .cards import ActivatedManaAbility, CardDefinition
from .types import CardType, Color


def _basic_land(name: str, color: Color) -> CardDefinition:
    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.LAND}),
        supertypes=("Basic",),
        subtypes=(name,),
        rules_text=f"Tap to add {{{color.value}}} to your mana pool.",
        produces_mana=color,
        activated_abilities=(ActivatedManaAbility(color),),
    )


PLAINS = _basic_land("Plains", Color.WHITE)
ISLAND = _basic_land("Island", Color.BLUE)
SWAMP = _basic_land("Swamp", Color.BLACK)
MOUNTAIN = _basic_land("Mountain", Color.RED)
FOREST = _basic_land("Forest", Color.GREEN)

BASIC_LANDS = (PLAINS, ISLAND, SWAMP, MOUNTAIN, FOREST)
