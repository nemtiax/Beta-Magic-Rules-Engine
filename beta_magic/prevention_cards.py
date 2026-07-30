"""Initial damage-prevention cards from Limited Edition Beta."""

from .cards import (
    ActivatedPreventDamageAbility,
    CardDefinition,
    GainLifeEffect,
    TargetRequirement,
)
from .mana import ManaCost
from .types import CardType, Color


HEALING_SALVE = CardDefinition(
    name="Healing Salve",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{W}"),
    rules_text=(
        "Gain 3 life, or prevent up to 3 damage from being dealt "
        "to a single target."
    ),
    colors=frozenset({Color.WHITE}),
    target_requirement=TargetRequirement(players=True),
    spell_effects=(GainLifeEffect(amount=3),),
    prevention_amount=3,
)

SAMITE_HEALER = CardDefinition(
    name="Samite Healer",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{W}"),
    rules_text="Tap to prevent 1 damage to any target.",
    colors=frozenset({Color.WHITE}),
    subtypes=("Cleric",),
    power=1,
    toughness=1,
    activated_abilities=(ActivatedPreventDamageAbility(amount=1),),
)

PREVENTION_CARDS = (HEALING_SALVE, SAMITE_HEALER)
