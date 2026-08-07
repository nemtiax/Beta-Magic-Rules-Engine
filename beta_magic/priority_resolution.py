"""Priority, interrupt, and fast-effect batch resolution for GameState."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable
from uuid import UUID

from .abilities import (
    ActivatedCounterSpellAbility,
    ActivatedAnimationAbility,
    ActivatedAttackRequirementAbility,
    ActivatedDamageAbility,
    ActivatedGlobalDamageAbility,
    ActivatedDestroyAbility,
    ActivatedDestroyAllAbility,
    ActivatedDiscardAbility,
    ActivatedDrawAbility,
    ActivatedEventLifeGainAbility,
    ActivatedExtraTurnAbility,
    ActivatedLandTypeAbility,
    ActivatedPumpAbility,
    ActivatedTapAbility,
    ActivatedTemporaryAbility,
    ActivatedUntapAbility,
    ActivatedUnblockableAbility,
)
from .cards import Card
from .combat import AttackRequirement
from .damage import DamageIncidentKind, DamageRecipientKind
from .destruction import DestructionIncident, DestructionTarget
from .effects import (
    AddManaEffect,
    BalanceEffect,
    ChangeTargetColorEffect,
    ContinuousEffect,
    CounterTargetSpellEffect,
    DamageEffect,
    DestroyAllEffect,
    DestroyTargetsEffect,
    DiscardCardsEffect,
    DiscardHandsAndDrawEffect,
    DrawCardsEffect,
    EffectRecipient,
    ExileTargetsEffect,
    ExtraTurnEffect,
    GainLifeEffect,
    GlobalDamageEffect,
    MoveTargetsEffect,
    RegenerateTargetsEffect,
    RetroactiveDamageTransferEffect,
    ReverseDamageEffect,
    SetTappedEffect,
    ShuffleHandAndGraveyardEffect,
    SirensCallEffect,
    BlazeOfGloryEffect,
    TemporaryPumpEffect,
    TapLandsAndEmptyManaPoolEffect,
)
from .types import CardType, CombatStep, KeywordAbility, Zone

if TYPE_CHECKING:
    from .game import PlayerState


@dataclass(slots=True)
class PendingDiscardChoice:
    player_id: str
    amount: int
    source_name: str


@dataclass(frozen=True, slots=True)
class BalanceChoice:
    player_id: str
    category: str
    amount: int
    candidate_ids: frozenset[UUID]


@dataclass(slots=True)
class PendingBalance:
    choices: list[BalanceChoice]
    selections: list[frozenset[UUID]] = field(default_factory=list)

    @property
    def current_choice(self) -> BalanceChoice | None:
        return (
            self.choices[len(self.selections)]
            if len(self.selections) < len(self.choices)
            else None
        )


class PriorityBatchResolutionMixin:
    """Coordinate priority, interrupts, and simultaneous fast-effect batches."""

    __slots__ = ()

    def _combat_response_pending(self) -> bool:
        return bool(
            self.combat is not None
            and self.combat.step in {
                CombatStep.ATTACK_RESPONSE,
                CombatStep.ATTACKER_RESPONSE,
                CombatStep.BLOCKER_RESPONSE,
            }
        )

    def _close_combat_response_window(self) -> None:
        assert self.combat is not None
        if self.combat.step is CombatStep.ATTACK_RESPONSE:
            self._empty_mana_pools()
            self.combat.step = CombatStep.DECLARE_ATTACKERS
        elif self.combat.step is CombatStep.ATTACKER_RESPONSE:
            self.combat.step = CombatStep.DECLARE_BLOCKERS
        elif self.combat.step is CombatStep.BLOCKER_RESPONSE:
            self.combat.step = CombatStep.DAMAGE
        else:
            raise RuntimeError("combat is not awaiting responses")
        self.priority_player_index = None
        self.consecutive_passes = 0

    def pass_priority(self, player_id: str) -> tuple[Card, ...] | None:
        """Pass once; unanimous passes resolve a batch or pending timed event."""

        if self.pending_damage is not None:
            self._pass_damage_priority(player_id)
            return None
        if self.pending_destruction is not None:
            self._pass_destruction_priority(player_id)
            return None
        self._require_no_pending_action(allow_stack=True)
        if (
            not self.stack
            and not self.batch_abilities
            and not self.timed_events
            and not self.event_opportunities
            and self.pending_phase_advance is None
            and not self._combat_response_pending()
            or self.priority_player_index is None
        ):
            raise RuntimeError(
                "there is no batch, timed event, or rules event awaiting priority"
            )
        player = self.player(player_id)
        if player is not self.players[self.priority_player_index]:
            raise RuntimeError(
                f"{self.players[self.priority_player_index].name} has priority"
            )
        if (
            not self.stack
            and not self.batch_abilities
            and not self.event_opportunities
            and self._timed_event_needs_payment()
            and player.id == self.timed_events[0].affected_player_id
        ):
            raise RuntimeError("choose whether to pay the upkeep cost first")
        self.consecutive_passes += 1
        if self.consecutive_passes < len(self.players):
            self.priority_player_index = (
                self.priority_player_index + 1
            ) % len(self.players)
            return None

        if self.stack or self.batch_abilities:
            if (
                self.stack
                and CardType.INTERRUPT
                in self.stack[-1].definition.card_types
            ):
                resolved = self._resolve_interrupt()
                return resolved
            if self.interrupt_abilities:
                self._resolve_counter_ability()
                return ()
            resolved = self._resolve_batch()
            if (
                self.pending_damage is None
                and self.pending_destruction is None
            ):
                self.consecutive_passes = 0
                self.priority_player_index = (
                    self.active_player_index
                    if self.timed_events or self.event_opportunities
                    or self.pending_phase_advance is not None
                    or self._combat_response_pending()
                    else None
                )
            return resolved

        if self.event_opportunities:
            self._close_event_opportunities()
            if (
                self.pending_damage is None
                and self.pending_destruction is None
            ):
                self.consecutive_passes = 0
                self.priority_player_index = (
                    self.active_player_index
                    if self.timed_events or self.event_opportunities
                    or self.pending_phase_advance is not None
                    or self._combat_response_pending()
                    else None
                )
            return ()

        if self.pending_phase_advance is not None:
            self.pending_phase_advance = None
            self.priority_player_index = None
            self.consecutive_passes = 0
            self.advance_phase()
            return ()

        if self._combat_response_pending():
            self._close_combat_response_window()
            return ()

        self._resolve_timed_event()
        if (
            self.pending_damage is None
            and self.pending_destruction is None
        ):
            self.consecutive_passes = 0
            self.priority_player_index = (
                self.active_player_index
                if self.timed_events or self.event_opportunities
                or self.pending_phase_advance is not None
                or self._combat_response_pending()
                else None
            )
        return ()

    def _discard_random(self, player: PlayerState, amount: int) -> tuple[Card, ...]:
        chosen = tuple(self.random.sample(player.hand, min(amount, len(player.hand))))
        for card in chosen:
            self._move_card(card, Zone.GRAVEYARD)
        return chosen

    def choose_discard(self, player_id: str, cards: Iterable[Card]) -> tuple[Card, ...]:
        """Complete the oldest opponent-chosen discard effect."""

        if not self.pending_discard_choices:
            raise RuntimeError("there is no discard choice pending")
        choice = self.pending_discard_choices[0]
        if choice.player_id != player_id:
            raise ValueError("only the affected player may choose the discarded cards")
        player = self.player(player_id)
        chosen = tuple(cards)
        required = min(choice.amount, len(player.hand))
        if len(chosen) != required or len({card.id for card in chosen}) != len(chosen):
            raise ValueError(f"choose exactly {required} card(s) to discard")
        if any(card not in player.hand for card in chosen):
            raise ValueError("discard choices must be cards in the affected player's hand")
        for card in chosen:
            self._move_card(card, Zone.GRAVEYARD)
        self.pending_discard_choices.pop(0)
        if not self.pending_discard_choices and self.pending_damage is None:
            self.priority_player_index = (
                self.active_player_index
                if self.timed_events or self.event_opportunities
                or self.pending_phase_advance is not None
                or self._combat_response_pending()
                else None
            )
            self.consecutive_passes = 0
        return chosen

    def _begin_balance(self) -> None:
        """Snapshot all Balance counts before any player makes a choice."""

        lands = {
            player.id: tuple(
                card
                for card in player.battlefield
                if CardType.LAND in self.card_types(card)
            )
            for player in self.players
        }
        creatures = {
            player.id: tuple(
                card
                for card in player.battlefield
                if CardType.CREATURE in self.card_types(card)
            )
            for player in self.players
        }
        hands = {player.id: tuple(player.hand) for player in self.players}
        groups = (("land", lands), ("hand", hands), ("creature", creatures))
        choices: list[BalanceChoice] = []
        for category, candidates_by_player in groups:
            minimum = min(len(cards) for cards in candidates_by_player.values())
            for player in self.players:
                candidates = candidates_by_player[player.id]
                amount = len(candidates) - minimum
                if amount:
                    choices.append(
                        BalanceChoice(
                            player.id,
                            category,
                            amount,
                            frozenset(card.id for card in candidates),
                        )
                    )
        self.pending_balance = PendingBalance(choices) if choices else None

    def choose_balance_cards(
        self, player_id: str, cards: Iterable[Card]
    ) -> tuple[Card, ...]:
        """Record one prompted Balance selection and finish once all are chosen."""

        pending = self.pending_balance
        if pending is None or pending.current_choice is None:
            raise RuntimeError("there is no Balance choice pending")
        choice = pending.current_choice
        if choice.player_id != player_id:
            raise ValueError("only the prompted player may make this Balance choice")
        chosen = tuple(cards)
        chosen_ids = frozenset(card.id for card in chosen)
        if len(chosen) != choice.amount or len(chosen_ids) != len(chosen):
            raise ValueError(
                f"choose exactly {choice.amount} {choice.category} card(s)"
            )
        if not chosen_ids.issubset(choice.candidate_ids):
            raise ValueError(f"Balance requires {choice.category} cards from its snapshot")
        pending.selections.append(chosen_ids)
        if pending.current_choice is not None:
            return chosen

        battlefield_ids: set[UUID] = set()
        hand_ids: set[UUID] = set()
        for completed_choice, selected in zip(pending.choices, pending.selections):
            (hand_ids if completed_choice.category == "hand" else battlefield_ids).update(
                selected
            )
        self.pending_balance = None
        doomed = [
            card
            for player in self.players
            for card in tuple(player.battlefield)
            if card.id in battlefield_ids
        ]
        self._destroy_permanents(doomed)
        for player in self.players:
            for card in tuple(player.hand):
                if card.id in hand_ids:
                    self._move_card(card, Zone.GRAVEYARD)
        self.check_state_based_actions()
        return chosen

    def _resolve_interrupt(self) -> tuple[Card, ...]:
        """Resolve the newest interrupt immediately, before its target spell."""

        interrupts = [
            card
            for card in self.stack
            if CardType.INTERRUPT in card.definition.card_types
        ]
        targeted_interrupt_ids = {
            target.id
            for card in interrupts
            for target in self.stack_spells[card.id].targets
            if isinstance(target, Card)
            and CardType.INTERRUPT in target.definition.card_types
        }
        resolvable = [
            card for card in interrupts if card.id not in targeted_interrupt_ids
        ]

        def interrupt_rank(card: Card) -> tuple[int, int, int]:
            state = self.stack_spells[card.id]
            target = (
                state.targets[0]
                if state.targets and isinstance(state.targets[0], Card)
                else None
            )
            depth = 0
            cursor = target
            while (
                cursor is not None
                and CardType.INTERRUPT in cursor.definition.card_types
                and cursor.id in self.stack_spells
            ):
                depth += 1
                cursor_state = self.stack_spells[cursor.id]
                cursor = (
                    cursor_state.targets[0]
                    if cursor_state.targets
                    and isinstance(cursor_state.targets[0], Card)
                    else None
                )
            target_caster_id = (
                self.stack_spells[target.id].caster_id
                if target is not None and target.id in self.stack_spells
                else None
            )
            caster_first = int(state.caster_id == target_caster_id)
            declaration_order = self.stack.index(card)
            return depth, caster_first, -declaration_order

        interrupt = max(resolvable, key=interrupt_rank)
        spell = self.stack_spells.pop(interrupt.id)
        target = (
            spell.targets[0]
            if spell.targets and isinstance(spell.targets[0], Card)
            else None
        )
        legal_target = (
            target is not None
            and (
                target.zone is Zone.BATTLEFIELD
                or (
                    target.zone is Zone.STACK
                    and target.id in self.stack_spells
                )
            )
        )
        requirement = interrupt.definition.target_requirement
        if legal_target and requirement is not None:
            legal_target = self._requirement_accepts_card(
                requirement,
                target,
                spell.caster_id,
                source_colors=self.card_colors(interrupt),
            )
        if (
            legal_target
            and interrupt.definition.casting_mode_target_zones
        ):
            mode_index = interrupt.definition.casting_modes.index(
                spell.chosen_mode
            )
            legal_target = (
                target.zone
                is interrupt.definition.casting_mode_target_zones[mode_index]
            )
        destruction_effect = next(
            (
                effect
                for effect in interrupt.definition.spell_effects
                if isinstance(effect, DestroyTargetsEffect)
            ),
            None,
        )
        if (
            legal_target
            and target.zone is Zone.STACK
            and any(
            isinstance(effect, CounterTargetSpellEffect)
            for effect in interrupt.definition.spell_effects
            )
        ):
            self.stack_spells.pop(target.id, None)
            self.event_opportunities = [
                event
                for event in self.event_opportunities
                if event.spell_id != target.id
            ]
            self._move_card(target, Zone.GRAVEYARD)
        elif (
            legal_target
            and target.zone is Zone.BATTLEFIELD
            and destruction_effect is not None
        ):
            self.pending_destruction = DestructionIncident(
                [
                    DestructionTarget(
                        target.id,
                        target.name,
                        destruction_effect.regeneration_allowed,
                    )
                ]
            )
            self.resume_interrupts_after_destruction = True
        elif legal_target:
            color_effect = next(
                (
                    effect
                    for effect in interrupt.definition.spell_effects
                    if isinstance(effect, ChangeTargetColorEffect)
                ),
                None,
            )
            if color_effect is not None:
                target.color_override = color_effect.color
                if target.zone is Zone.STACK:
                    self._refresh_spell_cast_opportunity(target)
        for effect in interrupt.definition.spell_effects:
            if isinstance(effect, AddManaEffect):
                self.player(spell.caster_id).mana_pool.add(
                    effect.color, effect.amount
                )

        if interrupt.zone is Zone.STACK:
            self._move_card(interrupt, Zone.GRAVEYARD)

        if not any(
            card.id == self.interruptible_spell_id for card in self.stack
        ):
            self.interruptible_spell_id = None
        self.consecutive_passes = 0
        if self.stack:
            underlying = self.stack_spells[self.stack[-1].id]
            self.priority_player_index = self.players.index(
                self.player(underlying.caster_id)
            )
        elif (
            self.batch_abilities
            or self.event_opportunities
            or self.pending_phase_advance is not None
            or self._combat_response_pending()
        ):
            self.priority_player_index = self.active_player_index
        else:
            self.priority_player_index = None
        if self.pending_destruction is not None:
            self._open_destruction_incident()
        self.check_state_based_actions()
        return (interrupt,)

    def _resolve_counter_ability(self) -> None:
        """Resolve a Deathgrip/Lifeforce activation in the interrupt sequence."""

        state = self.interrupt_abilities.pop(0)
        ability = state.ability
        assert isinstance(ability, ActivatedCounterSpellAbility)
        target = state.targets[0] if state.targets else None
        if (
            isinstance(target, Card)
            and target.zone is Zone.STACK
            and target.id in self.stack_spells
            and ability.spell_color in self.card_colors(target)
        ):
            self.stack_spells.pop(target.id, None)
            self.event_opportunities = [
                event for event in self.event_opportunities
                if event.spell_id != target.id
            ]
            self._move_card(target, Zone.GRAVEYARD)
        if not any(card.id == self.interruptible_spell_id for card in self.stack):
            self.interruptible_spell_id = None
        self.consecutive_passes = 0
        if self.stack:
            underlying = self.stack_spells[self.stack[-1].id]
            self.priority_player_index = self.players.index(
                self.player(underlying.caster_id)
            )
        elif (
            self.batch_abilities
            or self.event_opportunities
            or self.pending_phase_advance is not None
            or self._combat_response_pending()
        ):
            self.priority_player_index = self.active_player_index
        else:
            self.priority_player_index = None
        self.check_state_based_actions()

    def _resolve_batch(self) -> tuple[Card, ...]:
        """Apply one 1993 fast-effect batch, then stabilize exactly once."""

        cards = tuple(self.stack)
        self.interruptible_spell_id = None
        spells = tuple(self.stack_spells[card.id] for card in cards)
        abilities = tuple(self.batch_abilities)
        caught_event_ids = {event.id for event in self.event_opportunities}
        self._begin_damage_incident(DamageIncidentKind.FAST_EFFECT_BATCH)

        # Target validity is fixed before any member of the simultaneous batch
        # changes zones or characteristics.
        legal: dict[UUID, bool] = {}
        for spell in spells:
            requirement = spell.card.definition.target_requirement
            legal[spell.card.id] = requirement is None or all(
                (
                    self._requirement_accepts_card(
                        requirement,
                        target,
                        spell.caster_id,
                        source_colors=self.card_colors(spell.card),
                    )
                    if isinstance(target, Card)
                    else requirement.players and target in self.players
                )
                for target in spell.targets
            )
        legal_abilities = [
            (
                True
                if isinstance(
                    ability.ability,
                    (
                        ActivatedDestroyAllAbility,
                        ActivatedGlobalDamageAbility,
                        ActivatedEventLifeGainAbility,
                        ActivatedUntapAbility,
                    ),
                )
                else ability.source.zone is Zone.BATTLEFIELD
                if isinstance(ability.ability, ActivatedAnimationAbility)
                else all(
                    isinstance(target, Card)
                    and target.zone is Zone.BATTLEFIELD
                    for target in ability.targets
                )
                if isinstance(ability.ability, ActivatedPumpAbility)
                else all(
                    (
                        self._requirement_accepts_card(
                            ability.ability.target_requirement,
                            target,
                            ability.controller_id,
                            check_tapped=False,
                            source_colors=self.card_colors(ability.source),
                        )
                        if isinstance(target, Card)
                        else ability.ability.target_requirement.players
                        and target in self.players
                    )
                    for target in ability.targets
                )
            )
            for ability in abilities
        ]

        # Slow permanents enter as part of the same instant. This lets their
        # continuous effects participate in the final state of the batch.
        for spell in spells:
            card = spell.card
            if legal[card.id] and card.definition.is_permanent:
                self._move_card(card, Zone.BATTLEFIELD)
                card.entered_battlefield_turn = self.turn_number
                card.enchanted_card_id = (
                    spell.targets[0].id
                    if spell.targets and isinstance(spell.targets[0], Card)
                    else None
                )
                if (
                    card.definition.taps_attached_on_entry
                    and spell.targets
                    and isinstance(spell.targets[0], Card)
                ):
                    self._tap_permanent(spell.targets[0])
                if (
                    CardType.CREATURE in card.definition.card_types
                    and CardType.ARTIFACT not in card.definition.card_types
                ):
                    card.summoned_turn = self.turn_number

        pending_destruction: list[tuple[Card, bool]] = []
        pending_regeneration: list[Card] = []
        for spell in spells:
            card = spell.card
            if not legal[card.id] or card.definition.is_permanent:
                continue
            caster = self.player(spell.caster_id)
            for effect in card.definition.spell_effects:
                if isinstance(effect, DamageEffect):
                    recipients = (
                        (caster,)
                        if effect.recipient is EffectRecipient.CASTER
                        else spell.targets
                    )
                    for recipient in recipients:
                        if (
                            effect.disintegrates_target
                            and isinstance(recipient, Card)
                        ):
                            self.disintegrated_this_turn.add(recipient.id)
                        self._deal_damage(
                            recipient,
                            effect.amount + effect.amount_per_x * spell.x_value,
                            card.name,
                            source_card=card,
                            source_controller_id=spell.caster_id,
                        )
                elif isinstance(effect, TemporaryPumpEffect):
                    power = effect.power + effect.power_per_x * spell.x_value
                    toughness = (
                        effect.toughness
                        + effect.toughness_per_x * spell.x_value
                    )
                    for target in spell.targets:
                        if isinstance(target, Card):
                            self.temporary_creature_effects.setdefault(
                                target.id, []
                            ).append(
                                ContinuousEffect(
                                    power=power,
                                    toughness=toughness,
                                    granted_abilities=effect.granted_abilities,
                                )
                            )
                elif isinstance(effect, RegenerateTargetsEffect):
                    pending_regeneration.extend(
                        target
                        for target in spell.targets
                        if isinstance(target, Card)
                    )
                elif isinstance(effect, GainLifeEffect):
                    amount = effect.amount + effect.amount_per_x * spell.x_value
                    for target in spell.targets:
                        if not isinstance(target, Card):
                            target.life += amount
                elif isinstance(effect, DrawCardsEffect):
                    amount = effect.amount + effect.amount_per_x * spell.x_value
                    for target in spell.targets:
                        if not isinstance(target, Card):
                            target.draw(amount)
                elif isinstance(effect, DiscardCardsEffect):
                    amount = effect.amount + effect.amount_per_x * spell.x_value
                    for target in spell.targets:
                        if not not isinstance(target, Card):
                            continue
                        if effect.random:
                            self._discard_random(target, amount)
                        elif target.hand:
                            self.pending_discard_choices.append(
                                PendingDiscardChoice(target.id, amount, card.name)
                            )
                elif isinstance(effect, DiscardHandsAndDrawEffect):
                    for player in self.players:
                        for discarded in tuple(player.hand):
                            self._move_card(discarded, Zone.GRAVEYARD)
                    for player in self.players:
                        player.draw(effect.draw_count)
                elif isinstance(effect, ShuffleHandAndGraveyardEffect):
                    for player in self.players:
                        recyclable = tuple(player.hand) + tuple(player.graveyard)
                        for recyclable_card in recyclable:
                            self._move_card(recyclable_card, Zone.LIBRARY)
                        player.shuffle_library(self.random)
                    for player in self.players:
                        player.draw(effect.draw_count)
                elif isinstance(effect, SirensCallEffect):
                    for creature in tuple(self.active_player.battlefield):
                        if (
                            CardType.CREATURE not in self.card_types(creature)
                            or creature.summoned_turn == self.turn_number
                        ):
                            continue
                        is_wall = "Wall" in creature.definition.subtypes
                        self.attack_requirements[creature.id] = AttackRequirement(
                            creature.id, destroy_if_no_attack=not is_wall
                        )
                elif isinstance(effect, BlazeOfGloryEffect):
                    if self.combat is not None:
                        self.combat.blaze_of_glory_blocker_ids.update(
                            target.id
                            for target in spell.targets
                            if isinstance(target, Card)
                        )
                elif isinstance(effect, BalanceEffect):
                    self._begin_balance()
                elif isinstance(effect, ExtraTurnEffect):
                    self.schedule_extra_turn(spell.caster_id)
                elif isinstance(effect, GlobalDamageEffect):
                    amount = effect.amount + effect.amount_per_x * spell.x_value
                    if effect.damage_players:
                        for player in self.players:
                            self._deal_damage(
                                player,
                                amount,
                                card.name,
                                source_card=card,
                                source_controller_id=spell.caster_id,
                            )
                    for player in self.players:
                        for creature in tuple(player.battlefield):
                            if CardType.CREATURE not in self.card_types(creature):
                                continue
                            has_flying = (
                                KeywordAbility.FLYING
                                in self.creature_abilities(creature)
                            )
                            if (
                                effect.creatures_with_flying is not None
                                and has_flying
                                is not effect.creatures_with_flying
                            ):
                                continue
                            self._deal_damage(
                                creature,
                                amount,
                                card.name,
                                source_card=card,
                                source_controller_id=spell.caster_id,
                            )
                elif isinstance(effect, DestroyTargetsEffect):
                    pending_destruction.extend(
                        (target, effect.regeneration_allowed)
                        for target in spell.targets
                        if isinstance(target, Card)
                    )
                elif isinstance(effect, DestroyAllEffect):
                    pending_destruction.extend(
                        (permanent, effect.regeneration_allowed)
                        for player in self.players
                        for permanent in tuple(player.battlefield)
                        if effect.matches(
                            permanent,
                            current_card_types=self.card_types(permanent),
                            current_subtypes=(
                                self.land_subtypes(permanent)
                                if CardType.LAND
                                in permanent.definition.card_types
                                else None
                            ),
                        )
                    )
                elif isinstance(effect, MoveTargetsEffect):
                    for target in spell.targets:
                        if not isinstance(target, Card):
                            continue
                        if effect.under_caster_control:
                            target.controller_id = caster.id
                        self._move_card(target, effect.destination)
                        if effect.destination is Zone.BATTLEFIELD:
                            target.entered_battlefield_turn = self.turn_number
                elif isinstance(effect, ExileTargetsEffect):
                    for target in spell.targets:
                        if not isinstance(target, Card):
                            continue
                        controller = self.player(
                            target.controller_id or target.owner_id
                        )
                        life_gain = (
                            max(0, self.creature_power(target))
                            if effect.controller_gains_life_equal_to_power
                            else 0
                        )
                        self._move_card(target, Zone.EXILE)
                        controller.life += life_gain
                elif isinstance(effect, ReverseDamageEffect):
                    if spell.damage_source_key is None:
                        continue
                    reversed_damage = sum(
                        amount
                        for _, amount in self._consume_player_damage(
                            caster.id, source_key=spell.damage_source_key
                        )
                    )
                    # Undo the loss, then gain that much life instead.
                    caster.life += reversed_damage * 2
                    if caster.life > 0:
                        caster.has_lost = False
                elif isinstance(effect, RetroactiveDamageTransferEffect):
                    target = next(
                        (item for item in spell.targets if isinstance(item, Card)),
                        None,
                    )
                    if target is None:
                        continue
                    consumed = self._consume_player_damage(caster.id)
                    caster.life += sum(amount for _, amount in consumed)
                    if caster.life > 0:
                        caster.has_lost = False
                    for record, amount in consumed:
                        self._deal_damage(
                            target,
                            amount,
                            record.source_name,
                            source_id=record.source_id,
                            source_controller_id=record.source_controller_id,
                            source_colors=record.colors,
                            combat=record.combat,
                        )
                elif isinstance(effect, SetTappedEffect):
                    tapped = spell.chosen_mode == "Tap"
                    for target in spell.targets:
                        if isinstance(target, Card):
                            if tapped:
                                self._tap_permanent(target)
                            else:
                                target.tapped = False
                elif isinstance(effect, TapLandsAndEmptyManaPoolEffect):
                    for target in spell.targets:
                        if isinstance(target, Card):
                            continue
                        for owner in self.players:
                            for permanent in tuple(owner.battlefield):
                                if (
                                    permanent.controller_id == target.id
                                    and CardType.LAND in self.card_types(permanent)
                                ):
                                    self._tap_permanent(permanent)
                        target.mana_pool.empty()

        for declared, is_legal in zip(abilities, legal_abilities):
            if not is_legal:
                continue
            if isinstance(declared.ability, ActivatedDamageAbility):
                for target in declared.targets:
                    self._deal_damage(
                        target,
                        declared.ability.damage,
                        declared.source_name,
                        source_card=declared.source,
                        source_controller_id=declared.controller_id,
                    )
                if declared.ability.controller_damage:
                    self._deal_damage(
                        self.player(declared.controller_id),
                        declared.ability.controller_damage,
                        declared.source_name,
                        source_card=declared.source,
                        source_controller_id=declared.controller_id,
                    )
            elif isinstance(declared.ability, ActivatedGlobalDamageAbility):
                damage = (
                    declared.amount * declared.ability.damage_per_payment
                )
                for player in self.players:
                    self._deal_damage(
                        player,
                        damage,
                        declared.source_name,
                        source_card=declared.source,
                        source_controller_id=declared.controller_id,
                    )
                for player in self.players:
                    for permanent in tuple(player.battlefield):
                        if CardType.CREATURE in self.card_types(permanent):
                            self._deal_damage(
                                permanent,
                                damage,
                                declared.source_name,
                                source_card=declared.source,
                                source_controller_id=declared.controller_id,
                            )
            elif isinstance(declared.ability, ActivatedDestroyAbility):
                pending_destruction.extend(
                    (target, declared.ability.regeneration_allowed)
                    for target in declared.targets
                    if isinstance(target, Card)
                )
            elif isinstance(declared.ability, ActivatedDestroyAllAbility):
                pending_destruction.extend(
                    (permanent, declared.ability.regeneration_allowed)
                    for player in self.players
                    for permanent in tuple(player.battlefield)
                    if self.card_types(permanent) & declared.ability.card_types
                )
            elif isinstance(declared.ability, ActivatedTapAbility):
                for target in declared.targets:
                    if isinstance(target, Card):
                        self._tap_permanent(target)
            elif isinstance(declared.ability, ActivatedUnblockableAbility):
                for target in declared.targets:
                    if isinstance(target, Card):
                        self.temporary_creature_effects.setdefault(
                            target.id, []
                        ).append(ContinuousEffect(unblockable=True))
            elif isinstance(declared.ability, ActivatedTemporaryAbility):
                for target in declared.targets:
                    if not isinstance(target, Card):
                        continue
                    self.temporary_creature_effects.setdefault(
                        target.id, []
                    ).append(
                        ContinuousEffect(
                            granted_abilities=declared.ability.granted_abilities
                        )
                    )
                    if declared.ability.destroy_at_end_of_turn:
                        self.destroy_at_end_of_turn.add(target.id)
            elif isinstance(declared.ability, ActivatedDrawAbility):
                self.player(declared.controller_id).draw(
                    declared.ability.amount
                )
            elif isinstance(declared.ability, ActivatedDiscardAbility):
                for target in declared.targets:
                    if not isinstance(target, Card) and target.hand:
                        self.pending_discard_choices.append(
                            PendingDiscardChoice(
                                target.id, declared.ability.amount, declared.source_name
                            )
                        )
            elif isinstance(declared.ability, ActivatedAttackRequirementAbility):
                for target in declared.targets:
                    if isinstance(target, Card):
                        self.attack_requirements[target.id] = AttackRequirement(target.id)
            elif isinstance(declared.ability, ActivatedLandTypeAbility):
                if declared.source.zone is not Zone.BATTLEFIELD:
                    continue
                for target in declared.targets:
                    if isinstance(target, Card):
                        self.battlefield_entry_sequence += 1
                        target.land_type_marks[declared.source.id] = (
                            declared.ability.replacement_subtype,
                            self.battlefield_entry_sequence,
                        )
            elif isinstance(declared.ability, ActivatedExtraTurnAbility):
                self.schedule_extra_turn(declared.controller_id)
            elif isinstance(declared.ability, ActivatedUntapAbility):
                declared.source.tapped = False
            elif isinstance(
                declared.ability, ActivatedEventLifeGainAbility
            ):
                self.player(declared.controller_id).life += (
                    declared.ability.amount
                )
            elif isinstance(declared.ability, ActivatedAnimationAbility):
                self.combat_creature_effects.setdefault(
                    declared.source.id, []
                ).append(
                    ContinuousEffect(
                        granted_card_types=frozenset({CardType.CREATURE}),
                        base_power=declared.ability.power,
                        base_toughness=declared.ability.toughness,
                    )
                )
            else:
                for target in declared.targets:
                    if isinstance(target, Card):
                        self.temporary_creature_effects.setdefault(
                            target.id, []
                        ).append(
                            ContinuousEffect(
                                power=declared.ability.power,
                                toughness=declared.ability.toughness,
                                granted_abilities=(
                                    declared.ability.granted_abilities
                                ),
                            )
                        )

        destruction_by_card: dict[Card, bool] = {}
        for card, regeneration_allowed in pending_destruction:
            destruction_by_card[card] = (
                destruction_by_card.get(card, True) and regeneration_allowed
            )
        destruction_targets = [
            DestructionTarget(
                card.id,
                card.name,
                regeneration_allowed
                and card.id not in self.disintegrated_this_turn,
            )
            for card, regeneration_allowed in destruction_by_card.items()
            if card.zone is Zone.BATTLEFIELD
        ]
        if destruction_targets:
            self.pending_destruction = DestructionIncident(destruction_targets)
        for target in pending_regeneration:
            incoming_damage = sum(
                packet.remaining
                for packet in (
                    self.pending_damage.packets
                    if self.pending_damage is not None
                    else ()
                )
                if packet.recipient_kind is DamageRecipientKind.CREATURE
                and packet.recipient_id == target.id
            )
            if (
                self.pending_damage is not None
                and target.id not in self.disintegrated_this_turn
                and self.creature_toughness(target) > 0
                and target.damage + incoming_damage
                >= self.creature_toughness(target)
            ):
                self.pending_damage.regenerated_card_ids.add(target.id)
                if self.combat is not None:
                    self.combat.regenerated_card_ids.add(target.id)
            if self.pending_destruction is not None:
                matching = next(
                    (
                        item
                        for item in self.pending_destruction.targets
                        if item.card_id == target.id
                    ),
                    None,
                )
                if matching is not None and matching.regeneration_allowed:
                    self.pending_destruction.regenerated_card_ids.add(target.id)
                    self._tap_permanent(target)
                    target.damage = 0
        self._resolve_damage_incident()
        if self.pending_damage is None:
            self._open_destruction_incident()

        for spell in spells:
            card = spell.card
            self.stack_spells.pop(card.id, None)
            if card.zone is Zone.STACK:
                self._move_card(card, Zone.GRAVEYARD)
        self.batch_abilities.clear()
        self.check_state_based_actions()
        self._close_event_opportunities(caught_event_ids)
        return cards

    def _resolve_spell_effects(
        self,
        card: Card,
        targets: tuple[Card | PlayerState, ...],
        caster: PlayerState,
    ) -> None:
        for effect in card.definition.spell_effects:
            if isinstance(effect, DamageEffect):
                recipients: tuple[Card | PlayerState, ...]
                if effect.recipient is EffectRecipient.CASTER:
                    recipients = (caster,)
                else:
                    recipients = targets
                for recipient in recipients:
                    if (
                        effect.disintegrates_target
                        and isinstance(recipient, Card)
                    ):
                        self.disintegrated_this_turn.add(recipient.id)
                    self._deal_damage(
                        recipient,
                        effect.amount,
                        card.name,
                        source_card=card,
                        source_controller_id=caster.id,
                    )
            elif isinstance(effect, DestroyTargetsEffect):
                self._destroy_permanents(
                    target for target in targets if isinstance(target, Card)
                )
            elif isinstance(effect, DestroyAllEffect):
                self._destroy_permanents(
                    permanent
                    for player in self.players
                    for permanent in tuple(player.battlefield)
                    if effect.matches(
                        permanent,
                        current_card_types=self.card_types(permanent),
                        current_subtypes=(
                            self.land_subtypes(permanent)
                            if CardType.LAND
                            in permanent.definition.card_types
                            else None
                        ),
                    )
                )
            elif isinstance(effect, MoveTargetsEffect):
                for target in targets:
                    if not isinstance(target, Card):
                        continue
                    if effect.under_caster_control:
                        target.controller_id = caster.id
                    self._move_card(target, effect.destination)
                    if effect.destination is Zone.BATTLEFIELD:
                        target.entered_battlefield_turn = self.turn_number
            elif isinstance(effect, ExileTargetsEffect):
                for target in targets:
                    if not isinstance(target, Card):
                        continue
                    controller = self.player(
                        target.controller_id or target.owner_id
                    )
                    life_gain = (
                        max(0, self.creature_power(target))
                        if effect.controller_gains_life_equal_to_power
                        else 0
                    )
                    self._move_card(target, Zone.EXILE)
                    controller.life += life_gain

