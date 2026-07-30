"""Straightforward activated artifacts from Limited Edition Beta."""

from .cards import (
    ActivatedDamageAbility,
    ActivatedDrawAbility,
    ActivatedTapAbility,
    CardDefinition,
    TargetRequirement,
)
from .damage_spells import ANY_CREATURE_OR_PLAYER
from .mana import ManaCost
from .types import CardType, Zone


ROD_OF_RUIN = CardDefinition(
    name="Rod of Ruin",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text="{3}: Rod of Ruin does 1 damage to any target.",
    activated_abilities=(
        ActivatedDamageAbility(
            damage=1,
            target_requirement=ANY_CREATURE_OR_PLAYER,
            mana_cost=ManaCost.parse("{3}"),
        ),
    ),
)

JAYEMDAE_TOME = CardDefinition(
    name="Jayemdae Tome",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text="{4}: Draw one card.",
    activated_abilities=(
        ActivatedDrawAbility(ManaCost.parse("{4}")),
    ),
)

ICY_MANIPULATOR = CardDefinition(
    name="Icy Manipulator",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text="{1}: Tap target artifact, creature, or land.",
    activated_abilities=(
        ActivatedTapAbility(
            TargetRequirement(
                zone=Zone.BATTLEFIELD,
                any_card_types=frozenset(
                    {CardType.ARTIFACT, CardType.CREATURE, CardType.LAND}
                ),
            ),
            mana_cost=ManaCost.parse("{1}"),
        ),
    ),
)

UTILITY_ARTIFACTS = (ROD_OF_RUIN, JAYEMDAE_TOME, ICY_MANIPULATOR)
