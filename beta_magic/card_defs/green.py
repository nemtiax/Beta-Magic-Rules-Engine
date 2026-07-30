"""Canonical definitions of currently supported green Beta cards."""

from ..abilities import (
    ActivatedManaAbility,
    ActivatedRegenerationAbility,
    TargetRequirement,
)
from ..cards import CardDefinition
from ..effects import (
    ContinuousEffect,
    DestroyAllEffect,
    DestroyTargetsEffect,
    EffectScope,
    GainLifeEffect,
    GlobalDamageEffect,
    MoveTargetsEffect,
    TemporaryPumpEffect,
    UpkeepCostEffect,
    UpkeepDamageEffect,
    UpkeepDamageRecipient,
    UpkeepFailure,
)
from ..mana import ManaCost
from ..types import CardType, Color, KeywordAbility, Zone


_CREATURE_IN_PLAY = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
)


def _creature(
    name: str, cost: str, subtype: str, power: int, toughness: int
) -> CardDefinition:
    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.CREATURE}),
        mana_cost=ManaCost.parse(cost),
        colors=frozenset({Color.GREEN}),
        subtypes=(subtype,),
        power=power,
        toughness=toughness,
    )


CRAW_WURM = _creature("Craw Wurm", "{4}{G}{G}", "Wurm", 6, 4)
GRIZZLY_BEARS = _creature("Grizzly Bears", "{1}{G}", "Bears", 2, 2)
IRONROOT_TREEFOLK = _creature(
    "Ironroot Treefolk", "{4}{G}", "Treefolk", 3, 5
)
WALL_OF_ICE = _creature("Wall of Ice", "{2}{G}", "Wall", 0, 7)
WALL_OF_WOOD = _creature("Wall of Wood", "{G}", "Wall", 0, 3)

SCRYB_SPRITES = CardDefinition(
    name="Scryb Sprites",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{G}"),
    rules_text="Flying",
    colors=frozenset({Color.GREEN}),
    subtypes=("Faeries",),
    power=1,
    toughness=1,
    abilities=frozenset({KeywordAbility.FLYING}),
)

ELVISH_ARCHERS = CardDefinition(
    name="Elvish Archers",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{G}"),
    rules_text="First strike",
    colors=frozenset({Color.GREEN}),
    subtypes=("Elves",),
    power=2,
    toughness=1,
    abilities=frozenset({KeywordAbility.FIRST_STRIKE}),
)

WAR_MAMMOTH = CardDefinition(
    name="War Mammoth",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{G}"),
    rules_text="Trample",
    colors=frozenset({Color.GREEN}),
    subtypes=("Mammoth",),
    power=3,
    toughness=3,
    abilities=frozenset({KeywordAbility.TRAMPLE}),
)

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

SHANODIN_DRYADS = CardDefinition(
    name="Shanodin Dryads",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{G}"),
    rules_text="Forestwalk",
    colors=frozenset({Color.GREEN}),
    subtypes=("Nymph", "Dryad"),
    power=1,
    toughness=1,
    abilities=frozenset({KeywordAbility.FORESTWALK}),
)

LLANOWAR_ELVES = CardDefinition(
    name="Llanowar Elves",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{G}"),
    rules_text="Tap to add {G} to your mana pool.",
    colors=frozenset({Color.GREEN}),
    subtypes=("Mana Elves",),
    power=1,
    toughness=1,
    activated_abilities=(ActivatedManaAbility(Color.GREEN),),
)

BIRDS_OF_PARADISE = CardDefinition(
    name="Birds of Paradise",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{G}"),
    rules_text="Flying. Tap to add one mana of any color to your mana pool.",
    colors=frozenset({Color.GREEN}),
    subtypes=("Mana Birds",),
    power=0,
    toughness=1,
    abilities=frozenset({KeywordAbility.FLYING}),
    activated_abilities=tuple(
        ActivatedManaAbility(color)
        for color in (
            Color.WHITE,
            Color.BLUE,
            Color.BLACK,
            Color.RED,
            Color.GREEN,
        )
    ),
)

FORCE_OF_NATURE = CardDefinition(
    name="Force of Nature",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{G}{G}{G}{G}"),
    rules_text=(
        "Trample. During your upkeep, pay {G}{G}{G}{G} or "
        "Force of Nature deals 8 damage to you."
    ),
    colors=frozenset({Color.GREEN}),
    subtypes=("Elemental",),
    power=8,
    toughness=8,
    abilities=frozenset({KeywordAbility.TRAMPLE}),
    upkeep_effects=(
        UpkeepCostEffect(
            ManaCost.parse("{G}{G}{G}{G}"),
            failure=UpkeepFailure.DAMAGE_CONTROLLER,
            damage=8,
        ),
    ),
)

WALL_OF_BRAMBLES = CardDefinition(
    name="Wall of Brambles",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{G}"),
    rules_text="{G}: Regenerate Wall of Brambles.",
    colors=frozenset({Color.GREEN}),
    subtypes=("Wall",),
    power=2,
    toughness=3,
    activated_abilities=(
        ActivatedRegenerationAbility(ManaCost.parse("{G}")),
    ),
)

REGENERATION = CardDefinition(
    name="Regeneration",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{1}{G}"),
    rules_text="{G}: Enchanted creature regenerates.",
    colors=frozenset({Color.GREEN}),
    subtypes=("Enchant Creature",),
    activated_abilities=(
        ActivatedRegenerationAbility(
            ManaCost.parse("{G}"), affects_attached_creature=True
        ),
    ),
    target_requirement=_CREATURE_IN_PLAY,
)

WEB = CardDefinition(
    name="Web",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{G}"),
    rules_text=(
        "Enchanted creature gets +0/+2 and can block flying creatures."
    ),
    colors=frozenset({Color.GREEN}),
    subtypes=("Enchant Creature",),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD,
            toughness=2,
            granted_abilities=frozenset({KeywordAbility.CAN_BLOCK_FLYING}),
        ),
    ),
    target_requirement=_CREATURE_IN_PLAY,
)

WANDERLUST = CardDefinition(
    name="Wanderlust",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{2}{G}"),
    rules_text=(
        "Wanderlust deals 1 damage to enchanted creature's controller "
        "during that player's upkeep."
    ),
    colors=frozenset({Color.GREEN}),
    subtypes=("Enchant Creature",),
    target_requirement=_CREATURE_IN_PLAY,
    upkeep_effects=(
        UpkeepDamageEffect(
            1,
            recipient=UpkeepDamageRecipient.ATTACHED_PERMANENT_CONTROLLER,
        ),
    ),
)

GIANT_GROWTH = CardDefinition(
    name="Giant Growth",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{G}"),
    rules_text="Target creature gains +3/+3 until end of turn.",
    colors=frozenset({Color.GREEN}),
    target_requirement=_CREATURE_IN_PLAY,
    spell_effects=(TemporaryPumpEffect(power=3, toughness=3),),
)

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

STREAM_OF_LIFE = CardDefinition(
    name="Stream of Life",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{X}{G}"),
    rules_text="Target player gains X life.",
    colors=frozenset({Color.GREEN}),
    target_requirement=TargetRequirement(players=True),
    spell_effects=(GainLifeEffect(amount_per_x=1),),
)

HURRICANE = CardDefinition(
    name="Hurricane",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{X}{G}"),
    rules_text="Hurricane does X damage to each player and flying creature.",
    colors=frozenset({Color.GREEN}),
    spell_effects=(
        GlobalDamageEffect(amount_per_x=1, creatures_with_flying=True),
    ),
)

TRANQUILITY = CardDefinition(
    name="Tranquility",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{2}{G}"),
    rules_text="All enchantments in play must be discarded.",
    colors=frozenset({Color.GREEN}),
    spell_effects=(DestroyAllEffect(frozenset({CardType.ENCHANTMENT})),),
)

ICE_STORM = CardDefinition(
    name="Ice Storm",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{2}{G}"),
    rules_text="Destroy any one land.",
    colors=frozenset({Color.GREEN}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.LAND}),
    ),
    spell_effects=(DestroyTargetsEffect(),),
)

TSUNAMI = CardDefinition(
    name="Tsunami",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{3}{G}"),
    rules_text="Destroy all Islands in play.",
    colors=frozenset({Color.GREEN}),
    spell_effects=(
        DestroyAllEffect(
            frozenset({CardType.LAND}),
            subtypes=frozenset({"Island"}),
        ),
    ),
)


GREEN_CARDS = tuple(
    sorted(
        (
            BIRDS_OF_PARADISE,
            CRAW_WURM,
            ELVISH_ARCHERS,
            FORCE_OF_NATURE,
            GIANT_GROWTH,
            GIANT_SPIDER,
            GRIZZLY_BEARS,
            HURRICANE,
            ICE_STORM,
            IRONROOT_TREEFOLK,
            LLANOWAR_ELVES,
            REGENERATION,
            REGROWTH,
            SCRYB_SPRITES,
            SHANODIN_DRYADS,
            STREAM_OF_LIFE,
            TRANQUILITY,
            TSUNAMI,
            WALL_OF_BRAMBLES,
            WALL_OF_ICE,
            WALL_OF_WOOD,
            WANDERLUST,
            WAR_MAMMOTH,
            WEB,
        ),
        key=lambda card: card.name,
    )
)
