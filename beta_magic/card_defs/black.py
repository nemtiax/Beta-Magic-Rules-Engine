"""Canonical definitions of currently supported black Beta cards."""

from ..abilities import (
    ActivatedCounterSpellAbility,
    ActivatedDestroyAbility,
    ActivatedGlobalDamageAbility,
    ActivatedAttackRequirementAbility,
    ActivatedPumpAbility,
    ActivatedRegenerationAbility,
    TargetRequirement,
)
from ..cards import CardDefinition
from ..effects import (
    AddManaEffect,
    ContinuousEffect,
    AttachedLandTypeEffect,
    DestroyTargetsEffect,
    EffectScope,
    MoveTargetsEffect,
    RetroactiveDamageTransferEffect,
    OptionalUpkeepPaymentEffect,
    TemporaryPumpEffect,
    UpkeepDamageEffect,
    UpkeepDamageRecipient,
    UpkeepCostEffect,
    UpkeepFailure,
    UpkeepBenefit,
    UpkeepCreatureSacrificeEffect,
    VariableCreatureStats,
    VariableStatKind,
    DiscardCardsEffect,
)
from ..mana import ManaCost
from ..types import CardType, Color, KeywordAbility, Zone
from .shared import lace


_CREATURE_IN_PLAY = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.CREATURE}),
)

DEATHLACE = lace("Deathlace", Color.BLACK)

DEATHGRIP = CardDefinition(
    name="Deathgrip",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{B}{B}"),
    rules_text=(
        "Pay {B}{B}: Counter a green spell as it is being cast. This action "
        "may be played as an interrupt and does not affect cards already in play."
    ),
    colors=frozenset({Color.BLACK}),
    activated_abilities=(
        ActivatedCounterSpellAbility(ManaCost.parse("{B}{B}"), Color.GREEN),
    ),
)

DEMONIC_HORDES = CardDefinition(
    name="Demonic Hordes",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{B}{B}{B}"),
    rules_text=(
        "{T}: Destroy target land. Pay {B}{B}{B} during upkeep or tap "
        "Demonic Hordes and lose a land chosen by an opponent. Its tap "
        "ability cannot be used until its upkeep is paid."
    ),
    colors=frozenset({Color.BLACK}),
    subtypes=("Demon",),
    power=5,
    toughness=5,
    activated_abilities=(
        ActivatedDestroyAbility(
            TargetRequirement(
                zone=Zone.BATTLEFIELD,
                card_types=frozenset({CardType.LAND}),
            )
        ),
    ),
    upkeep_effects=(
        UpkeepCostEffect(
            ManaCost.parse("{B}{B}{B}"),
            failure=UpkeepFailure.TAP_SOURCE_AND_OPPONENT_CHOOSES_LAND,
        ),
    ),
    tap_abilities_require_paid_upkeep=True,
)

LORD_OF_THE_PIT = CardDefinition(
    name="Lord of the Pit",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{4}{B}{B}{B}"),
    rules_text=(
        "Flying, trample. During upkeep, sacrifice another eligible creature "
        "if possible; otherwise Lord of the Pit deals 7 damage to you."
    ),
    colors=frozenset({Color.BLACK}),
    subtypes=("Demon",),
    abilities=frozenset({KeywordAbility.FLYING, KeywordAbility.TRAMPLE}),
    power=7,
    toughness=7,
    upkeep_effects=(UpkeepCreatureSacrificeEffect(7),),
)

PARALYZE = CardDefinition(
    name="Paralyze",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{B}"),
    rules_text=(
        "Enchant creature. Tap enchanted creature. It does not untap normally; "
        "its controller may pay {4} during upkeep to untap it."
    ),
    colors=frozenset({Color.BLACK}),
    subtypes=("Enchant Creature",),
    target_requirement=_CREATURE_IN_PLAY,
    continuous_effects=(
        ContinuousEffect(scope=EffectScope.ATTACHED_CARD, prevents_untap=True),
    ),
    upkeep_effects=(
        OptionalUpkeepPaymentEffect(
            ManaCost.parse("{4}"),
            UpkeepBenefit.UNTAP_ATTACHED,
            attached_permanent_controller=True,
            require_all_matching_attachments=True,
        ),
    ),
    taps_attached_on_entry=True,
)

PESTILENCE = CardDefinition(
    name="Pestilence",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{2}{B}{B}"),
    rules_text=(
        "{B}: Pestilence deals 1 damage to each creature and player. "
        "You may pay multiple {B} as one damage effect. Destroy Pestilence "
        "at end of turn if no creatures are in play."
    ),
    colors=frozenset({Color.BLACK}),
    activated_abilities=(
        ActivatedGlobalDamageAbility(ManaCost.parse("{B}")),
    ),
    destroy_at_end_of_turn_if_no_creatures=True,
)
_LAND_IN_PLAY = TargetRequirement(
    zone=Zone.BATTLEFIELD,
    card_types=frozenset({CardType.LAND}),
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

NETTLING_IMP = CardDefinition(
    name="Nettling Imp",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{B}"),
    rules_text=(
        "Tap during an opponent's turn before the attack: target opposing "
        "non-Wall creature must attack this turn or be destroyed at end of turn."
    ),
    colors=frozenset({Color.BLACK}),
    subtypes=("Imp",),
    power=1,
    toughness=1,
    activated_abilities=(
        ActivatedAttackRequirementAbility(
            TargetRequirement(
                zone=Zone.BATTLEFIELD,
                card_types=frozenset({CardType.CREATURE}),
                excluded_subtypes=frozenset({"Wall"}),
                active_player_only=True,
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

EVIL_PRESENCE = CardDefinition(
    name="Evil Presence",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{B}"),
    rules_text="Target land becomes a Swamp.",
    colors=frozenset({Color.BLACK}),
    subtypes=("Enchant Land",),
    land_type_effects=(AttachedLandTypeEffect(replacement_subtype="Swamp"),),
    target_requirement=_LAND_IN_PLAY,
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

DARK_RITUAL = CardDefinition(
    name="Dark Ritual",
    card_types=frozenset({CardType.INTERRUPT}),
    mana_cost=ManaCost.parse("{B}"),
    rules_text="Add 3 black mana to your mana pool.",
    colors=frozenset({Color.BLACK}),
    spell_effects=(AddManaEffect(Color.BLACK, 3),),
)

HYPNOTIC_SPECTER = CardDefinition(
    name="Hypnotic Specter",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{B}{B}"),
    rules_text=(
        "Flying. An opponent damaged by Hypnotic Specter must discard "
        "a card at random from hand."
    ),
    colors=frozenset({Color.BLACK}),
    subtypes=("Specter",),
    power=2,
    toughness=2,
    abilities=frozenset({KeywordAbility.FLYING}),
    combat_player_damage_random_discard=1,
)

SENGIR_VAMPIRE = CardDefinition(
    name="Sengir Vampire",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{3}{B}{B}"),
    rules_text=(
        "Flying. Whenever a creature damaged by Sengir Vampire this turn "
        "dies without regenerating, put a +1/+1 counter on Sengir Vampire."
    ),
    colors=frozenset({Color.BLACK}),
    subtypes=("Vampire",),
    power=4,
    toughness=4,
    abilities=frozenset({KeywordAbility.FLYING}),
    grows_when_damaged_creature_dies=True,
)

SIMULACRUM = CardDefinition(
    name="Simulacrum",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{1}{B}"),
    rules_text=(
        "Move all damage dealt to you so far this turn onto target creature "
        "you control. That creature may regenerate."
    ),
    colors=frozenset({Color.BLACK}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
        controller_only=True,
    ),
    spell_effects=(RetroactiveDamageTransferEffect(),),
)

MIND_TWIST = CardDefinition(
    name="Mind Twist",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{X}{B}"),
    rules_text="Opponent discards X cards at random from hand.",
    colors=frozenset({Color.BLACK}),
    target_requirement=TargetRequirement(players=True, opponent_only=True),
    spell_effects=(DiscardCardsEffect(amount_per_x=1, random=True),),
)

FEAR = CardDefinition(
    name="Fear",
    card_types=frozenset({CardType.ENCHANTMENT}),
    mana_cost=ManaCost.parse("{B}{B}"),
    rules_text=(
        "Target creature cannot be blocked except by artifact creatures "
        "and black creatures."
    ),
    colors=frozenset({Color.BLACK}),
    subtypes=("Enchant Creature",),
    continuous_effects=(
        ContinuousEffect(
            scope=EffectScope.ATTACHED_CARD,
            blocking_allowed_colors=frozenset({Color.BLACK}),
            blocking_allowed_card_types=frozenset({CardType.ARTIFACT}),
        ),
    ),
    target_requirement=_CREATURE_IN_PLAY,
)

TERROR = CardDefinition(
    name="Terror",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{1}{B}"),
    rules_text=(
        "Destroy target nonartifact, nonblack creature. "
        "That creature cannot be regenerated."
    ),
    colors=frozenset({Color.BLACK}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        card_types=frozenset({CardType.CREATURE}),
        excluded_card_types=frozenset({CardType.ARTIFACT}),
        excluded_colors=frozenset({Color.BLACK}),
    ),
    spell_effects=(DestroyTargetsEffect(regeneration_allowed=False),),
)


BLACK_CARDS = tuple(
    sorted(
        (
            BAD_MOON,
            BLACK_KNIGHT,
            BOG_WRAITH,
            CURSED_LAND,
            DARK_RITUAL,
            DEATHLACE,
            DEATHGRIP,
            DEMONIC_HORDES,
            DRUDGE_SKELETONS,
            EVIL_PRESENCE,
            FEAR,
            FROZEN_SHADE,
            HOWL_FROM_BEYOND,
            HYPNOTIC_SPECTER,
            LORD_OF_THE_PIT,
            MIND_TWIST,
            NETTLING_IMP,
            NIGHTMARE,
            PARALYZE,
            PESTILENCE,
            PLAGUE_RATS,
            RAISE_DEAD,
            ROYAL_ASSASSIN,
            SCATHE_ZOMBIES,
            SENGIR_VAMPIRE,
            SIMULACRUM,
            SINKHOLE,
            TERROR,
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
