"""Artifacts with mandatory effects at defined turn times."""

from .cards import CardDefinition, UpkeepDamageEffect
from .mana import ManaCost
from .types import CardType


COPPER_TABLET = CardDefinition(
    name="Copper Tablet",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{2}"),
    rules_text="Copper Tablet deals 1 damage to each player during their upkeep.",
    upkeep_effects=(UpkeepDamageEffect(1),),
)

TIMED_ARTIFACTS = (COPPER_TABLET,)
