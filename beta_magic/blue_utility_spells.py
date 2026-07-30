"""Straightforward blue utility spells from Limited Edition Beta."""

from .cards import (
    CardDefinition,
    DrawCardsEffect,
    MoveTargetsEffect,
    TargetRequirement,
    TemporaryPumpEffect,
)
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility, Zone


ANCESTRAL_RECALL = CardDefinition(
    name="Ancestral Recall",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{U}"),
    rules_text="Target player draws 3 cards.",
    colors=frozenset({Color.BLUE}),
    target_requirement=TargetRequirement(players=True),
    spell_effects=(DrawCardsEffect(amount=3),),
)

JUMP = CardDefinition(
    name="Jump",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{U}"),
    rules_text="Target creature gains flying until end of turn.",
    colors=frozenset({Color.BLUE}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
    ),
    spell_effects=(
        TemporaryPumpEffect(
            granted_abilities=frozenset({KeywordAbility.FLYING})
        ),
    ),
)

UNSUMMON = CardDefinition(
    name="Unsummon",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{U}"),
    rules_text="Return target creature to its owner's hand.",
    colors=frozenset({Color.BLUE}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
    ),
    spell_effects=(MoveTargetsEffect(Zone.HAND),),
)

BLUE_UTILITY_SPELLS = (ANCESTRAL_RECALL, JUMP, UNSUMMON)
