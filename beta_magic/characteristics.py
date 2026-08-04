"""Current card characteristics and continuous-effect calculation."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .abilities import (
    ActivatedAbility,
    ActivatedManaAbility,
    ActivatedRegenerationAbility,
)
from .cards import Card
from .effects import (
    AttachedLandTypeEffect,
    ContinuousEffect,
    EffectScope,
    GlobalLandTypeConversion,
    VariableStatKind,
)
from .types import CardType, Color, KeywordAbility


_BASIC_LAND_MANA = {
    "Plains": Color.WHITE,
    "Island": Color.BLUE,
    "Swamp": Color.BLACK,
    "Mountain": Color.RED,
    "Forest": Color.GREEN,
}


class CharacteristicsMixin:
    """Calculate current characteristics without mutating game state."""

    __slots__ = ()

    def card_colors(self, card: Card) -> frozenset[Color]:
        """Return a card's current color after persistent Lace effects."""

        return (
            frozenset({card.color_override})
            if card.color_override is not None
            else card.definition.colors
        )

    def card_types(self, card: Card) -> frozenset[CardType]:
        """Return current card types after continuous animation effects."""

        granted = {
            card_type
            for effect in self._continuous_effects_for(card)
            for card_type in effect.granted_card_types
        }
        return card.definition.card_types | granted

    def wall_can_attack(self, card: Card) -> bool:
        return any(
            effect.wall_can_attack for effect in self._continuous_effects_for(card)
        )

    def blocking_subtype_requirement(self, card: Card) -> str | None:
        """Return a subtype every creature blocking ``card`` must have."""

        return next(
            (
                effect.blocking_subtype
                for effect in self._continuous_effects_for(card)
                if effect.blocking_subtype is not None
            ),
            None,
        )

    def blocking_exceptions(
        self, card: Card
    ) -> tuple[frozenset[Color], frozenset[CardType]] | None:
        """Colors or types permitted to block by a restrictive effect."""

        effect = next(
            (
                effect
                for effect in self._continuous_effects_for(card)
                if effect.blocking_allowed_colors
                or effect.blocking_allowed_card_types
            ),
            None,
        )
        if effect is None:
            return None
        return effect.blocking_allowed_colors, effect.blocking_allowed_card_types

    def creature_is_unblockable(self, card: Card) -> bool:
        return any(
            effect.unblockable for effect in self._continuous_effects_for(card)
        )

    def creature_power(self, creature: Card) -> int:
        """Return current power after applying continuous bonuses."""

        base = self._variable_creature_base_stat(creature)
        if base is None:
            explicit = next(
                (
                    effect
                    for effect in self._continuous_effects_for(creature)
                    if effect.base_power is not None
                ),
                None,
            )
            animated = next(
                (
                    effect
                    for effect in self._continuous_effects_for(creature)
                    if effect.base_stats_from_mana_value
                ),
                None,
            )
            base = (
                explicit.base_power
                if explicit is not None
                else creature.definition.mana_cost.mana_value
                if animated is not None
                else creature.definition.power or 0
            )
        return base + creature.plus_one_counters + self._creature_bonus(creature)[0]

    def creature_toughness(self, creature: Card) -> int:
        """Return current toughness after applying continuous bonuses."""

        base = self._variable_creature_base_stat(creature)
        if base is None:
            explicit = next(
                (
                    effect
                    for effect in self._continuous_effects_for(creature)
                    if effect.base_toughness is not None
                ),
                None,
            )
            animated = next(
                (
                    effect
                    for effect in self._continuous_effects_for(creature)
                    if effect.base_stats_from_mana_value
                ),
                None,
            )
            base = (
                explicit.base_toughness
                if explicit is not None
                else creature.definition.mana_cost.mana_value
                if animated is not None
                else creature.definition.toughness or 0
            )
        return base + creature.plus_one_counters + self._creature_bonus(creature)[1]

    def has_summoning_sickness(self, creature: Card) -> bool:
        """Whether a creature began the turn under its current controller."""

        if CardType.CREATURE not in self.card_types(creature):
            return False
        if creature.controller_at_turn_start_id is not None:
            return (
                creature.controller_at_turn_start_id
                != creature.controller_id
            )
        return creature.entered_battlefield_turn == self.turn_number

    def player_controls_land_subtype(
        self, player_id: str, subtype: str
    ) -> bool:
        """Whether a player's battlefield contains a land of a subtype."""

        return any(
            CardType.LAND in permanent.definition.card_types
            and subtype in self.land_subtypes(permanent)
            for permanent in self.player(player_id).battlefield
        )

    def land_subtypes(self, land: Card) -> tuple[str, ...]:
        """Return a land's current types after attached and global changes."""

        if CardType.LAND not in land.definition.card_types:
            return land.definition.subtypes
        subtypes = tuple(land.definition.subtypes)
        local_replacements = [
                (
                    source.battlefield_entry_sequence or 0,
                    (
                        source.chosen_land_subtype
                        if effect.chosen_basic_subtype
                        else effect.replacement_subtype
                    ),
                )
                for player in self.players
                for source in player.battlefield
                if source.enchanted_card_id == land.id
                for effect in source.definition.land_type_effects
                if isinstance(effect, AttachedLandTypeEffect)
        ]
        local_replacements.extend(
            (sequence, subtype)
            for subtype, sequence in land.land_type_marks.values()
        )
        for _, replacement in sorted(local_replacements):
            if replacement is not None:
                subtypes = (replacement,)

        conversions = [
            effect
            for player in self.players
            for source in player.battlefield
            for effect in source.definition.land_type_effects
            if isinstance(effect, GlobalLandTypeConversion)
        ]
        for _ in range(len(conversions) + 1):
            changed = False
            for effect in conversions:
                if effect.source_subtype in subtypes:
                    replacement = (effect.replacement_subtype,)
                    if subtypes != replacement:
                        subtypes = replacement
                        changed = True
            if not changed:
                break
        return subtypes

    def _variable_creature_base_stat(self, creature: Card) -> int | None:
        """Return the shared */* value, or ``None`` for a numeric creature."""

        variable = creature.definition.variable_stats
        if variable is None:
            return None
        controller = self.player(creature.controller_id or creature.owner_id)
        if variable.kind is VariableStatKind.CONTROLLED_NON_WALL_CREATURES:
            return sum(
                CardType.CREATURE in self.card_types(permanent)
                and "Wall" not in permanent.definition.subtypes
                for permanent in controller.battlefield
            )
        if variable.kind is VariableStatKind.CONTROLLED_LAND_SUBTYPE:
            return sum(
                CardType.LAND in permanent.definition.card_types
                and variable.subtype in self.land_subtypes(permanent)
                for permanent in controller.battlefield
            )
        if variable.kind is VariableStatKind.ATTACKING_DEFENDER_LAND_SUBTYPE:
            counted_player = controller
            if self.combat is not None and creature in self.combat.attackers:
                counted_player = self.player(self.combat.defending_player_id)
            return sum(
                CardType.LAND in permanent.definition.card_types
                and variable.subtype in self.land_subtypes(permanent)
                for permanent in counted_player.battlefield
            )
        return sum(
            CardType.CREATURE in self.card_types(permanent)
            and variable.subtype in permanent.definition.subtypes
            for player in self.players
            for permanent in player.battlefield
        )

    def creature_abilities(self, creature: Card) -> frozenset[KeywordAbility]:
        """Return printed and continuously granted keyword abilities."""

        granted = {
            ability
            for effect in self._continuous_effects_for(creature)
            for ability in effect.granted_abilities
        }
        return creature.definition.abilities | granted

    def activated_abilities(self, card: Card) -> tuple[ActivatedAbility, ...]:
        """Return printed and continuously granted activated abilities."""

        printed = card.definition.activated_abilities
        if (
            CardType.LAND in card.definition.card_types
            and self.land_subtypes(card) != card.definition.subtypes
        ):
            mana = tuple(
                ActivatedManaAbility(_BASIC_LAND_MANA[subtype])
                for subtype in _BASIC_LAND_MANA
                if subtype in self.land_subtypes(card)
            )
            printed = mana
        granted = tuple(
            ActivatedRegenerationAbility(effect.granted_regeneration_cost)
            for effect in self._continuous_effects_for(card)
            if effect.granted_regeneration_cost is not None
        )
        return printed + granted

    def untaps_during_untap(self, card: Card) -> bool:
        """Whether normal untap processing may untap this permanent."""

        return card.definition.untaps_normally and not any(
            effect.prevents_untap for effect in self._continuous_effects_for(card)
        )

    def _continuous_effects_for(
        self, creature: Card
    ) -> Iterable[ContinuousEffect]:
        yield from self.combat_creature_effects.get(creature.id, ())
        yield from self.temporary_creature_effects.get(creature.id, ())
        attacking = self.combat is not None and creature in self.combat.attackers
        for player in self.players:
            for source in player.battlefield:
                if not self.continuous_permanent_is_active(source):
                    continue
                for effect in source.definition.continuous_effects:
                    if (
                        effect.scope is EffectScope.ATTACHED_CARD
                        and source.enchanted_card_id != creature.id
                    ):
                        continue
                    if (
                        effect.color is not None
                        and effect.color not in self.card_colors(creature)
                    ):
                        continue
                    if (
                        effect.subtype is not None
                        and effect.subtype not in creature.definition.subtypes
                    ):
                        continue
                    if (
                        effect.land_subtype is not None
                        and (
                            CardType.LAND not in creature.definition.card_types
                            or effect.land_subtype
                            not in self.land_subtypes(creature)
                        )
                    ):
                        continue
                    if effect.exclude_source and source is creature:
                        continue
                    if effect.source_only and source is not creature:
                        continue
                    if (
                        effect.controller_only
                        and creature.controller_id != source.controller_id
                    ):
                        continue
                    if effect.attacking_only and not attacking:
                        continue
                    if effect.untapped_only and creature.tapped:
                        continue
                    if effect.nonattacking_only and attacking:
                        continue
                    if effect.controller_has_land_subtype is not None:
                        controller = self.player(
                            source.controller_id or source.owner_id
                        )
                        if not any(
                            CardType.LAND in permanent.definition.card_types
                            and effect.controller_has_land_subtype
                            in self.land_subtypes(permanent)
                            for permanent in controller.battlefield
                        ):
                            continue
                    if effect.counted_controller_land_subtype is not None:
                        controller = self.player(
                            source.controller_id or source.owner_id
                        )
                        count = sum(
                            CardType.LAND in permanent.definition.card_types
                            and effect.counted_controller_land_subtype
                            in self.land_subtypes(permanent)
                            for permanent in controller.battlefield
                        )
                        divisor = effect.count_divisor
                        power = count * effect.power_per_count // divisor
                        toughness_numerator = count * effect.toughness_per_count
                        toughness = (
                            (toughness_numerator + divisor - 1) // divisor
                            if effect.round_toughness_up
                            else toughness_numerator // divisor
                        )
                        effect = replace(
                            effect,
                            power=effect.power + power,
                            toughness=effect.toughness + toughness,
                        )
                    yield effect

    @staticmethod
    def continuous_permanent_is_active(source: Card) -> bool:
        """Whether a permanent may currently supply continuous effects."""

        return not (
            source.tapped
            and CardType.ARTIFACT in source.definition.card_types
        )

    def _creature_bonus(self, creature: Card) -> tuple[int, int]:
        effects = tuple(self._continuous_effects_for(creature))
        return (
            sum(effect.power for effect in effects),
            sum(effect.toughness for effect in effects),
        )
