"""Canonical definitions of currently supported blue Beta cards."""

from ..abilities import (
    ActivatedDamageAbility,
    ActivatedPumpAbility,
    TargetRequirement,
)
from ..cards import CardDefinition
from ..effects import (
    ContinuousEffect,
    AttachedEventDamageEffect,
    AttachedLandTypeEffect,
    CounterTargetSpellEffect,
    DamageEffect,
    DrawCardsEffect,
    EffectRecipient,
    EffectScope,
    ExtraTurnEffect,
    GlobalDamageEffect,
    LandhomeRequirement,
    MoveTargetsEffect,
    PermanentTappedEffect,
    PartialUpkeepDamageEffect,
    DestroyTargetsEffect,
    SetTappedEffect,
    ShuffleHandAndGraveyardEffect,
    SirensCallEffect,
    TemporaryPumpEffect,
    TapLandsAndEmptyManaPoolEffect,
    UpkeepCostEffect,
    UpkeepDamageEffect,
    UpkeepDamageRecipient,
    UntapRestrictionEffect,
    UpkeepFailure,
)
from ..mana import ManaCost
from ..types import CardType, Color, KeywordAbility, Zone
from .shared import lace


_CREATURE_IN_PLAY = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
)

THOUGHTLACE = lace("Thoughtlace", Color.BLUE)

STASIS = CardDefinition(
    name="Stasis",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{1}{U}"),
    rules_text=(
        "Players skip their untap phases. During your upkeep, pay {U} or "
        "Stasis is destroyed."
    ),
    colors=frozenset({Color.BLUE}),
    untap_effects=(UntapRestrictionEffect(skip_untap=True),),
    upkeep_effects=(
        UpkeepCostEffect(ManaCost.parse("{U}"), UpkeepFailure.DESTROY_SOURCE),
    ),
)

LIFETAP = CardDefinition(
    name="Lifetap",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{U}{U}"),
    rules_text=(
        "You gain 1 life whenever a Forest controlled by an opponent "
        "becomes tapped."
    ),
    colors=frozenset({Color.BLUE}),
    permanent_tapped_effects=(
        PermanentTappedEffect(
            life_gain=1,
            land_subtype="Forest",
            opponent_controlled_only=True,
        ),
    ),
)

CREATURE_BOND = CardDefinition(
    name="Creature Bond",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{1}{U}"),
    rules_text=(
        "Enchant creature. If enchanted creature is destroyed, Creature Bond "
        "deals damage equal to its toughness to that creature's controller."
    ),
    colors=frozenset({Color.BLUE}),
    subtypes=("Enchant Creature",),
    target_requirement=_CREATURE_IN_PLAY,
    attached_event_damage_effects=(
        AttachedEventDamageEffect(
            amount_from_toughness=True, when_destroyed=True
        ),
    ),
)

PSYCHIC_VENOM = CardDefinition(
    name="Psychic Venom",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{1}{U}"),
    rules_text=(
        "Enchant land. Whenever enchanted land is tapped, Psychic Venom "
        "deals 2 damage to that land's controller."
    ),
    colors=frozenset({Color.BLUE}),
    subtypes=("Enchant Land",),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.LAND}),
    ),
    attached_event_damage_effects=(
        AttachedEventDamageEffect(amount=2, when_tapped=True),
    ),
)
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

COPY_ARTIFACT = CardDefinition(
    name="Copy Artifact",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{1}{U}"),
    rules_text=(
        "Choose an artifact in play as this spell is cast. In play, Copy "
        "Artifact is a blue artifact-enchantment copy of that artifact."
    ),
    colors=frozenset({Color.BLUE}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.ARTIFACT}),
    ),
    copies_artifact=True,
)

CLONE = CardDefinition(
    name="Clone",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{U}"),
    rules_text=(
        "As Clone is cast or otherwise brought into play, choose another "
        "creature in play. Clone copies that creature's normal characteristics."
    ),
    colors=frozenset({Color.BLUE}),
    subtypes=("Clone",),
    power=0,
    toughness=0,
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
        printed_card_types_only=True,
    ),
    copies_creature=True,
)

VESUVAN_DOPPELGANGER = CardDefinition(
    name="Vesuvan Doppelganger",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{U}{U}"),
    rules_text=(
        "As Vesuvan Doppelganger is cast or otherwise brought into play, "
        "choose another creature in play. It copies that creature's normal "
        "characteristics except color and remains blue. During your upkeep, "
        "you may change it into a different creature in play."
    ),
    colors=frozenset({Color.BLUE}),
    subtypes=("Doppelganger",),
    power=0,
    toughness=0,
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
        printed_card_types_only=True,
    ),
    copies_creature=True,
    is_vesuvan_doppelganger=True,
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

POWER_LEAK = CardDefinition(
    name="Power Leak",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{1}{U}"),
    rules_text=(
        "Enchanted enchantment costs 2 extra mana during upkeep. Its "
        "controller takes 1 damage for each unpaid mana."
    ),
    colors=frozenset({Color.BLUE}),
    subtypes=("Enchant Enchantment",),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.ENCHANTMENT}),
    ),
    upkeep_effects=(
        PartialUpkeepDamageEffect(
            maximum_payment=2,
            attached_permanent_controller=True,
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

BLUE_ELEMENTAL_BLAST = CardDefinition(
    name="Blue Elemental Blast",
    card_types=frozenset({CardType.INTERRUPT}),
    mana_cost=ManaCost.parse("{U}"),
    rules_text=(
        "Counters a red spell being cast or destroys a red card in play."
    ),
    colors=frozenset({Color.BLUE}),
    target_requirement=TargetRequirement(
        zone=Zone.STACK,
        additional_zones=frozenset({Zone.BATTLEFIELD}),
        color=Color.RED,
    ),
    spell_effects=(CounterTargetSpellEffect(), DestroyTargetsEffect()),
    casting_modes=("Counter spell", "Destroy permanent"),
    casting_mode_target_zones=(Zone.STACK, Zone.BATTLEFIELD),
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

POWER_SINK = CardDefinition(
    name="Power Sink",
    card_types=frozenset({CardType.INTERRUPT}),
    mana_cost=ManaCost.parse("{X}{U}"),
    rules_text=(
        "Target spell is countered unless its caster pays X additional mana. "
        "That player must use available mana in their pool and from lands."
    ),
    colors=frozenset({Color.BLUE}),
    target_requirement=_SPELL_BEING_CAST,
    spell_effects=(CounterTargetSpellEffect(power_sink=True),),
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

MANA_SHORT = CardDefinition(
    name="Mana Short",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{2}{U}"),
    rules_text=(
        "Tap all lands controlled by target opponent, then empty that "
        "player's mana pool without mana burn."
    ),
    colors=frozenset({Color.BLUE}),
    target_requirement=TargetRequirement(players=True, opponent_only=True),
    spell_effects=(TapLandsAndEmptyManaPoolEffect(),),
)

DRAIN_POWER = CardDefinition(
    name="Drain Power",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{U}{U}"),
    rules_text=(
        "Tap all lands controlled by target opponent. Add all mana those "
        "lands produce and all mana in that player's pool to your pool."
    ),
    colors=frozenset({Color.BLUE}),
    target_requirement=TargetRequirement(players=True, opponent_only=True),
    spell_effects=(
        TapLandsAndEmptyManaPoolEffect(
            transfer_to_caster=True,
            produce_land_mana=True,
        ),
    ),
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

TIME_WALK = CardDefinition(
    name="Time Walk",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{1}{U}"),
    rules_text="Take an extra turn after this one.",
    colors=frozenset({Color.BLUE}),
    spell_effects=(ExtraTurnEffect(),),
)

TIMETWISTER = CardDefinition(
    name="Timetwister",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{2}{U}"),
    rules_text=(
        "Set Timetwister aside. Each player shuffles their hand, library, "
        "and graveyard together, then draws seven cards."
    ),
    colors=frozenset({Color.BLUE}),
    spell_effects=(ShuffleHandAndGraveyardEffect(7),),
)

VOLCANIC_ERUPTION = CardDefinition(
    name="Volcanic Eruption",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{X}{U}{U}{U}"),
    rules_text=(
        "Destroy X target Mountains. Volcanic Eruption deals X damage to "
        "each creature and each player."
    ),
    colors=frozenset({Color.BLUE}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.LAND}),
        required_land_subtypes=frozenset({"Mountain"}),
        count_equals_x=True,
    ),
    spell_effects=(
        DestroyTargetsEffect(),
        GlobalDamageEffect(amount_per_x=1),
    ),
)

SIRENS_CALL = CardDefinition(
    name="Siren's Call",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{U}"),
    rules_text=(
        "Cast only during an opponent's turn before the attack. Their "
        "creatures must attack if able; destroy affected non-Walls that "
        "do not attack at end of turn. Creatures summoned this turn are unaffected."
    ),
    colors=frozenset({Color.BLUE}),
    spell_effects=(SirensCallEffect(),),
)

BLUE_CARDS = tuple(
    sorted(
        (
            AIR_ELEMENTAL,
            ANIMATE_ARTIFACT,
            ANCESTRAL_RECALL,
            BRAINGEYSER,
            BLUE_ELEMENTAL_BLAST,
            CLONE,
            CONTROL_MAGIC,
            COPY_ARTIFACT,
            COUNTERSPELL,
            CREATURE_BOND,
            DRAIN_POWER,
            FEEDBACK,
            FLIGHT,
            INVISIBILITY,
            JUMP,
            LIFETAP,
            LORD_OF_ATLANTIS,
            MAHAMOTI_DJINN,
            MANA_SHORT,
            MERFOLK_OF_THE_PEARL_TRIDENT,
            PHANTASMAL_FORCES,
            PHANTASMAL_TERRAIN,
            PHANTOM_MONSTER,
            PIRATE_SHIP,
            POWER_LEAK,
            PRODIGAL_SORCERER,
            POWER_SINK,
            PSIONIC_BLAST,
            PSYCHIC_VENOM,
            SEA_SERPENT,
            SIRENS_CALL,
            SPELL_BLAST,
            STASIS,
            STEAL_ARTIFACT,
            THOUGHTLACE,
            TIME_WALK,
            TIMETWISTER,
            TWIDDLE,
            UNSUMMON,
            VESUVAN_DOPPELGANGER,
            VOLCANIC_ERUPTION,
            WALL_OF_AIR,
            WALL_OF_WATER,
            WATER_ELEMENTAL,
        ),
        key=lambda card: card.name,
    )
)
