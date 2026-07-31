"""Canonical definitions of currently supported blue Beta cards."""

from ..abilities import (
    ActivatedDamageAbility,
    ActivatedPumpAbility,
    TargetRequirement,
)
from ..cards import CardDefinition
from ..effects import (
    ContinuousEffect,
    AttachedLandTypeEffect,
    CounterTargetSpellEffect,
    DamageEffect,
    DrawCardsEffect,
    EffectRecipient,
    EffectScope,
    LandhomeRequirement,
    MoveTargetsEffect,
    SetTappedEffect,
    TemporaryPumpEffect,
    UpkeepCostEffect,
    UpkeepDamageEffect,
    UpkeepDamageRecipient,
)
from ..mana import ManaCost
from ..types import CardType, Color, KeywordAbility, Zone
from .shared import lace


_CREATURE_IN_PLAY = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
)

THOUGHTLACE = lace("Thoughtlace", Color.BLUE)
_NONCREATURE_ARTIFACT_IN_PLAY = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.ARTIFACT}),
    excluded_card_types=frozenset({CardType.CREATURE}),
)
_ANY_CREATURE_OR_PLAYER = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
    players=True,
)
_LAND_IN_PLAY = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.LAND}),
)
_SPELL_BEING_CAST = TargetRequirement(zone=Zone.STACK)

ANIMATE_ARTIFACT = CardDefinition(
    name="Animate Artifact",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{3}{U}"),
    rules_text=(
        "Target noncreature artifact becomes an artifact creature with power "
        "and toughness each equal to its casting cost. It retains its abilities."
    ),
    colors=frozenset({Color.BLUE}),
    subtypes=("Enchant Artifact",),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD,
            granted_card_types=frozenset({CardType.CREATURE}),
            base_stats_from_mana_value=True,
        ),
    ),
    target_requirement=_NONCREATURE_ARTIFACT_IN_PLAY,
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
WALL_OF_WATER = CardDefinition(
    name="Wall of Water",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{U}{U}"),
    rules_text="{U}: Wall of Water gets +1/+0 until end of turn.",
    colors=frozenset({Color.BLUE}),
    subtypes=("Wall",),
    power=0,
    toughness=5,
    activated_abilities=(
        ActivatedPumpAbility(ManaCost.parse("{U}"), power=1),
    ),
)

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

PIRATE_SHIP = CardDefinition(
    name="Pirate Ship",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{4}{U}"),
    rules_text=(
        "Tap to do 1 damage to any target. Cannot attack unless opponent "
        "has Islands in play, though controller may still tap. Pirate Ship "
        "is destroyed immediately if at any time controller has no Islands "
        "in play."
    ),
    colors=frozenset({Color.BLUE}),
    subtypes=("Ship",),
    power=4,
    toughness=3,
    landhome=LandhomeRequirement("Island"),
    activated_abilities=(ActivatedDamageAbility(1, _ANY_CREATURE_OR_PLAYER),),
)

SEA_SERPENT = CardDefinition(
    name="Sea Serpent",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{5}{U}"),
    rules_text=(
        "Sea Serpent cannot attack unless opponent has Islands in play. "
        "Sea Serpent is destroyed immediately if at any time controller "
        "has no Islands in play."
    ),
    colors=frozenset({Color.BLUE}),
    subtypes=("Serpent",),
    power=5,
    toughness=5,
    landhome=LandhomeRequirement("Island"),
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

INVISIBILITY = CardDefinition(
    name="Invisibility",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{U}{U}"),
    rules_text="Walls are the only creatures that can block target creature.",
    colors=frozenset({Color.BLUE}),
    subtypes=("Enchant Creature",),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD,
            blocking_subtype="Wall",
        ),
    ),
    target_requirement=_CREATURE_IN_PLAY,
)

CONTROL_MAGIC = CardDefinition(
    name="Control Magic",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{2}{U}{U}"),
    rules_text=(
        "You control enchanted creature until Control Magic is removed."
    ),
    colors=frozenset({Color.BLUE}),
    subtypes=("Enchant Creature",),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD,
            controls_attached_card=True,
        ),
    ),
    target_requirement=_CREATURE_IN_PLAY,
)

PHANTASMAL_TERRAIN = CardDefinition(
    name="Phantasmal Terrain",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{U}{U}"),
    rules_text="Target land becomes the chosen basic land type.",
    colors=frozenset({Color.BLUE}),
    subtypes=("Enchant Land",),
    land_type_effects=(AttachedLandTypeEffect(chosen_basic_subtype=True),),
    target_requirement=_LAND_IN_PLAY,
)

STEAL_ARTIFACT = CardDefinition(
    name="Steal Artifact",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{2}{U}{U}"),
    rules_text=(
        "You control enchanted artifact until Steal Artifact is removed."
    ),
    colors=frozenset({Color.BLUE}),
    subtypes=("Enchant Artifact",),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD,
            controls_attached_card=True,
        ),
    ),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.ARTIFACT}),
    ),
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

COUNTERSPELL = CardDefinition(
    name="Counterspell",
    card_types=frozenset({CardType.INTERRUPT}),
    mana_cost=ManaCost.parse("{U}{U}"),
    rules_text="Counters target spell as it is being cast.",
    colors=frozenset({Color.BLUE}),
    target_requirement=_SPELL_BEING_CAST,
    spell_effects=(CounterTargetSpellEffect(),),
)

SPELL_BLAST = CardDefinition(
    name="Spell Blast",
    card_types=frozenset({CardType.INTERRUPT}),
    mana_cost=ManaCost.parse("{X}{U}"),
    rules_text="Target spell is countered; X is cost of target spell.",
    colors=frozenset({Color.BLUE}),
    target_requirement=_SPELL_BEING_CAST,
    spell_effects=(CounterTargetSpellEffect(x_equals_target_cost=True),),
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

TWIDDLE = CardDefinition(
    name="Twiddle",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{U}"),
    rules_text="Tap or untap target artifact, creature, or land.",
    colors=frozenset({Color.BLUE}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        any_card_types=frozenset(
            {CardType.ARTIFACT, CardType.CREATURE, CardType.LAND}
        ),
    ),
    spell_effects=(SetTappedEffect(),),
    casting_modes=("Tap", "Untap"),
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
            ANIMATE_ARTIFACT,
            ANCESTRAL_RECALL,
            BRAINGEYSER,
            CONTROL_MAGIC,
            COUNTERSPELL,
            FEEDBACK,
            FLIGHT,
            INVISIBILITY,
            JUMP,
            LORD_OF_ATLANTIS,
            MAHAMOTI_DJINN,
            MERFOLK_OF_THE_PEARL_TRIDENT,
            PHANTASMAL_FORCES,
            PHANTASMAL_TERRAIN,
            PHANTOM_MONSTER,
            PIRATE_SHIP,
            PRODIGAL_SORCERER,
            PSIONIC_BLAST,
            SEA_SERPENT,
            SPELL_BLAST,
            STEAL_ARTIFACT,
            THOUGHTLACE,
            TWIDDLE,
            UNSUMMON,
            WALL_OF_AIR,
            WALL_OF_WATER,
            WATER_ELEMENTAL,
        ),
        key=lambda card: card.name,
    )
)
