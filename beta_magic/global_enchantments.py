"""Simple global creature-buff enchantments from Limited Edition Beta."""

from .cards import CardDefinition, ContinuousEffect
from .mana import ManaCost
from .types import CardType, Color


CRUSADE = CardDefinition(
    name="Crusade",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{W}{W}"),
    rules_text="All white creatures gain +1/+1.",
    colors=frozenset({Color.WHITE}),
    continuous_effects=(
        ContinuousEffect(power=1, toughness=1, color=Color.WHITE),
    ),
)

BAD_MOON = CardDefinition(
    name="Bad Moon",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{1}{B}"),
    rules_text="All black creatures in play gain +1/+1.",
    colors=frozenset({Color.BLACK}),
    continuous_effects=(
        ContinuousEffect(power=1, toughness=1, color=Color.BLACK),
    ),
)

ORCISH_ORIFLAMME = CardDefinition(
    name="Orcish Oriflamme",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{3}{R}"),
    rules_text="When attacking, all of your attacking creatures gain +1/+0.",
    colors=frozenset({Color.RED}),
    continuous_effects=(
        ContinuousEffect(power=1, controller_only=True, attacking_only=True),
    ),
)

GLOBAL_ENCHANTMENTS = (CRUSADE, BAD_MOON, ORCISH_ORIFLAMME)
