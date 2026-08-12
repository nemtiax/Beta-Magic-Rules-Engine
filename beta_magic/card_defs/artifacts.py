"""Canonical definitions of currently supported Beta artifacts."""

from ..abilities import (
    ActivatedAnimationAbility,
    ActivatedDamageAbility,
    ActivatedDestroyAllAbility,
    ActivatedDrawAbility,
    ActivatedCreateTokenAbility,
    ActivatedDiscardAbility,
    ActivatedExtraTurnAbility,
    ActivatedEventLifeGainAbility,
    ActivatedManaAbility,
    ActivatedPreventDamageAbility,
    ActivatedRevealHandAbility,
    ActivatedRegenerationAbility,
    ActivatedRedirectDamageAbility,
    ActivatedTapAbility,
    ActivatedTemporaryAbility,
    ActivatedUntapAbility,
    TargetRequirement,
)
from ..cards import CardDefinition
from ..effects import (
    ContinuousEffect,
    DrawPhaseEffect,
    LandEventDamageEffect,
    LandTapManaEffect,
    ManaPaymentEffect,
    UntapRestrictionEffect,
    UpkeepDamageEffect,
    UpkeepHandSizeDamageEffect,
)
from ..mana import ManaCost
from ..types import CardType, Color, KeywordAbility, Zone


def _mox(name: str, color: Color) -> CardDefinition:
    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.ARTIFACT}),
        mana_cost=ManaCost.parse("{0}"),
        rules_text=(
            f"Tap to add {{{color.value}}} to your mana pool. "
            "This ability can be played as an interrupt."
        ),
        activated_abilities=(ActivatedManaAbility(color),),
    )


MOX_PEARL = _mox("Mox Pearl", Color.WHITE)
MOX_SAPPHIRE = _mox("Mox Sapphire", Color.BLUE)
MOX_JET = _mox("Mox Jet", Color.BLACK)
MOX_RUBY = _mox("Mox Ruby", Color.RED)
MOX_EMERALD = _mox("Mox Emerald", Color.GREEN)

SOL_RING = CardDefinition(
    name="Sol Ring",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{1}"),
    rules_text=(
        "Tap to add {C}{C} to your mana pool. "
        "This ability can be played as an interrupt."
    ),
    activated_abilities=(ActivatedManaAbility(Color.COLORLESS, amount=2),),
)

BLACK_LOTUS = CardDefinition(
    name="Black Lotus",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{0}"),
    rules_text=(
        "Tap to add three mana of any single color to your mana pool, "
        "then destroy Black Lotus. This ability can be played as an interrupt."
    ),
    activated_abilities=tuple(
        ActivatedManaAbility(color, amount=3, sacrifice_source=True)
        for color in (
            Color.WHITE,
            Color.BLUE,
            Color.BLACK,
            Color.RED,
            Color.GREEN,
        )
    ),
)

MANA_VAULT = CardDefinition(
    name="Mana Vault",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{1}"),
    rules_text=(
        "Tap to add {C}{C}{C}. Mana Vault does not untap normally. Pay {4} "
        "to untap it. If it remains tapped during your upkeep, it deals 1 "
        "damage to you."
    ),
    activated_abilities=(
        ActivatedManaAbility(Color.COLORLESS, amount=3),
        ActivatedUntapAbility(ManaCost.parse("{4}")),
    ),
    upkeep_effects=(
        UpkeepDamageEffect(
            1, controller_upkeep_only=True, source_tapped=True
        ),
    ),
    untaps_normally=False,
)

BASALT_MONOLITH = CardDefinition(
    name="Basalt Monolith",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{3}"),
    rules_text=(
        "Tap to add {C}{C}{C} to your mana pool. Basalt Monolith does not "
        "untap normally. Pay {3} to untap it; this is a fast effect. Its "
        "mana ability can be played as an interrupt."
    ),
    activated_abilities=(
        ActivatedManaAbility(Color.COLORLESS, amount=3),
        ActivatedUntapAbility(ManaCost.parse("{3}")),
    ),
    untaps_normally=False,
)

SUNGLASSES_OF_URZA = CardDefinition(
    name="Sunglasses of Urza",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{3}"),
    rules_text=(
        "White mana in your mana pool can be used as either white or red mana."
    ),
    mana_payment_effects=(ManaPaymentEffect(Color.WHITE, Color.RED),),
)

CELESTIAL_PRISM = CardDefinition(
    name="Celestial Prism",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{3}"),
    rules_text=(
        "{2}, {T}: Add one mana of any color to your mana pool. This ability "
        "can be played as an interrupt."
    ),
    activated_abilities=tuple(
        ActivatedManaAbility(color, mana_cost=ManaCost.parse("{2}"))
        for color in (
            Color.WHITE,
            Color.BLUE,
            Color.BLACK,
            Color.RED,
            Color.GREEN,
        )
    ),
)

DISRUPTING_SCEPTER = CardDefinition(
    name="Disrupting Scepter",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{3}"),
    rules_text="{3}, {T}: Opponent discards one card of their choice from hand.",
    activated_abilities=(ActivatedDiscardAbility(ManaCost.parse("{3}")),),
)

MOXEN = (MOX_PEARL, MOX_SAPPHIRE, MOX_JET, MOX_RUBY, MOX_EMERALD)
MANA_ARTIFACTS = MOXEN + (
    SOL_RING,
    BLACK_LOTUS,
    MANA_VAULT,
    BASALT_MONOLITH,
    CELESTIAL_PRISM,
)


def _lucky_charm(name: str, color: Color) -> CardDefinition:
    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.ARTIFACT}),
        mana_cost=ManaCost.parse("{1}"),
        rules_text=(
            f"{{1}}: Any {color.name.lower()} spell cast by any player "
            "gives you 1 life."
        ),
        activated_abilities=(
            ActivatedEventLifeGainAbility(
                ManaCost.parse("{1}"),
                spell_color=color,
            ),
        ),
    )


THRONE_OF_BONE = _lucky_charm("Throne of Bone", Color.BLACK)
WOODEN_SPHERE = _lucky_charm("Wooden Sphere", Color.GREEN)
IVORY_CUP = _lucky_charm("Ivory Cup", Color.WHITE)
IRON_STAR = _lucky_charm("Iron Star", Color.RED)
CRYSTAL_ROD = _lucky_charm("Crystal Rod", Color.BLUE)
LUCKY_CHARMS = (
    THRONE_OF_BONE,
    WOODEN_SPHERE,
    IVORY_CUP,
    IRON_STAR,
    CRYSTAL_ROD,
)

SOUL_NET = CardDefinition(
    name="Soul Net",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{1}"),
    rules_text=(
        "{1}: You gain 1 life every time a creature is destroyed, "
        "unless it is then regenerated."
    ),
    activated_abilities=(
        ActivatedEventLifeGainAbility(
            ManaCost.parse("{1}"),
            creature_death=True,
        ),
    ),
)

EVENT_LIFE_ARTIFACTS = LUCKY_CHARMS + (SOUL_NET,)

ANKH_OF_MISHRA = CardDefinition(
    name="Ankh of Mishra",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{2}"),
    rules_text="Ankh does 2 damage to anyone who puts a new land into play.",
    land_event_effects=(LandEventDamageEffect(2, land_enters=True),),
)

DINGUS_EGG = CardDefinition(
    name="Dingus Egg",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text=(
        "Whenever anyone loses a land, Dingus Egg does 2 damage to that "
        "player for each land lost."
    ),
    land_event_effects=(LandEventDamageEffect(2, land_lost=True),),
)

HOWLING_MINE = CardDefinition(
    name="Howling Mine",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{2}"),
    rules_text=(
        "Each player draws one extra card during the draw phase of each turn."
    ),
    draw_phase_effects=(DrawPhaseEffect(),),
)

KORMUS_BELL = CardDefinition(
    name="Kormus Bell",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text=(
        "All Swamps in play are 1/1 colorless creatures as well as lands."
    ),
    continuous_effects=(
        ContinuousEffect(
            land_subtype="Swamp",
            granted_card_types=frozenset({CardType.CREATURE}),
            base_power=1,
            base_toughness=1,
        ),
    ),
)

MEEKSTONE = CardDefinition(
    name="Meekstone",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{1}"),
    rules_text=(
        "Creatures with power greater than 2 do not untap during their "
        "controllers' untap phases."
    ),
    untap_effects=(UntapRestrictionEffect(maximum_creature_power=2),),
)

WINTER_ORB = CardDefinition(
    name="Winter Orb",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{2}"),
    rules_text="Each player untaps only one land during their untap phase.",
    untap_effects=(
        UntapRestrictionEffect(card_type=CardType.LAND, maximum_untaps=1),
    ),
)

GAUNTLET_OF_MIGHT = CardDefinition(
    name="Gauntlet of Might",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text=(
        "All red creatures get +1/+1. Whenever a Mountain is tapped, "
        "its owner adds {R}."
    ),
    continuous_effects=(
        ContinuousEffect(power=1, toughness=1, color=Color.RED),
    ),
    land_tap_mana_effects=(
        LandTapManaEffect(
            Color.RED,
            "Mountain",
            owner_receives=True,
        ),
    ),
)

HELM_OF_CHATZUK = CardDefinition(
    name="Helm of Chatzuk",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{1}"),
    rules_text=(
        "{1}, {T}: Target creature gains Banding until end of turn."
    ),
    activated_abilities=(
        ActivatedTemporaryAbility(
            TargetRequirement(
                zone=Zone.BATTLEFIELD,
                card_types=frozenset({CardType.CREATURE}),
            ),
            granted_abilities=frozenset({KeywordAbility.BANDING}),
            mana_cost=ManaCost.parse("{1}"),
        ),
    ),
)

LAND_EVENT_ARTIFACTS = (ANKH_OF_MISHRA, DINGUS_EGG)

_ANY_CREATURE_OR_PLAYER = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
    players=True,
)

ROD_OF_RUIN = CardDefinition(
    name="Rod of Ruin",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text="{3}: Rod of Ruin does 1 damage to any target.",
    activated_abilities=(
        ActivatedDamageAbility(
            damage=1,
            target_requirement=_ANY_CREATURE_OR_PLAYER,
            mana_cost=ManaCost.parse("{3}"),
        ),
    ),
)

CONSERVATOR = CardDefinition(
    name="Conservator",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text="{3}, {T}: Prevent the loss of up to 2 life.",
    activated_abilities=(
        ActivatedPreventDamageAbility(
            amount=2,
            mana_cost=ManaCost.parse("{3}"),
            controller_only=True,
            prevents_life_loss=True,
        ),
    ),
)

GLASSES_OF_URZA = CardDefinition(
    name="Glasses of Urza",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{1}"),
    rules_text="{T}: You may look at opponent's hand.",
    activated_abilities=(ActivatedRevealHandAbility(),),
)

JAYEMDAE_TOME = CardDefinition(
    name="Jayemdae Tome",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text="{4}: Draw one card.",
    activated_abilities=(ActivatedDrawAbility(ManaCost.parse("{4}")),),
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

NEVINYRRALS_DISK = CardDefinition(
    name="Nevinyrral's Disk",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text=(
        "Nevinyrral's Disk begins tapped. {1}, {T}: Destroy all artifacts, "
        "creatures, and enchantments."
    ),
    activated_abilities=(
        ActivatedDestroyAllAbility(
            frozenset(
                {CardType.ARTIFACT, CardType.CREATURE, CardType.ENCHANTMENT}
            ),
            mana_cost=ManaCost.parse("{1}"),
        ),
    ),
    enters_tapped=True,
)

JADE_MONOLITH = CardDefinition(
    name="Jade Monolith",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text=(
        "{1}: Redirect all damage from one source being dealt to a creature "
        "to you."
    ),
    activated_abilities=(
        ActivatedRedirectDamageAbility(ManaCost.parse("{1}")),
    ),
)

JADE_STATUE = CardDefinition(
    name="Jade Statue",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text=(
        "{2}: Jade Statue becomes a 3/6 artifact creature for the current "
        "attack. Use only during an attack and only once each turn."
    ),
    activated_abilities=(
        ActivatedAnimationAbility(
            ManaCost.parse("{2}"), power=3, toughness=6
        ),
    ),
)

TIME_VAULT = CardDefinition(
    name="Time Vault",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{2}"),
    rules_text=(
        "Tap to gain an additional turn after the current one. Time Vault "
        "doesn't untap normally; skip a turn to untap it on your following "
        "turn. Time Vault begins tapped."
    ),
    activated_abilities=(ActivatedExtraTurnAbility(),),
    enters_tapped=True,
    untaps_normally=False,
    may_skip_turn_to_untap=True,
)

GIANT_WASP_TOKEN = CardDefinition(
    name="Giant Wasp",
    card_types=frozenset({CardType.ARTIFACT, CardType.CREATURE}),
    mana_cost=ManaCost(),
    rules_text="Flying",
    subtypes=("Wasp",),
    power=1,
    toughness=1,
    abilities=frozenset({KeywordAbility.FLYING}),
)

THE_HIVE = CardDefinition(
    name="The Hive",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{5}"),
    rules_text=(
        "{5}, {T}: Create a Giant Wasp, a 1/1 flying artifact creature token."
    ),
    activated_abilities=(
        ActivatedCreateTokenAbility(
            token_definition=GIANT_WASP_TOKEN,
            mana_cost=ManaCost.parse("{5}"),
        ),
    ),
)

UTILITY_ARTIFACTS = (
    CONSERVATOR,
    GLASSES_OF_URZA,
    DISRUPTING_SCEPTER,
    ROD_OF_RUIN,
    JAYEMDAE_TOME,
    ICY_MANIPULATOR,
    NEVINYRRALS_DISK,
    JADE_MONOLITH,
    JADE_STATUE,
    HOWLING_MINE,
    KORMUS_BELL,
    GAUNTLET_OF_MIGHT,
    HELM_OF_CHATZUK,
    SUNGLASSES_OF_URZA,
    THE_HIVE,
)

UNTAP_ARTIFACTS = (MEEKSTONE, WINTER_ORB)

TURN_ARTIFACTS = (TIME_VAULT,)

COPPER_TABLET = CardDefinition(
    name="Copper Tablet",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{2}"),
    rules_text="Copper Tablet deals 1 damage to each player during their upkeep.",
    upkeep_effects=(UpkeepDamageEffect(1),),
)

BLACK_VISE = CardDefinition(
    name="Black Vise",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{1}"),
    rules_text=(
        "During an opponent's upkeep, Black Vise deals 1 damage to that "
        "player for each card in their hand beyond four."
    ),
    upkeep_effects=(UpkeepHandSizeDamageEffect(4),),
)

TIMED_ARTIFACTS = (COPPER_TABLET, BLACK_VISE)

LIVING_WALL = CardDefinition(
    name="Living Wall",
    card_types=frozenset({CardType.ARTIFACT, CardType.CREATURE}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text="Counts as a Wall. {1}: Regenerates.",
    subtypes=("Wall",),
    power=0,
    toughness=6,
    activated_abilities=(
        ActivatedRegenerationAbility(ManaCost.parse("{1}")),
    ),
)

OBSIANUS_GOLEM = CardDefinition(
    name="Obsianus Golem",
    card_types=frozenset({CardType.ARTIFACT, CardType.CREATURE}),
    mana_cost=ManaCost.parse("{6}"),
    subtypes=("Golem",),
    power=4,
    toughness=6,
)

CLOCKWORK_BEAST = CardDefinition(
    name="Clockwork Beast",
    card_types=frozenset({CardType.ARTIFACT, CardType.CREATURE}),
    mana_cost=ManaCost.parse("{6}"),
    rules_text=(
        "Enters with seven +1/+0 counters. Remove one immediately when it "
        "is declared as an attacker or blocker. During untap, pay 1 per "
        "lost counter to replace counters instead of untapping it."
    ),
    subtypes=("Beast",),
    power=0,
    toughness=4,
    initial_counters=(("+1/+0", 7),),
    counter_power_bonus=(("+1/+0", 1),),
    loses_counter_when_declared_for_combat="+1/+0",
    rewinds_during_untap=("+1/+0", 7),
)

JUGGERNAUT = CardDefinition(
    name="Juggernaut",
    card_types=frozenset({CardType.ARTIFACT, CardType.CREATURE}),
    mana_cost=ManaCost.parse("{4}"),
    rules_text="Must attack each turn if possible. Cannot be blocked by Walls.",
    subtypes=("Juggernaut",),
    power=5,
    toughness=3,
    must_attack_if_able=True,
    cannot_be_blocked_by_subtypes=frozenset({"Wall"}),
)

ARTIFACT_CREATURES = (
    CLOCKWORK_BEAST,
    JUGGERNAUT,
    LIVING_WALL,
    OBSIANUS_GOLEM,
)

ARTIFACT_CARDS = tuple(
    sorted(
        MANA_ARTIFACTS
        + EVENT_LIFE_ARTIFACTS
        + LAND_EVENT_ARTIFACTS
        + UTILITY_ARTIFACTS
        + TIMED_ARTIFACTS
        + TURN_ARTIFACTS
        + UNTAP_ARTIFACTS
        + ARTIFACT_CREATURES,
        key=lambda card: card.name,
    )
)

__all__ = [
    "MOX_PEARL",
    "MOX_SAPPHIRE",
    "MOX_JET",
    "MOX_RUBY",
    "MOX_EMERALD",
    "MOXEN",
    "SOL_RING",
    "BLACK_LOTUS",
    "MANA_VAULT",
    "BASALT_MONOLITH",
    "CELESTIAL_PRISM",
    "SUNGLASSES_OF_URZA",
    "DISRUPTING_SCEPTER",
    "MANA_ARTIFACTS",
    "THRONE_OF_BONE",
    "WOODEN_SPHERE",
    "IVORY_CUP",
    "IRON_STAR",
    "CRYSTAL_ROD",
    "LUCKY_CHARMS",
    "SOUL_NET",
    "EVENT_LIFE_ARTIFACTS",
    "ANKH_OF_MISHRA",
    "DINGUS_EGG",
    "HOWLING_MINE",
    "KORMUS_BELL",
    "GAUNTLET_OF_MIGHT",
    "HELM_OF_CHATZUK",
    "LAND_EVENT_ARTIFACTS",
    "ROD_OF_RUIN",
    "CONSERVATOR",
    "GLASSES_OF_URZA",
    "JAYEMDAE_TOME",
    "ICY_MANIPULATOR",
    "NEVINYRRALS_DISK",
    "JADE_MONOLITH",
    "JADE_STATUE",
    "TIME_VAULT",
    "THE_HIVE",
    "GIANT_WASP_TOKEN",
    "TURN_ARTIFACTS",
    "MEEKSTONE",
    "WINTER_ORB",
    "UNTAP_ARTIFACTS",
    "UTILITY_ARTIFACTS",
    "COPPER_TABLET",
    "BLACK_VISE",
    "TIMED_ARTIFACTS",
    "LIVING_WALL",
    "CLOCKWORK_BEAST",
    "JUGGERNAUT",
    "OBSIANUS_GOLEM",
    "ARTIFACT_CREATURES",
    "ARTIFACT_CARDS",
]
