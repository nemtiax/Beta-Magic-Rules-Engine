"""Auras that damage their enchanted permanent's controller during upkeep."""

from .cards import (
    CardDefinition,
    TargetRequirement,
    UpkeepDamageEffect,
    UpkeepDamageRecipient,
)
from .mana import ManaCost
from .types import CardType, Color, Zone


def _damaging_aura(
    name: str,
    cost: str,
    color: Color,
    enchanted_type: CardType,
    type_name: str,
) -> CardDefinition:
    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.ENCHANTMENT}),
        mana_cost=ManaCost.parse(cost),
        rules_text=(
            f"{name} deals 1 damage to enchanted {type_name.lower()}'s "
            "controller during that player's upkeep."
        ),
        colors=frozenset({color}),
        subtypes=(f"Enchant {type_name}",),
        target_requirement=TargetRequirement(
            zone=Zone.BATTLEFIELD,
            card_types=frozenset({enchanted_type}),
        ),
        upkeep_effects=(
            UpkeepDamageEffect(
                1,
                recipient=(
                    UpkeepDamageRecipient.ATTACHED_PERMANENT_CONTROLLER
                ),
            ),
        ),
    )


CURSED_LAND = _damaging_aura(
    "Cursed Land", "{2}{B}{B}", Color.BLACK, CardType.LAND, "Land"
)
FEEDBACK = _damaging_aura(
    "Feedback", "{2}{U}", Color.BLUE, CardType.ENCHANTMENT, "Enchantment"
)
WANDERLUST = _damaging_aura(
    "Wanderlust", "{2}{G}", Color.GREEN, CardType.CREATURE, "Creature"
)
WARP_ARTIFACT = _damaging_aura(
    "Warp Artifact", "{B}{B}", Color.BLACK, CardType.ARTIFACT, "Artifact"
)

TIMED_ENCHANTMENTS = (CURSED_LAND, FEEDBACK, WANDERLUST, WARP_ARTIFACT)
