"""Artifact and enchantment destruction from Limited Edition Beta."""

from .cards import (
    CardDefinition,
    DestroyAllEffect,
    DestroyTargetsEffect,
    TargetRequirement,
)
from .mana import ManaCost
from .types import CardType, Color, Zone


DISENCHANT = CardDefinition(
    name="Disenchant",
    card_types=frozenset({CardType.INSTANT}),
    mana_cost=ManaCost.parse("{1}{W}"),
    rules_text="Target enchantment or artifact must be discarded.",
    colors=frozenset({Color.WHITE}),
    target_requirement=TargetRequirement(
        zone=Zone.BATTLEFIELD,
        any_card_types=frozenset({CardType.ENCHANTMENT, CardType.ARTIFACT}),
    ),
    spell_effects=(DestroyTargetsEffect(),),
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

TRANQUILITY = CardDefinition(
    name="Tranquility",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{2}{G}"),
    rules_text="All enchantments in play must be discarded.",
    colors=frozenset({Color.GREEN}),
    spell_effects=(DestroyAllEffect(frozenset({CardType.ENCHANTMENT})),),
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

ARMAGEDDON = CardDefinition(
    name="Armageddon",
    card_types=frozenset({CardType.SORCERY}),
    mana_cost=ManaCost.parse("{3}{W}"),
    rules_text="Destroy all lands in play.",
    colors=frozenset({Color.WHITE}),
    spell_effects=(DestroyAllEffect(frozenset({CardType.LAND})),),
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

LAND_DESTRUCTION_SPELLS = (
    STONE_RAIN,
    SINKHOLE,
    ICE_STORM,
    ARMAGEDDON,
    FLASHFIRES,
    TSUNAMI,
)
PERMANENT_DESTRUCTION_SPELLS = (
    DISENCHANT,
    SHATTER,
    TUNNEL,
    TRANQUILITY,
) + LAND_DESTRUCTION_SPELLS
