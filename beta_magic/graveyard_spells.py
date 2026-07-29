"""Simple targeted graveyard recursion from Limited Edition Beta."""

from .cards import CardDefinition, MoveTargetsEffect, TargetRequirement
from .mana import ManaCost
from .types import CardType, Color, Zone


REGROWTH = CardDefinition(
    name="Regrowth",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{1}{G}"),
    rules_text="Return any card from your graveyard to your hand.",
    colors=frozenset({Color.GREEN}),
    target_requirement=TargetRequirement(
        zone=Zone.GRAVEYARD,
        owner_only=True,
    ),
    spell_effects=(MoveTargetsEffect(Zone.HAND),),
)

RAISE_DEAD = CardDefinition(
    name="Raise Dead",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{B}"),
    rules_text="Return a creature from your graveyard to your hand.",
    colors=frozenset({Color.BLACK}),
    target_requirement=TargetRequirement(
        zone=Zone.GRAVEYARD,
        card_types=frozenset({CardType.CREATURE}),
        owner_only=True,
    ),
    spell_effects=(MoveTargetsEffect(Zone.HAND),),
)

RESURRECTION = CardDefinition(
    name="Resurrection",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{2}{W}{W}"),
    rules_text=(
        "Put a creature from your graveyard directly into play. "
        "It cannot attack or use tap abilities this turn."
    ),
    colors=frozenset({Color.WHITE}),
    target_requirement=TargetRequirement(
        zone=Zone.GRAVEYARD,
        card_types=frozenset({CardType.CREATURE}),
        owner_only=True,
    ),
    spell_effects=(
        MoveTargetsEffect(Zone.BATTLEFIELD, under_caster_control=True),
    ),
)

GRAVEYARD_RECURSION_SPELLS = (REGROWTH, RAISE_DEAD, RESURRECTION)
