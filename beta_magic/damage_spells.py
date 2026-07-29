"""Simple targeted damage spells from Limited Edition Beta."""

from .cards import (
    CardDefinition,
    DamageEffect,
    EffectRecipient,
    TargetRequirement,
)
from .mana import ManaCost
from .types import CardType, Color, Zone


ANY_CREATURE_OR_PLAYER = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
    players=True,
)

LIGHTNING_BOLT = CardDefinition(
    name="Lightning Bolt",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{R}"),
    rules_text="Lightning Bolt does 3 damage to one target.",
    colors=frozenset({Color.RED}),
    target_requirement=ANY_CREATURE_OR_PLAYER,
    spell_effects=(DamageEffect(3),),
)

PSIONIC_BLAST = CardDefinition(
    name="Psionic Blast",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{2}{U}"),
    rules_text=(
        "Psionic Blast does 4 damage to any target, "
        "but it does 2 damage to you as well."
    ),
    colors=frozenset({Color.BLUE}),
    target_requirement=ANY_CREATURE_OR_PLAYER,
    spell_effects=(
        DamageEffect(4),
        DamageEffect(2, recipient=EffectRecipient.CASTER),
    ),
)

TARGETED_DAMAGE_SPELLS = (LIGHTNING_BOLT, PSIONIC_BLAST)
