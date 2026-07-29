"""Definitions of Limited Edition Beta's ten original dual lands."""

from .cards import ActivatedManaAbility, CardDefinition
from .types import CardType, Color


def _dual_land(
    name: str,
    first_subtype: str,
    first_color: Color,
    second_subtype: str,
    second_color: Color,
) -> CardDefinition:
    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.LAND}),
        subtypes=(first_subtype, second_subtype),
        rules_text=(
            f"Tap to add {{{first_color.value}}} or "
            f"{{{second_color.value}}} to your mana pool."
        ),
        activated_abilities=(
            ActivatedManaAbility(first_color),
            ActivatedManaAbility(second_color),
        ),
    )


TUNDRA = _dual_land("Tundra", "Plains", Color.WHITE, "Island", Color.BLUE)
UNDERGROUND_SEA = _dual_land(
    "Underground Sea", "Island", Color.BLUE, "Swamp", Color.BLACK
)
BADLANDS = _dual_land("Badlands", "Swamp", Color.BLACK, "Mountain", Color.RED)
TAIGA = _dual_land("Taiga", "Mountain", Color.RED, "Forest", Color.GREEN)
SAVANNAH = _dual_land("Savannah", "Forest", Color.GREEN, "Plains", Color.WHITE)
SCRUBLAND = _dual_land("Scrubland", "Plains", Color.WHITE, "Swamp", Color.BLACK)
VOLCANIC_ISLAND = _dual_land(
    "Volcanic Island", "Island", Color.BLUE, "Mountain", Color.RED
)
BAYOU = _dual_land("Bayou", "Swamp", Color.BLACK, "Forest", Color.GREEN)
PLATEAU = _dual_land("Plateau", "Mountain", Color.RED, "Plains", Color.WHITE)
TROPICAL_ISLAND = _dual_land(
    "Tropical Island", "Forest", Color.GREEN, "Island", Color.BLUE
)

DUAL_LANDS = (
    TUNDRA,
    UNDERGROUND_SEA,
    BADLANDS,
    TAIGA,
    SAVANNAH,
    SCRUBLAND,
    VOLCANIC_ISLAND,
    BAYOU,
    PLATEAU,
    TROPICAL_ISLAND,
)
