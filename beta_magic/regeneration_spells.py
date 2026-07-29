"""Spells that regenerate creatures during a resolving fast-effect batch."""

from .cards import CardDefinition, RegenerateTargetsEffect, TargetRequirement
from .mana import ManaCost
from .types import CardType, Color, Zone


DEATH_WARD = CardDefinition(
    name="Death Ward",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{W}"),
    rules_text="Regenerates target creature.",
    colors=frozenset({Color.WHITE}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
    ),
    spell_effects=(RegenerateTargetsEffect(),),
)

REGENERATION_SPELLS = (DEATH_WARD,)
