"""Canonical definitions of currently supported black Beta cards."""

from ..abilities import (
    ActivatedDestroyAbility,
    ActivatedPumpAbility,
    ActivatedRegenerationAbility,
    TargetRequirement,
)
from ..cards import CardDefinition
from ..effects import (
    ContinuousEffect,
    DestroyTargetsEffect,
    EffectScope,
    MoveTargetsEffect,
    TemporaryPumpEffect,
    UpkeepDamageEffect,
    UpkeepDamageRecipient,
    VariableCreatureStats,
    VariableStatKind,
)
from ..mana import ManaCost
from ..types import CardType, Color, KeywordAbility, Zone


_CREATURE_IN_PLAY = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
)


def _regeneration(cost: str) -> tuple[ActivatedRegenerationAbility, ...]:
    return (ActivatedRegenerationAbility(ManaCost.parse(cost)),)


def _damaging_aura(
    name: str,
    cost: str,
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
        colors=frozenset({Color.BLACK}),
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


SCATHE_ZOMBIES = CardDefinition(
    name="Scathe Zombies",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{B}"),
    colors=frozenset({Color.BLACK}),
    subtypes=("Zombies",),
    power=2,
    toughness=2,
)

BLACK_KNIGHT = CardDefinition(
    name="Black Knight",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{B}{B}"),
    rules_text="Protection from white, first strike",
    colors=frozenset({Color.BLACK}),
    subtypes=("Knight",),
    power=2,
    toughness=2,
    abilities=frozenset(
        {
            KeywordAbility.FIRST_STRIKE,
            KeywordAbility.PROTECTION_FROM_WHITE,
        }
    ),
)

BOG_WRAITH = CardDefinition(
    name="Bog Wraith",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{B}"),
    rules_text="Swampwalk",
    colors=frozenset({Color.BLACK}),
    subtypes=("Wraith",),
    power=3,
    toughness=3,
    abilities=frozenset({KeywordAbility.SWAMPWALK}),
)

FROZEN_SHADE = CardDefinition(
    name="Frozen Shade",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{B}"),
    rules_text="{B}: +1/+1 until end of turn.",
    colors=frozenset({Color.BLACK}),
    subtypes=("Shade",),
    power=0,
    toughness=1,
    activated_abilities=(
        ActivatedPumpAbility(ManaCost.parse("{B}"), power=1, toughness=1),
    ),
)

NIGHTMARE = CardDefinition(
    name="Nightmare",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{5}{B}"),
    rules_text=(
        "Flying. Power and toughness each equal the number of Swamps "
        "you control."
    ),
    colors=frozenset({Color.BLACK}),
    subtypes=("Nightmare",),
    abilities=frozenset({KeywordAbility.FLYING}),
    variable_stats=VariableCreatureStats(
        VariableStatKind.CONTROLLED_LAND_SUBTYPE,
        subtype="Swamp",
    ),
)

PLAGUE_RATS = CardDefinition(
    name="Plague Rats",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{B}"),
    rules_text=(
        "Power and toughness each equal the number of Rats in play, "
        "counting both sides."
    ),
    colors=frozenset({Color.BLACK}),
    subtypes=("Rats",),
    variable_stats=VariableCreatureStats(
        VariableStatKind.ALL_CREATURE_SUBTYPE,
        subtype="Rats",
    ),
)

DRUDGE_SKELETONS = CardDefinition(
    name="Drudge Skeletons",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{B}"),
    rules_text="{B}: Regenerate Drudge Skeletons.",
    colors=frozenset({Color.BLACK}),
    subtypes=("Skeletons",),
    power=1,
    toughness=1,
    activated_abilities=_regeneration("{B}"),
)

WILL_O_THE_WISP = CardDefinition(
    name="Will-o'-the-Wisp",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{B}"),
    rules_text="Flying. {B}: Regenerate Will-o'-the-Wisp.",
    colors=frozenset({Color.BLACK}),
    subtypes=("Will-O'-The-Wisp",),
    power=0,
    toughness=1,
    abilities=frozenset({KeywordAbility.FLYING}),
    activated_abilities=_regeneration("{B}"),
)

WALL_OF_BONE = CardDefinition(
    name="Wall of Bone",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{B}"),
    rules_text="{B}: Regenerate Wall of Bone.",
    colors=frozenset({Color.BLACK}),
    subtypes=("Wall",),
    power=1,
    toughness=4,
    activated_abilities=_regeneration("{B}"),
)

ZOMBIE_MASTER = CardDefinition(
    name="Zombie Master",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{B}{B}"),
    rules_text=(
        "All Zombies in play gain swampwalk and "
        '"{B}: Regenerates" while Zombie Master remains in play.'
    ),
    colors=frozenset({Color.BLACK}),
    subtypes=("Lord",),
    power=2,
    toughness=3,
    continuous_effects=(
        ContinuousEffect(
            subtype="Zombies",
            exclude_source=True,
            granted_abilities=frozenset({KeywordAbility.SWAMPWALK}),
            granted_regeneration_cost=ManaCost.parse("{B}"),
        ),
    ),
)

ROYAL_ASSASSIN = CardDefinition(
    name="Royal Assassin",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{B}{B}"),
    rules_text="Tap to destroy any tapped creature.",
    colors=frozenset({Color.BLACK}),
    subtypes=("Assassin",),
    power=1,
    toughness=1,
    activated_abilities=(
        ActivatedDestroyAbility(
            TargetRequirement(
                zone=Zone.BATTLEFIELD,
                card_types=frozenset({CardType.CREATURE}),
                tapped_only=True,
            )
        ),
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

UNHOLY_STRENGTH = CardDefinition(
    name="Unholy Strength",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{B}"),
    rules_text="Target creature gains +2/+1.",
    colors=frozenset({Color.BLACK}),
    subtypes=("Enchant Creature",),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD, power=2, toughness=1
        ),
    ),
    target_requirement=_CREATURE_IN_PLAY,
)

WEAKNESS = CardDefinition(
    name="Weakness",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{B}"),
    rules_text="Target creature gets -2/-1.",
    colors=frozenset({Color.BLACK}),
    subtypes=("Enchant Creature",),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD, power=-2, toughness=-1
        ),
    ),
    target_requirement=_CREATURE_IN_PLAY,
)

CURSED_LAND = _damaging_aura(
    "Cursed Land", "{2}{B}{B}", CardType.LAND, "Land"
)
WARP_ARTIFACT = _damaging_aura(
    "Warp Artifact", "{B}{B}", CardType.ARTIFACT, "Artifact"
)

SINKHOLE = CardDefinition(
    name="Sinkhole",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{B}{B}"),
    rules_text="Destroy any one land.",
    colors=frozenset({Color.BLACK}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.LAND}),
    ),
    spell_effects=(DestroyTargetsEffect(),),
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

HOWL_FROM_BEYOND = CardDefinition(
    name="Howl from Beyond",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{X}{B}"),
    rules_text="Target creature gains +X/+0 until end of turn.",
    colors=frozenset({Color.BLACK}),
    target_requirement=_CREATURE_IN_PLAY,
    spell_effects=(TemporaryPumpEffect(power_per_x=1),),
)


BLACK_CARDS = tuple(
    sorted(
        (
            BAD_MOON,
            BLACK_KNIGHT,
            BOG_WRAITH,
            CURSED_LAND,
            DRUDGE_SKELETONS,
            FROZEN_SHADE,
            HOWL_FROM_BEYOND,
            NIGHTMARE,
            PLAGUE_RATS,
            RAISE_DEAD,
            ROYAL_ASSASSIN,
            SCATHE_ZOMBIES,
            SINKHOLE,
            UNHOLY_STRENGTH,
            WALL_OF_BONE,
            WARP_ARTIFACT,
            WEAKNESS,
            WILL_O_THE_WISP,
            ZOMBIE_MASTER,
        ),
        key=lambda card: card.name,
    )
)
