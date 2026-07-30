"""Canonical definitions of currently supported blue Beta cards."""

from ..abilities import ActivatedDamageAbility, TargetRequirement
from ..cards import CardDefinition
from ..effects import (
    ContinuousEffect,
    DamageEffect,
    DrawCardsEffect,
    EffectRecipient,
    EffectScope,
    MoveTargetsEffect,
    TemporaryPumpEffect,
    UpkeepCostEffect,
    UpkeepDamageEffect,
    UpkeepDamageRecipient,
)
from ..mana import ManaCost
from ..types import CardType, Color, KeywordAbility, Zone


_CREATURE_IN_PLAY = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
)
_ANY_CREATURE_OR_PLAYER = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
    players=True,
)


def _flyer(
    name: str, cost: str, subtype: str, power: int, toughness: int
) -> CardDefinition:
    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.CREATURE}),
        mana_cost=ManaCost.parse(cost),
        rules_text="Flying",
        colors=frozenset({Color.BLUE}),
        subtypes=(subtype,),
        power=power,
        toughness=toughness,
        abilities=frozenset({KeywordAbility.FLYING}),
    )


MERFOLK_OF_THE_PEARL_TRIDENT = CardDefinition(
    name="Merfolk of the Pearl Trident",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{U}"),
    colors=frozenset({Color.BLUE}),
    subtypes=("Merfolk",),
    power=1,
    toughness=1,
)

WATER_ELEMENTAL = CardDefinition(
    name="Water Elemental",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{U}{U}"),
    colors=frozenset({Color.BLUE}),
    subtypes=("Elemental",),
    power=5,
    toughness=4,
)

AIR_ELEMENTAL = _flyer("Air Elemental", "{3}{U}{U}", "Elemental", 4, 4)
MAHAMOTI_DJINN = _flyer("Mahamoti Djinn", "{4}{U}{U}", "Djinn", 5, 6)
PHANTOM_MONSTER = _flyer("Phantom Monster", "{3}{U}", "Phantasm", 3, 3)
WALL_OF_AIR = _flyer("Wall of Air", "{1}{U}{U}", "Wall", 1, 5)

LORD_OF_ATLANTIS = CardDefinition(
    name="Lord of Atlantis",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{U}{U}"),
    rules_text=(
        "All Merfolk in play gain +1/+1 and islandwalk. "
        "Lord of Atlantis does not affect itself."
    ),
    colors=frozenset({Color.BLUE}),
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

PHANTASMAL_FORCES = CardDefinition(
    name="Phantasmal Forces",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{U}"),
    rules_text=(
        "Flying. During your upkeep, pay {U} or destroy Phantasmal Forces."
    ),
    colors=frozenset({Color.BLUE}),
    subtypes=("Illusion",),
    power=4,
    toughness=1,
    abilities=frozenset({KeywordAbility.FLYING}),
    upkeep_effects=(UpkeepCostEffect(ManaCost.parse("{U}")),),
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
        ActivatedDamageAbility(1, _ANY_CREATURE_OR_PLAYER),
    ),
)

FLIGHT = CardDefinition(
    name="Flight",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{U}"),
    rules_text="Target creature is now a flying creature.",
    colors=frozenset({Color.BLUE}),
    subtypes=("Enchant Creature",),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD,
            granted_abilities=frozenset({KeywordAbility.FLYING}),
        ),
    ),
    target_requirement=_CREATURE_IN_PLAY,
)

FEEDBACK = CardDefinition(
    name="Feedback",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{2}{U}"),
    rules_text=(
        "Feedback deals 1 damage to enchanted enchantment's "
        "controller during that player's upkeep."
    ),
    colors=frozenset({Color.BLUE}),
    subtypes=("Enchant Enchantment",),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.ENCHANTMENT}),
    ),
    upkeep_effects=(
        UpkeepDamageEffect(
            1,
            recipient=UpkeepDamageRecipient.ATTACHED_PERMANENT_CONTROLLER,
        ),
    ),
)

ANCESTRAL_RECALL = CardDefinition(
    name="Ancestral Recall",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{U}"),
    rules_text="Target player draws 3 cards.",
    colors=frozenset({Color.BLUE}),
    target_requirement=TargetRequirement(players=True),
    spell_effects=(DrawCardsEffect(amount=3),),
)

JUMP = CardDefinition(
    name="Jump",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{U}"),
    rules_text="Target creature gains flying until end of turn.",
    colors=frozenset({Color.BLUE}),
    target_requirement=_CREATURE_IN_PLAY,
    spell_effects=(
        TemporaryPumpEffect(
            granted_abilities=frozenset({KeywordAbility.FLYING})
        ),
    ),
)

UNSUMMON = CardDefinition(
    name="Unsummon",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{U}"),
    rules_text="Return target creature to its owner's hand.",
    colors=frozenset({Color.BLUE}),
    target_requirement=_CREATURE_IN_PLAY,
    spell_effects=(MoveTargetsEffect(Zone.HAND),),
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
    target_requirement=_ANY_CREATURE_OR_PLAYER,
    spell_effects=(
        DamageEffect(4),
        DamageEffect(2, recipient=EffectRecipient.CASTER),
    ),
)

BRAINGEYSER = CardDefinition(
    name="Braingeyser",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{X}{U}{U}"),
    rules_text="Target player draws X cards.",
    colors=frozenset({Color.BLUE}),
    target_requirement=TargetRequirement(players=True),
    spell_effects=(DrawCardsEffect(amount_per_x=1),),
)

BLUE_CARDS = tuple(
    sorted(
        (
            AIR_ELEMENTAL,
            ANCESTRAL_RECALL,
            BRAINGEYSER,
            FEEDBACK,
            FLIGHT,
            JUMP,
            LORD_OF_ATLANTIS,
            MAHAMOTI_DJINN,
            MERFOLK_OF_THE_PEARL_TRIDENT,
            PHANTASMAL_FORCES,
            PHANTOM_MONSTER,
            PRODIGAL_SORCERER,
            PSIONIC_BLAST,
            UNSUMMON,
            WALL_OF_AIR,
            WATER_ELEMENTAL,
        ),
        key=lambda card: card.name,
    )
)
