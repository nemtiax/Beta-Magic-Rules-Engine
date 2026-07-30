"""Compatibility intake for definitions still exported by older modules.

New card definitions belong in the printed-characteristic modules. This
module is temporary migration plumbing and is deliberately private.
"""

from __future__ import annotations

from types import MappingProxyType

from ..basic_lands import BASIC_LANDS
from ..blue_utility_spells import BLUE_UTILITY_SPELLS
from ..cards import CardDefinition
from ..circles_of_protection import CIRCLES_OF_PROTECTION
from ..combat_tricks import TARGETED_PUMP_SPELLS
from ..creature_lords import CREATURE_LORDS
from ..damage_ability_creatures import DAMAGE_ABILITY_CREATURES
from ..damage_spells import TARGETED_DAMAGE_SPELLS
from ..destruction_spells import PERMANENT_DESTRUCTION_SPELLS
from ..dual_lands import DUAL_LANDS
from ..enchant_creatures import ENCHANT_CREATURES
from ..first_strike_creatures import FIRST_STRIKE_CREATURES
from ..flying_creatures import FLYING_CREATURES, SPECIAL_FLYING_CREATURES
from ..global_enchantments import GLOBAL_ENCHANTMENTS
from ..graveyard_spells import GRAVEYARD_RECURSION_SPELLS
from ..landwalk_creatures import LANDWALK_CREATURES
from ..life_spells import LIFE_GAIN_SPELLS
from ..mana_artifacts import MANA_ARTIFACTS
from ..mana_creatures import MANA_CREATURES
from ..prevention_cards import PREVENTION_CARDS
from ..protection_creatures import PROTECTION_CREATURES
from ..pump_creatures import PUMP_CREATURES
from ..reach_creatures import REACH_CREATURES
from ..regeneration_creatures import REGENERATION_CREATURES
from ..regeneration_spells import REGENERATION_SPELLS
from ..timed_artifacts import TIMED_ARTIFACTS
from ..timed_enchantments import TIMED_ENCHANTMENTS
from ..trample_creatures import TRAMPLE_CREATURES
from ..upkeep_creatures import UPKEEP_CREATURES
from ..utility_ability_creatures import UTILITY_ABILITY_CREATURES
from ..utility_artifacts import UTILITY_ARTIFACTS
from ..vanilla_creatures import VANILLA_CREATURES
from ..vanilla_walls import VANILLA_WALLS
from ..variable_creatures import VARIABLE_CREATURES
from ..variable_spells import VARIABLE_SPELLS


_CARD_GROUPS: tuple[tuple[CardDefinition, ...], ...] = (
    BASIC_LANDS,
    DUAL_LANDS,
    MANA_ARTIFACTS,
    UTILITY_ARTIFACTS,
    VANILLA_CREATURES,
    MANA_CREATURES,
    LANDWALK_CREATURES,
    CREATURE_LORDS,
    PUMP_CREATURES,
    VANILLA_WALLS,
    FLYING_CREATURES,
    SPECIAL_FLYING_CREATURES,
    REACH_CREATURES,
    FIRST_STRIKE_CREATURES,
    PROTECTION_CREATURES,
    PREVENTION_CARDS,
    TRAMPLE_CREATURES,
    GLOBAL_ENCHANTMENTS,
    CIRCLES_OF_PROTECTION,
    ENCHANT_CREATURES,
    TARGETED_DAMAGE_SPELLS,
    TARGETED_PUMP_SPELLS,
    PERMANENT_DESTRUCTION_SPELLS,
    GRAVEYARD_RECURSION_SPELLS,
    TIMED_ARTIFACTS,
    TIMED_ENCHANTMENTS,
    UPKEEP_CREATURES,
    VARIABLE_CREATURES,
    DAMAGE_ABILITY_CREATURES,
    UTILITY_ABILITY_CREATURES,
    REGENERATION_CREATURES,
    REGENERATION_SPELLS,
    LIFE_GAIN_SPELLS,
    VARIABLE_SPELLS,
    BLUE_UTILITY_SPELLS,
)


def _build_catalog() -> tuple[CardDefinition, ...]:
    cards = tuple(card for group in _CARD_GROUPS for card in group)
    names = [card.name for card in cards]
    if len(names) != len(set(names)):
        duplicates = sorted(
            name for name in set(names) if names.count(name) > 1
        )
        raise RuntimeError(
            "duplicate supported card definitions: " + ", ".join(duplicates)
        )
    return tuple(sorted(cards, key=lambda card: card.name))


LEGACY_CARDS = _build_catalog()
