"""Canonical definitions of currently supported Beta artifacts."""

from ..abilities import (
    ActivatedDamageAbility,
    ActivatedDrawAbility,
    ActivatedEventLifeGainAbility,
    ActivatedManaAbility,
    ActivatedRegenerationAbility,
    ActivatedTapAbility,
    TargetRequirement,
)
from ..cards import CardDefinition
from ..effects import UpkeepDamageEffect
from ..mana import ManaCost
from ..types import CardType, Color, Zone


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

MOXEN = (MOX_PEARL, MOX_SAPPHIRE, MOX_JET, MOX_RUBY, MOX_EMERALD)
MANA_ARTIFACTS = MOXEN + (SOL_RING, BLACK_LOTUS)


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

UTILITY_ARTIFACTS = (ROD_OF_RUIN, JAYEMDAE_TOME, ICY_MANIPULATOR)

COPPER_TABLET = CardDefinition(
    name="Copper Tablet",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{2}"),
    rules_text="Copper Tablet deals 1 damage to each player during their upkeep.",
    upkeep_effects=(UpkeepDamageEffect(1),),
)

TIMED_ARTIFACTS = (COPPER_TABLET,)

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

ARTIFACT_CREATURES = (LIVING_WALL, OBSIANUS_GOLEM)

ARTIFACT_CARDS = tuple(
    sorted(
        MANA_ARTIFACTS
        + EVENT_LIFE_ARTIFACTS
        + UTILITY_ARTIFACTS
        + TIMED_ARTIFACTS
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
    "MANA_ARTIFACTS",
    "THRONE_OF_BONE",
    "WOODEN_SPHERE",
    "IVORY_CUP",
    "IRON_STAR",
    "CRYSTAL_ROD",
    "LUCKY_CHARMS",
    "SOUL_NET",
    "EVENT_LIFE_ARTIFACTS",
    "ROD_OF_RUIN",
    "JAYEMDAE_TOME",
    "ICY_MANIPULATOR",
    "UTILITY_ARTIFACTS",
    "COPPER_TABLET",
    "TIMED_ARTIFACTS",
    "LIVING_WALL",
    "OBSIANUS_GOLEM",
    "ARTIFACT_CREATURES",
    "ARTIFACT_CARDS",
]
