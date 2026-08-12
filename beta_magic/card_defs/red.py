"""Canonical definitions of currently supported red Beta cards."""

from ..abilities import (
    ActivatedDamageAbility,
    ActivatedDestroyAbility,
    ActivatedPumpAbility,
    ActivatedRegenerationAbility,
    ActivatedTemporaryAbility,
    ActivatedUnblockableAbility,
    TargetRequirement,
)
from ..cards import CardDefinition
from ..effects import (
    CounterPurchaseUpkeepEffect,
    ContinuousEffect,
    CounterTargetSpellEffect,
    DamageEffect,
    DestroyAllEffect,
    DestroyTargetsEffect,
    DiscardHandsAndDrawEffect,
    EffectScope,
    GlobalDamageEffect,
    LandManaBonusEffect,
    PermanentTappedEffect,
    UntapRestrictionEffect,
    VariableCreatureStats,
    VariableStatKind,
)
from ..mana import ManaCost
from ..types import CardType, Color, KeywordAbility, Zone
from .shared import lace


_CREATURE_IN_PLAY = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
)

CHAOSLACE = lace("Chaoslace", Color.RED)

SMOKE = CardDefinition(
    name="Smoke",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{R}{R}"),
    rules_text="Each player untaps only one creature during their untap phase.",
    colors=frozenset({Color.RED}),
    untap_effects=(
        UntapRestrictionEffect(card_type=CardType.CREATURE, maximum_untaps=1),
    ),
)

MANABARBS = CardDefinition(
    name="Manabarbs",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{3}{R}"),
    rules_text=(
        "Whenever any land becomes tapped, Manabarbs deals 1 damage to "
        "that land's controller."
    ),
    colors=frozenset({Color.RED}),
    permanent_tapped_effects=(PermanentTappedEffect(damage=1),),
)

MANA_FLARE = CardDefinition(
    name="Mana Flare",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{2}{R}"),
    rules_text=(
        "Whenever either player taps a land for mana, that land produces "
        "one additional mana of the chosen type."
    ),
    colors=frozenset({Color.RED}),
    land_mana_bonus_effects=(LandManaBonusEffect(),),
)

ROCK_HYDRA = CardDefinition(
    name="Rock Hydra",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{X}{R}{R}"),
    rules_text=(
        "Put X +1/+1 counters (heads) on Rock Hydra. Each point of damage "
        "Rock Hydra suffers destroys one head unless {R} is spent. During "
        "upkeep, new heads may be grown for {R}{R}{R} apiece."
    ),
    colors=frozenset({Color.RED}),
    subtypes=("Hydra",),
    power=0,
    toughness=0,
    x_enters_with_counter="head",
    counter_power_bonus=(("head", 1),),
    counter_toughness_bonus=(("head", 1),),
    damage_absorbing_counter="head",
    damage_counter_preservation_cost=ManaCost.parse("{R}"),
    upkeep_effects=(
        CounterPurchaseUpkeepEffect("head", ManaCost.parse("{R}{R}{R}")),
    ),
)

RED_ELEMENTAL_BLAST = CardDefinition(
    name="Red Elemental Blast",
    card_types=frozenset({CardType.INTERRUPT}),
    mana_cost=ManaCost.parse("{R}"),
    rules_text=(
        "Counters a blue spell being cast or destroys a blue card in play."
    ),
    colors=frozenset({Color.RED}),
    target_requirement=TargetRequirement(
        zone=Zone.STACK,
        additional_zones=frozenset({Zone.BATTLEFIELD}),
        color=Color.BLUE,
    ),
    spell_effects=(CounterTargetSpellEffect(), DestroyTargetsEffect()),
    casting_modes=("Counter spell", "Destroy permanent"),
    casting_mode_target_zones=(Zone.STACK, Zone.BATTLEFIELD),
)
_ANY_CREATURE_OR_PLAYER = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
    players=True,
)


def _creature(
    name: str, cost: str, subtype: str, power: int, toughness: int
) -> CardDefinition:
    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.CREATURE}),
        mana_cost=ManaCost.parse(cost),
        colors=frozenset({Color.RED}),
        subtypes=(subtype,),
        power=power,
        toughness=toughness,
    )


EARTH_ELEMENTAL = _creature(
    "Earth Elemental", "{3}{R}{R}", "Elemental", 4, 5
)
EARTHBIND = CardDefinition(
    name="Earthbind",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{R}"),
    rules_text=(
        "Enchant flying creature. Earthbind deals 2 damage to enchanted "
        "creature, which loses flying."
    ),
    colors=frozenset({Color.RED}),
    subtypes=("Enchant Flying Creature",),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
        required_abilities=frozenset({KeywordAbility.FLYING}),
    ),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD,
            removed_abilities=frozenset({KeywordAbility.FLYING}),
        ),
    ),
    damages_attached_on_entry=2,
)
FIRE_ELEMENTAL = _creature(
    "Fire Elemental", "{3}{R}{R}", "Elemental", 5, 4
)
GRAY_OGRE = _creature("Gray Ogre", "{2}{R}", "Ogre", 2, 2)
HILL_GIANT = _creature("Hill Giant", "{3}{R}", "Giant", 3, 3)
STONE_GIANT = CardDefinition(
    name="Stone Giant",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{R}{R}"),
    rules_text=(
        "Tap to make one of your own creatures flying until end of turn. "
        "That creature must have toughness less than Stone Giant's power "
        "and is destroyed at end of turn."
    ),
    colors=frozenset({Color.RED}),
    subtypes=("Giant",),
    power=3,
    toughness=4,
    activated_abilities=(
        ActivatedTemporaryAbility(
            TargetRequirement(
                zone=Zone.BATTLEFIELD,
                card_types=frozenset({CardType.CREATURE}),
                controller_only=True,
            ),
            granted_abilities=frozenset({KeywordAbility.FLYING}),
            toughness_less_than_source_power=True,
            destroy_at_end_of_turn=True,
        ),
    ),
)
TWO_HEADED_GIANT_OF_FORIYS = CardDefinition(
    name="Two-Headed Giant of Foriys",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{4}{R}"),
    rules_text=(
        "Trample. May block two attacking creatures; divide damage between "
        "them however its controller likes."
    ),
    colors=frozenset({Color.RED}),
    subtypes=("Giant",),
    power=4,
    toughness=4,
    abilities=frozenset({KeywordAbility.TRAMPLE}),
    maximum_attackers_blocked=2,
)
HURLOON_MINOTAUR = _creature(
    "Hurloon Minotaur", "{1}{R}{R}", "Minotaur", 2, 3
)
MONSS_GOBLIN_RAIDERS = _creature(
    "Mons's Goblin Raiders", "{R}", "Goblins", 1, 1
)
WALL_OF_STONE = _creature("Wall of Stone", "{1}{R}{R}", "Wall", 0, 8)
WALL_OF_FIRE = CardDefinition(
    name="Wall of Fire",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{R}{R}"),
    rules_text="{R}: Wall of Fire gets +1/+0 until end of turn.",
    colors=frozenset({Color.RED}),
    subtypes=("Wall",),
    power=0,
    toughness=5,
    activated_abilities=(
        ActivatedPumpAbility(ManaCost.parse("{R}"), power=1),
    ),
)
IRONCLAW_ORCS = CardDefinition(
    name="Ironclaw Orcs",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{R}"),
    rules_text=(
        "Ironclaw Orcs cannot be assigned to block any creature with "
        "power greater than 1."
    ),
    colors=frozenset({Color.RED}),
    subtypes=("Orcs",),
    power=2,
    toughness=2,
    maximum_blocked_power=1,
)

ROC_OF_KHER_RIDGES = CardDefinition(
    name="Roc of Kher Ridges",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{R}"),
    rules_text="Flying",
    colors=frozenset({Color.RED}),
    subtypes=("Roc",),
    power=3,
    toughness=3,
    abilities=frozenset({KeywordAbility.FLYING}),
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

SHIVAN_DRAGON = CardDefinition(
    name="Shivan Dragon",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{4}{R}{R}"),
    rules_text="Flying. {R}: +1/+0 until end of turn.",
    colors=frozenset({Color.RED}),
    subtypes=("Dragon",),
    power=5,
    toughness=5,
    abilities=frozenset({KeywordAbility.FLYING}),
    activated_abilities=(
        ActivatedPumpAbility(ManaCost.parse("{R}"), power=1),
    ),
)

GRANITE_GARGOYLE = CardDefinition(
    name="Granite Gargoyle",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{R}"),
    rules_text="Flying. {R}: +0/+1 until end of turn.",
    colors=frozenset({Color.RED}),
    subtypes=("Gargoyle",),
    power=2,
    toughness=2,
    abilities=frozenset({KeywordAbility.FLYING}),
    activated_abilities=(
        ActivatedPumpAbility(ManaCost.parse("{R}"), toughness=1),
    ),
)

DRAGON_WHELP = CardDefinition(
    name="Dragon Whelp",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{R}{R}"),
    rules_text=(
        "Flying. {R}: +1/+0 until end of turn. If more than {R}{R}{R} "
        "is spent this way in a turn, destroy Dragon Whelp at end of turn."
    ),
    colors=frozenset({Color.RED}),
    subtypes=("Dragon",),
    power=2,
    toughness=3,
    abilities=frozenset({KeywordAbility.FLYING}),
    activated_abilities=(
        ActivatedPumpAbility(
            ManaCost.parse("{R}"),
            power=1,
            safe_activations_per_turn=3,
        ),
    ),
)

KELDON_WARLORD = CardDefinition(
    name="Keldon Warlord",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{R}{R}"),
    rules_text=(
        "Power and toughness each equal the number of non-Wall creatures "
        "you control, including Keldon Warlord."
    ),
    colors=frozenset({Color.RED}),
    subtypes=("Lord",),
    variable_stats=VariableCreatureStats(
        VariableStatKind.CONTROLLED_NON_WALL_CREATURES
    ),
)

UTHDEN_TROLL = CardDefinition(
    name="Uthden Troll",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{R}"),
    rules_text="{R}: Regenerate Uthden Troll.",
    colors=frozenset({Color.RED}),
    subtypes=("Troll",),
    power=2,
    toughness=2,
    activated_abilities=(
        ActivatedRegenerationAbility(ManaCost.parse("{R}")),
    ),
)

SEDGE_TROLL = CardDefinition(
    name="Sedge Troll",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{R}"),
    rules_text=(
        "{B}: Regenerates. Sedge Troll gains +1/+1 if its controller "
        "has any Swamps in play."
    ),
    colors=frozenset({Color.RED}),
    subtypes=("Troll",),
    power=2,
    toughness=2,
    activated_abilities=(
        ActivatedRegenerationAbility(ManaCost.parse("{B}")),
    ),
    continuous_effects=(
        ContinuousEffect(
            power=1,
            toughness=1,
            source_only=True,
            controller_has_land_subtype="Swamp",
        ),
    ),
)

ORCISH_ARTILLERY = CardDefinition(
    name="Orcish Artillery",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{R}{R}"),
    rules_text=(
        "Tap: Orcish Artillery does 2 damage to any target and "
        "3 damage to you."
    ),
    colors=frozenset({Color.RED}),
    subtypes=("Orcs",),
    power=1,
    toughness=3,
    activated_abilities=(
        ActivatedDamageAbility(
            2,
            _ANY_CREATURE_OR_PLAYER,
            controller_damage=3,
        ),
    ),
)

DWARVEN_DEMOLITION_TEAM = CardDefinition(
    name="Dwarven Demolition Team",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{R}"),
    rules_text="Tap to destroy a Wall.",
    colors=frozenset({Color.RED}),
    subtypes=("Dwarves",),
    power=1,
    toughness=1,
    activated_abilities=(
        ActivatedDestroyAbility(
            TargetRequirement(
                zone=Zone.BATTLEFIELD,
                card_types=frozenset({CardType.CREATURE}),
                subtypes=frozenset({"Wall"}),
            )
        ),
    ),
)

DWARVEN_WARRIORS = CardDefinition(
    name="Dwarven Warriors",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{R}"),
    rules_text=(
        "Tap: Target creature with power no greater than 2 is unblockable "
        "this turn."
    ),
    colors=frozenset({Color.RED}),
    subtypes=("Dwarves",),
    power=1,
    toughness=1,
    activated_abilities=(
        ActivatedUnblockableAbility(
            TargetRequirement(
                zone=Zone.BATTLEFIELD,
                card_types=frozenset({CardType.CREATURE}),
                maximum_power=2,
            )
        ),
    ),
)

GOBLIN_BALLOON_BRIGADE = CardDefinition(
    name="Goblin Balloon Brigade",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{R}"),
    rules_text="{R}: Goblin Balloon Brigade gains flying until end of turn.",
    colors=frozenset({Color.RED}),
    subtypes=("Goblins",),
    power=1,
    toughness=1,
    activated_abilities=(
        ActivatedPumpAbility(
            ManaCost.parse("{R}"),
            granted_abilities=frozenset({KeywordAbility.FLYING}),
        ),
    ),
)

ORCISH_ORIFLAMME = CardDefinition(
    name="Orcish Oriflamme",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{3}{R}"),
    rules_text="When attacking, all of your attacking creatures gain +1/+0.",
    colors=frozenset({Color.RED}),
    continuous_effects=(
        ContinuousEffect(power=1, controller_only=True, attacking_only=True),
    ),
)

BURROWING = CardDefinition(
    name="Burrowing",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{R}"),
    rules_text="Target creature gains mountainwalk.",
    colors=frozenset({Color.RED}),
    subtypes=("Enchant Creature",),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD,
            granted_abilities=frozenset({KeywordAbility.MOUNTAINWALK}),
        ),
    ),
    target_requirement=_CREATURE_IN_PLAY,
)

FIREBREATHING = CardDefinition(
    name="Firebreathing",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{R}"),
    rules_text="{R}: Enchanted creature gets +1/+0 until end of turn.",
    colors=frozenset({Color.RED}),
    subtypes=("Enchant Creature",),
    activated_abilities=(
        ActivatedPumpAbility(
            ManaCost.parse("{R}"),
            power=1,
            affects_attached_creature=True,
        ),
    ),
    target_requirement=_CREATURE_IN_PLAY,
)

LIGHTNING_BOLT = CardDefinition(
    name="Lightning Bolt",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{R}"),
    rules_text="Lightning Bolt does 3 damage to one target.",
    colors=frozenset({Color.RED}),
    target_requirement=_ANY_CREATURE_OR_PLAYER,
    spell_effects=(DamageEffect(3),),
)

DISINTEGRATE = CardDefinition(
    name="Disintegrate",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{X}{R}"),
    rules_text=(
        "Disintegrate does X damage to one target. If target dies this turn, "
        "it is removed from the game and cannot be regenerated."
    ),
    colors=frozenset({Color.RED}),
    target_requirement=_ANY_CREATURE_OR_PLAYER,
    spell_effects=(
        DamageEffect(amount_per_x=1, disintegrates_target=True),
    ),
)

SHATTER = CardDefinition(
    name="Shatter",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{1}{R}"),
    rules_text="Shatter destroys target artifact.",
    colors=frozenset({Color.RED}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.ARTIFACT}),
    ),
    spell_effects=(DestroyTargetsEffect(),),
)

TUNNEL = CardDefinition(
    name="Tunnel",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{R}"),
    rules_text="Destroys 1 wall. Target wall cannot be regenerated.",
    colors=frozenset({Color.RED}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
        subtypes=frozenset({"Wall"}),
    ),
    spell_effects=(DestroyTargetsEffect(regeneration_allowed=False),),
)

STONE_RAIN = CardDefinition(
    name="Stone Rain",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{2}{R}"),
    rules_text="Destroy any one land.",
    colors=frozenset({Color.RED}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.LAND}),
    ),
    spell_effects=(DestroyTargetsEffect(),),
)

FLASHFIRES = CardDefinition(
    name="Flashfires",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{3}{R}"),
    rules_text="Destroy all Plains in play.",
    colors=frozenset({Color.RED}),
    spell_effects=(
        DestroyAllEffect(
            frozenset({CardType.LAND}),
            subtypes=frozenset({"Plains"}),
        ),
    ),
)

EARTHQUAKE = CardDefinition(
    name="Earthquake",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{X}{R}"),
    rules_text=(
        "Earthquake does X damage to each player and each non-flying "
        "creature in play."
    ),
    colors=frozenset({Color.RED}),
    spell_effects=(
        GlobalDamageEffect(amount_per_x=1, creatures_with_flying=False),
    ),
)

WHEEL_OF_FORTUNE = CardDefinition(
    name="Wheel of Fortune",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{2}{R}"),
    rules_text="Both players discard their hands, then draw seven cards.",
    colors=frozenset({Color.RED}),
    spell_effects=(DiscardHandsAndDrawEffect(7),),
)


RED_CARDS = tuple(
    sorted(
        (
            BURROWING,
            CHAOSLACE,
            DRAGON_WHELP,
            DWARVEN_DEMOLITION_TEAM,
            DWARVEN_WARRIORS,
            DISINTEGRATE,
            EARTH_ELEMENTAL,
            EARTHBIND,
            EARTHQUAKE,
            FIRE_ELEMENTAL,
            FIREBREATHING,
            FLASHFIRES,
            GOBLIN_BALLOON_BRIGADE,
            GOBLIN_KING,
            GRANITE_GARGOYLE,
            GRAY_OGRE,
            HILL_GIANT,
            HURLOON_MINOTAUR,
            IRONCLAW_ORCS,
            KELDON_WARLORD,
            LIGHTNING_BOLT,
            MANABARBS,
            MANA_FLARE,
            MONSS_GOBLIN_RAIDERS,
            ORCISH_ARTILLERY,
            ORCISH_ORIFLAMME,
            ROC_OF_KHER_RIDGES,
            ROCK_HYDRA,
            RED_ELEMENTAL_BLAST,
            SEDGE_TROLL,
            SHATTER,
            SHIVAN_DRAGON,
            SMOKE,
            STONE_RAIN,
            STONE_GIANT,
            TUNNEL,
            TWO_HEADED_GIANT_OF_FORIYS,
            UTHDEN_TROLL,
            WALL_OF_STONE,
            WALL_OF_FIRE,
            WHEEL_OF_FORTUNE,
        ),
        key=lambda card: card.name,
    )
)
