"""Creatures that can block Flying without having Flying."""

from .cards import CardDefinition
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility


GIANT_SPIDER = CardDefinition(
    name="Giant Spider",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{G}"),
    rules_text="Can block flying creatures.",
    colors=frozenset({Color.GREEN}),
    subtypes=("Spider",),
    power=2,
    toughness=4,
    abilities=frozenset({KeywordAbility.CAN_BLOCK_FLYING}),
)

REACH_CREATURES = (GIANT_SPIDER,)
