"""Straightforward spells whose casting costs and effects use X."""

from .cards import (
    CardDefinition,
    DrawCardsEffect,
    GlobalDamageEffect,
    TargetRequirement,
    TemporaryPumpEffect,
)
from .mana import ManaCost
from .types import CardType, Color, Zone


BRAINGEYSER = CardDefinition(
    name="Braingeyser",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{X}{U}{U}"),
    rules_text="Target player draws X cards.",
    colors=frozenset({Color.BLUE}),
    target_requirement=TargetRequirement(players=True),
    spell_effects=(DrawCardsEffect(amount_per_x=1),),
)

HOWL_FROM_BEYOND = CardDefinition(
    name="Howl from Beyond",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{X}{B}"),
    rules_text="Target creature gains +X/+0 until end of turn.",
    colors=frozenset({Color.BLACK}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
    ),
    spell_effects=(TemporaryPumpEffect(power_per_x=1),),
)

EARTHQUAKE = CardDefinition(
    name="Earthquake",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{X}{R}"),
    rules_text=(
        "Earthquake does X damage to each player and each non-flying "
        "creature in play."
    ),
    colors=frozenset({Color.RED}),
    spell_effects=(
        GlobalDamageEffect(amount_per_x=1, creatures_with_flying=False),
    ),
)

HURRICANE = CardDefinition(
    name="Hurricane",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{X}{G}"),
    rules_text="Hurricane does X damage to each player and flying creature.",
    colors=frozenset({Color.GREEN}),
    spell_effects=(
        GlobalDamageEffect(amount_per_x=1, creatures_with_flying=True),
    ),
)

VARIABLE_SPELLS = (BRAINGEYSER, HOWL_FROM_BEYOND, EARTHQUAKE, HURRICANE)
