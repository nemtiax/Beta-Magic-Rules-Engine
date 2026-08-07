"""Turn progression and mandatory timed-event handling."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING
from uuid import UUID

from .cards import Card
from .damage import DamageIncidentKind
from .destruction import DestructionIncident, DestructionTarget
from .effects import (
    OptionalUpkeepPaymentEffect,
    UpkeepBenefit,
    UpkeepCostEffect,
    UpkeepDamageEffect,
    UpkeepDamageRecipient,
    UpkeepEffect,
    UpkeepFailure,
    UpkeepCreatureSacrificeEffect,
    UntapRestrictionEffect,
)
from .events import ManaBurnEvent
from .types import CardType, GameStatus, TurnPhase, Zone

if TYPE_CHECKING:
    from .game import PlayerState


@dataclass(slots=True)
class PendingTimedEvent:
    """A mandatory turn event waiting for a response window to close."""

    source_id: UUID
    source_name: str
    affected_player_id: str
    affected_player_name: str
    effect: UpkeepEffect
    attached_permanent_id: UUID | None = None
    payment_decision: bool | None = None

    @property
    def label(self) -> str:
        if isinstance(self.effect, OptionalUpkeepPaymentEffect):
            benefit = (
                f"gain {self.effect.amount} life"
                if self.effect.benefit is UpkeepBenefit.GAIN_LIFE
                else "untap the enchanted permanent"
            )
            return (
                f"{self.source_name}: pay {self.effect.mana_cost.compact} "
                f"to {benefit}"
            )
        if isinstance(self.effect, UpkeepCostEffect):
            consequence = (
                f"take {self.effect.damage} damage"
                if self.effect.failure is UpkeepFailure.DAMAGE_CONTROLLER
                else "tap it and let your opponent choose a land you lose"
                if self.effect.failure
                is UpkeepFailure.TAP_SOURCE_AND_OPPONENT_CHOOSES_LAND
                else "destroy it"
            )
            return (
                f"{self.source_name}: pay {self.effect.mana_cost.compact} "
                f"or {consequence}"
            )
        if isinstance(self.effect, UpkeepCreatureSacrificeEffect):
            return (
                f"{self.source_name}: sacrifice another eligible creature "
                f"or take {self.effect.damage} damage"
            )
        return (
            f"{self.source_name}: {self.effect.amount} damage to "
            f"{self.affected_player_name}"
        )


@dataclass(slots=True)
class PendingTurnChoice:
    """A player may give up their upcoming turn to ready one Time Vault."""

    player_id: str
    player_name: str
    vault_ids: tuple[UUID, ...]


@dataclass(slots=True)
class PendingUntapChoice:
    """The active player must choose permanents allowed by capped untap rules."""

    player_id: str
    eligible_ids: frozenset[UUID]
    caps: tuple[tuple[CardType, int], ...]
    selected_ids: set[UUID]
    category_index: int = 0

    @property
    def card_type(self) -> CardType:
        return self.caps[self.category_index][0]

    @property
    def maximum(self) -> int:
        return self.caps[self.category_index][1]


@dataclass(slots=True)
class PendingUpkeepLandLossChoice:
    """An opponent must choose a land lost to a declined upkeep."""

    chooser_id: str
    affected_player_id: str
    source_name: str
    candidate_ids: frozenset[UUID]


class TurnFlowMixin:
    """Run turns, phase boundaries, cleanup, and mandatory timed events."""

    __slots__ = ()

    def choose_untap_cards(self, player_id: str, cards: tuple[Card, ...]) -> None:
        """Choose the permanents to untap for the currently capped category."""

        choice = self.pending_untap_choice
        if choice is None:
            raise RuntimeError("there is no pending untap choice")
        if choice.player_id != player_id:
            raise RuntimeError(f"{self.player(choice.player_id).name} must choose")
        legal = self._legal_current_untap_ids(choice)
        already = self._selected_untap_count(choice, choice.card_type)
        required = min(choice.maximum - already, len(legal))
        ids = {card.id for card in cards}
        if len(ids) != len(cards) or len(ids) != required:
            raise ValueError(f"choose exactly {required} permanent(s) to untap")
        if not ids <= legal:
            raise ValueError("one or more selected permanents cannot be untapped")
        choice.selected_ids.update(ids)
        choice.category_index += 1
        self._continue_untap_choices()

    def _selected_untap_count(
        self, choice: PendingUntapChoice, card_type: CardType
    ) -> int:
        return sum(
            card_type in self.card_types(card)
            for card in self._battlefield_cards()
            if card.id in choice.selected_ids
        )

    def _legal_current_untap_ids(self, choice: PendingUntapChoice) -> set[UUID]:
        current_type = choice.card_type
        return {
            card.id
            for card in self._battlefield_cards()
            if card.id in choice.eligible_ids
            and card.id not in choice.selected_ids
            and current_type in self.card_types(card)
            and all(
                card_type not in self.card_types(card)
                or self._selected_untap_count(choice, card_type) < maximum
                for card_type, maximum in choice.caps
            )
        }

    def _continue_untap_choices(self) -> None:
        choice = self.pending_untap_choice
        assert choice is not None
        while choice.category_index < len(choice.caps):
            legal = self._legal_current_untap_ids(choice)
            remaining = max(
                0,
                choice.maximum
                - self._selected_untap_count(choice, choice.card_type),
            )
            if len(legal) > remaining:
                return
            choice.selected_ids.update(legal)
            choice.category_index += 1
        for card in self._battlefield_cards():
            if card.id in choice.selected_ids:
                card.tapped = False
        self.pending_untap_choice = None
        self._finish_untap_processing()

    def _battlefield_cards(self) -> tuple[Card, ...]:
        return tuple(card for player in self.players for card in player.battlefield)

    def _finish_untap_processing(self) -> None:
        owed_vaults = self.vaults_untapping_next_turn.pop(
            self.active_player.id, set()
        )
        for permanent in self._battlefield_cards():
            if permanent.id in owed_vaults:
                permanent.tapped = False
        self.check_state_based_actions()

    def propose_phase_advance(self) -> TurnPhase:
        """Declare the active player done and give the opponent a response."""

        self._require_no_pending_action()
        if self.status is not GameStatus.IN_PROGRESS or self.current_phase is None:
            raise RuntimeError("phases can only advance during a game")
        if self.combat is not None:
            raise RuntimeError("finish the current attack before leaving the Main phase")
        if self.current_phase is TurnPhase.UNTAP:
            return self.advance_phase()
        if (
            self.current_phase is TurnPhase.DISCARD
            and self.active_player.discard_required
        ):
            raise RuntimeError(
                f"{self.active_player.name} must discard "
                f"{self.active_player.discard_required} card(s)"
            )
        self.pending_phase_advance = self.current_phase
        self.priority_player_index = (
            self.active_player_index + 1
        ) % len(self.players)
        # Clicking Advance is the active player's first pass. If the opponent
        # acts, ordinary spell/ability declaration resets this count to zero.
        self.consecutive_passes = 1
        return self.current_phase

    def start(self, *, opening_hand_size: int = 7, shuffle: bool = True) -> None:
        if self.status is not GameStatus.NOT_STARTED:
            raise RuntimeError("the game has already started")
        if opening_hand_size < 0:
            raise ValueError("opening hand size cannot be negative")
        if shuffle:
            for player in self.players:
                player.shuffle_library()
        for player in self.players:
            player.draw(opening_hand_size)
        self.turn_number = 1
        self.next_natural_player_index = (
            self.active_player_index + 1
        ) % len(self.players)
        self.status = GameStatus.IN_PROGRESS
        self.lands_played_this_turn = 0
        self.attacks_this_turn = 0
        self.attack_requirements.clear()
        self.attacked_this_turn.clear()
        self._enter_phase(TurnPhase.UNTAP)

    def next_turn(self) -> PlayerState:
        self._require_no_pending_action()
        if self.status is not GameStatus.IN_PROGRESS:
            raise RuntimeError("turns can only advance during a game")
        if self.current_phase is not TurnPhase.END:
            raise RuntimeError("a new turn can only begin after the End phase")
        self._empty_mana_pools()
        self._finish_turn_effects()
        if self.pending_destruction is not None:
            return self.active_player
        self._clear_creature_damage()
        self.vampire_damage_marks.clear()
        self.player_damage_history.clear()
        self.temporary_creature_effects.clear()
        self.ability_activations_this_turn.clear()
        self.disintegrated_this_turn.clear()
        self.upkeep_payments_this_turn.clear()
        self.check_state_based_actions()
        self._offer_vault_skip_or_begin_turn()
        return self.active_player

    def schedule_extra_turn(self, player_id: str) -> None:
        """Put a newly created turn immediately after the current turn."""

        self.player(player_id)
        self.upcoming_turns.insert(0, player_id)

    def _peek_upcoming_turn(self) -> tuple[str, bool]:
        if self.upcoming_turns:
            return self.upcoming_turns[0], True
        return self.players[self.next_natural_player_index].id, False

    def _consume_upcoming_turn(self, extra: bool) -> None:
        if extra:
            self.upcoming_turns.pop(0)
        else:
            self.next_natural_player_index = (
                self.next_natural_player_index + 1
            ) % len(self.players)

    def _offer_vault_skip_or_begin_turn(self) -> None:
        player_id, extra = self._peek_upcoming_turn()
        player = self.player(player_id)
        already_owed = self.vaults_untapping_next_turn.get(player_id, set())
        vaults = tuple(
            card.id
            for owner in self.players
            for card in owner.battlefield
            if card.controller_id == player_id
            and card.definition.may_skip_turn_to_untap
            and card.tapped
            and card.id not in already_owed
        )
        if vaults:
            self.pending_turn_choice = PendingTurnChoice(
                player_id, player.name, vaults
            )
            return
        self._consume_upcoming_turn(extra)
        self._begin_scheduled_turn(player_id)

    def choose_time_vault_skip(
        self, player_id: str, vault: Card | None
    ) -> PlayerState:
        """Take the offered turn, or skip it to ready one chosen Vault later."""

        choice = self.pending_turn_choice
        if choice is None:
            raise RuntimeError("there is no upcoming-turn choice")
        if choice.player_id != player_id:
            raise RuntimeError(f"{choice.player_name} must make this choice")
        scheduled_player_id, extra = self._peek_upcoming_turn()
        if scheduled_player_id != player_id:
            raise RuntimeError("the upcoming turn has changed")
        if vault is not None and (
            vault.id not in choice.vault_ids
            or vault.zone is not Zone.BATTLEFIELD
            or vault.controller_id != player_id
            or not vault.tapped
        ):
            raise ValueError("that Time Vault cannot be readied by this skipped turn")
        self.pending_turn_choice = None
        self._consume_upcoming_turn(extra)
        if vault is None:
            self._begin_scheduled_turn(player_id)
            return self.active_player
        self.vaults_untapping_next_turn.setdefault(player_id, set()).add(
            vault.id
        )
        self._offer_vault_skip_or_begin_turn()
        return self.active_player

    def _begin_scheduled_turn(self, player_id: str) -> None:
        self.active_player_index = self.players.index(self.player(player_id))
        self.turn_number += 1
        self.lands_played_this_turn = 0
        self.attacks_this_turn = 0
        self.attack_requirements.clear()
        self.attacked_this_turn.clear()
        self._enter_phase(TurnPhase.UNTAP)

    def _finish_turn_effects(self) -> None:
        """Resolve delayed end-of-turn destruction before cleanup."""

        doomed_ids = tuple(self.destroy_at_end_of_turn)
        doomed = (
            card
            for player in self.players
            for card in tuple(player.battlefield)
            if card.id in doomed_ids
        )
        self._destroy_permanents(doomed)
        self.destroy_at_end_of_turn.clear()
        no_creatures = not any(
            CardType.CREATURE in self.card_types(permanent)
            for player in self.players
            for permanent in player.battlefield
        )
        if no_creatures:
            conditional = (
                permanent
                for player in self.players
                for permanent in tuple(player.battlefield)
                if permanent.definition.destroy_at_end_of_turn_if_no_creatures
            )
            self._destroy_permanents(conditional)
        failed_ids = {
            card_id
            for card_id, requirement in self.attack_requirements.items()
            if requirement.destroy_if_no_attack
            and card_id not in self.attacked_this_turn
        }
        self.attack_requirements.clear()
        failed = [
            card
            for player in self.players
            for card in player.battlefield
            if card.id in failed_ids
        ]
        if failed:
            self.pending_destruction = DestructionIncident(
                [DestructionTarget(card.id, card.name, True) for card in failed]
            )
            self._open_destruction_incident()

    def can_pay_upkeep_cost(self, player_id: str) -> bool:
        """Whether the current event offers an affordable upkeep payment."""

        if (
            not self.timed_events
            or self.stack
            or self.priority_player_index is None
            or self.players[self.priority_player_index].id != player_id
        ):
            return False
        event = self.timed_events[0]
        return bool(
            isinstance(
                event.effect,
                (UpkeepCostEffect, OptionalUpkeepPaymentEffect),
            )
            and event.affected_player_id == player_id
            and event.payment_decision is None
            and self._timed_event_source(event) is not None
            and self.can_pay_mana(self.player(player_id), event.effect.mana_cost)
        )

    @property
    def upkeep_payment_required(self) -> bool:
        """Whether the current timed event still needs an explicit choice."""

        return (
            not self.stack
            and not self.batch_abilities
            and self._timed_event_needs_payment()
        )

    def choose_upkeep_payment(self, player_id: str, *, pay: bool) -> None:
        """Pay or decline the current mandatory upkeep choice."""

        if not self.timed_events or self.stack:
            raise RuntimeError("there is no upkeep payment waiting for a choice")
        event = self.timed_events[0]
        if not isinstance(
            event.effect, (UpkeepCostEffect, OptionalUpkeepPaymentEffect)
        ):
            raise RuntimeError("the current timed event has no upkeep payment")
        if event.payment_decision is not None:
            raise RuntimeError("the upkeep payment has already been decided")
        player = self.player(player_id)
        if event.affected_player_id != player.id:
            raise RuntimeError("only the affected player chooses this upkeep payment")
        if (
            self.priority_player_index is None
            or self.players[self.priority_player_index] is not player
        ):
            priority_name = (
                self.players[self.priority_player_index].name
                if self.priority_player_index is not None
                else "No player"
            )
            raise RuntimeError(f"{priority_name} has priority")
        if self._timed_event_source(event) is None:
            raise RuntimeError("the upkeep source is no longer in play")
        if pay:
            self.pay_mana(player, event.effect.mana_cost)
            if (
                isinstance(event.effect, UpkeepCostEffect)
                and event.effect.failure
                is UpkeepFailure.TAP_SOURCE_AND_OPPONENT_CHOOSES_LAND
            ):
                self.unpaid_tap_upkeep_ids.discard(event.source_id)
        event.payment_decision = pay
        self.priority_player_index = (
            self.players.index(player) + 1
        ) % len(self.players)
        self.consecutive_passes = 0

    def legal_upkeep_sacrifices(self, player_id: str) -> list[Card]:
        """Eligible mandatory sacrifices for Lord-of-the-Pit-style upkeep."""

        if not self.timed_events:
            return []
        event = self.timed_events[0]
        if (
            not isinstance(event.effect, UpkeepCreatureSacrificeEffect)
            or event.affected_player_id != player_id
            or event.payment_decision is not None
        ):
            return []
        source = self._timed_event_source(event)
        if source is None:
            return []
        player = self.player(player_id)
        source_colors = self.card_colors(source)
        return [
            creature
            for creature in player.battlefield
            if creature is not source
            and CardType.CREATURE in self.card_types(creature)
            and not self._is_protected_from(creature, source_colors)
        ]

    def choose_upkeep_land_loss(self, player_id: str, land: Card) -> None:
        """Choose the land lost after Demonic-Hordes-style upkeep failure."""

        choice = self.pending_upkeep_land_loss
        if choice is None:
            raise RuntimeError("there is no pending upkeep land choice")
        if choice.chooser_id != player_id:
            raise RuntimeError(
                f"{self.player(choice.chooser_id).name} must choose the land"
            )
        if (
            land.id not in choice.candidate_ids
            or land.zone is not Zone.BATTLEFIELD
            or land.controller_id != choice.affected_player_id
            or CardType.LAND not in self.card_types(land)
        ):
            raise ValueError("that land cannot be chosen")
        self.pending_upkeep_land_loss = None
        self._move_card(land, Zone.GRAVEYARD)
        self.check_state_based_actions()

    def choose_upkeep_sacrifice(self, player_id: str, creature: Card) -> None:
        """Sacrifice the selected creature as the mandatory upkeep payment."""

        if not self.timed_events:
            raise RuntimeError("there is no upkeep sacrifice waiting for a choice")
        event = self.timed_events[0]
        if not isinstance(event.effect, UpkeepCreatureSacrificeEffect):
            raise RuntimeError("the current upkeep event does not sacrifice a creature")
        player = self.player(player_id)
        if (
            self.priority_player_index is None
            or self.players[self.priority_player_index] is not player
        ):
            raise RuntimeError("that player does not have priority")
        if creature not in self.legal_upkeep_sacrifices(player_id):
            raise ValueError("that creature cannot be sacrificed for this upkeep")
        self._move_card(creature, Zone.GRAVEYARD)
        event.payment_decision = True
        self.priority_player_index = (
            self.players.index(player) + 1
        ) % len(self.players)
        self.consecutive_passes = 0

    def _timed_event_source(self, event: PendingTimedEvent) -> Card | None:
        return next(
            (
                permanent
                for player in self.players
                for permanent in player.battlefield
                if permanent.id == event.source_id
            ),
            None,
        )

    def _timed_event_needs_payment(self) -> bool:
        if not self.timed_events:
            return False
        event = self.timed_events[0]
        if isinstance(event.effect, UpkeepCreatureSacrificeEffect):
            return bool(
                event.payment_decision is None
                and self._timed_event_source(event) is not None
                and self.legal_upkeep_sacrifices(event.affected_player_id)
            )
        return bool(
            isinstance(
                event.effect,
                (UpkeepCostEffect, OptionalUpkeepPaymentEffect),
            )
            and event.payment_decision is None
            and self._timed_event_source(event) is not None
        )

    def _resolve_timed_event(self) -> None:
        """Resolve the first mandatory event after its response window closes."""

        event = self.timed_events.pop(0)
        source = self._timed_event_source(event)
        if source is None:
            return
        if isinstance(event.effect, UpkeepCostEffect):
            if event.payment_decision:
                return
            if (
                event.effect.failure
                is UpkeepFailure.TAP_SOURCE_AND_OPPONENT_CHOOSES_LAND
            ):
                self._tap_permanent(source)
                lands = frozenset(
                    permanent.id
                    for player in self.players
                    for permanent in player.battlefield
                    if permanent.controller_id == event.affected_player_id
                    and CardType.LAND in self.card_types(permanent)
                )
                if lands:
                    affected_index = self.players.index(
                        self.player(event.affected_player_id)
                    )
                    chooser = self.players[
                        (affected_index + 1) % len(self.players)
                    ]
                    self.pending_upkeep_land_loss = PendingUpkeepLandLossChoice(
                        chooser.id,
                        event.affected_player_id,
                        event.source_name,
                        lands,
                    )
                self.check_state_based_actions()
                return
            if event.effect.failure is UpkeepFailure.DESTROY_SOURCE:
                self._move_card(source, Zone.GRAVEYARD)
            else:
                affected_player = self.player(event.affected_player_id)
                self._begin_damage_incident(DamageIncidentKind.TIMED_EVENT)
                self._deal_damage(
                    affected_player,
                    event.effect.damage,
                    event.source_name,
                    source_card=source,
                )
                self._resolve_damage_incident()
            self.check_state_based_actions()
            return
        if isinstance(event.effect, UpkeepCreatureSacrificeEffect):
            if event.payment_decision:
                return
            affected_player = self.player(event.affected_player_id)
            self._begin_damage_incident(DamageIncidentKind.TIMED_EVENT)
            self._deal_damage(
                affected_player,
                event.effect.damage,
                event.source_name,
                source_card=source,
            )
            self._resolve_damage_incident()
            self.check_state_based_actions()
            return
        if isinstance(event.effect, OptionalUpkeepPaymentEffect):
            if not event.payment_decision:
                return
            if event.effect.benefit is UpkeepBenefit.GAIN_LIFE:
                self.player(event.affected_player_id).life += event.effect.amount
                return
            assert event.attached_permanent_id is not None
            self.upkeep_payments_this_turn.add(event.source_id)
            attached = next(
                (
                    permanent
                    for player in self.players
                    for permanent in player.battlefield
                    if permanent.id == event.attached_permanent_id
                ),
                None,
            )
            if attached is None:
                return
            matching_sources = {
                permanent.id
                for player in self.players
                for permanent in player.battlefield
                if permanent.enchanted_card_id == attached.id
                and any(
                    isinstance(effect, OptionalUpkeepPaymentEffect)
                    and effect.benefit is UpkeepBenefit.UNTAP_ATTACHED
                    and effect.require_all_matching_attachments
                    for effect in permanent.definition.upkeep_effects
                )
            }
            if (
                not event.effect.require_all_matching_attachments
                or matching_sources <= self.upkeep_payments_this_turn
            ):
                attached.tapped = False
            return
        if (
            source.tapped
            and CardType.ARTIFACT in source.definition.card_types
            and event.effect.source_tapped is not True
        ):
            return
        if event.effect.source_tapped is True and not source.tapped:
            return
        if event.attached_permanent_id is not None:
            attached = next(
                (
                    permanent
                    for player in self.players
                    for permanent in player.battlefield
                    if permanent.id == event.attached_permanent_id
                ),
                None,
            )
            if (
                attached is None
                or source.enchanted_card_id != attached.id
                or attached.controller_id != event.affected_player_id
            ):
                return
        affected_player = self.player(event.affected_player_id)
        self._begin_damage_incident(DamageIncidentKind.TIMED_EVENT)
        self._deal_damage(
            affected_player,
            event.effect.amount,
            event.source_name,
            source_card=source,
        )
        self._resolve_damage_incident()
        self.check_state_based_actions()

    def discard(self, card: Card) -> None:
        """Discard one chosen card when the active player is required to."""

        self._require_no_pending_action()
        if self.status is not GameStatus.IN_PROGRESS:
            raise RuntimeError("cards can only be discarded during a game")
        if self.current_phase is not TurnPhase.DISCARD:
            raise RuntimeError("turn-based discarding occurs during the Discard phase")
        if not self.active_player.discard_required:
            raise RuntimeError("the active player is not required to discard")
        if card not in self.active_player.hand:
            raise ValueError(f"{card.name} is not in the active player's hand")
        self._move_card(card, Zone.GRAVEYARD)

    def advance_phase(self) -> TurnPhase:
        """Finish the current phase and enter the next one.

        Advancing from End begins the next player's turn. The engine performs
        the mandatory, choice-free Untap and Draw actions on entering those
        phases. A player with more than seven cards must explicitly choose
        discards before leaving the Discard phase.
        """

        self._require_no_pending_action()
        if self.status is not GameStatus.IN_PROGRESS or self.current_phase is None:
            raise RuntimeError("phases can only advance during a game")
        if self.combat is not None:
            raise RuntimeError("finish the current attack before leaving the Main phase")
        if (
            self.current_phase is TurnPhase.DISCARD
            and self.active_player.discard_required
        ):
            raise RuntimeError(
                f"{self.active_player.name} must discard "
                f"{self.active_player.discard_required} card(s)"
            )

        next_phase = self.current_phase.next
        if next_phase is None:
            self.next_turn()
        else:
            self._empty_mana_pools()
            self._enter_phase(next_phase)
        assert self.current_phase is not None
        return self.current_phase

    def _enter_phase(self, phase: TurnPhase) -> None:
        self.current_phase = phase
        if phase is TurnPhase.UNTAP:
            for player in self.players:
                for permanent in player.battlefield:
                    permanent.controller_at_turn_start_id = (
                        permanent.controller_id
                    )
            restrictions: list[UntapRestrictionEffect] = []
            for source in self._battlefield_cards():
                if self.continuous_permanent_is_active(source):
                    restrictions.extend(source.definition.untap_effects)
            if any(effect.skip_untap for effect in restrictions):
                # The scheduled Time Vault untap is also lost when there is no
                # untap phase at all.
                self.vaults_untapping_next_turn.pop(self.active_player.id, None)
                self.check_state_based_actions()
                return
            power_ceiling = min(
                (
                    effect.maximum_creature_power
                    for effect in restrictions
                    if effect.maximum_creature_power is not None
                ),
                default=None,
            )
            eligible = {
                permanent.id
                for permanent in self._battlefield_cards()
                if permanent.controller_id == self.active_player.id
                and permanent.tapped
                and self.untaps_during_untap(permanent)
                and not (
                    power_ceiling is not None
                    and CardType.CREATURE in self.card_types(permanent)
                    and self.creature_power(permanent) > power_ceiling
                )
            }
            caps_by_type: dict[CardType, int] = {}
            for effect in restrictions:
                if effect.maximum_untaps is not None:
                    assert effect.card_type is not None
                    caps_by_type[effect.card_type] = min(
                        caps_by_type.get(effect.card_type, effect.maximum_untaps),
                        effect.maximum_untaps,
                    )
            capped_ids = {
                permanent.id
                for permanent in self._battlefield_cards()
                if permanent.id in eligible
                and any(kind in self.card_types(permanent) for kind in caps_by_type)
            }
            selected = eligible - capped_ids
            if caps_by_type:
                self.pending_untap_choice = PendingUntapChoice(
                    self.active_player.id,
                    frozenset(eligible),
                    tuple(caps_by_type.items()),
                    set(selected),
                )
                self._continue_untap_choices()
                if self.pending_untap_choice is not None:
                    return
            else:
                for permanent in self._battlefield_cards():
                    if permanent.id in selected:
                        permanent.tapped = False
                self._finish_untap_processing()
                return
        elif phase is TurnPhase.UPKEEP:
            self._queue_upkeep_events()
        elif phase is TurnPhase.DRAW:
            self.active_player.draw()
            for owner in self.players:
                for source in tuple(owner.battlefield):
                    if not self.continuous_permanent_is_active(source):
                        continue
                    for effect in source.definition.draw_phase_effects:
                        self.active_player.draw(effect.amount)

    def _queue_upkeep_events(self) -> None:
        """Collect mandatory upkeep events and open the first response window."""

        battlefield = [
            permanent
            for player in self.players
            for permanent in player.battlefield
        ]
        self.timed_events = []
        for source in battlefield:
            for effect in source.definition.upkeep_effects:
                if isinstance(effect, UpkeepDamageEffect):
                    if (
                        effect.controller_upkeep_only
                        and source.controller_id != self.active_player.id
                    ):
                        continue
                    if effect.source_tapped is True and not source.tapped:
                        continue
                    if effect.source_tapped is False and source.tapped:
                        continue
                    if effect.counted_active_player_owned_land_subtype:
                        land_count = sum(
                            1
                            for permanent in battlefield
                            if permanent.owner_id == self.active_player.id
                            and CardType.LAND in self.card_types(permanent)
                            and effect.counted_active_player_owned_land_subtype
                            in self.land_subtypes(permanent)
                        )
                        if not land_count:
                            continue
                        effect = replace(
                            effect,
                            amount=effect.amount * land_count,
                        )
                if (
                    source.tapped
                    and CardType.ARTIFACT in source.definition.card_types
                    and isinstance(effect, UpkeepDamageEffect)
                    and effect.source_tapped is not True
                ):
                    continue
                attached = None
                if (
                    isinstance(effect, UpkeepDamageEffect)
                    and effect.recipient
                    is UpkeepDamageRecipient.ATTACHED_PERMANENT_CONTROLLER
                ):
                    attached = next(
                        (
                            permanent
                            for permanent in battlefield
                            if permanent.id == source.enchanted_card_id
                        ),
                        None,
                    )
                    if (
                        attached is None
                        or attached.controller_id != self.active_player.id
                    ):
                        continue
                elif (
                    isinstance(effect, UpkeepCostEffect)
                    and source.controller_id != self.active_player.id
                ):
                    continue
                elif (
                    isinstance(effect, UpkeepCreatureSacrificeEffect)
                    and source.controller_id != self.active_player.id
                ):
                    continue
                elif isinstance(effect, OptionalUpkeepPaymentEffect):
                    attached = next(
                        (
                            permanent
                            for permanent in battlefield
                            if permanent.id == source.enchanted_card_id
                        ),
                        None,
                    )
                    if effect.attached_permanent_controller:
                        if (
                            attached is None
                            or attached.controller_id != self.active_player.id
                        ):
                            continue
                    elif source.controller_id != self.active_player.id:
                        continue
                if (
                    isinstance(effect, UpkeepCostEffect)
                    and effect.failure
                    is UpkeepFailure.TAP_SOURCE_AND_OPPONENT_CHOOSES_LAND
                ):
                    self.unpaid_tap_upkeep_ids.add(source.id)
                self.timed_events.append(
                    PendingTimedEvent(
                        source_id=source.id,
                        source_name=source.name,
                        affected_player_id=self.active_player.id,
                        affected_player_name=self.active_player.name,
                        effect=effect,
                        attached_permanent_id=attached.id if attached else None,
                    )
                )
        if self.timed_events:
            self.priority_player_index = self.active_player_index
            self.consecutive_passes = 0

    def _clear_creature_damage(self) -> None:
        for player in self.players:
            for card in player.battlefield:
                card.damage = 0

    def _empty_mana_pools(self) -> None:
        """Empty every pool and apply Beta's mana burn rule."""

        for player in self.players:
            mana_burn = player.mana_pool.empty()
            player.life -= mana_burn
            if mana_burn:
                self.events.append(ManaBurnEvent(player.id, mana_burn))
            if player.life <= 0:
                player.has_lost = True
