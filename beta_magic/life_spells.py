"""Simple life-gain spells from Limited Edition Beta."""

from .cards import CardDefinition, GainLifeEffect, TargetRequirement
from .mana import ManaCost
from .types import CardType, Color


STREAM_OF_LIFE = CardDefinition(
    name="Stream of Life",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{X}{G}"),
    rules_text="Target player gains X life.",
    colors=frozenset({Color.GREEN}),
    target_requirement=TargetRequirement(players=True),
    spell_effects=(GainLifeEffect(amount_per_x=1),),
)

LIFE_GAIN_SPELLS = (STREAM_OF_LIFE,)
