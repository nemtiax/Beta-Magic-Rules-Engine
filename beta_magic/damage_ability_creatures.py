"""Beta creatures with targeted tap-to-damage fast effects."""

from .cards import ActivatedDamageAbility, CardDefinition, TargetRequirement
from .mana import ManaCost
from .types import CardType, Color, Zone


ANY_CREATURE_OR_PLAYER = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
    players=True,
)

PRODIGAL_SORCERER = CardDefinition(
    name="Prodigal Sorcerer",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{U}"),
    rules_text="Tap: Prodigal Sorcerer does 1 damage to any target.",
    colors=frozenset({Color.BLUE}),
    subtypes=("Wizard",),
    power=1,
    toughness=1,
    activated_abilities=(
        ActivatedDamageAbility(1, ANY_CREATURE_OR_PLAYER),
    ),
)

ORCISH_ARTILLERY = CardDefinition(
    name="Orcish Artillery",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{R}{R}"),
    rules_text=(
        "Tap: Orcish Artillery does 2 damage to any target and "
        "3 damage to you."
    ),
    colors=frozenset({Color.RED}),
    subtypes=("Orcs",),
    power=1,
    toughness=3,
    activated_abilities=(
        ActivatedDamageAbility(
            2,
            ANY_CREATURE_OR_PLAYER,
            controller_damage=3,
        ),
    ),
)

DAMAGE_ABILITY_CREATURES = (PRODIGAL_SORCERER, ORCISH_ARTILLERY)
