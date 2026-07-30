"""Simple creature-enchanting enchantments from Limited Edition Beta."""

from .cards import (
    ActivatedPumpAbility,
    ActivatedRegenerationAbility,
    CardDefinition,
    ContinuousEffect,
    EffectScope,
    TargetRequirement,
)
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility, Zone


HOLY_STRENGTH = CardDefinition(
    name="Holy Strength",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{W}"),
    rules_text="Target creature gains +1/+2.",
    colors=frozenset({Color.WHITE}),
    subtypes=("Enchant Creature",),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD, power=1, toughness=2
        ),
    ),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD, card_types=frozenset({CardType.CREATURE})
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
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD, card_types=frozenset({CardType.CREATURE})
    ),
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
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD, card_types=frozenset({CardType.CREATURE})
    ),
)

LANCE = CardDefinition(
    name="Lance",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{W}"),
    rules_text="Target creature gains first strike.",
    colors=frozenset({Color.WHITE}),
    subtypes=("Enchant Creature",),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD,
            granted_abilities=frozenset({KeywordAbility.FIRST_STRIKE}),
        ),
    ),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD, card_types=frozenset({CardType.CREATURE})
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
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD, card_types=frozenset({CardType.CREATURE})
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
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD, card_types=frozenset({CardType.CREATURE})
    ),
)

BLESSING = CardDefinition(
    name="Blessing",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{W}{W}"),
    rules_text="{W}: Enchanted creature gets +1/+1 until end of turn.",
    colors=frozenset({Color.WHITE}),
    subtypes=("Enchant Creature",),
    activated_abilities=(
        ActivatedPumpAbility(
            ManaCost.parse("{W}"),
            power=1,
            toughness=1,
            affects_attached_creature=True,
        ),
    ),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD, card_types=frozenset({CardType.CREATURE})
    ),
)

HOLY_ARMOR = CardDefinition(
    name="Holy Armor",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{W}"),
    rules_text=(
        "Enchanted creature gets +0/+2. "
        "{W}: Enchanted creature gets +0/+1 until end of turn."
    ),
    colors=frozenset({Color.WHITE}),
    subtypes=("Enchant Creature",),
    continuous_effects=(
        ContinuousEffect(scope=EffectScope.ATTACHED_CARD, toughness=2),
    ),
    activated_abilities=(
        ActivatedPumpAbility(
            ManaCost.parse("{W}"),
            toughness=1,
            affects_attached_creature=True,
        ),
    ),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD, card_types=frozenset({CardType.CREATURE})
    ),
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
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD, card_types=frozenset({CardType.CREATURE})
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
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD, card_types=frozenset({CardType.CREATURE})
    ),
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
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
    ),
)

def _ward(name: str, protected_color: Color, ability: KeywordAbility) -> CardDefinition:
    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.ENCHANTMENT}),
        mana_cost=ManaCost.parse("{W}"),
        rules_text=f"Target creature gains protection from {protected_color.name.lower()}.",
        colors=frozenset({Color.WHITE}),
        subtypes=("Enchant Creature",),
        continuous_effects=(
            ContinuousEffect(
                scope=EffectScope.ATTACHED_CARD,
                granted_abilities=frozenset({ability}),
            ),
        ),
        target_requirement=TargetRequirement(
            zone=Zone.BATTLEFIELD,
            card_types=frozenset({CardType.CREATURE}),
        ),
    )


BLACK_WARD = _ward(
    "Black Ward", Color.BLACK, KeywordAbility.PROTECTION_FROM_BLACK
)
BLUE_WARD = _ward(
    "Blue Ward", Color.BLUE, KeywordAbility.PROTECTION_FROM_BLUE
)
GREEN_WARD = _ward(
    "Green Ward", Color.GREEN, KeywordAbility.PROTECTION_FROM_GREEN
)
RED_WARD = _ward(
    "Red Ward", Color.RED, KeywordAbility.PROTECTION_FROM_RED
)
WHITE_WARD = _ward(
    "White Ward", Color.WHITE, KeywordAbility.PROTECTION_FROM_WHITE
)


SIMPLE_ENCHANT_CREATURES = (HOLY_STRENGTH, UNHOLY_STRENGTH, WEAKNESS)
ABILITY_ENCHANT_CREATURES = (LANCE, FLIGHT, BURROWING, REGENERATION, WEB)
PUMP_ENCHANT_CREATURES = (BLESSING, HOLY_ARMOR, FIREBREATHING)
PROTECTION_ENCHANT_CREATURES = (
    BLACK_WARD,
    BLUE_WARD,
    GREEN_WARD,
    RED_WARD,
    WHITE_WARD,
)
ENCHANT_CREATURES = (
    SIMPLE_ENCHANT_CREATURES
    + ABILITY_ENCHANT_CREATURES
    + PUMP_ENCHANT_CREATURES
    + PROTECTION_ENCHANT_CREATURES
)
