"""Priority, interrupt, and fast-effect batch resolution for GameState."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Iterable
from uuid import UUID, uuid4

from .abilities import (
    ActivatedManaAbility,
    ActivatedCounterSpellAbility,
    ActivatedAnimationAbility,
    ActivatedAttackRequirementAbility,
    ActivatedDamageAbility,
    ActivatedGlobalDamageAbility,
    ActivatedDestroyAbility,
    ActivatedDestroyAllAbility,
    ActivatedDiscardAbility,
    ActivatedDrawAbility,
    ActivatedCreateTokenAbility,
    ActivatedGraveyardReturnAbility,
    ActivatedRevealHandAbility,
    ActivatedEventDrawAbility,
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
from .casting import SpellOnStack
from .combat import AttackRequirement, PendingFalseOrdersChoice
from .damage import DamageIncidentKind, DamageRecipientKind
from .destruction import DestructionIncident, DestructionTarget
from .effects import (
    AddManaEffect,
    BalanceEffect,
    ChangeTargetColorEffect,
    ChangeTextWordEffect,
    ChannelEffect,
    ContinuousEffect,
    CounterTargetSpellEffect,
    CopyTargetSpellEffect,
    DamageEffect,
    DividedDamageEffect,
    DrainLifeEffect,
    DestroyAllEffect,
    DestroyTargetsEffect,
    DiscardCardsEffect,
    DiscardHandsAndDrawEffect,
    DiscardHandAnteAndDrawEffect,
    DemonicAttorneyEffect,
    NaturalSelectionEffect,
    LibrarySearchEffect,
    SacrificeCreatureForManaEffect,
    DrawCardsEffect,
    EffectRecipient,
    ExileTargetsEffect,
    ExtraTurnEffect,
    GainLifeEffect,
    GlobalDamageEffect,
    MoveTargetsEffect,
    PreventCombatDamageEffect,
    RegenerateTargetsEffect,
    RetroactiveDamageTransferEffect,
    ReverseDamageEffect,
    SetTappedEffect,
    ShuffleHandAndGraveyardEffect,
    SirensCallEffect,
    BlazeOfGloryEffect,
    FalseOrdersEffect,
    TemporaryPumpEffect,
    TapLandsAndEmptyManaPoolEffect,
    SwapLibraryTopWithAnteEffect,
)
from .mana import ManaCost
from .types import CardType, Color, CombatStep, KeywordAbility, Zone

if TYPE_CHECKING:
    from .game import PlayerState


@dataclass(slots=True)
class PendingDiscardChoice:
    player_id: str
    amount: int
    source_name: str


@dataclass(slots=True)
class PendingLibraryDiscardChoice:
    """An affected player assigns forced discards with Library of Leng."""

    player_id: str
    card_ids: tuple[UUID, ...]
    source_name: str
    library_ids_bottom_to_top: list[UUID] = field(default_factory=list)
    draw_after: int = 0
    ante_after: bool = False


@dataclass(frozen=True, slots=True)
class CyclopeanTombMark:
    id: UUID
    effect_id: UUID
    land_id: UUID
    sequence: int
    land_subtype: str


@dataclass(frozen=True, slots=True)
class PendingTombCleanupChoice:
    player_id: str
    effect_id: UUID
    mark_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class PendingDrainPowerChoice:
    caster_id: str
    land_id: UUID
    land_name: str
    mana_options: tuple[tuple[Color, int], ...]


@dataclass(slots=True)
class PendingPowerSinkPayment:
    target: Card
    payer_id: str
    remaining: int


@dataclass(frozen=True, slots=True)
class PendingDemonicAttorneyChoice:
    caster_id: str
    opponent_id: str


@dataclass(slots=True)
class PendingNaturalSelectionChoice:
    chooser_id: str
    target_player_id: str
    card_ids_top_first: list[UUID]


@dataclass(frozen=True, slots=True)
class PendingLibrarySearchChoice:
    chooser_id: str
    library_player_id: str
    source_name: str
    card_types: frozenset[CardType]
    destination: Zone



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

    def choose_demonic_attorney(self, player_id: str, *, concede: bool) -> None:
        """Resolve the opponent's choice after Demonic Attorney resolves."""

        if not self.pending_demonic_attorney_choices:
            raise RuntimeError("there is no Demonic Attorney choice pending")
        choice = self.pending_demonic_attorney_choices[0]
        if player_id != choice.opponent_id:
            raise ValueError("only the caster's opponent may make this choice")
        self.pending_demonic_attorney_choices.pop(0)
        if concede:
            self.concede(player_id)
            return
        for player in self.players:
            if not player.library:
                player.has_lost = True
                continue
            card = player.library.pop()
            card.zone = Zone.ANTE
            player.ante.append(card)
        self.check_state_based_actions()

    def move_natural_selection_card(
        self, player_id: str, card_id: UUID, delta: int
    ) -> None:
        """Move one inspected card one position in the proposed order."""

        if not self.pending_natural_selection_choices:
            raise RuntimeError("there is no Natural Selection choice pending")
        choice = self.pending_natural_selection_choices[0]
        if player_id != choice.chooser_id:
            raise ValueError("only the Natural Selection caster may reorder cards")
        if delta not in {-1, 1}:
            raise ValueError("cards may only move one position at a time")
        try:
            index = choice.card_ids_top_first.index(card_id)
        except ValueError as error:
            raise ValueError("that card is not among the inspected cards") from error
        destination = index + delta
        if not 0 <= destination < len(choice.card_ids_top_first):
            return
        choice.card_ids_top_first[index], choice.card_ids_top_first[destination] = (
            choice.card_ids_top_first[destination],
            choice.card_ids_top_first[index],
        )

    def choose_natural_selection(self, player_id: str, *, shuffle: bool) -> None:
        """Commit the proposed top-three order or shuffle the target library."""

        if not self.pending_natural_selection_choices:
            raise RuntimeError("there is no Natural Selection choice pending")
        choice = self.pending_natural_selection_choices[0]
        if player_id != choice.chooser_id:
            raise ValueError("only the Natural Selection caster may decide")
        target = self.player(choice.target_player_id)
        inspected = [
            next((card for card in target.library if card.id == card_id), None)
            for card_id in choice.card_ids_top_first
        ]
        if any(card is None for card in inspected):
            raise RuntimeError("an inspected card is no longer in that library")
        self.pending_natural_selection_choices.pop(0)
        if shuffle:
            target.shuffle_library(self.random)
            return
        cards = [card for card in inspected if card is not None]
        for card in cards:
            target.library.remove(card)
        # Libraries store their top card at the end of the list.
        target.library.extend(reversed(cards))

    def legal_library_search_cards(self) -> tuple[Card, ...]:
        """Return current legal cards for the oldest private library search."""

        if not self.pending_library_search_choices:
            return ()
        choice = self.pending_library_search_choices[0]
        return tuple(
            card
            for card in self.player(choice.library_player_id).library
            if not choice.card_types
            or choice.card_types.issubset(card.definition.card_types)
        )

    def choose_library_search_card(self, player_id: str, card: Card) -> None:
        """Finish a search, move the private choice, then shuffle the library."""

        if not self.pending_library_search_choices:
            raise RuntimeError("there is no library search pending")
        choice = self.pending_library_search_choices[0]
        if player_id != choice.chooser_id:
            raise ValueError("only the searching player may choose a card")
        if card not in self.legal_library_search_cards():
            raise ValueError("that card is not eligible for this library search")
        library_player = self.player(choice.library_player_id)
        self.pending_library_search_choices.pop(0)
        self._move_card(card, choice.destination)
        library_player.shuffle_library(self.random)

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
            if not self._begin_river_defender_assignment(
                CombatStep.DECLARE_ATTACKERS
            ):
                self.combat.step = CombatStep.DECLARE_ATTACKERS
        elif self.combat.step is CombatStep.ATTACKER_RESPONSE:
            if not self._begin_river_defender_assignment(
                CombatStep.DECLARE_BLOCKERS
            ):
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
        self._clear_land_tap_undo_window()
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

    def _discard_random(
        self, player: PlayerState, amount: int, *, source_name: str = "random discard"
    ) -> tuple[Card, ...]:
        chosen = tuple(self.random.sample(player.hand, min(amount, len(player.hand))))
        self._discard_forced(player, chosen, source_name=source_name)
        return chosen

    def _library_of_leng_active(self, player: PlayerState) -> bool:
        return any(
            permanent.definition.is_library_of_leng
            and self.continuous_permanent_is_active(permanent)
            for permanent in player.battlefield
        )

    def required_discards(self, player: PlayerState) -> int:
        """Return the turn-based hand-size discard, accounting for Leng."""

        return 0 if self._library_of_leng_active(player) else player.discard_required

    def _discard_forced(
        self,
        player: PlayerState,
        cards: Iterable[Card],
        *,
        source_name: str,
        draw_after: int = 0,
        ante_after: bool = False,
    ) -> tuple[Card, ...]:
        """Discard hand cards, pausing for Library of Leng when applicable."""

        chosen = tuple(cards)
        if chosen and self._library_of_leng_active(player):
            self.pending_library_discard_choices.append(
                PendingLibraryDiscardChoice(
                    player.id,
                    tuple(card.id for card in chosen),
                    source_name,
                    draw_after=draw_after,
                    ante_after=ante_after,
                )
            )
            return chosen
        graveyard_lengths = self._graveyard_lengths()
        for card in chosen:
            self._move_card(card, Zone.GRAVEYARD)
        self._queue_new_graveyard_order_choices(graveyard_lengths)
        if ante_after:
            self._ante_top_card(player)
        if draw_after:
            player.draw(draw_after)
        return chosen

    @staticmethod
    def _ante_top_card(player: PlayerState) -> None:
        if player.library:
            ante_card = player.library.pop()
            ante_card.zone = Zone.ANTE
            player.ante.append(ante_card)
        else:
            player.has_lost = True

    def toggle_library_discard_destination(
        self, player_id: str, card: Card
    ) -> None:
        if not self.pending_library_discard_choices:
            raise RuntimeError("there is no Library of Leng choice pending")
        choice = self.pending_library_discard_choices[0]
        if choice.player_id != player_id:
            raise ValueError("only the affected player may choose discard destinations")
        if card.id not in choice.card_ids or card not in self.player(player_id).hand:
            raise ValueError("that card is not part of this forced discard")
        if card.id in choice.library_ids_bottom_to_top:
            choice.library_ids_bottom_to_top.remove(card.id)
        else:
            choice.library_ids_bottom_to_top.append(card.id)

    def move_library_discard_card(
        self, player_id: str, card: Card, direction: int
    ) -> None:
        if not self.pending_library_discard_choices:
            raise RuntimeError("there is no Library of Leng choice pending")
        choice = self.pending_library_discard_choices[0]
        if choice.player_id != player_id:
            raise ValueError("only the affected player may order the cards")
        if direction not in {-1, 1}:
            raise ValueError("library order movement must be up or down")
        try:
            index = choice.library_ids_bottom_to_top.index(card.id)
        except ValueError as error:
            raise ValueError("that card is not being put on the library") from error
        destination = index + direction
        if 0 <= destination < len(choice.library_ids_bottom_to_top):
            choice.library_ids_bottom_to_top[index], choice.library_ids_bottom_to_top[destination] = (
                choice.library_ids_bottom_to_top[destination],
                choice.library_ids_bottom_to_top[index],
            )

    def confirm_library_discard(self, player_id: str) -> None:
        if not self.pending_library_discard_choices:
            raise RuntimeError("there is no Library of Leng choice pending")
        choice = self.pending_library_discard_choices[0]
        if choice.player_id != player_id:
            raise ValueError("only the affected player may confirm this discard")
        player = self.player(player_id)
        cards = {card.id: card for card in player.hand}
        if not set(choice.card_ids) <= cards.keys():
            raise RuntimeError("a card awaiting discard is no longer in hand")
        library_ids = set(choice.library_ids_bottom_to_top)
        graveyard_lengths = self._graveyard_lengths()
        for card_id in choice.card_ids:
            if card_id not in library_ids:
                self._move_card(cards[card_id], Zone.GRAVEYARD)
        self._queue_new_graveyard_order_choices(graveyard_lengths)
        for card_id in choice.library_ids_bottom_to_top:
            self._move_card(cards[card_id], Zone.LIBRARY)
        if choice.ante_after:
            self._ante_top_card(player)
        if choice.draw_after:
            player.draw(choice.draw_after)
        self.pending_library_discard_choices.pop(0)
        if not self.pending_library_discard_choices and not self.pending_discard_choices:
            self.consecutive_passes = 0
            self.priority_player_index = None

    def choose_drain_power_mana(self, player_id: str, color: Color) -> None:
        """Choose the mana produced by the next dual land drained at resolution."""

        if not self.pending_drain_power_choices:
            raise RuntimeError("there is no Drain Power mana choice pending")
        choice = self.pending_drain_power_choices[0]
        if choice.caster_id != player_id:
            raise ValueError("only the Drain Power caster may choose the mana")
        amount = next(
            (
                option_amount
                for option_color, option_amount in choice.mana_options
                if option_color is color
            ),
            None,
        )
        if amount is None:
            raise ValueError(f"{choice.land_name} cannot produce {color.value}")
        self.player(player_id).mana_pool.add(color, amount)
        self.pending_drain_power_choices.pop(0)

    def _land_mana_bonus(self) -> int:
        return sum(
            effect.amount
            for owner in self.players
            for source in owner.battlefield
            if self.continuous_permanent_is_active(source)
            for effect in source.definition.land_mana_bonus_effects
        )

    def power_sink_mana_choices(
        self,
    ) -> list[tuple[Card, int, Color, int]]:
        """Currently usable land modes for a mandatory Power Sink payment."""

        pending = self.pending_power_sink_payment
        if pending is None:
            return []
        payer = self.player(pending.payer_id)
        bonus = self._land_mana_bonus()
        return [
            (land, index, ability.color, ability.amount + bonus)
            for land in payer.battlefield
            if CardType.LAND in self.card_types(land) and not land.tapped
            for index, ability in enumerate(self.activated_abilities(land))
            if isinstance(ability, ActivatedManaAbility)
        ]

    def _spend_power_sink_pool(self) -> None:
        pending = self.pending_power_sink_payment
        assert pending is not None
        payer = self.player(pending.payer_id)
        amount = min(pending.remaining, payer.mana_pool.total)
        if amount:
            self.pay_mana(payer, ManaCost(generic=amount))
            pending.remaining -= amount

    def _finish_power_sink_payment(self, *, countered: bool) -> None:
        pending = self.pending_power_sink_payment
        assert pending is not None
        target = pending.target
        if countered and target.zone is Zone.STACK:
            self.stack_spells.pop(target.id, None)
            self._discard_spell_cast_opportunities(target.id)
            self._move_card(target, Zone.GRAVEYARD)
        self.pending_power_sink_payment = None
        if not any(card.id == self.interruptible_spell_id for card in self.stack):
            self.interruptible_spell_id = None
        self.consecutive_passes = 0
        if self.stack:
            underlying = self.stack_spells[self.stack[-1].id]
            self.priority_player_index = self.players.index(
                self.player(underlying.caster_id)
            )
        elif self.event_opportunities:
            self.priority_player_index = self.active_player_index
        else:
            self.priority_player_index = None

    def _continue_power_sink_payment(self) -> None:
        pending = self.pending_power_sink_payment
        assert pending is not None
        self._spend_power_sink_pool()
        if pending.remaining == 0:
            self._finish_power_sink_payment(countered=False)
        elif not self.power_sink_mana_choices():
            self._finish_power_sink_payment(countered=True)

    def choose_power_sink_mana(
        self, player_id: str, land_id: UUID, ability_index: int
    ) -> None:
        """Tap one land for the mandatory Power Sink payment."""

        pending = self.pending_power_sink_payment
        if pending is None:
            raise RuntimeError("there is no Power Sink payment pending")
        if pending.payer_id != player_id:
            raise ValueError("only the targeted spell's caster may choose mana")
        choice = next(
            (
                item
                for item in self.power_sink_mana_choices()
                if item[0].id == land_id and item[1] == ability_index
            ),
            None,
        )
        if choice is None:
            raise ValueError("that land mana ability is not available")
        land, _, color, amount = choice
        payer = self.player(player_id)
        self._tap_permanent(land)
        payer.mana_pool.add(color, amount)
        self._continue_power_sink_payment()

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
        self._discard_forced(player, chosen, source_name=choice.source_name)
        self.pending_discard_choices.pop(0)
        if (
            not self.pending_discard_choices
            and not self.pending_library_discard_choices
            and self.pending_damage is None
        ):
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
                if category in {"land", "creature"}:
                    candidates = tuple(
                        card for card in candidates
                        if not self.land_is_consecrated(card)
                    )
                    amount = min(amount, len(candidates))
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
            self._discard_forced(
                player,
                (card for card in tuple(player.hand) if card.id in hand_ids),
                source_name="Balance",
            )
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
            requirement = self._translated_target_requirement(
                interrupt, requirement
            )
            legal_target = self._requirement_accepts_card(
                requirement,
                target,
                spell.caster_id,
                source_colors=self.card_colors(interrupt),
            )
        word_effect = next(
            (
                effect
                for effect in interrupt.definition.spell_effects
                if isinstance(effect, ChangeTextWordEffect)
            ),
            None,
        )
        if legal_target and word_effect is not None and target is not None:
            if word_effect.word_kind == "color":
                legal_target = (
                    isinstance(spell.chosen_word_from, Color)
                    and isinstance(spell.chosen_word_to, Color)
                    and spell.chosen_word_from in self.current_color_words(target)
                )
            else:
                legal_target = (
                    isinstance(spell.chosen_word_from, str)
                    and isinstance(spell.chosen_word_to, str)
                    and spell.chosen_word_from in self.current_land_words(target)
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
        counter_effect = next(
            (
                effect
                for effect in interrupt.definition.spell_effects
                if isinstance(effect, CounterTargetSpellEffect)
            ),
            None,
        )
        power_sink_started = False
        if (
            legal_target
            and target.zone is Zone.STACK
            and counter_effect is not None
        ):
            if counter_effect.power_sink:
                self.pending_power_sink_payment = PendingPowerSinkPayment(
                    target=target,
                    payer_id=self.stack_spells[target.id].caster_id,
                    remaining=spell.x_value,
                )
                power_sink_started = True
            else:
                self.stack_spells.pop(target.id, None)
                self._discard_spell_cast_opportunities(target.id)
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
            if word_effect is not None:
                if word_effect.word_kind == "color":
                    assert isinstance(spell.chosen_word_from, Color)
                    assert isinstance(spell.chosen_word_to, Color)
                    target.change_color_word(
                        spell.chosen_word_from, spell.chosen_word_to
                    )
                else:
                    assert isinstance(spell.chosen_word_from, str)
                    assert isinstance(spell.chosen_word_to, str)
                    target.change_land_word(
                        spell.chosen_word_from, spell.chosen_word_to
                    )
            copy_effect = next(
                (
                    effect
                    for effect in interrupt.definition.spell_effects
                    if isinstance(effect, CopyTargetSpellEffect)
                ),
                None,
            )
            if copy_effect is not None and target.id in self.stack_spells:
                original = self.stack_spells[target.id]
                copy_definition = replace(
                    target.definition,
                    colors=frozenset({
                        self.color_word(interrupt, copy_effect.copy_color)
                    }),
                )
                copy_card = Card(
                    copy_definition,
                    owner_id=spell.caster_id,
                    controller_id=spell.caster_id,
                    base_controller_id=spell.caster_id,
                    zone=Zone.STACK,
                    is_spell_copy=True,
                )
                copy_card.copy_word_changes_from(target)
                # Keep any still-unresolved interrupts above both spell
                # instances.  The original precedes its copy so sorceries
                # that cannot be simultaneous follow the FAQ's original-first
                # ruling.
                self.stack.insert(self.stack.index(target) + 1, copy_card)
                self.stack_spells[copy_card.id] = SpellOnStack(
                    card=copy_card,
                    caster_id=spell.caster_id,
                    targets=(
                        spell.copied_spell_targets
                        if spell.copied_spell_targets is not None
                        else original.targets
                    ),
                    x_value=(
                        spell.copied_spell_x_value
                        if spell.copied_spell_x_value is not None
                        else original.x_value
                    ),
                    chosen_mode=original.chosen_mode,
                    damage_source_key=original.damage_source_key,
                    declared_target_requirement=(
                        spell.copied_declared_target_requirement
                        if spell.copied_declared_target_requirement is not None
                        else original.declared_target_requirement
                    ),
                )
            color_effect = next(
                (
                    effect
                    for effect in interrupt.definition.spell_effects
                    if isinstance(effect, ChangeTargetColorEffect)
                ),
                None,
            )
            if color_effect is not None:
                target.color_override = self.color_word(
                    interrupt, color_effect.color
                )
                if target.zone is Zone.STACK:
                    self._refresh_spell_cast_opportunity(target)
            sacrifice_effect = next(
                (
                    effect
                    for effect in interrupt.definition.spell_effects
                    if isinstance(effect, SacrificeCreatureForManaEffect)
                ),
                None,
            )
            if sacrifice_effect is not None:
                amount = target.definition.mana_cost.mana_value
                self._move_card(target, Zone.GRAVEYARD)
                self.player(spell.caster_id).mana_pool.add(
                    self.color_word(interrupt, sacrifice_effect.color), amount
                )
        for effect in interrupt.definition.spell_effects:
            if isinstance(effect, AddManaEffect):
                self.player(spell.caster_id).mana_pool.add(
                    self.color_word(interrupt, effect.color), effect.amount
                )

        if interrupt.zone is Zone.STACK:
            self._move_card(interrupt, Zone.GRAVEYARD)

        if power_sink_started:
            self._continue_power_sink_payment()

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
            self._discard_spell_cast_opportunities(target.id)
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
        legal_spell_targets: dict[UUID, tuple[Card | PlayerState, ...]] = {}
        for spell in spells:
            requirement = spell.card.definition.target_requirement
            if requirement is not None:
                requirement = self._translated_target_requirement(
                    spell.card, requirement
                )
            valid_targets = tuple(
                target
                for target in spell.targets
                if requirement is not None
                and (
                    self._requirement_accepts_card(
                        requirement,
                        target,
                        spell.caster_id,
                        source_colors=self.card_colors(spell.card),
                    )
                    if isinstance(target, Card)
                    else requirement.players and target in self.players
                )
            )
            legal_spell_targets[spell.card.id] = valid_targets
            legal[spell.card.id] = (
                requirement is None
                or not spell.targets
                or bool(valid_targets)
            )
        legal_abilities = [
            (
                (
                    ability.event_id is not None
                    and any(
                        event.id == ability.event_id
                        for event in self.event_opportunities
                    )
                )
                if isinstance(
                    ability.ability,
                    (ActivatedEventLifeGainAbility, ActivatedEventDrawAbility),
                )
                else True
                if isinstance(
                    ability.ability,
                    (
                        ActivatedDestroyAllAbility,
                        ActivatedGlobalDamageAbility,
                        ActivatedUntapAbility,
                        ActivatedCreateTokenAbility,
                        ActivatedDiscardAbility,
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
            resolved_targets = legal_spell_targets[card.id]
            if legal[card.id] and card.definition.is_permanent:
                copied_animated_creature = False
                if card.definition.animates_dead_creature:
                    target = next(
                        (
                            target
                            for target in resolved_targets
                            if isinstance(target, Card)
                        ),
                        None,
                    )
                    assert target is not None
                    self._move_card(card, Zone.BATTLEFIELD)
                    card.entered_battlefield_turn = self.turn_number
                    if target.definition.copies_creature:
                        if not self.queue_creature_copy_entry(
                            target,
                            spell.caster_id,
                            attachment_id=card.id,
                        ):
                            self._move_card(card, Zone.GRAVEYARD)
                        continue
                    target.controller_id = spell.caster_id
                    self._move_card(target, Zone.BATTLEFIELD)
                    target.entered_battlefield_turn = self.turn_number
                    target.summoned_turn = self.turn_number
                    card.enchanted_card_id = target.id
                    continue
                if card.definition.copies_artifact:
                    target = next(
                        (
                            target
                            for target in resolved_targets
                            if isinstance(target, Card)
                        ),
                        None,
                    )
                    assert target is not None
                    self._copy_artifact_definition(card, target)
                elif card.definition.copies_creature:
                    target = next(
                        (
                            target
                            for target in resolved_targets
                            if isinstance(target, Card)
                        ),
                        None,
                    )
                    assert target is not None
                    copied_animated_creature = self.creature_has_animate_dead(
                        target
                    )
                    self._copy_creature_definition(card, target)
                self._move_card(card, Zone.BATTLEFIELD)
                if card.definition.x_enters_with_counter is not None:
                    card.counters[card.definition.x_enters_with_counter] = spell.x_value
                card.entered_battlefield_turn = self.turn_number
                card.enchanted_card_id = (
                    spell.targets[0].id
                    if spell.targets
                    and isinstance(spell.targets[0], Card)
                    and not (
                        card.printed_definition is not None
                        and (
                            card.printed_definition.copies_artifact
                            or card.printed_definition.copies_creature
                        )
                    )
                    else None
                )
                if card.definition.consecrates_attached_land:
                    target_land = next(
                        (
                            target
                            for target in spell.targets
                            if isinstance(target, Card)
                        ),
                        None,
                    )
                    if target_land is not None:
                        self._destroy_permanents(
                            aura
                            for player in self.players
                            for aura in tuple(player.battlefield)
                            if aura is not card
                            and aura.enchanted_card_id == target_land.id
                        )
                if (
                    card.definition.taps_attached_on_entry
                    and spell.targets
                    and isinstance(spell.targets[0], Card)
                ):
                    self._tap_permanent(spell.targets[0])
                if (
                    card.definition.damages_attached_on_entry
                    and spell.targets
                    and isinstance(spell.targets[0], Card)
                ):
                    self._deal_damage(
                        spell.targets[0],
                        card.definition.damages_attached_on_entry,
                        card.name,
                        source_card=card,
                        source_controller_id=spell.caster_id,
                    )
                if (
                    CardType.CREATURE in card.definition.card_types
                    and CardType.ARTIFACT not in card.definition.card_types
                ):
                    card.summoned_turn = self.turn_number
                if copied_animated_creature:
                    self._destroy_permanents((card,))

        pending_destruction: list[tuple[Card, bool]] = []
        pending_regeneration: list[Card] = []
        for spell in spells:
            card = spell.card
            if not legal[card.id] or card.definition.is_permanent:
                continue
            caster = self.player(spell.caster_id)
            resolved_targets = legal_spell_targets[card.id]
            for effect in card.definition.spell_effects:
                if isinstance(effect, DamageEffect):
                    recipients = (
                        (caster,)
                        if effect.recipient is EffectRecipient.CASTER
                        else resolved_targets
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
                elif isinstance(effect, DividedDamageEffect):
                    share = spell.x_value // len(spell.targets)
                    for recipient in legal_spell_targets[card.id]:
                        self._deal_damage(
                            recipient,
                            share,
                            card.name,
                            source_id=uuid4(),
                            source_controller_id=spell.caster_id,
                            source_colors=self.card_colors(card),
                        )
                elif isinstance(effect, DrainLifeEffect):
                    for recipient in resolved_targets:
                        cap = (
                            self.creature_toughness(recipient)
                            if isinstance(recipient, Card) else None
                        )
                        self._deal_damage(
                            recipient,
                            spell.x_value,
                            card.name,
                            source_card=card,
                            source_controller_id=spell.caster_id,
                            life_gain_player_id=caster.id,
                            life_gain_cap=cap,
                        )
                elif isinstance(effect, TemporaryPumpEffect):
                    power = effect.power + effect.power_per_x * spell.x_value
                    toughness = (
                        effect.toughness
                        + effect.toughness_per_x * spell.x_value
                    )
                    for target in resolved_targets:
                        if isinstance(target, Card):
                            self.temporary_creature_effects.setdefault(
                                target.id, []
                            ).append(
                                ContinuousEffect(
                                    power=power,
                                    toughness=toughness,
                                    power_multiplier=effect.power_multiplier,
                                    granted_abilities=effect.granted_abilities,
                                )
                            )
                            if effect.destroy_at_end_of_turn_if_attacked:
                                self.destroy_at_end_of_turn_if_attacked.add(
                                    target.id
                                )
                elif isinstance(effect, PreventCombatDamageEffect):
                    self.prevent_combat_damage_this_turn = True
                elif isinstance(effect, ChannelEffect):
                    self.channel_active_players.add(caster.id)
                elif isinstance(effect, RegenerateTargetsEffect):
                    pending_regeneration.extend(
                        target
                        for target in resolved_targets
                        if isinstance(target, Card)
                    )
                elif isinstance(effect, GainLifeEffect):
                    amount = effect.amount + effect.amount_per_x * spell.x_value
                    for target in resolved_targets:
                        if not isinstance(target, Card):
                            self._gain_life(target, amount)
                elif isinstance(effect, DrawCardsEffect):
                    amount = effect.amount + effect.amount_per_x * spell.x_value
                    for target in resolved_targets:
                        if not isinstance(target, Card):
                            target.draw(amount)
                elif isinstance(effect, DiscardCardsEffect):
                    amount = effect.amount + effect.amount_per_x * spell.x_value
                    for target in resolved_targets:
                        if not not isinstance(target, Card):
                            continue
                        if effect.random:
                            self._discard_random(
                                target, amount, source_name=card.name
                            )
                        elif target.hand:
                            self.pending_discard_choices.append(
                                PendingDiscardChoice(target.id, amount, card.name)
                            )
                elif isinstance(effect, DiscardHandsAndDrawEffect):
                    for player in self.players:
                        self._discard_forced(
                            player,
                            tuple(player.hand),
                            source_name=card.name,
                            draw_after=effect.draw_count,
                        )
                elif isinstance(effect, ShuffleHandAndGraveyardEffect):
                    for player in self.players:
                        recyclable = tuple(player.hand) + tuple(player.graveyard)
                        for recyclable_card in recyclable:
                            self._move_card(recyclable_card, Zone.LIBRARY)
                        player.shuffle_library(self.random)
                    for player in self.players:
                        player.draw(effect.draw_count)
                elif isinstance(effect, DiscardHandAnteAndDrawEffect):
                    self._discard_forced(
                        caster,
                        tuple(caster.hand),
                        source_name=card.name,
                        draw_after=effect.draw_count,
                        ante_after=True,
                    )
                elif isinstance(effect, SwapLibraryTopWithAnteEffect):
                    # The library-card requirement is checked when Darkpact is
                    # cast. Keep resolution robust if a future effect empties
                    # that library during the same batch.
                    if caster.library:
                        target = next(
                            item for item in resolved_targets if isinstance(item, Card)
                        )
                        ante_player = next(
                            player for player in self.players if target in player.ante
                        )
                        replacement = caster.library.pop()
                        ante_player.ante.remove(target)
                        target.owner_id = caster.id
                        target.controller_id = caster.id
                        target.zone = Zone.LIBRARY
                        caster.library.append(target)
                        replacement.owner_id = ante_player.id
                        replacement.controller_id = ante_player.id
                        replacement.zone = Zone.ANTE
                        ante_player.ante.append(replacement)
                elif isinstance(effect, DemonicAttorneyEffect):
                    opponent = next(
                        player for player in self.players if player.id != caster.id
                    )
                    self.pending_demonic_attorney_choices.append(
                        PendingDemonicAttorneyChoice(caster.id, opponent.id)
                    )
                elif isinstance(effect, NaturalSelectionEffect):
                    target = next(
                        item for item in resolved_targets if not isinstance(item, Card)
                    )
                    self.pending_natural_selection_choices.append(
                        PendingNaturalSelectionChoice(
                            caster.id,
                            target.id,
                            [card.id for card in reversed(target.library[-3:])],
                        )
                    )
                elif isinstance(effect, LibrarySearchEffect):
                    self.pending_library_search_choices.append(
                        PendingLibrarySearchChoice(
                            caster.id,
                            caster.id,
                            spell.card.name,
                            effect.card_types,
                            effect.destination,
                        )
                    )
                elif isinstance(effect, SirensCallEffect):
                    for creature in tuple(self.active_player.battlefield):
                        if (
                            CardType.CREATURE not in self.card_types(creature)
                            or (
                                (
                                    self.has_summoning_sickness(creature)
                                    or creature.summoned_turn == self.turn_number
                                )
                                and not self.may_attack_with_summoning_sickness(
                                    creature
                                )
                            )
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
                elif isinstance(effect, FalseOrdersEffect):
                    if (
                        self.combat is not None
                        and self.combat.step is CombatStep.BLOCKER_RESPONSE
                    ):
                        self.pending_false_orders_choices.extend(
                            PendingFalseOrdersChoice(
                                spell.caster_id,
                                target.id,
                                card.name,
                            )
                            for target in resolved_targets
                            if isinstance(target, Card)
                            and target.controller_id
                            == self.combat.defending_player_id
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
                        for target in resolved_targets
                        if isinstance(target, Card)
                    )
                elif isinstance(effect, DestroyAllEffect):
                    effect = replace(
                        effect,
                        subtypes=frozenset(
                            self.land_word(card, subtype)
                            for subtype in effect.subtypes
                        ),
                    )
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
                    for target in resolved_targets:
                        if not isinstance(target, Card):
                            continue
                        if (
                            effect.destination is Zone.BATTLEFIELD
                            and target.definition.copies_creature
                        ):
                            self.queue_creature_copy_entry(target, caster.id)
                            continue
                        if effect.under_caster_control:
                            target.controller_id = caster.id
                        self._move_card(target, effect.destination)
                        if effect.destination is Zone.BATTLEFIELD:
                            target.entered_battlefield_turn = self.turn_number
                elif isinstance(effect, ExileTargetsEffect):
                    for target in resolved_targets:
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
                        self._gain_life(controller, life_gain)
                elif isinstance(effect, ReverseDamageEffect):
                    if spell.damage_source_key is None:
                        continue
                    reversed_damage = sum(
                        amount
                        for _, amount in self._consume_player_damage(
                            caster.id, source_key=spell.damage_source_key
                        )
                    )
                    # Undo the loss, then gain that much life instead. Lich
                    # had no life loss to undo and replaces the gain with draws.
                    if not self._lich_count(caster.id):
                        caster.life += reversed_damage
                    self._gain_life(caster, reversed_damage)
                    if caster.life > 0:
                        caster.has_lost = False
                elif isinstance(effect, RetroactiveDamageTransferEffect):
                    target = next(
                        (item for item in resolved_targets if isinstance(item, Card)),
                        None,
                    )
                    if target is None:
                        continue
                    consumed = self._consume_player_damage(caster.id)
                    if not self._lich_count(caster.id):
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
                    for target in resolved_targets:
                        if isinstance(target, Card):
                            if tapped:
                                self._tap_permanent(target)
                            else:
                                target.tapped = False
                elif isinstance(effect, TapLandsAndEmptyManaPoolEffect):
                    for target in resolved_targets:
                        if isinstance(target, Card):
                            continue
                        caster = self.player(spell.caster_id)
                        for owner in self.players:
                            for permanent in tuple(owner.battlefield):
                                if (
                                    permanent.controller_id == target.id
                                    and CardType.LAND in self.card_types(permanent)
                                ):
                                    if permanent.tapped:
                                        continue
                                    mana_abilities = tuple(
                                        ability
                                        for ability in self.activated_abilities(permanent)
                                        if isinstance(ability, ActivatedManaAbility)
                                    )
                                    self._tap_permanent(permanent)
                                    if not effect.produce_land_mana:
                                        continue
                                    bonus = sum(
                                        bonus_effect.amount
                                        for bonus_owner in self.players
                                        for source in bonus_owner.battlefield
                                        if self.continuous_permanent_is_active(source)
                                        for bonus_effect in source.definition.land_mana_bonus_effects
                                    )
                                    by_color: dict[Color, int] = {}
                                    for ability in mana_abilities:
                                        by_color[ability.color] = max(
                                            by_color.get(ability.color, 0),
                                            ability.amount + bonus,
                                        )
                                    options = tuple(by_color.items())
                                    if len(options) == 1:
                                        color, amount = options[0]
                                        caster.mana_pool.add(color, amount)
                                    elif options:
                                        self.pending_drain_power_choices.append(
                                            PendingDrainPowerChoice(
                                                caster.id,
                                                permanent.id,
                                                permanent.name,
                                                options,
                                            )
                                        )
                        if effect.transfer_to_caster:
                            for color in Color:
                                amount = target.mana_pool.amount(color)
                                if amount:
                                    caster.mana_pool.add(color, amount)
                            target.mana_pool.empty()
                        else:
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
            elif isinstance(declared.ability, ActivatedCreateTokenAbility):
                ability = declared.ability
                token = Card(
                    ability.token_definition,
                    owner_id=declared.controller_id,
                    controller_id=declared.controller_id,
                    base_controller_id=declared.controller_id,
                    zone=Zone.BATTLEFIELD,
                    entered_battlefield_turn=self.turn_number,
                    is_token=True,
                )
                self.battlefield_entry_sequence += 1
                token.battlefield_entry_sequence = self.battlefield_entry_sequence
                self.player(declared.controller_id).battlefield.append(token)
            elif isinstance(declared.ability, ActivatedGraveyardReturnAbility):
                if declared.source.zone is Zone.GRAVEYARD:
                    declared.source.controller_id = declared.controller_id
                    self._move_card(declared.source, Zone.BATTLEFIELD)
                    declared.source.entered_battlefield_turn = self.turn_number
                    declared.source.summoned_turn = self.turn_number
            elif isinstance(declared.ability, ActivatedRevealHandAbility):
                self._queue_opponent_hand_reveal(declared.controller_id)
            elif isinstance(declared.ability, ActivatedDiscardAbility):
                controller = self.player(declared.controller_id)
                opponent = self.players[
                    (self.players.index(controller) + 1) % len(self.players)
                ]
                if opponent.hand:
                    self.pending_discard_choices.append(
                        PendingDiscardChoice(
                            opponent.id,
                            declared.ability.amount,
                            declared.source_name,
                        )
                    )
            elif isinstance(declared.ability, ActivatedAttackRequirementAbility):
                for target in declared.targets:
                    if isinstance(target, Card):
                        self.attack_requirements[target.id] = AttackRequirement(target.id)
            elif isinstance(declared.ability, ActivatedLandTypeAbility):
                if (
                    declared.source.zone is not Zone.BATTLEFIELD
                    and not declared.ability.persists_after_source_leaves
                ):
                    continue
                for target in declared.targets:
                    if isinstance(target, Card):
                        self.battlefield_entry_sequence += 1
                        if declared.ability.persists_after_source_leaves:
                            if declared.source.persistent_effect_instance_id is None:
                                declared.source.persistent_effect_instance_id = uuid4()
                            mark = CyclopeanTombMark(
                                uuid4(),
                                declared.source.persistent_effect_instance_id,
                                target.id,
                                self.battlefield_entry_sequence,
                                declared.ability.replacement_subtype,
                            )
                            self.cyclopean_tomb_marks.append(mark)
                            if declared.source.zone is not Zone.BATTLEFIELD:
                                self.cyclopean_tomb_cleanup_controllers[
                                    mark.effect_id
                                ] = declared.controller_id
                            target.counters["mire"] = (
                                target.counters.get("mire", 0) + 1
                            )
                        else:
                            target.land_type_marks[declared.source.id] = (
                                declared.ability.replacement_subtype,
                                self.battlefield_entry_sequence,
                            )
            elif isinstance(declared.ability, ActivatedExtraTurnAbility):
                self.schedule_extra_turn(declared.controller_id)
            elif isinstance(declared.ability, ActivatedUntapAbility):
                for target in declared.targets:
                    if isinstance(target, Card):
                        target.tapped = False
            elif isinstance(
                declared.ability, ActivatedEventLifeGainAbility
            ):
                self._gain_life(
                    self.player(declared.controller_id), declared.ability.amount
                )
            elif isinstance(declared.ability, ActivatedEventDrawAbility):
                self.player(declared.controller_id).draw(
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

        graveyard_lengths = self._graveyard_lengths()
        for spell in spells:
            card = spell.card
            self.stack_spells.pop(card.id, None)
            if card.zone is Zone.STACK:
                self._move_card(card, Zone.GRAVEYARD)
        self._queue_new_graveyard_order_choices(graveyard_lengths)
        self.batch_abilities.clear()
        self.check_state_based_actions()
        self._refresh_graveyard_return_choice()
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
            elif isinstance(effect, PreventCombatDamageEffect):
                self.prevent_combat_damage_this_turn = True
            elif isinstance(effect, DestroyAllEffect):
                effect = replace(
                    effect,
                    subtypes=frozenset(
                        self.land_word(card, subtype)
                        for subtype in effect.subtypes
                    ),
                )
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
                    if (
                        effect.destination is Zone.BATTLEFIELD
                        and target.definition.copies_creature
                    ):
                        self.queue_creature_copy_entry(target, caster.id)
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
                    self._gain_life(controller, life_gain)

