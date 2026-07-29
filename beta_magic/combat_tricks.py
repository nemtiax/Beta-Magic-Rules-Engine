"""Targeted temporary creature pumps from Limited Edition Beta."""

from .cards import CardDefinition, TargetRequirement, TemporaryPumpEffect
from .mana import ManaCost
from .types import CardType, Color, Zone


GIANT_GROWTH = CardDefinition(
    name="Giant Growth",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{G}"),
    rules_text="Target creature gains +3/+3 until end of turn.",
    colors=frozenset({Color.GREEN}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
    ),
    spell_effects=(TemporaryPumpEffect(power=3, toughness=3),),
)

RIGHTEOUSNESS = CardDefinition(
    name="Righteousness",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{W}"),
    rules_text=(
        "Target blocking creature gains +7/+7 until end of turn."
    ),
    colors=frozenset({Color.WHITE}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
        blocking_only=True,
    ),
    spell_effects=(TemporaryPumpEffect(power=7, toughness=7),),
)

TARGETED_PUMP_SPELLS = (GIANT_GROWTH, RIGHTEOUSNESS)
