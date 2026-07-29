"""Beta creature lords with subtype-wide bonuses and landwalk."""

from .cards import CardDefinition, ContinuousEffect
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility


LORD_OF_ATLANTIS = CardDefinition(
    name="Lord of Atlantis",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{U}{U}"),
    rules_text=(
        "All Merfolk in play gain +1/+1 and islandwalk. "
        "Lord of Atlantis does not affect itself."
    ),
    colors=frozenset({Color.BLUE}),
    # The Beta card was Summon Lord of Atlantis, not Summon Merfolk.
    subtypes=("Lord of Atlantis",),
    power=2,
    toughness=2,
    continuous_effects=(
        ContinuousEffect(
            power=1,
            toughness=1,
            subtype="Merfolk",
            exclude_source=True,
            granted_abilities=frozenset({KeywordAbility.ISLANDWALK}),
        ),
    ),
)

GOBLIN_KING = CardDefinition(
    name="Goblin King",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{R}{R}"),
    rules_text=(
        "All Goblins in play gain +1/+1 and mountainwalk. "
        "Goblin King does not affect itself."
    ),
    colors=frozenset({Color.RED}),
    # The ruling distinguishes Summon Goblin King from Summon Goblins.
    subtypes=("Goblin King",),
    power=2,
    toughness=2,
    continuous_effects=(
        ContinuousEffect(
            power=1,
            toughness=1,
            subtype="Goblins",
            exclude_source=True,
            granted_abilities=frozenset({KeywordAbility.MOUNTAINWALK}),
        ),
    ),
)

CREATURE_LORDS = (LORD_OF_ATLANTIS, GOBLIN_KING)
