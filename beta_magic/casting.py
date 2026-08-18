"""Target selection and spell-casting behavior for :class:`GameState`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from .abilities import (
    ActivatedDamageAbility,
    ActivatedDestroyAbility,
    ActivatedRegenerationAbility,
    ActivatedTapAbility,
    ActivatedTemporaryAbility,
    ActivatedDiscardAbility,
    ActivatedAttackRequirementAbility,
    ActivatedLandTypeAbility,
    ActivatedUnblockableAbility,
    ActivatedInterruptUntapAbility,
    ActivatedCounterSpellAbility,
    BatchActivatedAbility,
    TargetRequirement,
)
from .cards import Card
from .events import SpellCastEvent
from .effects import (
    AddManaEffect,
    AttachedLandTypeEffect,
    CounterTargetSpellEffect,
    CopyTargetSpellEffect,
    SirensCallEffect,
    BlazeOfGloryEffect,
    ReverseDamageEffect,
    RetroactiveDamageTransferEffect,
    TemporaryPumpEffect,
    PreventCombatDamageEffect,
    SwapLibraryTopWithAnteEffect,
    SacrificeCreatureForManaEffect,
    DrainLifeEffect,
    DividedDamageEffect,
)
from .types import (
    BASIC_LAND_SUBTYPES,
    CardType,
    Color,
    CombatStep,
    GameStatus,
    TurnPhase,
    Zone,
)
from .damage import DamageResolutionStep

if TYPE_CHECKING:
    from .game import PlayerState


@dataclass(slots=True)
class PendingCast:
    """A spell whose caster still needs to supply its required targets."""

    spell: Card
    caster_id: str
    x_value: int = 0
    chosen_land_subtype: str | None = None
    chosen_mode: str | None = None
    damage_source_key: str | None = None
    copied_spell_targets: tuple[Card | PlayerState, ...] | None = None
    copied_spell_x_value: int | None = None


@dataclass(slots=True)
class PendingActivation:
    """An activated ability whose controller still needs to choose targets."""

    source: Card
    controller_id: str
    ability_index: int


@dataclass(slots=True)
class AbilityOnStack:
    """An activated fast effect retained until its batch resolves."""

    source: Card
    source_name: str
    controller_id: str
    ability: BatchActivatedAbility
    targets: tuple[Card | PlayerState, ...]
    amount: int = 1
    event_id: UUID | None = None


@dataclass(slots=True)
class SpellOnStack:
    """Casting choices retained until a spell resolves."""

    card: Card
    caster_id: str
    targets: tuple[Card | PlayerState, ...] = ()
    x_value: int = 0
    chosen_mode: str | None = None
    damage_source_key: str | None = None
    copied_spell_targets: tuple[Card | PlayerState, ...] | None = None
    copied_spell_x_value: int | None = None


class TargetingCastingMixin:
    """Casting façade methods operating on state owned by ``GameState``."""

    __slots__ = ()

    def cast_creature(self, card: Card) -> None:
        """Pay for and resolve a creature spell from the active player's hand."""

        self._require_no_pending_action()
        self._validate_permanent_cast(card, CardType.CREATURE)
        self._resolve_permanent_spell(card, ())

    def _validate_permanent_cast(
        self,
        card: Card,
        expected_type: CardType | None = None,
        x_value: int = 0,
    ) -> None:
        if self.status is not GameStatus.IN_PROGRESS:
            raise RuntimeError("spells can only be cast during a game")
        if self.current_phase is not TurnPhase.MAIN:
            raise RuntimeError("permanent spells can only be cast during the Main phase")
        if self.combat is not None:
            raise RuntimeError("permanent spells cannot be cast during an attack")
        if self.stack or self.batch_abilities:
            raise RuntimeError("permanent spells require an empty response batch")
        player = self.active_player
        if card not in player.hand:
            raise ValueError("the spell must be in the active player's hand")
        if expected_type is not None and expected_type not in card.definition.card_types:
            raise ValueError(f"{card.name} is not a {expected_type.value.lower()}")
        if not card.definition.is_permanent or CardType.LAND in card.definition.card_types:
            raise ValueError(f"{card.name} is not a permanent spell")
        if not self.can_pay_mana(player, self.spell_mana_cost(card, x_value)):
            raise RuntimeError(f"not enough mana to cast {card.name}")

    def _validate_enchantment_cast(self, card: Card) -> None:
        self._validate_permanent_cast(card, CardType.ENCHANTMENT)

    def _caster_for(self, card: Card) -> PlayerState:
        for player in self.players:
            if card in player.hand:
                return player
        raise ValueError("the spell must be in a player's hand")

    def _validate_nonpermanent_cast(
        self, card: Card, x_value: int = 0
    ) -> PlayerState:
        if self.status is not GameStatus.IN_PROGRESS:
            raise RuntimeError("spells can only be cast during a game")
        caster = self._caster_for(card)
        is_instant = CardType.INSTANT in card.definition.card_types
        is_interrupt = CardType.INTERRUPT in card.definition.card_types
        is_sorcery = CardType.SORCERY in card.definition.card_types
        if not (is_instant or is_interrupt or is_sorcery):
            raise ValueError(
                f"{card.name} is not an instant, interrupt, or sorcery"
            )
        if not is_interrupt and any(
            CardType.INTERRUPT in spell.definition.card_types
            for spell in self.stack
        ):
            raise RuntimeError(
                "an interrupt sequence must finish before another spell"
            )
        if is_interrupt:
            target_requirement = card.definition.target_requirement
            can_target_in_play = (
                target_requirement is not None
                and (
                    target_requirement.zone is Zone.BATTLEFIELD
                    or Zone.BATTLEFIELD
                    in target_requirement.additional_zones
                )
            )
            has_interruptible_spell = (
                self.interruptible_spell_id is not None
                and any(
                    candidate.id == self.interruptible_spell_id
                    for candidate in self.stack
                )
            )
            can_resolve_standalone = any(
                isinstance(effect, (AddManaEffect, SacrificeCreatureForManaEffect))
                for effect in card.definition.spell_effects
            )
            if (
                not has_interruptible_spell
                and not can_target_in_play
                and not can_resolve_standalone
            ):
                raise RuntimeError(
                    "interrupts can only be cast immediately on the current spell"
                )
        if self.current_phase is TurnPhase.UNTAP:
            raise RuntimeError("spells cannot be cast during the Untap phase")
        if is_sorcery and (
            caster is not self.active_player
            or self.current_phase is not TurnPhase.MAIN
            or self.combat is not None
            or bool(self.stack or self.batch_abilities)
        ):
            raise RuntimeError(
                "sorceries can only be cast by the active player "
                "during the Main phase outside combat"
            )
        if (
            is_instant
            and self.combat is not None
            and self.combat.step is CombatStep.DAMAGE
        ):
            raise RuntimeError("instants cannot be cast during combat damage")
        if any(
            isinstance(effect, TemporaryPumpEffect)
            and effect.destroy_at_end_of_turn_if_attacked
            for effect in card.definition.spell_effects
        ) and self.attacks_this_turn and self.combat is None:
            raise RuntimeError(
                f"{card.name} cannot be cast after the current turn's attack"
            )
        if any(
            isinstance(effect, PreventCombatDamageEffect)
            for effect in card.definition.spell_effects
        ) and self.attacks_this_turn and self.combat is None:
            raise RuntimeError(
                f"{card.name} cannot be cast after the current turn's combat damage"
            )
        if not self.can_pay_mana(caster, self.spell_mana_cost(card, x_value)):
            raise RuntimeError(f"not enough mana to cast {card.name}")
        if any(
            isinstance(effect, SirensCallEffect)
            for effect in card.definition.spell_effects
        ) and (
            caster is self.active_player
            or self.attacks_this_turn
            or self.combat is not None
        ):
            raise RuntimeError(
                f"{card.name} can only be cast during an opponent's turn before the attack"
            )
        if any(
            isinstance(effect, BlazeOfGloryEffect)
            for effect in card.definition.spell_effects
        ) and (
            self.combat is None
            or self.combat.step is not CombatStep.ATTACKER_RESPONSE
        ):
            raise RuntimeError(
                f"{card.name} can only be cast after attackers and before blockers"
            )
        return caster

    def _validate_cast(self, card: Card, x_value: int = 0) -> PlayerState:
        if self.combat is not None and self.combat.step in {
            CombatStep.DECLARE_ATTACKERS,
            CombatStep.DECLARE_BLOCKERS,
        }:
            raise RuntimeError("spells cannot be cast during a combat declaration")
        if x_value < 0:
            raise ValueError("X cannot be negative")
        if card.definition.requires_ante and not self.ante_enabled:
            raise RuntimeError(f"{card.name} cannot be used when not playing for ante")
        if any(
            isinstance(effect, SwapLibraryTopWithAnteEffect)
            for effect in card.definition.spell_effects
        ) and not self._caster_for(card).library:
            raise RuntimeError(f"{card.name} requires a card in your library")
        if not card.definition.mana_cost.x_symbols and x_value:
            raise ValueError(f"{card.name} has no X in its mana cost")
        caster = self._caster_for(card)
        requirement = card.definition.target_requirement
        if (
            requirement is not None
            and requirement.count_equals_x
            and x_value > len(self.legal_targets_for(card))
        ):
            raise ValueError(
                f"X cannot exceed the number of legal targets for {card.name}"
            )
        if (
            self.priority_player_index is not None
            and caster is not self.players[self.priority_player_index]
        ):
            raise RuntimeError(
                f"{self.players[self.priority_player_index].name} has priority"
            )
        if card.definition.is_permanent:
            self._validate_permanent_cast(card, x_value=x_value)
            return caster
        return self._validate_nonpermanent_cast(card, x_value)

    def maximum_affordable_x(self, card: Card, target_count: int = 1) -> int:
        """Largest X the card's current holder can pay."""

        caster = self._caster_for(card)
        cost = card.definition.mana_cost
        if not cost.x_symbols:
            raise ValueError(f"{card.name} has no X in its mana cost")
        if not self.can_pay_mana(
            caster, self.spell_mana_cost(card, 0, target_count)
        ):
            raise RuntimeError(f"not enough mana to cast {card.name}")
        if any(
            isinstance(effect, DrainLifeEffect)
            for effect in card.definition.spell_effects
        ):
            maximum = 0
            while self.can_pay_mana(
                caster, self.spell_mana_cost(card, maximum + 1, target_count)
            ):
                maximum += 1
        else:
            remaining = (
                caster.mana_pool.total
                - self.spell_mana_cost(card, 0, target_count).mana_value
            )
            maximum = remaining // cost.x_symbols
        requirement = card.definition.target_requirement
        if requirement is not None and requirement.count_equals_x:
            maximum = min(maximum, len(self.legal_targets_for(card)))
        return maximum

    def begin_cast(
        self,
        card: Card,
        x_value: int = 0,
        *,
        land_subtype: str | None = None,
        mode: str | None = None,
        damage_source_key: str | None = None,
    ) -> PendingCast | None:
        """Cast an untargeted spell or wait for the spell's targets."""

        damage_window_effect = any(
            isinstance(
                effect,
                (ReverseDamageEffect, RetroactiveDamageTransferEffect),
            )
            for effect in card.definition.spell_effects
        )
        self._require_no_pending_action(
            allow_stack=True, allow_damage=damage_window_effect
        )
        if self.pending_damage is not None and (
            not damage_window_effect
            or self.pending_damage.step is not DamageResolutionStep.PREVENTION
        ):
            raise RuntimeError(
                "this spell can only be cast during the damage-prevention window"
            )
        caster = self._validate_cast(card, x_value)
        self._validate_land_type_choice(card, land_subtype)
        self._validate_casting_mode(card, mode)
        reverse_damage = any(
            isinstance(effect, ReverseDamageEffect)
            for effect in card.definition.spell_effects
        )
        if reverse_damage:
            legal_sources = {
                choice[0] for choice in self.damage_source_choices(caster.id)
            }
            if damage_source_key not in legal_sources:
                raise ValueError(f"{card.name} requires a damage source choice")
        elif damage_source_key is not None:
            raise ValueError(f"{card.name} does not choose a damage source")

        if card.definition.target_requirement is not None:
            requirement = card.definition.target_requirement
            if not (requirement.count_equals_x and x_value == 0) and not self.legal_targets_for(
                card, mode=mode
            ) and not self.legal_player_targets_for(card):
                raise RuntimeError(f"there are no legal targets for {card.name}")
            self.pending_cast = PendingCast(
                card, caster.id, x_value, land_subtype, mode, damage_source_key
            )
            return self.pending_cast
        if self.pending_damage is not None and reverse_damage:
            self.cast_reverse_damage_in_prevention(card, damage_source_key)
            return None
        self._cast_spell(
            card, (), caster, x_value, chosen_land_subtype=land_subtype,
            chosen_mode=mode,
            damage_source_key=damage_source_key,
        )
        return None

    def _validate_casting_mode(self, card: Card, mode: str | None) -> None:
        modes = card.definition.casting_modes
        if modes and mode not in modes:
            raise ValueError(f"{card.name} requires a casting mode choice")
        if not modes and mode is not None:
            raise ValueError(f"{card.name} does not have casting modes")

    def _validate_land_type_choice(
        self, card: Card, land_subtype: str | None
    ) -> None:
        """Validate a cast-time basic-land-type choice, when required."""

        chooses_land_type = any(
            isinstance(effect, AttachedLandTypeEffect)
            and effect.chosen_basic_subtype
            for effect in card.definition.land_type_effects
        )
        if chooses_land_type:
            if land_subtype not in BASIC_LAND_SUBTYPES:
                raise ValueError(
                    f"{card.name} requires a basic land type choice"
                )
        elif land_subtype is not None:
            raise ValueError(f"{card.name} does not choose a land type")

    def legal_targets_for(
        self, card: Card | None = None, *, mode: str | None = None
    ) -> list[Card]:
        """Return the cards that currently satisfy a spell's target requirement."""

        spell = card or (self.pending_cast.spell if self.pending_cast else None)
        pending_ability = self.pending_activation if card is None else None
        requirement = (
            spell.definition.target_requirement
            if spell is not None
            else self._pending_ability_requirement(pending_ability)
        )
        if requirement is None:
            return []
        if requirement.zone is None:
            return []
        caster_id = (
            self.pending_cast.caster_id
            if self.pending_cast is not None
            and self.pending_cast.spell is spell
            else pending_ability.controller_id
            if pending_ability is not None
            else spell.controller_id or spell.owner_id
        )
        target_zones = requirement.additional_zones | (
            frozenset({requirement.zone})
            if requirement.zone is not None
            else frozenset()
        )
        chosen_mode = (
            mode
            if mode is not None
            else self.pending_cast.chosen_mode
            if self.pending_cast is not None
            and self.pending_cast.spell is spell
            else None
        )
        if spell is not None and spell.definition.casting_mode_target_zones:
            try:
                mode_index = spell.definition.casting_modes.index(chosen_mode)
            except ValueError:
                return []
            target_zones &= frozenset(
                {spell.definition.casting_mode_target_zones[mode_index]}
            )
        if Zone.STACK in target_zones:
            interrupt_root_index = next(
                (
                    index
                    for index, candidate in enumerate(self.stack)
                    if candidate.id == self.interruptible_spell_id
                ),
                len(self.stack),
            )
            pending_effect = (
                self.activated_abilities(pending_ability.source)[
                    pending_ability.ability_index
                ]
                if pending_ability is not None
                else None
            )
            if (
                spell is not None
                and CardType.INTERRUPT in spell.definition.card_types
            ) or isinstance(pending_effect, ActivatedCounterSpellAbility):
                stack_candidates = (
                    self.stack[interrupt_root_index:]
                    if interrupt_root_index < len(self.stack)
                    else []
                )
            else:
                stack_candidates = self.stack
        else:
            stack_candidates = []
        candidates = [
            *stack_candidates,
            *[
                candidate
                for player in self.players
                for zone in target_zones - {Zone.STACK}
                for candidate in player.cards_in(zone)
            ],
        ]
        legal = [
            candidate
            for candidate in candidates
            if self._requirement_accepts_card(
                requirement,
                candidate,
                caster_id,
                source_colors=(
                    self.card_colors(spell)
                    if spell is not None
                    else self.card_colors(pending_ability.source)
                    if pending_ability is not None
                    else frozenset()
                ),
            )
        ]
        if (
            spell is not None
            and CardType.ENCHANTMENT in spell.definition.card_types
            and any(
                subtype.startswith("Enchant ")
                for subtype in spell.definition.subtypes
            )
        ):
            legal = [
                candidate
                for candidate in legal
                if not (
                    CardType.LAND in self.card_types(candidate)
                    and self.land_is_consecrated(candidate)
                )
            ]
        if spell is not None and any(
            isinstance(effect, SacrificeCreatureForManaEffect)
            for effect in spell.definition.spell_effects
        ):
            legal = [
                candidate
                for candidate in legal
                if candidate.damage < self.creature_toughness(candidate)
            ]
        if pending_ability is not None:
            pending_effect = self.activated_abilities(
                pending_ability.source
            )[pending_ability.ability_index]
            if isinstance(pending_effect, ActivatedAttackRequirementAbility):
                legal = [
                    candidate for candidate in legal
                    if candidate.summoned_turn != self.turn_number
                ]
            if (
                isinstance(pending_effect, ActivatedTemporaryAbility)
                and pending_effect.toughness_less_than_source_power
            ):
                source_power = self.creature_power(pending_ability.source)
                legal = [
                    candidate
                    for candidate in legal
                    if self.creature_toughness(candidate) < source_power
                ]
        counter_effect = next(
            (
                effect
                for effect in (
                    spell.definition.spell_effects
                    if spell is not None
                    else ()
                )
                if isinstance(effect, CounterTargetSpellEffect)
                and effect.x_equals_target_cost
            ),
            None,
        )
        if (
            counter_effect is not None
            and self.pending_cast is not None
            and self.pending_cast.spell is spell
        ):
            declared_x = self.pending_cast.x_value
            legal = [
                candidate
                for candidate in legal
                if candidate.id in self.stack_spells
                and self.spell_casting_cost_value(
                    candidate, self.stack_spells[candidate.id].x_value
                )
                == declared_x
            ]
        return legal

    def _requirement_accepts_card(
        self,
        requirement: TargetRequirement,
        card: Card,
        caster_id: str | None = None,
        *,
        check_tapped: bool = True,
        source_colors: frozenset[Color] = frozenset(),
    ) -> bool:
        if not requirement.accepts_card(
            card,
            check_tapped=check_tapped,
            current_colors=self.card_colors(card),
            current_card_types=(
                card.definition.card_types
                if requirement.printed_card_types_only
                else self.card_types(card)
            ),
        ):
            return False
        if self._is_protected_from(card, source_colors):
            return False
        if requirement.owner_only and card.owner_id != caster_id:
            return False
        if requirement.controller_only and card.controller_id != caster_id:
            return False
        if requirement.defending_player_only and (
            self.combat is None
            or card.controller_id != self.combat.defending_player_id
        ):
            return False
        if (
            requirement.active_player_only
            and card.controller_id != self.active_player.id
        ):
            return False
        if (
            requirement.maximum_power is not None
            and (
                CardType.CREATURE not in self.card_types(card)
                or self.creature_power(card) > requirement.maximum_power
            )
        ):
            return False
        if requirement.required_abilities and not requirement.required_abilities.issubset(
            self.creature_abilities(card)
        ):
            return False
        if requirement.required_land_subtypes and not requirement.required_land_subtypes.issubset(
            self.land_subtypes(card)
        ):
            return False
        if requirement.blocking_only:
            return (
                self.combat is not None
                and any(
                    card in blockers
                    for blockers in self.combat.blockers.values()
                )
            )
        return True

    def _is_protected_from(
        self, creature: Card, colors: frozenset[Color]
    ) -> bool:
        """Whether an in-play creature has FAQ protection from a source color."""

        if (
            CardType.CREATURE not in self.card_types(creature)
            or creature.zone is not Zone.BATTLEFIELD
        ):
            return False
        protected_colors = {
            ability.protection_color
            for ability in self.creature_abilities(creature)
            if ability.protection_color is not None
        }
        return bool(protected_colors & colors)

    def legal_player_targets_for(
        self, card: Card | None = None
    ) -> list[PlayerState]:
        spell = card or (self.pending_cast.spell if self.pending_cast else None)
        pending_ability = self.pending_activation if card is None else None
        requirement = (
            spell.definition.target_requirement
            if spell is not None
            else self._pending_ability_requirement(pending_ability)
        )
        if requirement is None or not requirement.players:
            return []
        players = list(self.players)
        if requirement.opponent_only:
            controller_id = (
                spell.owner_id
                if spell is not None
                else pending_ability.controller_id
            )
            players = [player for player in players if player.id != controller_id]
        return players

    def _pending_ability_requirement(
        self, pending: PendingActivation | None
    ) -> TargetRequirement | None:
        if pending is None:
            return None
        ability = self.activated_abilities(pending.source)[pending.ability_index]
        return (
            ability.target_requirement
            if isinstance(
                ability,
                (
                    ActivatedDamageAbility,
                    ActivatedDestroyAbility,
                    ActivatedTapAbility,
                    ActivatedUnblockableAbility,
                    ActivatedTemporaryAbility,
                    ActivatedDiscardAbility,
                    ActivatedAttackRequirementAbility,
                    ActivatedLandTypeAbility,
                    ActivatedInterruptUntapAbility,
                    ActivatedCounterSpellAbility,
                ),
            )
            else None
        )

    def complete_pending_activation(
        self, targets: Iterable[Card | PlayerState]
    ) -> None:
        """Choose targets, pay tap costs, and declare an activated fast effect."""

        if self.pending_activation is None:
            raise RuntimeError("there is no activated ability waiting for targets")
        pending = self.pending_activation
        ability = self.activated_abilities(pending.source)[pending.ability_index]
        assert isinstance(
            ability,
            (
                ActivatedDamageAbility,
                ActivatedDestroyAbility,
                ActivatedTapAbility,
                ActivatedUnblockableAbility,
                ActivatedTemporaryAbility,
                ActivatedDiscardAbility,
                ActivatedAttackRequirementAbility,
                ActivatedLandTypeAbility,
                ActivatedInterruptUntapAbility,
                ActivatedCounterSpellAbility,
            ),
        )
        chosen = tuple(targets)
        requirement = ability.target_requirement
        if len(chosen) != requirement.count:
            raise ValueError(
                f"{pending.source.name} requires {requirement.count} target(s)"
            )
        legal_cards = self.legal_targets_for()
        legal_players = self.legal_player_targets_for()
        if any(
            target not in (
                legal_cards if isinstance(target, Card) else legal_players
            )
            for target in chosen
        ):
            raise ValueError(f"illegal target for {pending.source.name}")
        self.pending_activation = None
        try:
            player, validated = self._validate_ability_activation(
                pending.controller_id, pending.source, pending.ability_index
            )
        except (ValueError, RuntimeError):
            self.pending_activation = pending
            raise
        assert validated is ability
        if ability.tap_cost:
            self._tap_permanent(pending.source)
        if isinstance(
            ability,
            (
                ActivatedDamageAbility,
                ActivatedDestroyAbility,
                ActivatedTapAbility,
                ActivatedUnblockableAbility,
                ActivatedTemporaryAbility,
                ActivatedDiscardAbility,
                ActivatedAttackRequirementAbility,
                ActivatedLandTypeAbility,
                ActivatedInterruptUntapAbility,
                ActivatedCounterSpellAbility,
            ),
        ):
            self.pay_mana(player, ability.mana_cost)
        if isinstance(ability, ActivatedInterruptUntapAbility):
            for target in chosen:
                if isinstance(target, Card):
                    target.tapped = False
            # Interrupt-speed permanent abilities resolve immediately. Taking
            # the action invalidates earlier passes without closing or
            # replacing the current spell's interrupt window.
            self.consecutive_passes = 0
            self.check_state_based_actions()
            return
        if isinstance(ability, ActivatedCounterSpellAbility):
            self.interrupt_abilities.append(
                AbilityOnStack(
                    pending.source,
                    pending.source.name,
                    player.id,
                    ability,
                    chosen,
                )
            )
            # It belongs to the current spell's interrupt sequence. It does
            # not replace the root spell or surrender priority.
            self.consecutive_passes = 0
            return
        self.batch_abilities.append(
            AbilityOnStack(
                pending.source,
                pending.source.name,
                player.id,
                ability,
                chosen,
            )
        )
        self.interruptible_spell_id = None
        self.check_state_based_actions()
        self.priority_player_index = (
            self.players.index(player) + 1
        ) % len(self.players)
        self.consecutive_passes = 0

    def cancel_pending_activation(self) -> None:
        if self.pending_activation is None:
            raise RuntimeError("there is no pending ability to cancel")
        self.pending_activation = None

    def complete_pending_cast(
        self, targets: Iterable[Card | PlayerState]
    ) -> None:
        """Validate chosen targets, then pay for and resolve the pending spell."""

        if self.pending_cast is None:
            raise RuntimeError("there is no spell waiting for targets")
        pending = self.pending_cast
        chosen = tuple(targets)
        requirement = pending.spell.definition.target_requirement
        assert requirement is not None
        required_count = pending.x_value if requirement.count_equals_x else requirement.count
        if requirement.any_number:
            if not chosen:
                raise ValueError(f"{pending.spell.name} requires at least one target")
        elif len(chosen) != required_count:
            raise ValueError(
                f"{pending.spell.name} requires {required_count} target(s)"
            )
        target_keys = {
            ("card", target.id)
            if isinstance(target, Card)
            else ("player", target.id)
            for target in chosen
        }
        if len(target_keys) != len(chosen):
            raise ValueError("the same card cannot be chosen as a target twice")
        legal_cards = self.legal_targets_for(
            pending.spell, mode=pending.chosen_mode
        )
        legal_players = self.legal_player_targets_for(pending.spell)
        if any(
            target not in (
                legal_cards if isinstance(target, Card) else legal_players
            )
            for target in chosen
        ):
            raise ValueError(f"illegal target for {pending.spell.name}")
        counter_effect = next(
            (
                effect
                for effect in pending.spell.definition.spell_effects
                if isinstance(effect, CounterTargetSpellEffect)
            ),
            None,
        )
        if counter_effect is not None and counter_effect.x_equals_target_cost:
            target = chosen[0]
            assert isinstance(target, Card)
            target_spell = self.stack_spells[target.id]
            target_cost = self.spell_casting_cost_value(
                target, target_spell.x_value
            )
            if pending.x_value != target_cost:
                raise ValueError(
                    f"X must equal {target.name}'s casting cost ({target_cost})"
                )
        caster = self.player(pending.caster_id)
        validated_caster = self._validate_cast(
            pending.spell, pending.x_value
        )
        if caster is not validated_caster:
            raise RuntimeError("the pending spell's caster has changed")
        final_cost = self.spell_mana_cost(
            pending.spell, pending.x_value, len(chosen)
        )
        if not self.can_pay_mana(caster, final_cost):
            raise RuntimeError(
                f"not enough mana to cast {pending.spell.name} with "
                f"{len(chosen)} targets"
            )
        self.pending_cast = None
        if self.pending_damage is not None and any(
            isinstance(effect, RetroactiveDamageTransferEffect)
            for effect in pending.spell.definition.spell_effects
        ):
            target = next(
                (item for item in chosen if isinstance(item, Card)), None
            )
            assert target is not None
            self.cast_simulacrum_in_prevention(pending.spell, target)
            return
        self._cast_spell(
            pending.spell,
            chosen,
            caster,
            pending.x_value,
            chosen_land_subtype=pending.chosen_land_subtype,
            chosen_mode=pending.chosen_mode,
            damage_source_key=pending.damage_source_key,
            copied_spell_targets=pending.copied_spell_targets,
            copied_spell_x_value=pending.copied_spell_x_value,
        )

    def fork_copy_target_options(
        self, original: Card
    ) -> tuple[list[Card], list[PlayerState]]:
        """Return legal new targets for a pending Fork copy."""

        if self.pending_cast is None:
            raise RuntimeError("Fork is not waiting for a spell choice")
        if not any(
            isinstance(effect, CopyTargetSpellEffect)
            for effect in self.pending_cast.spell.definition.spell_effects
        ):
            raise RuntimeError("the pending spell is not Fork")
        if original.id not in self.stack_spells:
            raise ValueError("the spell to copy is no longer being cast")
        state = self.stack_spells[original.id]
        requirement = original.definition.target_requirement
        if requirement is None:
            return [], []
        caster_id = self.pending_cast.caster_id
        target_zones = requirement.additional_zones | (
            frozenset({requirement.zone})
            if requirement.zone is not None else frozenset()
        )
        cards = [
            candidate
            for player in self.players
            for zone in target_zones - {Zone.STACK}
            for candidate in player.cards_in(zone)
            if self._requirement_accepts_card(
                requirement,
                candidate,
                caster_id,
                source_colors=frozenset({Color.RED}),
            )
        ]
        if Zone.STACK in target_zones:
            cards.extend(
                candidate for candidate in self.stack
                if self._requirement_accepts_card(
                    requirement,
                    candidate,
                    caster_id,
                    source_colors=frozenset({Color.RED}),
                )
            )
        if original.definition.casting_mode_target_zones:
            mode_index = original.definition.casting_modes.index(state.chosen_mode)
            required_zone = original.definition.casting_mode_target_zones[mode_index]
            cards = [candidate for candidate in cards if candidate.zone is required_zone]
        players = list(self.players) if requirement.players else []
        if requirement.opponent_only:
            players = [player for player in players if player.id != caster_id]
        return cards, players

    def choose_pending_fork_copy(
        self,
        original: Card,
        targets: Iterable[Card | PlayerState],
        *,
        x_value: int | None = None,
    ) -> None:
        """Record Fork's independently controlled targets before it is cast."""

        if self.pending_cast is None:
            raise RuntimeError("Fork is not waiting for a spell choice")
        pending = self.pending_cast
        if original.id not in self.stack_spells:
            raise ValueError("the spell to copy is no longer being cast")
        original_state = self.stack_spells[original.id]
        requirement = original.definition.target_requirement
        chosen = tuple(targets)
        copied_x = original_state.x_value if x_value is None else x_value
        if copied_x < 0:
            raise ValueError("a copied X value cannot be negative")
        if requirement is None:
            if chosen:
                raise ValueError(f"{original.name} has no targets")
        else:
            required_count = copied_x if requirement.count_equals_x else requirement.count
            if requirement.any_number:
                if not chosen:
                    raise ValueError(f"the {original.name} copy requires a target")
            elif len(chosen) != required_count:
                raise ValueError(
                    f"the {original.name} copy requires {required_count} target(s)"
                )
            keys = {
                ("card", target.id) if isinstance(target, Card)
                else ("player", target.id)
                for target in chosen
            }
            if len(keys) != len(chosen):
                raise ValueError("the same target cannot be chosen twice")
            legal_cards, legal_players = self.fork_copy_target_options(original)
            if any(
                target not in (legal_cards if isinstance(target, Card) else legal_players)
                for target in chosen
            ):
                raise ValueError(f"illegal target for the {original.name} copy")
        if any(
            isinstance(effect, DividedDamageEffect)
            for effect in original.definition.spell_effects
        ):
            budget = original_state.x_value + max(0, len(original_state.targets) - 1)
            if copied_x + max(0, len(chosen) - 1) != budget:
                raise ValueError(
                    "a Forked Fireball must redistribute the original mana total"
                )
        elif copied_x != original_state.x_value:
            raise ValueError("Fork cannot change the copied spell's X value")
        pending.copied_spell_targets = chosen
        pending.copied_spell_x_value = copied_x

    def cancel_pending_cast(self) -> None:
        if self.pending_cast is None:
            raise RuntimeError("there is no pending spell to cancel")
        self.pending_cast = None

    def _resolve_permanent_spell(
        self,
        card: Card,
        targets: tuple[Card, ...],
        *,
        chosen_land_subtype: str | None = None,
    ) -> None:
        player = self.active_player
        self.pay_mana(player, self.spell_mana_cost(card))
        card.controller_id = player.id
        copies_artifact = card.definition.copies_artifact
        copies_creature = card.definition.copies_creature
        if copies_artifact or copies_creature:
            if len(targets) != 1:
                raise ValueError(f"{card.name} requires exactly one copy choice")
            if copies_artifact:
                self._copy_artifact_definition(card, targets[0])
            else:
                self._copy_creature_definition(card, targets[0])
        self._move_card(card, Zone.BATTLEFIELD)
        card.entered_battlefield_turn = self.turn_number
        card.enchanted_card_id = (
            targets[0].id
            if targets and not copies_artifact and not copies_creature
            else None
        )
        if card.definition.taps_attached_on_entry and targets:
            self._tap_permanent(targets[0])
        card.chosen_land_subtype = chosen_land_subtype
        self._reconcile_control_effects()
        self.events.append(
            SpellCastEvent(
                card_id=card.id,
                card_name=card.name,
                caster_id=player.id,
                target_ids=tuple(target.id for target in targets),
                target_names=tuple(target.name for target in targets),
            )
        )
        self._record_spell_cast_opportunity(card)
        self.check_state_based_actions()

    def _cast_spell(
        self,
        card: Card,
        targets: tuple[Card | PlayerState, ...],
        caster: PlayerState,
        x_value: int = 0,
        *,
        chosen_land_subtype: str | None = None,
        chosen_mode: str | None = None,
        damage_source_key: str | None = None,
        copied_spell_targets: tuple[Card | PlayerState, ...] | None = None,
        copied_spell_x_value: int | None = None,
    ) -> None:
        """Pay for a spell and add it to the current response batch."""

        self.pay_mana(
            caster, self.spell_mana_cost(card, x_value, len(targets) or 1)
        )
        card.controller_id = caster.id
        self._move_card(card, Zone.STACK)
        card.chosen_land_subtype = chosen_land_subtype
        if (
            CardType.INTERRUPT not in card.definition.card_types
            or self.interruptible_spell_id is None
        ):
            self.interruptible_spell_id = card.id
        self.stack_spells[card.id] = SpellOnStack(
            card, caster.id, targets, x_value, chosen_mode, damage_source_key,
            copied_spell_targets, copied_spell_x_value,
        )
        self.events.append(
            SpellCastEvent(
                card_id=card.id,
                card_name=card.name,
                caster_id=caster.id,
                target_ids=tuple(
                    target.id for target in targets if isinstance(target, Card)
                ),
                target_player_ids=tuple(
                    target.id
                    for target in targets
                    if not isinstance(target, Card)
                ),
                target_names=tuple(target.name for target in targets),
            )
        )
        self._record_spell_cast_opportunity(card)
        self.priority_player_index = (
            self.players.index(caster) + 1
        ) % len(self.players)
        self.consecutive_passes = 0
