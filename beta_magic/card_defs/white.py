"""Canonical definitions of currently supported white Beta cards."""

from ..abilities import (
    ActivatedDestroyAbility,
    ActivatedPreventDamageAbility,
    ActivatedPumpAbility,
    TargetRequirement,
)
from ..cards import CardDefinition
from ..effects import (
    ContinuousEffect,
    DestroyAllEffect,
    DestroyTargetsEffect,
    EffectScope,
    GainLifeEffect,
    MoveTargetsEffect,
    RegenerateTargetsEffect,
    TemporaryPumpEffect,
    GlobalLandTypeConversion,
    UpkeepCostEffect,
)
from ..mana import ManaCost
from ..types import CardType, Color, KeywordAbility, Zone
from .shared import lace


_CREATURE_IN_PLAY = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
)
_WALL_IN_PLAY = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
    subtypes=frozenset({"Wall"}),
)

PURELACE = lace("Purelace", Color.WHITE)

ANIMATE_WALL = CardDefinition(
    name="Animate Wall",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{W}"),
    rules_text="Target Wall can attack. Its power and toughness are unchanged.",
    colors=frozenset({Color.WHITE}),
    subtypes=("Enchant Wall",),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD,
            wall_can_attack=True,
        ),
    ),
    target_requirement=_WALL_IN_PLAY,
)


def _ward(
    name: str, protected_color: Color, ability: KeywordAbility
) -> CardDefinition:
    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.ENCHANTMENT}),
        mana_cost=ManaCost.parse("{W}"),
        rules_text=(
            f"Target creature gains protection from "
            f"{protected_color.name.lower()}."
        ),
        colors=frozenset({Color.WHITE}),
        subtypes=("Enchant Creature",),
        continuous_effects=(
            ContinuousEffect(
                scope=EffectScope.ATTACHED_CARD,
                granted_abilities=frozenset({ability}),
            ),
        ),
        target_requirement=_CREATURE_IN_PLAY,
    )


def _circle(color: Color) -> CardDefinition:
    color_name = color.name.title()
    return CardDefinition(
        name=f"Circle of Protection: {color_name}",
        card_types=frozenset({CardType.ENCHANTMENT}),
        mana_cost=ManaCost.parse("{1}{W}"),
        rules_text=(
            f"{{1}}: Prevents all damage against you from one "
            f"{color_name.lower()} source."
        ),
        colors=frozenset({Color.WHITE}),
        activated_abilities=(
            ActivatedPreventDamageAbility(
                amount=None,
                mana_cost=ManaCost.parse("{1}"),
                tap_cost=False,
                source_color=color,
                controller_only=True,
            ),
        ),
    )


PEARLED_UNICORN = CardDefinition(
    name="Pearled Unicorn",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{W}"),
    colors=frozenset({Color.WHITE}),
    subtypes=("Unicorn",),
    power=2,
    toughness=2,
)

SAVANNAH_LIONS = CardDefinition(
    name="Savannah Lions",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{W}"),
    colors=frozenset({Color.WHITE}),
    subtypes=("Lions",),
    power=2,
    toughness=1,
)

WHITE_KNIGHT = CardDefinition(
    name="White Knight",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{W}{W}"),
    rules_text="Protection from black, first strike",
    colors=frozenset({Color.WHITE}),
    subtypes=("Knight",),
    power=2,
    toughness=2,
    abilities=frozenset(
        {
            KeywordAbility.FIRST_STRIKE,
            KeywordAbility.PROTECTION_FROM_BLACK,
        }
    ),
)

SAMITE_HEALER = CardDefinition(
    name="Samite Healer",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{W}"),
    rules_text="Tap to prevent 1 damage to any target.",
    colors=frozenset({Color.WHITE}),
    subtypes=("Cleric",),
    power=1,
    toughness=1,
    activated_abilities=(ActivatedPreventDamageAbility(amount=1),),
)

NORTHERN_PALADIN = CardDefinition(
    name="Northern Paladin",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{W}{W}"),
    rules_text="{W}{W} and tap: Destroy a black card in play.",
    colors=frozenset({Color.WHITE}),
    subtypes=("Paladin",),
    power=3,
    toughness=3,
    activated_abilities=(
        ActivatedDestroyAbility(
            TargetRequirement(zone=Zone.BATTLEFIELD, color=Color.BLACK),
            mana_cost=ManaCost.parse("{W}{W}"),
        ),
    ),
)

WALL_OF_SWORDS = CardDefinition(
    name="Wall of Swords",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{W}"),
    rules_text="Flying",
    colors=frozenset({Color.WHITE}),
    subtypes=("Wall",),
    power=3,
    toughness=5,
    abilities=frozenset({KeywordAbility.FLYING}),
)

SERRA_ANGEL = CardDefinition(
    name="Serra Angel",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{W}{W}"),
    rules_text="Flying. Does not tap when attacking.",
    colors=frozenset({Color.WHITE}),
    subtypes=("Angel",),
    power=4,
    toughness=4,
    abilities=frozenset(
        {
            KeywordAbility.FLYING,
            KeywordAbility.DOES_NOT_TAP_TO_ATTACK,
        }
    ),
)

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
    target_requirement=_CREATURE_IN_PLAY,
)

CONVERSION = CardDefinition(
    name="Conversion",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{2}{W}{W}"),
    rules_text=(
        "All Mountains are Plains. Pay {W}{W} during upkeep or destroy Conversion."
    ),
    colors=frozenset({Color.WHITE}),
    land_type_effects=(GlobalLandTypeConversion("Mountain", "Plains"),),
    upkeep_effects=(UpkeepCostEffect(ManaCost.parse("{W}{W}")),),
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
    target_requirement=_CREATURE_IN_PLAY,
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
    target_requirement=_CREATURE_IN_PLAY,
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
    target_requirement=_CREATURE_IN_PLAY,
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

CIRCLE_OF_PROTECTION_BLACK = _circle(Color.BLACK)
CIRCLE_OF_PROTECTION_BLUE = _circle(Color.BLUE)
CIRCLE_OF_PROTECTION_GREEN = _circle(Color.GREEN)
CIRCLE_OF_PROTECTION_RED = _circle(Color.RED)
CIRCLE_OF_PROTECTION_WHITE = _circle(Color.WHITE)

CIRCLES_OF_PROTECTION = (
    CIRCLE_OF_PROTECTION_BLACK,
    CIRCLE_OF_PROTECTION_BLUE,
    CIRCLE_OF_PROTECTION_GREEN,
    CIRCLE_OF_PROTECTION_RED,
    CIRCLE_OF_PROTECTION_WHITE,
)

CRUSADE = CardDefinition(
    name="Crusade",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{W}{W}"),
    rules_text="All white creatures gain +1/+1.",
    colors=frozenset({Color.WHITE}),
    continuous_effects=(
        ContinuousEffect(power=1, toughness=1, color=Color.WHITE),
    ),
)

CASTLE = CardDefinition(
    name="Castle",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{3}{W}"),
    rules_text=(
        "Your untapped creatures gain +0/+2. "
        "Attacking creatures lose this bonus."
    ),
    colors=frozenset({Color.WHITE}),
    continuous_effects=(
        ContinuousEffect(
            toughness=2,
            controller_only=True,
            untapped_only=True,
            nonattacking_only=True,
        ),
    ),
)

HEALING_SALVE = CardDefinition(
    name="Healing Salve",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{W}"),
    rules_text=(
        "Gain 3 life, or prevent up to 3 damage from being dealt "
        "to a single target."
    ),
    colors=frozenset({Color.WHITE}),
    target_requirement=TargetRequirement(players=True),
    spell_effects=(GainLifeEffect(amount=3),),
    prevention_amount=3,
)

RIGHTEOUSNESS = CardDefinition(
    name="Righteousness",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{W}"),
    rules_text="Target blocking creature gains +7/+7 until end of turn.",
    colors=frozenset({Color.WHITE}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
        blocking_only=True,
    ),
    spell_effects=(TemporaryPumpEffect(power=7, toughness=7),),
)

DEATH_WARD = CardDefinition(
    name="Death Ward",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{W}"),
    rules_text="Regenerates target creature.",
    colors=frozenset({Color.WHITE}),
    target_requirement=_CREATURE_IN_PLAY,
    spell_effects=(RegenerateTargetsEffect(),),
)

DISENCHANT = CardDefinition(
    name="Disenchant",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{1}{W}"),
    rules_text="Target enchantment or artifact must be discarded.",
    colors=frozenset({Color.WHITE}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        any_card_types=frozenset(
            {CardType.ENCHANTMENT, CardType.ARTIFACT}
        ),
    ),
    spell_effects=(DestroyTargetsEffect(),),
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

ARMAGEDDON = CardDefinition(
    name="Armageddon",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{3}{W}"),
    rules_text="Destroy all lands in play.",
    colors=frozenset({Color.WHITE}),
    spell_effects=(DestroyAllEffect(frozenset({CardType.LAND})),),
)

WRATH_OF_GOD = CardDefinition(
    name="Wrath of God",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{2}{W}{W}"),
    rules_text="Destroy all creatures. They cannot regenerate.",
    colors=frozenset({Color.WHITE}),
    spell_effects=(
        DestroyAllEffect(
            frozenset({CardType.CREATURE}),
            regeneration_allowed=False,
        ),
    ),
)

WHITE_CARDS = tuple(
    sorted(
        (
            ANIMATE_WALL,
            ARMAGEDDON,
            BLACK_WARD,
            BLESSING,
            BLUE_WARD,
            CASTLE,
            CONVERSION,
            *CIRCLES_OF_PROTECTION,
            CRUSADE,
            DEATH_WARD,
            DISENCHANT,
            GREEN_WARD,
            HEALING_SALVE,
            HOLY_ARMOR,
            HOLY_STRENGTH,
            LANCE,
            NORTHERN_PALADIN,
            PEARLED_UNICORN,
            PURELACE,
            RED_WARD,
            RESURRECTION,
            RIGHTEOUSNESS,
            SAMITE_HEALER,
            SAVANNAH_LIONS,
            SERRA_ANGEL,
            WALL_OF_SWORDS,
            WHITE_KNIGHT,
            WHITE_WARD,
            WRATH_OF_GOD,
        ),
        key=lambda card: card.name,
    )
)
