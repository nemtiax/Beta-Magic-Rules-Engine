"""Priority, interrupt, and fast-effect batch resolution for GameState."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Callable, Iterable
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
    TargetRequirement,
)
from .cards import Card
from .batch_resolution import (
    BatchCharacteristicSnapshot,
    BatchConflict,
    BatchConflictKind,
    BatchConsequences,
    BatchEffectIntent,
    BatchIntentKind,
    BatchLegalitySnapshot,
    PendingBatchConflictChoice,
    BatchResolutionPlan,
)
from .casting import AbilityOnStack, PendingCast, SpellOnStack
from .combat import AttackRequirement, PendingFalseOrdersChoice
from .damage import DamageIncidentKind, DamageRecipientKind
from .destruction import DestructionIncident, DestructionTarget
from .effects import (
    AddManaEffect,
    AttachedLandTypeEffect,
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
    WordOfCommandEffect,
    NaturalSelectionEffect,
    LibrarySearchEffect,
    SacrificeCreatureForManaEffect,
    DrawCardsEffect,
    EffectScope,
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
    CamouflageEffect,
    TemporaryPumpEffect,
    TapLandsAndEmptyManaPoolEffect,
    SwapLibraryTopWithAnteEffect,
)
from .mana import (
    LandManaActivation,
    LandManaPaymentPlan,
    ManaAllocation,
    ManaCost,
)
from .types import CardType, Color, CombatStep, KeywordAbility, TurnPhase, Zone

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
    decision_maker_id: str
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
class PendingWordOfCommandChoice:
    """A resolved Word whose caster is making the opponent's casting choices."""

    id: UUID
    commander_id: str
    commanded_player_id: str
    source_name: str = "Word of Command"
    card_id: UUID | None = None
    stage: str = "choose_card"
    x_value: int = 0
    chosen_land_subtype: str | None = None
    chosen_mode: str | None = None
    damage_source_key: str | None = None
    targets: tuple[Card | PlayerState, ...] = ()
    copied_spell_targets: tuple[Card | PlayerState, ...] | None = None
    copied_spell_x_value: int | None = None
    copied_declared_target_requirement: TargetRequirement | None = None
    chosen_word_from: Color | str | None = None
    chosen_word_to: Color | str | None = None


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

    def _queue_batch_ability(self, declared: AbilityOnStack) -> None:
        """Queue a fast effect and retain its announcement position.

        Spells and interrupt-speed abilities already use the shared
        declaration counter. Ordinary activated abilities need the same
        sequence so a batch plan can reconstruct the actual announcement
        order without relying on separate spell and ability collections.
        """

        self.interrupt_declaration_sequence += 1
        declared.declaration_sequence = self.interrupt_declaration_sequence
        self.batch_abilities.append(declared)

    def current_word_command(self) -> PendingWordOfCommandChoice | None:
        return (
            self.pending_word_command_choices[0]
            if self.pending_word_command_choices else None
        )

    def _word_command_card(self, choice: PendingWordOfCommandChoice) -> Card | None:
        commanded = self.player(choice.commanded_player_id)
        return next(
            (card for card in commanded.hand if card.id == choice.card_id),
            None,
        )

    def _word_command_timing_is_legal(
        self, card: Card, caster: PlayerState
    ) -> bool:
        """Whether ``card`` could be the play compelled by a resolved Word."""

        types = card.definition.card_types
        if CardType.LAND in types:
            return bool(
                caster is self.active_player
                and self.current_phase is TurnPhase.MAIN
                and self.combat is None
                and self.lands_played_this_turn == 0
            )
        if card.definition.requires_ante and not self.ante_enabled:
            return False
        if self.current_phase is TurnPhase.UNTAP:
            return False
        if self.combat is not None and self.combat.step in {
            CombatStep.DECLARE_ATTACKERS,
            CombatStep.DECLARE_BLOCKERS,
            CombatStep.RIVER_DEFENDER_ASSIGNMENT,
            CombatStep.RIVER_ATTACKER_ASSIGNMENT,
            CombatStep.DAMAGE,
        }:
            return False
        if card.definition.is_permanent or CardType.SORCERY in types:
            return bool(
                caster is self.active_player
                and self.current_phase is TurnPhase.MAIN
                and self.combat is None
            )
        if CardType.INTERRUPT in types:
            # Once Word has resolved there is no spell left for a counter or
            # lace to interrupt. Standalone mana interrupts and interrupts
            # whose printed target can be a permanent remain legal.
            requirement = card.definition.target_requirement
            can_target_in_play = bool(
                requirement is not None
                and (
                    requirement.zone is Zone.BATTLEFIELD
                    or Zone.BATTLEFIELD in requirement.additional_zones
                )
            )
            return can_target_in_play or any(
                isinstance(effect, (AddManaEffect, SacrificeCreatureForManaEffect))
                for effect in card.definition.spell_effects
            )
        if CardType.INSTANT not in types:
            return False
        if any(
            isinstance(effect, SirensCallEffect)
            for effect in card.definition.spell_effects
        ) and (
            caster is self.active_player
            or self.attacks_this_turn
            or self.combat is not None
        ):
            return False
        if any(
            isinstance(effect, BlazeOfGloryEffect)
            for effect in card.definition.spell_effects
        ) and (
            self.combat is None
            or self.combat.step is not CombatStep.ATTACKER_RESPONSE
        ):
            return False
        if any(
            isinstance(effect, FalseOrdersEffect)
            for effect in card.definition.spell_effects
        ) and (
            self.combat is None
            or self.combat.step is not CombatStep.BLOCKER_RESPONSE
        ):
            return False
        if any(
            isinstance(effect, TemporaryPumpEffect)
            and effect.destroy_at_end_of_turn_if_attacked
            for effect in card.definition.spell_effects
        ) and self.attacks_this_turn and self.combat is None:
            return False
        if any(
            isinstance(effect, PreventCombatDamageEffect)
            for effect in card.definition.spell_effects
        ) and self.attacks_this_turn and self.combat is None:
            return False
        return not card.definition.is_guardian_angel

    def _validate_word_command_card(
        self,
        choice: PendingWordOfCommandChoice,
        card: Card,
        *,
        x_value: int = 0,
        chosen_mode: str | None = None,
        target_count: int = 1,
        require_targets: bool = True,
    ) -> ManaCost:
        caster = self.player(choice.commanded_player_id)
        if card not in caster.hand:
            raise ValueError("Word of Command must choose a card in that hand")
        if not self._word_command_timing_is_legal(card, caster):
            raise RuntimeError(f"{card.name} cannot legally be played now")
        if x_value < 0:
            raise ValueError("X cannot be negative")
        if not card.definition.mana_cost.x_symbols and x_value:
            raise ValueError(f"{card.name} has no X in its mana cost")
        if (
            card.definition.casting_modes
            and chosen_mode not in card.definition.casting_modes
        ):
            raise ValueError(f"{card.name} requires a casting mode choice")
        if not card.definition.casting_modes and chosen_mode is not None:
            raise ValueError(f"{card.name} does not have casting modes")
        if any(
            isinstance(effect, SwapLibraryTopWithAnteEffect)
            for effect in card.definition.spell_effects
        ) and not caster.library:
            raise RuntimeError(f"{card.name} requires a card in its caster's library")
        if any(
            isinstance(effect, ReverseDamageEffect)
            for effect in card.definition.spell_effects
        ) and not self.damage_source_choices(caster.id):
            raise RuntimeError(f"{card.name} has no damage source to choose")
        cost = self.spell_mana_cost(card, x_value, target_count)
        if (
            CardType.LAND not in card.definition.card_types
            and not self.can_pay_mana_with_lands(caster.id, cost)
        ):
            raise RuntimeError(
                f"{caster.name} cannot pay for {card.name} using their mana pool and lands"
            )
        requirement = card.definition.target_requirement
        if requirement is not None and require_targets:
            legal_count = len(
                self.legal_targets_for(
                    card,
                    mode=chosen_mode,
                    acting_player_id=choice.commanded_player_id,
                    decision_player_id=choice.commander_id,
                )
            ) + len(
                self.legal_player_targets_for(
                    card,
                    acting_player_id=choice.commanded_player_id,
                )
            )
            needed = x_value if requirement.count_equals_x else requirement.count
            if requirement.any_number:
                needed = 1
            if needed and legal_count < needed:
                raise RuntimeError(f"there are no legal targets for {card.name}")
        return cost

    def word_commandable_cards(self) -> tuple[Card, ...]:
        """Return the cards the current Word commander is obliged to consider."""

        choice = self.current_word_command()
        if choice is None or choice.stage != "choose_card":
            return ()
        commanded = self.player(choice.commanded_player_id)
        legal: list[Card] = []
        for card in commanded.hand:
            modes = card.definition.casting_modes or (None,)
            for mode in modes:
                try:
                    self._validate_word_command_card(
                        choice, card, chosen_mode=mode
                    )
                except (ValueError, RuntimeError):
                    continue
                legal.append(card)
                break
        return tuple(legal)

    def finish_word_command_without_play(self, commander_id: str) -> None:
        """Finish Word only when the revealed hand contains no legal play."""

        choice = self.current_word_command()
        if choice is None or choice.commander_id != commander_id:
            raise ValueError("only the Word of Command caster may finish the choice")
        if self.word_commandable_cards():
            raise RuntimeError("a legal card must be played for Word of Command")
        self.pending_word_command_choices.pop(0)
        self._resume_ordered_batch_hand_library_effects()

    def maximum_word_command_x(self, card: Card, target_count: int = 1) -> int:
        choice = self.current_word_command()
        if choice is None:
            raise RuntimeError("there is no Word of Command choice pending")
        if not card.definition.mana_cost.x_symbols:
            raise ValueError(f"{card.name} has no X in its mana cost")
        maximum = 0
        while True:
            candidate = maximum + 1
            try:
                self._validate_word_command_card(
                    choice,
                    card,
                    x_value=candidate,
                    target_count=target_count,
                )
            except (ValueError, RuntimeError):
                break
            maximum = candidate
        requirement = card.definition.target_requirement
        if requirement is not None and requirement.count_equals_x:
            maximum = min(
                maximum,
                len(
                    self.legal_targets_for(
                        card,
                        acting_player_id=choice.commanded_player_id,
                        decision_player_id=choice.commander_id,
                    )
                )
                + len(
                    self.legal_player_targets_for(
                        card,
                        acting_player_id=choice.commanded_player_id,
                    )
                ),
            )
        return maximum

    def begin_word_command_cast(
        self,
        commander_id: str,
        card: Card,
        *,
        x_value: int = 0,
        land_subtype: str | None = None,
        mode: str | None = None,
        damage_source_key: str | None = None,
    ) -> PendingCast | None:
        """Choose the compelled card and gather its normal casting choices."""

        choice = self.current_word_command()
        if choice is None or choice.commander_id != commander_id:
            raise ValueError("only the Word of Command caster may choose the card")
        if choice.stage != "choose_card":
            raise RuntimeError("the commanded play has already been chosen")
        self._validate_word_command_card(
            choice, card, x_value=x_value, chosen_mode=mode
        )
        self._validate_land_type_choice(card, land_subtype)
        if any(
            isinstance(effect, ReverseDamageEffect)
            for effect in card.definition.spell_effects
        ):
            legal_sources = {
                key
                for key, _name, _amount in self.damage_source_choices(
                    choice.commanded_player_id
                )
            }
            if damage_source_key not in legal_sources:
                raise ValueError(f"{card.name} requires a damage source choice")
        elif damage_source_key is not None:
            raise ValueError(f"{card.name} does not choose a damage source")
        if CardType.LAND in card.definition.card_types:
            self.pending_word_command_choices.pop(0)
            self._play_land_for(self.player(choice.commanded_player_id), card)
            self._resume_ordered_batch_hand_library_effects()
            return None
        choice.card_id = card.id
        choice.x_value = x_value
        choice.chosen_land_subtype = land_subtype
        choice.chosen_mode = mode
        choice.damage_source_key = damage_source_key
        if card.definition.target_requirement is not None:
            self.pending_cast = PendingCast(
                spell=card,
                caster_id=choice.commanded_player_id,
                decision_maker_id=choice.commander_id,
                x_value=x_value,
                chosen_land_subtype=land_subtype,
                chosen_mode=mode,
                damage_source_key=damage_source_key,
                word_command_id=choice.id,
            )
            choice.stage = "choose_targets"
            return self.pending_cast
        choice.stage = "choose_payment"
        return None

    def _store_word_command_targets(
        self,
        pending: PendingCast,
        targets: tuple[Card | PlayerState, ...],
    ) -> None:
        choice = self.current_word_command()
        if choice is None or choice.id != pending.word_command_id:
            raise RuntimeError("the Word of Command choice is no longer pending")
        choice.targets = targets
        choice.copied_spell_targets = pending.copied_spell_targets
        choice.copied_spell_x_value = pending.copied_spell_x_value
        choice.copied_declared_target_requirement = (
            pending.copied_declared_target_requirement
        )
        choice.chosen_word_from = pending.chosen_word_from
        choice.chosen_word_to = pending.chosen_word_to
        choice.stage = "choose_payment"

    def word_command_mana_options(self) -> tuple[LandManaActivation, ...]:
        choice = self.current_word_command()
        if choice is None or choice.stage != "choose_payment":
            return ()
        return self.land_mana_activations(choice.commanded_player_id)

    def complete_word_command_payment(
        self,
        commander_id: str,
        activations: Iterable[tuple[UUID, int]],
        spending: ManaAllocation | None = None,
    ) -> Card:
        """Tap the lands selected by the commander and announce the forced spell."""

        choice = self.current_word_command()
        if choice is None or choice.commander_id != commander_id:
            raise ValueError("only the Word of Command caster may choose the payment")
        if choice.stage != "choose_payment":
            raise RuntimeError("finish choosing the commanded spell first")
        card = self._word_command_card(choice)
        if card is None:
            raise RuntimeError(
                "the commanded card is no longer in its owner's hand"
            )
        caster = self.player(choice.commanded_player_id)
        cost = self._validate_word_command_card(
            choice,
            card,
            x_value=choice.x_value,
            chosen_mode=choice.chosen_mode,
            target_count=len(choice.targets) or 1,
            require_targets=False,
        )
        plan: LandManaPaymentPlan = self.plan_land_mana_payment(
            caster.id,
            cost,
            activations,
            require_exact_when_available=True,
            spending=spending,
        )
        self._clear_land_tap_undo_window()
        for activation in plan.activations:
            land = next(
                permanent
                for permanent in caster.battlefield
                if permanent.id == activation.land_id
            )
            ability = self.activated_abilities(land)[activation.ability_index]
            assert isinstance(ability, ActivatedManaAbility)
            if ability.tap_cost:
                self._tap_permanent(land)
            for recipient_id, color, amount in self._land_activation_mana_contributions(
                caster, land, ability
            ):
                self.player(recipient_id).mana_pool.add(color, amount)
        self.pending_word_command_choices.pop(0)
        self._cast_spell(
            card,
            choice.targets,
            caster,
            choice.x_value,
            chosen_land_subtype=choice.chosen_land_subtype,
            chosen_mode=choice.chosen_mode,
            damage_source_key=choice.damage_source_key,
            copied_spell_targets=choice.copied_spell_targets,
            copied_spell_x_value=choice.copied_spell_x_value,
            copied_declared_target_requirement=(
                choice.copied_declared_target_requirement
            ),
            chosen_word_from=choice.chosen_word_from,
            chosen_word_to=choice.chosen_word_to,
            decision_maker_id=choice.commander_id,
            mana_allocation=plan.spending,
        )
        # A Word ordered before another hand effect must finish forcing this
        # announcement before the later effect reads or changes that hand.
        # Preserve the fresh spell's interrupt opportunity across any later
        # interactive operation that keeps the outer batch suspended.
        outer_plan = self.pending_batch_resolution
        if outer_plan is not None and not outer_plan.finalized:
            outer_plan.commanded_spell_priority_player_index = (
                self.priority_player_index
            )
            outer_plan.commanded_spell_interruptible_id = (
                self.interruptible_spell_id
            )
        self._resume_ordered_batch_hand_library_effects()
        return card

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
            self._resume_ordered_batch_hand_library_effects()
            return
        cards = [card for card in inspected if card is not None]
        for card in cards:
            target.library.remove(card)
        # Libraries store their top card at the end of the list.
        target.library.extend(reversed(cards))
        self._resume_ordered_batch_hand_library_effects()

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
        self._resume_ordered_batch_hand_library_effects()

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
            if self._check_life_loss_checkpoint():
                self.combat = None
                self.combat_creature_effects.clear()
                return
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

        # Every announced spell first has a dedicated interrupt-only window.
        # Interrupts are also always legal inside damage prevention,
        # redirection, and regeneration windows. Finish the current or nested
        # interrupt sequence before a pass advances ordinary batch timing or
        # the surrounding incident.
        if (
            self.interruptible_spell_id is not None
            or (
                self.stack
                and CardType.INTERRUPT in self.stack[-1].definition.card_types
            )
        ) or self.interrupt_abilities:
            self._require_no_pending_action(allow_stack=True, allow_damage=True)
            if self.priority_player_index is None:
                raise RuntimeError("the interrupt sequence has no priority player")
            player = self.player(player_id)
            if player is not self.players[self.priority_player_index]:
                raise RuntimeError(
                    f"{self.players[self.priority_player_index].name} has priority"
                )
            self._clear_land_tap_undo_window()
            self.consecutive_passes += 1
            if self.consecutive_passes < len(self.players):
                self.priority_player_index = (
                    self.priority_player_index + 1
                ) % len(self.players)
                return None
            if any(
                CardType.INTERRUPT in card.definition.card_types
                for card in self.stack
            ) or self.interrupt_abilities:
                interrupt, ability = self._next_interrupt_to_resolve()
                if interrupt is not None:
                    return self._resolve_interrupt(interrupt)
                assert ability is not None
                self._resolve_counter_ability(ability)
                return ()

            # No interrupt remains above the current ordinary spell. It is
            # now successfully cast and may receive ordinary instant and
            # fast-effect responses. Those responses start a fresh pass
            # sequence with the spell caster's opponent.
            root_id = self.interruptible_spell_id
            assert root_id is not None
            root = self.stack_spells.get(root_id)
            self.interruptible_spell_id = None
            self.consecutive_passes = 0
            if root is None:
                if self._continue_incident_spell_resolutions():
                    return ()
                self._restore_pending_context_priority()
                return None
            if root.incident_window_mode is not None:
                self._continue_incident_spell_resolutions()
                if self.pending_prevention is None:
                    caster = self.player(root.caster_id)
                    self.priority_player_index = (
                        self.players.index(caster) + 1
                    ) % len(self.players)
                    self.consecutive_passes = 0
                return ()
            caster = self.player(root.caster_id)
            self.priority_player_index = (
                self.players.index(caster) + 1
            ) % len(self.players)
            return None

        if self.pending_destruction is not None:
            self._pass_destruction_priority(player_id)
            return None
        if self.pending_damage is not None:
            self._pass_damage_priority(player_id)
            return None
        self._require_no_pending_action(allow_stack=True)
        if (
            not self.stack
            and not self.batch_abilities
            and not self.timed_events
            and not self.event_opportunities
            and self.pending_phase_advance is None
            and self.pending_action_response is None
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
            resolved = self._resolve_batch()
            if (
                self.pending_damage is None
                and self.pending_destruction is None
                and not self.pending_batch_conflict_choices
            ):
                self._restore_pending_context_priority()
            return resolved

        if self.event_opportunities:
            self._close_event_opportunities()
            if (
                self.pending_damage is None
                and self.pending_destruction is None
            ):
                self._restore_pending_context_priority()
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

        if self.pending_action_response is not None:
            self.pending_action_response = None
            self.priority_player_index = None
            self.consecutive_passes = 0
            return ()

        self._resolve_timed_event()
        if (
            self.pending_damage is None
            and self.pending_destruction is None
        ):
            self._restore_pending_context_priority()
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
        self._resume_ordered_batch_hand_library_effects()

    def choose_drain_power_mana(self, player_id: str, color: Color) -> None:
        """Choose the mana produced by the next dual land drained at resolution."""

        if not self.pending_drain_power_choices:
            raise RuntimeError("there is no Drain Power mana choice pending")
        choice = self.pending_drain_power_choices[0]
        if choice.decision_maker_id != player_id:
            raise ValueError(
                "only the spell's decision-maker may choose the mana"
            )
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
        self.player(choice.caster_id).mana_pool.add(color, amount)
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
        self._resume_ordered_batch_hand_library_effects()
        return chosen

    def _begin_balance(
        self,
        snapshot: BatchCharacteristicSnapshot | None = None,
    ) -> None:
        """Snapshot all Balance counts before any player makes a choice."""

        if snapshot is None:
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
        else:
            battlefield_by_id = {
                card.id: card
                for player in self.players
                for card in player.battlefield
            }
            lands = {
                player_id: tuple(
                    battlefield_by_id[card_id]
                    for card_id in card_ids
                    if card_id in battlefield_by_id
                )
                for player_id, card_ids in snapshot.balance_lands
            }
            creatures = {
                player_id: tuple(
                    battlefield_by_id[card_id]
                    for card_id in card_ids
                    if card_id in battlefield_by_id
                )
                for player_id, card_ids in snapshot.balance_creatures
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
        for player in self.players:
            self._discard_forced(
                player,
                (card for card in tuple(player.hand) if card.id in hand_ids),
                source_name="Balance",
            )
        if doomed:
            self.pending_destruction = DestructionIncident(
                [
                    DestructionTarget(card.id, card.name)
                    for card in doomed
                ]
            )
            self._open_destruction_incident()
        self.check_state_based_actions()
        self._resume_ordered_batch_hand_library_effects()
        return chosen

    def _next_interrupt_to_resolve(
        self,
    ) -> tuple[Card | None, AbilityOnStack | None]:
        """Select the next spell or activated interrupt under Beta ordering."""

        spell_interrupts = [
            (card, self.stack_spells[card.id])
            for card in self.stack
            if CardType.INTERRUPT in card.definition.card_types
        ]
        ability_interrupts = list(self.interrupt_abilities)
        interrupt_states: list[SpellOnStack | AbilityOnStack] = [
            state for _, state in spell_interrupts
        ]
        interrupt_states.extend(ability_interrupts)
        targeted_interrupt_ids = {
            target.id
            for state in interrupt_states
            for target in state.targets
            if isinstance(target, Card)
            and CardType.INTERRUPT in target.definition.card_types
        }
        candidates: list[
            tuple[
                Card | None,
                AbilityOnStack | None,
                SpellOnStack | AbilityOnStack,
            ]
        ] = [
            (card, None, state)
            for card, state in spell_interrupts
            if card.id not in targeted_interrupt_ids
        ]
        candidates.extend((None, state, state) for state in ability_interrupts)

        def interrupt_rank(
            candidate: tuple[
                Card | None,
                AbilityOnStack | None,
                SpellOnStack | AbilityOnStack,
            ]
        ) -> tuple[int, int, int]:
            _, _, state = candidate
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
            controller_id = (
                state.caster_id
                if isinstance(state, SpellOnStack)
                else state.controller_id
            )
            caster_first = int(controller_id == target_caster_id)
            return depth, caster_first, -state.declaration_sequence

        if not candidates:
            raise RuntimeError("there is no unresolved interrupt")
        interrupt, ability, _ = max(candidates, key=interrupt_rank)
        return interrupt, ability

    def _resolve_interrupt(self, interrupt: Card) -> tuple[Card, ...]:
        """Resolve the selected interrupt immediately, before its target."""

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
        if (
            legal_target
            and target is not None
            and target.zone is Zone.STACK
            and counter_effect is not None
            and counter_effect.x_equals_target_cost
        ):
            target_spell = self.stack_spells[target.id]
            legal_target = spell.x_value == self.spell_casting_cost_value(
                target, target_spell.x_value
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
            if self.pending_destruction is not None:
                self.suspended_destruction_incidents.append(
                    (
                        self.pending_destruction,
                        self.resume_interrupts_after_destruction,
                    )
                )
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
                    decision_maker_id=spell.decision_maker_id,
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
                    incident_window_mode=original.incident_window_mode,
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
        else:
            self._restore_pending_context_priority()
        if self.pending_destruction is not None:
            self._open_destruction_incident()
        self.check_state_based_actions()
        return (interrupt,)

    def _resolve_counter_ability(self, state: AbilityOnStack) -> None:
        """Resolve a Deathgrip/Lifeforce activation in the interrupt sequence."""

        self.interrupt_abilities.pop(
            next(
                index
                for index, candidate in enumerate(self.interrupt_abilities)
                if candidate is state
            )
        )
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
        else:
            self._restore_pending_context_priority()
        self.check_state_based_actions()

    def _snapshot_batch_spell_targets(
        self, spells: tuple[SpellOnStack, ...]
    ) -> tuple[
        dict[UUID, bool],
        dict[UUID, tuple[Card | PlayerState, ...]],
    ]:
        """Freeze spell target legality before the batch changes state."""

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
        return legal, legal_spell_targets

    def _snapshot_batch_ability_legality(
        self, abilities: tuple[AbilityOnStack, ...]
    ) -> tuple[bool, ...]:
        """Freeze activated-ability legality at batch resolution start."""

        return tuple(
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
        )

    def _snapshot_batch_legality(
        self,
        spells: tuple[SpellOnStack, ...],
        abilities: tuple[AbilityOnStack, ...],
    ) -> BatchLegalitySnapshot:
        """Capture all legality information used by a simultaneous batch."""

        spell_legality, spell_targets = self._snapshot_batch_spell_targets(
            spells
        )
        return BatchLegalitySnapshot(
            spell_legality,
            spell_targets,
            self._snapshot_batch_ability_legality(abilities),
        )

    def _describe_batch_intents(
        self,
        spells: tuple[SpellOnStack, ...],
        abilities: tuple[AbilityOnStack, ...],
        legality: BatchLegalitySnapshot,
    ) -> tuple[BatchEffectIntent, ...]:
        """Describe the legal operations in a batch without applying them."""

        intents: list[BatchEffectIntent] = []
        for spell in spells:
            card = spell.card
            if not legality.spells[card.id]:
                continue
            targets = legality.spell_targets[card.id]
            if card.definition.is_permanent:
                intents.append(
                    BatchEffectIntent(
                        BatchIntentKind.PERMANENT_ENTRY,
                        card,
                        spell.caster_id,
                        spell.decision_maker_id,
                        targets,
                        card.definition,
                        spell.declaration_sequence,
                    )
                )
                continue
            for operation_index, effect in enumerate(
                card.definition.spell_effects
            ):
                intents.append(
                    BatchEffectIntent(
                        BatchIntentKind.SPELL_EFFECT,
                        card,
                        spell.caster_id,
                        spell.decision_maker_id,
                        targets,
                        effect,
                        spell.declaration_sequence,
                        operation_index,
                    )
                )

        for declared, is_legal in zip(abilities, legality.abilities):
            if not is_legal:
                continue
            intents.append(
                BatchEffectIntent(
                    BatchIntentKind.ACTIVATED_ABILITY,
                    declared.source,
                    declared.controller_id,
                    declared.controller_id,
                    declared.targets,
                    declared.ability,
                    declared.declaration_sequence,
                )
            )

        # Sorting is stable. The operation index orders multiple effects on one
        # spell, while the declaration sequence interleaves spells and
        # activated abilities that are stored separately by the live engine.
        return tuple(
            sorted(
                intents,
                key=lambda intent: (
                    intent.declaration_sequence,
                    intent.operation_index,
                ),
            )
        )

    def _plan_batch_resolution(self) -> BatchResolutionPlan:
        """Freeze a read-only description of the next batch resolution."""

        cards = tuple(self.stack)
        spells = tuple(self.stack_spells[card.id] for card in cards)
        abilities = tuple(self.batch_abilities)
        legality = self._snapshot_batch_legality(spells, abilities)
        return BatchResolutionPlan(
            cards=cards,
            spells=spells,
            abilities=abilities,
            legality=legality,
            caught_event_ids=frozenset(
                event.id for event in self.event_opportunities
            ),
            intents=self._describe_batch_intents(spells, abilities, legality),
        )

    def _detect_batch_conflicts(
        self, plan: BatchResolutionPlan
    ) -> tuple[BatchConflict, ...]:
        """Return recognized batch paradoxes that need an ordering choice."""

        writes_by_target: dict[UUID, list[tuple[int, Zone]]] = {}
        cards_by_id: dict[UUID, Card] = {}
        for intent_index, intent in enumerate(plan.intents):
            destination = self._batch_intent_destination(intent)
            if destination is None:
                continue
            for target in self._batch_destination_targets(intent):
                cards_by_id[target.id] = target
                writes_by_target.setdefault(target.id, []).append(
                    (intent_index, destination)
                )

        grouped_targets: dict[
            tuple[tuple[int, ...], str], list[UUID]
        ] = {}
        for target_id, writes in writes_by_target.items():
            if len({destination for _, destination in writes}) < 2:
                continue
            # Effects naming the same destination are one simultaneous cohort;
            # only the order between distinct destinations matters.
            representative_by_destination: dict[Zone, int] = {}
            for intent_index, destination in writes:
                representative_by_destination.setdefault(
                    destination, intent_index
                )
            intent_indexes = tuple(representative_by_destination.values())
            last_index = max(
                (index for index, _ in writes),
                key=lambda index: (
                    plan.intents[index].declaration_sequence,
                    plan.intents[index].operation_index,
                ),
            )
            chooser_id = plan.intents[last_index].controller_id
            grouped_targets.setdefault(
                (intent_indexes, chooser_id), []
            ).append(target_id)

        destination_conflicts: list[BatchConflict] = []
        for (intent_indexes, chooser_id), target_ids in grouped_targets.items():
            target_names = ", ".join(
                cards_by_id[target_id].name for target_id in target_ids
            )
            destination_conflicts.append(
                BatchConflict(
                    intent_indexes=intent_indexes,
                    chooser_id=chooser_id,
                    reason=f"Conflicting destinations for {target_names}",
                    kind=BatchConflictKind.DESTINATION,
                    target_ids=tuple(target_ids),
                )
            )
        conflicts: list[BatchConflict] = []
        conflicts.extend(self._detect_batch_tapped_state_conflicts(plan))
        power_conflicts = self._detect_batch_power_conflicts(plan)
        conflicts.extend(self._detect_batch_hand_library_conflicts(plan))
        conflicts.extend(self._detect_batch_land_type_conflicts(plan))
        conflicts.extend(self._detect_batch_turn_sequence_conflicts(plan))
        power_read_conflicts = self._detect_batch_power_read_conflicts(plan)
        aura_entry_conflicts = self._detect_batch_aura_entry_conflicts(plan)
        copy_entry_conflicts = self._detect_batch_copy_entry_conflicts(plan)
        characteristic_conflicts = (
            self._detect_batch_characteristic_conflicts(plan)
        )
        conflicts.extend(
            conflict
            for conflict in destination_conflicts
            if not any(
                set(conflict.intent_indexes) <= set(entry.intent_indexes)
                for entry in (*aura_entry_conflicts, *copy_entry_conflicts)
            )
        )
        # A Swords read component already orders all of its power modifiers.
        # Asking for a second order for the same modifier component could let
        # the two dialogs record contradictory answers.
        conflicts.extend(
            conflict
            for conflict in power_conflicts
            if not any(
                set(conflict.intent_indexes) <= set(read.intent_indexes)
                for read in power_read_conflicts
            )
        )
        conflicts.extend(
            conflict
            for conflict in aura_entry_conflicts
            if not any(
                set(conflict.intent_indexes) <= set(read.intent_indexes)
                for read in power_read_conflicts
            )
        )
        conflicts.extend(copy_entry_conflicts)
        conflicts.extend(
            conflict
            for conflict in characteristic_conflicts
            if not any(
                set(conflict.intent_indexes) <= set(other.intent_indexes)
                for other in (
                    *destination_conflicts,
                    *aura_entry_conflicts,
                    *copy_entry_conflicts,
                )
            )
        )
        conflicts.extend(power_read_conflicts)
        return tuple(conflicts)

    @staticmethod
    def _batch_intent_is_battlefield_aura_entry(
        intent: BatchEffectIntent,
    ) -> bool:
        """Whether an intent attaches an Aura to a permanent in play."""

        definition = intent.source.definition
        return bool(
            intent.kind is BatchIntentKind.PERMANENT_ENTRY
            and not definition.copies_artifact
            and not definition.copies_creature
            and not definition.animates_dead_creature
            and any(
                subtype.startswith("Enchant ")
                for subtype in definition.subtypes
            )
            and any(
                isinstance(target, Card)
                and target.zone is Zone.BATTLEFIELD
                for target in intent.targets
            )
        )

    def _detect_batch_aura_entry_conflicts(
        self, plan: BatchResolutionPlan
    ) -> tuple[BatchConflict, ...]:
        """Find Aura entries ordered against removal of their targets."""

        return self._detect_batch_targeted_entry_conflicts(
            plan,
            self._batch_intent_is_battlefield_aura_entry,
            BatchConflictKind.AURA_ENTRY,
            "Aura attachment and removal of ",
        )

    @staticmethod
    def _batch_intent_is_copy_entry(intent: BatchEffectIntent) -> bool:
        """Whether a permanent spell copies its chosen battlefield card."""

        definition = intent.source.definition
        return bool(
            intent.kind is BatchIntentKind.PERMANENT_ENTRY
            and (definition.copies_artifact or definition.copies_creature)
            and any(
                isinstance(target, Card)
                and target.zone is Zone.BATTLEFIELD
                for target in intent.targets
            )
        )

    def _detect_batch_copy_entry_conflicts(
        self, plan: BatchResolutionPlan
    ) -> tuple[BatchConflict, ...]:
        """Find copy entries ordered against removal of their chosen model."""

        return self._detect_batch_targeted_entry_conflicts(
            plan,
            self._batch_intent_is_copy_entry,
            BatchConflictKind.COPY_ENTRY,
            "Copying and removal of ",
        )

    def _detect_batch_targeted_entry_conflicts(
        self,
        plan: BatchResolutionPlan,
        is_entry: Callable[[BatchEffectIntent], bool],
        kind: BatchConflictKind,
        reason_prefix: str,
    ) -> tuple[BatchConflict, ...]:
        """Find targeted permanent entries ordered against target removal."""

        adjacency: dict[int, set[int]] = {}
        pair_targets: dict[frozenset[int], set[UUID]] = {}
        cards_by_id: dict[UUID, Card] = {}
        for entry_index, entry_intent in enumerate(plan.intents):
            if not is_entry(entry_intent):
                continue
            for target in entry_intent.targets:
                if not isinstance(target, Card):
                    continue
                removal_indexes = tuple(
                    index
                    for index, intent in enumerate(plan.intents)
                    if index != entry_index
                    and self._batch_intent_destination(intent)
                    not in {None, Zone.BATTLEFIELD}
                    and target in self._batch_destination_targets(intent)
                )
                if not removal_indexes:
                    continue
                cards_by_id[target.id] = target
                for removal_index in removal_indexes:
                    adjacency.setdefault(entry_index, set()).add(removal_index)
                    adjacency.setdefault(removal_index, set()).add(entry_index)
                    pair_targets.setdefault(
                        frozenset({entry_index, removal_index}), set()
                    ).add(target.id)

        conflicts: list[BatchConflict] = []
        remaining = set(adjacency)
        while remaining:
            seed = min(remaining)
            component: set[int] = set()
            pending = [seed]
            while pending:
                index = pending.pop()
                if index in component:
                    continue
                component.add(index)
                pending.extend(adjacency.get(index, ()))
            remaining.difference_update(component)
            intent_indexes = tuple(
                sorted(
                    component,
                    key=lambda index: (
                        plan.intents[index].declaration_sequence,
                        plan.intents[index].operation_index,
                    ),
                )
            )
            target_ids = tuple(
                card_id
                for card_id in cards_by_id
                if any(
                    pair <= component and card_id in targets
                    for pair, targets in pair_targets.items()
                )
            )
            last_index = intent_indexes[-1]
            conflicts.append(
                BatchConflict(
                    intent_indexes=intent_indexes,
                    chooser_id=plan.intents[last_index].controller_id,
                    reason=(
                        reason_prefix
                        + ", ".join(
                            cards_by_id[target_id].name
                            for target_id in target_ids
                        )
                    ),
                    kind=kind,
                    target_ids=target_ids,
                )
            )
        return tuple(conflicts)

    def _batch_characteristic_snapshot(
        self, intent: BatchEffectIntent
    ) -> BatchCharacteristicSnapshot | None:
        """Describe values an effect reads from current characteristics."""

        operation = intent.operation
        battlefield = tuple(
            permanent
            for player in self.players
            for permanent in player.battlefield
        )
        if isinstance(operation, DestroyAllEffect):
            resolved = replace(
                operation,
                subtypes=frozenset(
                    self.land_word(intent.source, subtype)
                    for subtype in operation.subtypes
                ),
            )
            targets = tuple(
                permanent
                for permanent in battlefield
                if resolved.matches(
                    permanent,
                    current_card_types=self.card_types(permanent),
                    current_subtypes=(
                        self.land_subtypes(permanent)
                        if CardType.LAND in permanent.definition.card_types
                        else None
                    ),
                )
            )
            return BatchCharacteristicSnapshot(
                target_ids=tuple(card.id for card in targets)
            )
        if isinstance(operation, ActivatedDestroyAllAbility):
            return BatchCharacteristicSnapshot(
                target_ids=tuple(
                    permanent.id
                    for permanent in battlefield
                    if self.card_types(permanent) & operation.card_types
                )
            )
        if isinstance(operation, (GlobalDamageEffect, ActivatedGlobalDamageAbility)):
            targets: list[Card] = []
            for permanent in battlefield:
                if CardType.CREATURE not in self.card_types(permanent):
                    continue
                if isinstance(operation, GlobalDamageEffect):
                    flying = KeywordAbility.FLYING in self.creature_abilities(
                        permanent
                    )
                    if (
                        operation.creatures_with_flying is not None
                        and flying is not operation.creatures_with_flying
                    ):
                        continue
                targets.append(permanent)
            return BatchCharacteristicSnapshot(
                target_ids=tuple(card.id for card in targets)
            )
        if isinstance(operation, DrainLifeEffect):
            toughness = tuple(
                (target.id, self.creature_toughness(target))
                for target in intent.targets
                if isinstance(target, Card)
            )
            return BatchCharacteristicSnapshot(
                target_ids=tuple(card_id for card_id, _ in toughness),
                toughness_by_target=toughness,
            )
        if isinstance(operation, BalanceEffect):
            return BatchCharacteristicSnapshot(
                balance_lands=tuple(
                    (
                        player.id,
                        tuple(
                            card.id
                            for card in player.battlefield
                            if CardType.LAND in self.card_types(card)
                        ),
                    )
                    for player in self.players
                ),
                balance_creatures=tuple(
                    (
                        player.id,
                        tuple(
                            card.id
                            for card in player.battlefield
                            if CardType.CREATURE in self.card_types(card)
                        ),
                    )
                    for player in self.players
                ),
            )
        return None

    @staticmethod
    def _batch_characteristic_snapshot_ids(
        snapshot: BatchCharacteristicSnapshot,
    ) -> set[UUID]:
        """Return all battlefield object ids represented by a snapshot."""

        return (
            set(snapshot.target_ids)
            | {card_id for card_id, _ in snapshot.toughness_by_target}
            | {
                card_id
                for _, card_ids in snapshot.balance_lands
                for card_id in card_ids
            }
            | {
                card_id
                for _, card_ids in snapshot.balance_creatures
                for card_id in card_ids
            }
        )

    def _detect_batch_characteristic_conflicts(
        self, plan: BatchResolutionPlan
    ) -> tuple[BatchConflict, ...]:
        """Find effects whose result changes with battlefield characteristics."""

        readers = tuple(
            (index, snapshot)
            for index, intent in enumerate(plan.intents)
            if (snapshot := self._batch_characteristic_snapshot(intent))
            is not None
        )
        adjacency: dict[int, set[int]] = {}
        pair_targets: dict[frozenset[int], set[UUID]] = {}
        for reader_index, baseline in readers:
            for writer_index in range(len(plan.intents)):
                if writer_index == reader_index:
                    continue
                projected = self._project_batch_characteristic_snapshot(
                    plan,
                    plan.intents[reader_index],
                    (writer_index,),
                )
                if projected == baseline:
                    continue
                changed_ids = (
                    self._batch_characteristic_snapshot_ids(baseline)
                    ^ self._batch_characteristic_snapshot_ids(projected)
                )
                reader = plan.intents[reader_index]
                writer = plan.intents[writer_index]
                if (
                    isinstance(
                        reader.operation,
                        (DestroyAllEffect, ActivatedDestroyAllAbility),
                    )
                    and self._batch_intent_destination(writer)
                    is Zone.GRAVEYARD
                    and changed_ids
                    <= {
                        target.id
                        for target in self._batch_destination_targets(writer)
                    }
                ):
                    # Both effects destroy the same objects. Regeneration
                    # permissions are combined later, so their order cannot
                    # alter the result.
                    continue
                adjacency.setdefault(reader_index, set()).add(writer_index)
                adjacency.setdefault(writer_index, set()).add(reader_index)
                pair_targets.setdefault(
                    frozenset({reader_index, writer_index}), set()
                ).update(changed_ids)

        conflicts: list[BatchConflict] = []
        remaining = set(adjacency)
        while remaining:
            seed = min(remaining)
            component: set[int] = set()
            pending = [seed]
            while pending:
                intent_index = pending.pop()
                if intent_index in component:
                    continue
                component.add(intent_index)
                pending.extend(adjacency.get(intent_index, ()))
            remaining.difference_update(component)
            intent_indexes = tuple(
                sorted(
                    component,
                    key=lambda index: (
                        plan.intents[index].declaration_sequence,
                        plan.intents[index].operation_index,
                    ),
                )
            )
            target_ids = tuple(
                dict.fromkeys(
                    target_id
                    for pair, targets in pair_targets.items()
                    if pair <= component
                    for target_id in targets
                )
            )
            last_index = intent_indexes[-1]
            names_by_id = {
                card.id: card.name
                for player in self.players
                for card in player.battlefield
            }
            names_by_id.update(
                {card.id: card.name for card in plan.cards}
            )
            names = ", ".join(
                names_by_id[target_id]
                for target_id in target_ids
                if target_id in names_by_id
            )
            conflicts.append(
                BatchConflict(
                    intent_indexes=intent_indexes,
                    chooser_id=plan.intents[last_index].controller_id,
                    reason=(
                        "Characteristic-dependent effects"
                        + (f" involving {names}" if names else "")
                    ),
                    kind=BatchConflictKind.CHARACTERISTICS,
                    target_ids=target_ids,
                )
            )
        return tuple(conflicts)

    @staticmethod
    def _batch_intent_reads_power(intent: BatchEffectIntent) -> bool:
        """Whether an intent reads current power while it resolves."""

        return (
            isinstance(intent.operation, ExileTargetsEffect)
            and intent.operation.controller_gains_life_equal_to_power
        )

    def _batch_intent_can_change_battlefield_power(
        self,
        plan: BatchResolutionPlan,
        intent: BatchEffectIntent,
        target: Card,
    ) -> bool:
        """Conservatively identify operations that can change a power read.

        The final relevance check compares a projected battlefield with the
        current one.  Direct modifiers are retained even when the creature's
        current power happens to make their immediate numerical result equal;
        another ordered modifier may make that distinction matter.
        """

        if self._batch_intent_power_transform(plan, intent, target) is not None:
            return True
        operation = intent.operation
        if isinstance(operation, ActivatedAnimationAbility):
            return intent.source is target
        if isinstance(operation, ActivatedCreateTokenAbility):
            return True
        if isinstance(operation, ActivatedLandTypeAbility):
            return True
        if intent.kind is BatchIntentKind.PERMANENT_ENTRY:
            return True
        destination = self._batch_intent_destination(intent)
        if destination is not None:
            affected = self._batch_destination_targets(intent)
            # Competing destinations for the Swords target itself already use
            # the destination paradox pathway.  This conflict is about other
            # state changes altering the value Swords reads.
            return target not in affected and (
                destination is Zone.BATTLEFIELD
                or any(card.zone is Zone.BATTLEFIELD for card in affected)
            )
        return False

    def _projected_reconcile_control(self) -> None:
        """Reconcile control inside a temporary batch-power projection."""

        battlefield = [
            permanent
            for player in self.players
            for permanent in player.battlefield
        ]
        desired = {
            permanent.id: (
                permanent.base_controller_id
                or permanent.controller_id
                or permanent.owner_id
            )
            for permanent in battlefield
        }
        control_auras = sorted(
            (
                source
                for source in battlefield
                if source.enchanted_card_id is not None
                and any(
                    effect.controls_attached_card
                    for effect in source.definition.continuous_effects
                )
            ),
            key=lambda source: source.battlefield_entry_sequence or 0,
        )
        for aura in control_auras:
            if aura.enchanted_card_id in desired:
                desired[aura.enchanted_card_id] = (
                    aura.controller_id or aura.owner_id
                )
        for permanent in tuple(battlefield):
            controller_id = desired[permanent.id]
            if permanent.controller_id == controller_id:
                continue
            for player in self.players:
                if permanent in player.battlefield:
                    player.battlefield.remove(permanent)
                    break
            permanent.controller_id = controller_id
            self.player(controller_id).battlefield.append(permanent)

    def _apply_projected_power_intent(
        self, plan: BatchResolutionPlan, intent: BatchEffectIntent
    ) -> None:
        """Apply only the characteristic-relevant part of one intent."""

        operation = intent.operation
        tapped = self._batch_intent_tapped_state(plan, intent)
        if tapped is not None and intent.kind is not BatchIntentKind.PERMANENT_ENTRY:
            for target in self._batch_tapped_state_targets(plan, intent):
                target.tapped = tapped
            return
        destination = self._batch_intent_destination(intent)
        if destination is not None:
            for card in self._batch_destination_targets(intent):
                for player in self.players:
                    if card in player.battlefield:
                        player.battlefield.remove(card)
                card.zone = destination
                if destination is Zone.BATTLEFIELD:
                    card.controller_id = intent.controller_id
                    self.player(intent.controller_id).battlefield.append(card)
            self._projected_reconcile_control()
            return

        if isinstance(operation, TemporaryPumpEffect):
            spell = next(
                spell for spell in plan.spells if spell.card is intent.source
            )
            for target in intent.targets:
                if not isinstance(target, Card):
                    continue
                self.battlefield_entry_sequence += 1
                self.temporary_creature_effects.setdefault(target.id, []).append(
                    replace(
                        ContinuousEffect(
                            power=(
                                operation.power
                                + operation.power_per_x * spell.x_value
                            ),
                            toughness=(
                                operation.toughness
                                + operation.toughness_per_x * spell.x_value
                            ),
                            power_multiplier=operation.power_multiplier,
                            granted_abilities=operation.granted_abilities,
                        ),
                        application_sequence=self.battlefield_entry_sequence,
                    )
                )
            return
        if isinstance(operation, ActivatedPumpAbility):
            for target in intent.targets:
                if not isinstance(target, Card):
                    continue
                self.battlefield_entry_sequence += 1
                self.temporary_creature_effects.setdefault(target.id, []).append(
                    replace(
                        ContinuousEffect(
                            power=operation.power,
                            toughness=operation.toughness,
                            granted_abilities=operation.granted_abilities,
                        ),
                        application_sequence=self.battlefield_entry_sequence,
                    )
                )
            return
        if isinstance(operation, ActivatedAnimationAbility):
            self.battlefield_entry_sequence += 1
            self.combat_creature_effects.setdefault(intent.source.id, []).append(
                replace(
                    ContinuousEffect(
                        granted_card_types=frozenset({CardType.CREATURE}),
                        base_power=operation.power,
                        base_toughness=operation.toughness,
                    ),
                    application_sequence=self.battlefield_entry_sequence,
                )
            )
            return
        if isinstance(operation, ActivatedLandTypeAbility):
            for land in intent.targets:
                if not isinstance(land, Card):
                    continue
                self.battlefield_entry_sequence += 1
                land.land_type_marks[intent.source.id] = (
                    operation.replacement_subtype,
                    self.battlefield_entry_sequence,
                )
            return
        if isinstance(operation, ActivatedCreateTokenAbility):
            token = Card(
                operation.token_definition,
                intent.controller_id,
                controller_id=intent.controller_id,
                zone=Zone.BATTLEFIELD,
                is_token=True,
            )
            self.battlefield_entry_sequence += 1
            token.battlefield_entry_sequence = self.battlefield_entry_sequence
            self.player(intent.controller_id).battlefield.append(token)
            return
        if intent.kind is not BatchIntentKind.PERMANENT_ENTRY:
            return

        source = intent.source
        self.battlefield_entry_sequence += 1
        source.zone = Zone.BATTLEFIELD
        source.controller_id = intent.controller_id
        source.battlefield_entry_sequence = self.battlefield_entry_sequence
        card_target = next(
            (target for target in intent.targets if isinstance(target, Card)),
            None,
        )
        source.enchanted_card_id = card_target.id if card_target is not None else None
        self.player(intent.controller_id).battlefield.append(source)
        if source.definition.taps_attached_on_entry and card_target is not None:
            card_target.tapped = True
        if source.definition.animates_dead_creature and card_target is not None:
            for player in self.players:
                if card_target in player.graveyard:
                    player.graveyard.remove(card_target)
            card_target.zone = Zone.BATTLEFIELD
            card_target.controller_id = intent.controller_id
            self.player(intent.controller_id).battlefield.append(card_target)
        self._projected_reconcile_control()

    def _project_batch_state(
        self,
        plan: BatchResolutionPlan,
        intent_indexes: tuple[int, ...],
        read,
    ):
        """Apply selected intents to a reversible characteristic projection."""

        zone_lists = {
            player.id: {
                zone: list(player.cards_in(zone))
                for zone in (
                    Zone.LIBRARY,
                    Zone.HAND,
                    Zone.BATTLEFIELD,
                    Zone.GRAVEYARD,
                    Zone.EXILE,
                    Zone.ANTE,
                )
            }
            for player in self.players
        }
        cards = {
            card
            for zones in zone_lists.values()
            for cards_in_zone in zones.values()
            for card in cards_in_zone
        } | set(plan.cards)
        card_state = {
            card: (
                card.zone,
                card.controller_id,
                card.enchanted_card_id,
                card.battlefield_entry_sequence,
                dict(card.land_type_marks),
                card.tapped,
            )
            for card in cards
        }
        temporary = {
            card_id: list(effects)
            for card_id, effects in self.temporary_creature_effects.items()
        }
        combat = {
            card_id: list(effects)
            for card_id, effects in self.combat_creature_effects.items()
        }
        sequence = self.battlefield_entry_sequence
        try:
            for intent_index in intent_indexes:
                self._apply_projected_power_intent(
                    plan, plan.intents[intent_index]
                )
            return read()
        finally:
            for player in self.players:
                for zone, saved in zone_lists[player.id].items():
                    player.cards_in(zone)[:] = saved
            for card, state in card_state.items():
                (
                    card.zone,
                    card.controller_id,
                    card.enchanted_card_id,
                    card.battlefield_entry_sequence,
                    marks,
                    card.tapped,
                ) = state
                card.land_type_marks.clear()
                card.land_type_marks.update(marks)
            self.temporary_creature_effects.clear()
            self.temporary_creature_effects.update(temporary)
            self.combat_creature_effects.clear()
            self.combat_creature_effects.update(combat)
            self.battlefield_entry_sequence = sequence

    def _project_batch_swords_values(
        self,
        plan: BatchResolutionPlan,
        target: Card,
        intent_indexes: tuple[int, ...],
    ) -> tuple[int, str]:
        """Read Swords' power and controller from a reversible projection."""

        return self._project_batch_state(
            plan,
            intent_indexes,
            lambda: (
                self.creature_power(target),
                target.controller_id or target.owner_id,
            ),
        )

    def _project_batch_characteristic_snapshot(
        self,
        plan: BatchResolutionPlan,
        reader: BatchEffectIntent,
        prior_intent_indexes: tuple[int, ...],
    ) -> BatchCharacteristicSnapshot:
        """Read one effect after applying earlier intents reversibly."""

        snapshot = self._project_batch_state(
            plan,
            prior_intent_indexes,
            lambda: self._batch_characteristic_snapshot(reader),
        )
        assert snapshot is not None
        return snapshot

    def _detect_batch_power_read_conflicts(
        self, plan: BatchResolutionPlan
    ) -> tuple[BatchConflict, ...]:
        """Find effects that can change values observed by Swords."""

        adjacency: dict[int, set[int]] = {}
        pair_targets: dict[frozenset[int], set[UUID]] = {}
        cards_by_id: dict[UUID, Card] = {}
        readers = tuple(
            (index, intent)
            for index, intent in enumerate(plan.intents)
            if self._batch_intent_reads_power(intent)
        )
        for reader_index, reader in readers:
            for target in reader.targets:
                if not isinstance(target, Card):
                    continue
                cards_by_id[target.id] = target
                baseline = (
                    self.creature_power(target),
                    target.controller_id or target.owner_id,
                )
                for writer_index, writer in enumerate(plan.intents):
                    if writer_index == reader_index or not (
                        self._batch_intent_can_change_battlefield_power(
                            plan, writer, target
                        )
                    ):
                        continue
                    direct = self._batch_intent_power_transform(
                        plan, writer, target
                    ) is not None
                    projected = self._project_batch_swords_values(
                        plan, target, (writer_index,)
                    )
                    if not direct and projected == baseline:
                        continue
                    adjacency.setdefault(reader_index, set()).add(writer_index)
                    adjacency.setdefault(writer_index, set()).add(reader_index)
                    pair_targets.setdefault(
                        frozenset({reader_index, writer_index}), set()
                    ).add(target.id)

        conflicts: list[BatchConflict] = []
        remaining = set(adjacency)
        while remaining:
            seed = min(remaining)
            component: set[int] = set()
            pending = [seed]
            while pending:
                index = pending.pop()
                if index in component:
                    continue
                component.add(index)
                pending.extend(adjacency.get(index, ()))
            remaining.difference_update(component)
            intent_indexes = tuple(sorted(component))
            target_ids = tuple(
                target_id
                for target_id in cards_by_id
                if any(
                    pair <= component and target_id in target_ids_for_pair
                    for pair, target_ids_for_pair in pair_targets.items()
                )
            )
            last_index = max(
                intent_indexes,
                key=lambda index: (
                    plan.intents[index].declaration_sequence,
                    plan.intents[index].operation_index,
                ),
            )
            names = ", ".join(
                cards_by_id[target_id].name for target_id in target_ids
            )
            conflicts.append(
                BatchConflict(
                    intent_indexes=intent_indexes,
                    chooser_id=plan.intents[last_index].controller_id,
                    reason=f"Effects may change power read by Swords for {names}",
                    kind=BatchConflictKind.SWORDS_READ,
                    target_ids=target_ids,
                )
            )
        return tuple(conflicts)

    @staticmethod
    def _batch_intent_extra_turn_player(
        intent: BatchEffectIntent,
    ) -> str | None:
        """Return the player whose extra turn one intent creates."""

        if isinstance(
            intent.operation, (ExtraTurnEffect, ActivatedExtraTurnAbility)
        ):
            return intent.controller_id
        return None

    def _detect_batch_turn_sequence_conflicts(
        self, plan: BatchResolutionPlan
    ) -> tuple[BatchConflict, ...]:
        """Find extra-turn effects whose application order changes the queue."""

        extra_turns = tuple(
            (intent_index, player_id)
            for intent_index, intent in enumerate(plan.intents)
            if (
                player_id := self._batch_intent_extra_turn_player(intent)
            ) is not None
        )
        if len({player_id for _, player_id in extra_turns}) < 2:
            return ()

        intent_indexes = tuple(intent_index for intent_index, _ in extra_turns)
        last_index = max(
            intent_indexes,
            key=lambda index: (
                plan.intents[index].declaration_sequence,
                plan.intents[index].operation_index,
            ),
        )
        affected_player_ids = tuple(
            player.id
            for player in self.players
            if any(player.id == player_id for _, player_id in extra_turns)
        )
        names = ", ".join(
            self.player(player_id).name for player_id in affected_player_ids
        )
        return (
            BatchConflict(
                intent_indexes=intent_indexes,
                chooser_id=plan.intents[last_index].controller_id,
                reason=f"Competing extra turns for {names}",
                kind=BatchConflictKind.TURN_SEQUENCE,
                affected_player_ids=affected_player_ids,
            ),
        )

    def _batch_hand_library_footprint(
        self, plan: BatchResolutionPlan, intent: BatchEffectIntent
    ) -> dict[str, str]:
        """Map affected players to one hand/library operation category.

        The category is deliberately semantic rather than a raw read/write
        mask.  Drawing twice and drawing plus returning an external card to
        hand commute, while operations that inspect, remove, replace, or
        reorder the same resources generally do not.
        """

        operation = intent.operation
        player_ids = tuple(player.id for player in self.players)
        target_player_ids = tuple(
            target.id for target in intent.targets if not isinstance(target, Card)
        )
        if isinstance(
            operation,
            (DrawCardsEffect, ActivatedDrawAbility, ActivatedEventDrawAbility),
        ):
            affected = (
                (intent.controller_id,)
                if not isinstance(operation, DrawCardsEffect)
                else target_player_ids
            )
            return {player_id: "draw" for player_id in affected}
        if isinstance(operation, GainLifeEffect):
            return {
                player_id: "draw"
                for player_id in target_player_ids
                if self._lich_count(player_id)
            }
        if isinstance(operation, ActivatedEventLifeGainAbility):
            return (
                {intent.controller_id: "draw"}
                if self._lich_count(intent.controller_id)
                else {}
            )
        if isinstance(operation, DiscardCardsEffect):
            return {player_id: "discard" for player_id in target_player_ids}
        if isinstance(operation, ActivatedDiscardAbility):
            controller = self.player(intent.controller_id)
            opponent = self.players[
                (self.players.index(controller) + 1) % len(self.players)
            ]
            return {opponent.id: "discard"}
        if isinstance(operation, ActivatedRevealHandAbility):
            controller = self.player(intent.controller_id)
            opponent = self.players[
                (self.players.index(controller) + 1) % len(self.players)
            ]
            return {opponent.id: "inspect_hand"}
        if isinstance(operation, WordOfCommandEffect):
            controller = self.player(intent.controller_id)
            opponent = self.players[
                (self.players.index(controller) + 1) % len(self.players)
            ]
            return {opponent.id: "command_from_hand"}
        if isinstance(operation, DiscardHandsAndDrawEffect):
            return {
                player_id: f"replace_hand:{operation.draw_count}"
                for player_id in player_ids
            }
        if isinstance(operation, ShuffleHandAndGraveyardEffect):
            return {
                player_id: f"recycle:{operation.draw_count}"
                for player_id in player_ids
            }
        if isinstance(operation, DiscardHandAnteAndDrawEffect):
            return {
                intent.controller_id: f"ante_replace:{operation.draw_count}"
            }
        if isinstance(operation, SwapLibraryTopWithAnteEffect):
            return {intent.controller_id: "library_top"}
        if isinstance(operation, NaturalSelectionEffect):
            return {player_id: "library_order" for player_id in target_player_ids}
        if isinstance(operation, LibrarySearchEffect):
            return {intent.controller_id: "library_search"}
        if isinstance(operation, BalanceEffect):
            # Even a currently equal hand is read by Balance: an earlier draw
            # can change which player must discard.
            return {player_id: "balance" for player_id in player_ids}
        if isinstance(operation, MoveTargetsEffect) and operation.destination is Zone.HAND:
            return {
                target.owner_id: "add_to_hand"
                for target in intent.targets
                if isinstance(target, Card)
            }
        return {}

    @staticmethod
    def _batch_hand_library_operations_commute(first: str, second: str) -> bool:
        """Whether two operations can be simultaneous without a paradox."""

        first_kind = first.partition(":")[0]
        second_kind = second.partition(":")[0]
        additive = {"draw", "add_to_hand"}
        if first_kind in additive and second_kind in additive:
            return True
        if first == second and first_kind in {
            "replace_hand",
            "recycle",
            "ante_replace",
            "balance",
        }:
            return True
        if first_kind == second_kind == "inspect_hand":
            return True
        # Moving an external card to hand does not interact with an operation
        # that only inspects or rearranges the library.
        library_only = {"library_top", "library_order", "library_search"}
        if (
            first_kind == "add_to_hand" and second_kind in library_only
            or second_kind == "add_to_hand" and first_kind in library_only
        ):
            return True
        # Merely looking at a hand, or choosing a card already in it for
        # Word, does not alter the top or order of that player's library.
        # A search is deliberately excluded because it puts a new card into
        # the hand being inspected/commanded.
        passive_library_only = {"library_top", "library_order"}
        hand_readers = {"inspect_hand", "command_from_hand"}
        if (
            first_kind in hand_readers and second_kind in passive_library_only
            or second_kind in hand_readers and first_kind in passive_library_only
        ):
            return True
        return False

    def _detect_batch_hand_library_conflicts(
        self, plan: BatchResolutionPlan
    ) -> tuple[BatchConflict, ...]:
        """Find connected hand/library operations whose ordering matters."""

        footprints = {
            intent_index: self._batch_hand_library_footprint(plan, intent)
            for intent_index, intent in enumerate(plan.intents)
        }
        adjacency: dict[int, set[int]] = {}
        conflict_players: dict[frozenset[int], set[str]] = {}
        indexes = tuple(index for index, footprint in footprints.items() if footprint)
        for position, first_index in enumerate(indexes):
            for second_index in indexes[position + 1:]:
                shared = set(footprints[first_index]) & set(footprints[second_index])
                noncommuting = {
                    player_id
                    for player_id in shared
                    if not self._batch_hand_library_operations_commute(
                        footprints[first_index][player_id],
                        footprints[second_index][player_id],
                    )
                }
                if not noncommuting:
                    continue
                adjacency.setdefault(first_index, set()).add(second_index)
                adjacency.setdefault(second_index, set()).add(first_index)
                conflict_players[frozenset({first_index, second_index})] = noncommuting

        conflicts: list[BatchConflict] = []
        remaining = set(adjacency)
        while remaining:
            seed = min(remaining)
            component: set[int] = set()
            pending = [seed]
            while pending:
                intent_index = pending.pop()
                if intent_index in component:
                    continue
                component.add(intent_index)
                pending.extend(adjacency.get(intent_index, ()))
            remaining.difference_update(component)
            intent_indexes = tuple(sorted(component))
            affected_player_ids = tuple(
                player.id
                for player in self.players
                if any(
                    pair <= component and player.id in pair_players
                    for pair, pair_players in conflict_players.items()
                )
            )
            last_index = max(
                intent_indexes,
                key=lambda index: (
                    plan.intents[index].declaration_sequence,
                    plan.intents[index].operation_index,
                ),
            )
            names = ", ".join(
                self.player(player_id).name for player_id in affected_player_ids
            )
            conflicts.append(
                BatchConflict(
                    intent_indexes=intent_indexes,
                    chooser_id=plan.intents[last_index].controller_id,
                    reason=f"Conflicting hand or library effects for {names}",
                    kind=BatchConflictKind.HAND_LIBRARY,
                    affected_player_ids=affected_player_ids,
                )
            )
        return tuple(conflicts)

    def _batch_intent_land_type_setting(
        self, intent: BatchEffectIntent
    ) -> str | None:
        """Return the basic subtype unconditionally set by one intent."""

        operation = intent.operation
        if isinstance(operation, ActivatedLandTypeAbility):
            return operation.replacement_subtype
        if intent.kind is not BatchIntentKind.PERMANENT_ENTRY:
            return None
        for effect in intent.source.definition.land_type_effects:
            if not isinstance(effect, AttachedLandTypeEffect):
                continue
            return (
                intent.source.chosen_land_subtype
                if effect.chosen_basic_subtype
                else self.land_word(intent.source, effect.replacement_subtype)
            )
        return None

    def _batch_land_type_targets(
        self, intent: BatchEffectIntent
    ) -> tuple[Card, ...]:
        if self._batch_intent_land_type_setting(intent) is None:
            return ()
        return tuple(
            target
            for target in intent.targets
            if isinstance(target, Card)
            and CardType.LAND in self.card_types(target)
        )

    def _detect_batch_land_type_conflicts(
        self, plan: BatchResolutionPlan
    ) -> tuple[BatchConflict, ...]:
        """Find lands being set to competing basic types in one batch."""

        writes_by_target: dict[UUID, list[tuple[int, str]]] = {}
        cards_by_id: dict[UUID, Card] = {}
        for intent_index, intent in enumerate(plan.intents):
            replacement = self._batch_intent_land_type_setting(intent)
            if replacement is None:
                continue
            for target in self._batch_land_type_targets(intent):
                cards_by_id[target.id] = target
                writes_by_target.setdefault(target.id, []).append(
                    (intent_index, replacement)
                )

        adjacency: dict[int, set[int]] = {}
        conflict_targets: dict[frozenset[int], set[UUID]] = {}
        for target_id, writes in writes_by_target.items():
            for position, (first_index, first_type) in enumerate(writes):
                for second_index, second_type in writes[position + 1:]:
                    if first_type == second_type:
                        continue
                    adjacency.setdefault(first_index, set()).add(second_index)
                    adjacency.setdefault(second_index, set()).add(first_index)
                    conflict_targets.setdefault(
                        frozenset({first_index, second_index}), set()
                    ).add(target_id)

        conflicts: list[BatchConflict] = []
        remaining = set(adjacency)
        while remaining:
            seed = min(remaining)
            component: set[int] = set()
            pending = [seed]
            while pending:
                intent_index = pending.pop()
                if intent_index in component:
                    continue
                component.add(intent_index)
                pending.extend(adjacency.get(intent_index, ()))
            remaining.difference_update(component)
            intent_indexes = tuple(sorted(component))
            target_ids = tuple(
                target_id
                for target_id in cards_by_id
                if any(
                    pair <= component and target_id in pair_targets
                    for pair, pair_targets in conflict_targets.items()
                )
            )
            last_index = max(
                intent_indexes,
                key=lambda index: (
                    plan.intents[index].declaration_sequence,
                    plan.intents[index].operation_index,
                ),
            )
            conflicts.append(
                BatchConflict(
                    intent_indexes=intent_indexes,
                    chooser_id=plan.intents[last_index].controller_id,
                    reason=(
                        "Competing land-type settings for "
                        + ", ".join(
                            cards_by_id[target_id].name
                            for target_id in target_ids
                        )
                    ),
                    kind=BatchConflictKind.LAND_TYPE,
                    target_ids=target_ids,
                )
            )
        return tuple(conflicts)

    def _batch_intent_tapped_state(
        self, plan: BatchResolutionPlan, intent: BatchEffectIntent
    ) -> bool | None:
        operation = intent.operation
        if isinstance(operation, SetTappedEffect):
            spell = next(
                (
                    spell
                    for spell in plan.spells
                    if spell.card is intent.source
                ),
                None,
            )
            return spell.chosen_mode == "Tap" if spell is not None else None
        if isinstance(
            operation, (ActivatedTapAbility, TapLandsAndEmptyManaPoolEffect)
        ):
            return True
        if isinstance(operation, ActivatedUntapAbility):
            return False
        if (
            intent.kind is BatchIntentKind.PERMANENT_ENTRY
            and getattr(operation, "taps_attached_on_entry", False)
        ):
            return True
        return None

    def _batch_tapped_state_targets(
        self, plan: BatchResolutionPlan, intent: BatchEffectIntent
    ) -> tuple[Card, ...]:
        if isinstance(intent.operation, TapLandsAndEmptyManaPoolEffect):
            player_ids = {
                target.id
                for target in intent.targets
                if not isinstance(target, Card)
            }
            return tuple(
                permanent
                for player in self.players
                for permanent in player.battlefield
                if permanent.controller_id in player_ids
                and CardType.LAND in self.card_types(permanent)
            )
        return tuple(
            target for target in intent.targets if isinstance(target, Card)
        )

    def _detect_batch_tapped_state_conflicts(
        self, plan: BatchResolutionPlan
    ) -> tuple[BatchConflict, ...]:
        writes_by_target: dict[UUID, list[tuple[int, bool]]] = {}
        cards_by_id: dict[UUID, Card] = {}
        for intent_index, intent in enumerate(plan.intents):
            tapped = self._batch_intent_tapped_state(plan, intent)
            if tapped is None:
                continue
            for target in self._batch_tapped_state_targets(plan, intent):
                cards_by_id[target.id] = target
                writes_by_target.setdefault(target.id, []).append(
                    (intent_index, tapped)
                )

        grouped_targets: dict[
            tuple[tuple[int, ...], str], list[UUID]
        ] = {}
        for target_id, writes in writes_by_target.items():
            if len({tapped for _, tapped in writes}) < 2:
                continue
            intent_indexes = tuple(dict.fromkeys(index for index, _ in writes))
            last_index = max(
                intent_indexes,
                key=lambda index: (
                    plan.intents[index].declaration_sequence,
                    plan.intents[index].operation_index,
                ),
            )
            chooser_id = plan.intents[last_index].controller_id
            grouped_targets.setdefault(
                (intent_indexes, chooser_id), []
            ).append(target_id)

        return tuple(
            BatchConflict(
                intent_indexes=intent_indexes,
                chooser_id=chooser_id,
                reason=(
                    "Conflicting tap and untap effects for "
                    + ", ".join(
                        cards_by_id[target_id].name for target_id in target_ids
                    )
                ),
                kind=BatchConflictKind.TAPPED_STATE,
                target_ids=tuple(target_ids),
            )
            for (intent_indexes, chooser_id), target_ids
            in grouped_targets.items()
        )

    @staticmethod
    def _power_transform(power: int, multiplier: int) -> tuple[int, int]:
        """Return ``(slope, offset)`` for ``(power + bonus) * multiplier``."""

        return multiplier, power * multiplier

    @staticmethod
    def _power_transforms_commute(
        first: tuple[int, int], second: tuple[int, int]
    ) -> bool:
        """Whether two affine power changes give the same result in either order."""

        first_multiplier, first_offset = first
        second_multiplier, second_offset = second
        first_then_second = (
            second_multiplier * first_offset + second_offset
        )
        second_then_first = (
            first_multiplier * second_offset + first_offset
        )
        return first_then_second == second_then_first

    def _entry_power_effect_for_target(
        self,
        intent: BatchEffectIntent,
        effect: ContinuousEffect,
        target: Card,
    ) -> ContinuousEffect | None:
        """Resolve a new permanent's power effect against one current creature."""

        source = intent.source
        if effect.scope is EffectScope.ATTACHED_CARD:
            if target not in intent.targets:
                return None
        if effect.color is not None and self.color_word(
            source, effect.color
        ) not in self.card_colors(target):
            return None
        if effect.subtype is not None and self.land_word(
            source, effect.subtype
        ) not in target.definition.subtypes:
            return None
        if effect.land_subtype is not None:
            land_subtype = self.land_word(source, effect.land_subtype)
            if (
                CardType.LAND not in target.definition.card_types
                or land_subtype not in self.land_subtypes(target)
            ):
                return None
        if effect.exclude_source and source is target:
            return None
        if effect.source_only and source is not target:
            return None
        if effect.controller_only and target.controller_id != source.controller_id:
            return None
        attacking = self.combat is not None and target in self.combat.attackers
        if effect.attacking_only and not attacking:
            return None
        if effect.untapped_only and target.tapped:
            return None
        if effect.nonattacking_only and attacking:
            return None
        controller = self.player(source.controller_id or source.owner_id)
        if effect.controller_has_land_subtype is not None:
            required = self.land_word(
                source, effect.controller_has_land_subtype
            )
            if not any(
                CardType.LAND in permanent.definition.card_types
                and required in self.land_subtypes(permanent)
                for permanent in controller.battlefield
            ):
                return None
        if effect.counted_controller_land_subtype is not None:
            counted = self.land_word(
                source, effect.counted_controller_land_subtype
            )
            count = sum(
                CardType.LAND in permanent.definition.card_types
                and counted in self.land_subtypes(permanent)
                for permanent in controller.battlefield
            )
            effect = replace(
                effect,
                power=(
                    effect.power
                    + count * effect.power_per_count // effect.count_divisor
                ),
            )
        return effect

    def _batch_intent_power_transform(
        self,
        plan: BatchResolutionPlan,
        intent: BatchEffectIntent,
        target: Card,
    ) -> tuple[int, int] | None:
        """Describe one intent's current-power transformation for a target."""

        operation = intent.operation
        if isinstance(operation, TemporaryPumpEffect):
            spell = next(
                (
                    spell
                    for spell in plan.spells
                    if spell.card is intent.source
                ),
                None,
            )
            if spell is None or target not in intent.targets:
                return None
            power = operation.power + operation.power_per_x * spell.x_value
            transform = self._power_transform(
                power, operation.power_multiplier
            )
            return transform if transform != (1, 0) else None
        if isinstance(operation, ActivatedPumpAbility):
            if target not in intent.targets:
                return None
            transform = self._power_transform(operation.power, 1)
            return transform if transform != (1, 0) else None
        if intent.kind is not BatchIntentKind.PERMANENT_ENTRY:
            return None

        multiplier = 1
        offset = 0
        for effect in intent.source.definition.continuous_effects:
            resolved = self._entry_power_effect_for_target(
                intent, effect, target
            )
            if resolved is None:
                continue
            effect_transform = self._power_transform(
                resolved.power, resolved.power_multiplier
            )
            effect_multiplier, effect_offset = effect_transform
            offset = effect_multiplier * offset + effect_offset
            multiplier *= effect_multiplier
        transform = multiplier, offset
        return transform if transform != (1, 0) else None

    def _batch_power_modifier_targets(
        self, plan: BatchResolutionPlan, intent: BatchEffectIntent
    ) -> tuple[Card, ...]:
        if intent.kind is not BatchIntentKind.PERMANENT_ENTRY:
            return tuple(
                target for target in intent.targets if isinstance(target, Card)
            )
        return tuple(
            permanent
            for player in self.players
            for permanent in player.battlefield
            if CardType.CREATURE in self.card_types(permanent)
            and self._batch_intent_power_transform(
                plan, intent, permanent
            ) is not None
        )

    def _detect_batch_power_conflicts(
        self, plan: BatchResolutionPlan
    ) -> tuple[BatchConflict, ...]:
        """Find connected groups of power modifiers whose order changes power."""

        writes_by_target: dict[
            UUID, list[tuple[int, tuple[int, int]]]
        ] = {}
        cards_by_id: dict[UUID, Card] = {}
        for intent_index, intent in enumerate(plan.intents):
            for target in self._batch_power_modifier_targets(plan, intent):
                transform = self._batch_intent_power_transform(
                    plan, intent, target
                )
                if transform is None:
                    continue
                cards_by_id[target.id] = target
                writes_by_target.setdefault(target.id, []).append(
                    (intent_index, transform)
                )

        adjacency: dict[int, set[int]] = {}
        conflict_targets: dict[frozenset[int], set[UUID]] = {}
        for target_id, writes in writes_by_target.items():
            for position, (first_index, first) in enumerate(writes):
                for second_index, second in writes[position + 1:]:
                    if self._power_transforms_commute(first, second):
                        continue
                    adjacency.setdefault(first_index, set()).add(second_index)
                    adjacency.setdefault(second_index, set()).add(first_index)
                    conflict_targets.setdefault(
                        frozenset({first_index, second_index}), set()
                    ).add(target_id)

        conflicts: list[BatchConflict] = []
        remaining = set(adjacency)
        while remaining:
            seed = min(remaining)
            component: set[int] = set()
            pending = [seed]
            while pending:
                intent_index = pending.pop()
                if intent_index in component:
                    continue
                component.add(intent_index)
                pending.extend(adjacency.get(intent_index, ()))
            remaining.difference_update(component)
            intent_indexes = tuple(sorted(component))
            target_ids = tuple(
                target_id
                for target_id in cards_by_id
                if any(
                    pair <= component and target_id in pair_targets
                    for pair, pair_targets in conflict_targets.items()
                )
            )
            last_index = max(
                intent_indexes,
                key=lambda index: (
                    plan.intents[index].declaration_sequence,
                    plan.intents[index].operation_index,
                ),
            )
            names = ", ".join(cards_by_id[target_id].name for target_id in target_ids)
            conflicts.append(
                BatchConflict(
                    intent_indexes=intent_indexes,
                    chooser_id=plan.intents[last_index].controller_id,
                    reason=f"Noncommuting power modifiers for {names}",
                    kind=BatchConflictKind.POWER,
                    target_ids=target_ids,
                )
            )
        return tuple(conflicts)

    def _batch_intent_destination(
        self, intent: BatchEffectIntent
    ) -> Zone | None:
        operation = intent.operation
        if isinstance(
            operation,
            (
                DestroyTargetsEffect,
                DestroyAllEffect,
                ActivatedDestroyAbility,
                ActivatedDestroyAllAbility,
            ),
        ):
            return Zone.GRAVEYARD
        if isinstance(operation, MoveTargetsEffect):
            return operation.destination
        if isinstance(operation, ExileTargetsEffect):
            return Zone.EXILE
        if isinstance(operation, ActivatedGraveyardReturnAbility):
            return Zone.BATTLEFIELD
        return None

    def _batch_destination_targets(
        self, intent: BatchEffectIntent
    ) -> tuple[Card, ...]:
        operation = intent.operation
        if isinstance(operation, DestroyAllEffect):
            operation = replace(
                operation,
                subtypes=frozenset(
                    self.land_word(intent.source, subtype)
                    for subtype in operation.subtypes
                ),
            )
            return tuple(
                permanent
                for player in self.players
                for permanent in player.battlefield
                if operation.matches(
                    permanent,
                    current_card_types=self.card_types(permanent),
                    current_subtypes=(
                        self.land_subtypes(permanent)
                        if CardType.LAND in permanent.definition.card_types
                        else None
                    ),
                )
            )
        if isinstance(operation, ActivatedDestroyAllAbility):
            return tuple(
                permanent
                for player in self.players
                for permanent in player.battlefield
                if self.card_types(permanent) & operation.card_types
            )
        if isinstance(operation, ActivatedGraveyardReturnAbility):
            return (intent.source,)
        return tuple(
            target for target in intent.targets if isinstance(target, Card)
        )

    def batch_conflict_intent_label(
        self, choice: PendingBatchConflictChoice, intent_index: int
    ) -> str:
        """Describe one noncommuting operation for an engine or UI chooser."""

        plan = self.pending_batch_resolution
        if (
            plan is None
            or intent_index not in choice.intent_indexes_first_to_last
            or not 0 <= intent_index < len(plan.intents)
        ):
            raise ValueError("unknown batch intent")
        intent = plan.intents[intent_index]
        if choice.conflict.kind is BatchConflictKind.DESTINATION:
            destination = self._batch_intent_destination(intent)
            assert destination is not None
            result = destination.value
        elif choice.conflict.kind is BatchConflictKind.TAPPED_STATE:
            tapped = self._batch_intent_tapped_state(plan, intent)
            assert tapped is not None
            result = "tapped" if tapped else "untapped"
        elif choice.conflict.kind is BatchConflictKind.POWER:
            target = next(
                (
                    permanent
                    for player in self.players
                    for permanent in player.battlefield
                    if permanent.id in choice.conflict.target_ids
                    and self._batch_intent_power_transform(
                        plan, intent, permanent
                    ) is not None
                ),
                None,
            )
            assert target is not None
            multiplier, offset = self._batch_intent_power_transform(
                plan, intent, target
            ) or (1, 0)
            if multiplier == 1:
                result = f"{offset:+d} power"
            elif offset == 0:
                result = f"×{multiplier} power"
            else:
                result = f"×{multiplier} power with {offset:+d} offset"
        elif choice.conflict.kind is BatchConflictKind.HAND_LIBRARY:
            result = self._batch_hand_library_intent_label(plan, intent)
        elif choice.conflict.kind is BatchConflictKind.LAND_TYPE:
            replacement = self._batch_intent_land_type_setting(intent)
            assert replacement is not None
            result = f"set land type to {replacement}"
        elif choice.conflict.kind is BatchConflictKind.SWORDS_READ:
            if self._batch_intent_reads_power(intent):
                names = ", ".join(
                    target.name
                    for target in intent.targets
                    if isinstance(target, Card)
                    and target.id in choice.conflict.target_ids
                )
                result = f"read {names}'s power and controller, then exile it"
            else:
                destination = self._batch_intent_destination(intent)
                if destination is not None:
                    names = ", ".join(
                        target.name
                        for target in self._batch_destination_targets(intent)
                    )
                    result = f"move {names} to {destination.value}"
                elif isinstance(intent.operation, ActivatedLandTypeAbility):
                    result = (
                        "set land type to "
                        f"{intent.operation.replacement_subtype}"
                    )
                elif isinstance(intent.operation, ActivatedCreateTokenAbility):
                    result = f"create {intent.operation.token_definition.name}"
                elif intent.kind is BatchIntentKind.PERMANENT_ENTRY:
                    result = "enter the battlefield"
                else:
                    result = "change battlefield power"
        elif choice.conflict.kind is BatchConflictKind.AURA_ENTRY:
            if self._batch_intent_is_battlefield_aura_entry(intent):
                target = next(
                    target
                    for target in intent.targets
                    if isinstance(target, Card)
                )
                result = f"attach to {target.name}"
            else:
                destination = self._batch_intent_destination(intent)
                assert destination is not None
                names = ", ".join(
                    target.name
                    for target in self._batch_destination_targets(intent)
                )
                result = f"move {names} to {destination.value}"
        elif choice.conflict.kind is BatchConflictKind.COPY_ENTRY:
            if self._batch_intent_is_copy_entry(intent):
                target = next(
                    target
                    for target in intent.targets
                    if isinstance(target, Card)
                )
                result = f"copy {target.name} and enter the battlefield"
            else:
                destination = self._batch_intent_destination(intent)
                assert destination is not None
                names = ", ".join(
                    target.name
                    for target in self._batch_destination_targets(intent)
                )
                result = f"move {names} to {destination.value}"
        elif choice.conflict.kind is BatchConflictKind.CHARACTERISTICS:
            snapshot = self._batch_characteristic_snapshot(intent)
            if snapshot is not None:
                if isinstance(
                    intent.operation,
                    (DestroyAllEffect, ActivatedDestroyAllAbility),
                ):
                    result = "determine which permanents are destroyed"
                elif isinstance(
                    intent.operation,
                    (GlobalDamageEffect, ActivatedGlobalDamageAbility),
                ):
                    result = "determine which creatures are damaged"
                elif isinstance(intent.operation, DrainLifeEffect):
                    result = "read the target's toughness"
                else:
                    result = "count lands and creatures"
            elif intent.kind is BatchIntentKind.PERMANENT_ENTRY:
                result = "enter and apply its continuous effects"
            else:
                destination = self._batch_intent_destination(intent)
                if destination is not None:
                    names = ", ".join(
                        target.name
                        for target in self._batch_destination_targets(intent)
                    )
                    result = f"move {names} to {destination.value}"
                else:
                    result = "change battlefield characteristics"
        else:
            player_id = self._batch_intent_extra_turn_player(intent)
            assert player_id is not None
            result = f"{self.player(player_id).name} takes an extra turn"
        return f"{intent.source.name} → {result}"

    def _batch_hand_library_intent_label(
        self, plan: BatchResolutionPlan, intent: BatchEffectIntent
    ) -> str:
        """Describe one hand/library operation in player-facing language."""

        operation = intent.operation
        spell = next(
            (spell for spell in plan.spells if spell.card is intent.source),
            None,
        )
        if isinstance(operation, DrawCardsEffect):
            amount = operation.amount + operation.amount_per_x * (
                spell.x_value if spell is not None else 0
            )
            names = ", ".join(
                target.name
                for target in intent.targets
                if not isinstance(target, Card)
            )
            return f"{names} draws {amount}"
        if isinstance(operation, (ActivatedDrawAbility, ActivatedEventDrawAbility)):
            return f"{self.player(intent.controller_id).name} draws {operation.amount}"
        if isinstance(operation, GainLifeEffect):
            amount = operation.amount + operation.amount_per_x * (
                spell.x_value if spell is not None else 0
            )
            return f"life gain becomes {amount} draw(s) through Lich"
        if isinstance(operation, ActivatedEventLifeGainAbility):
            return f"life gain becomes {operation.amount} draw(s) through Lich"
        if isinstance(operation, DiscardCardsEffect):
            amount = operation.amount + operation.amount_per_x * (
                spell.x_value if spell is not None else 0
            )
            names = ", ".join(
                target.name
                for target in intent.targets
                if not isinstance(target, Card)
            )
            suffix = " at random" if operation.random else ""
            return f"{names} discards {amount}{suffix}"
        if isinstance(operation, ActivatedDiscardAbility):
            return f"opponent discards {operation.amount}"
        if isinstance(operation, ActivatedRevealHandAbility):
            return "look at opponent's hand"
        if isinstance(operation, WordOfCommandEffect):
            return "inspect opponent's hand and compel a play"
        if isinstance(operation, DiscardHandsAndDrawEffect):
            return (
                "each player discards their hand, then draws "
                f"{operation.draw_count}"
            )
        if isinstance(operation, ShuffleHandAndGraveyardEffect):
            return (
                "each player recycles hand and graveyard, then draws "
                f"{operation.draw_count}"
            )
        if isinstance(operation, DiscardHandAnteAndDrawEffect):
            return f"discard hand, ante a card, then draw {operation.draw_count}"
        if isinstance(operation, SwapLibraryTopWithAnteEffect):
            return "exchange a library-top card with ante"
        if isinstance(operation, NaturalSelectionEffect):
            return "inspect and reorder a library"
        if isinstance(operation, LibrarySearchEffect):
            return "search a library"
        if isinstance(operation, BalanceEffect):
            return "equalize both players' hands"
        if isinstance(operation, MoveTargetsEffect):
            names = ", ".join(
                target.name for target in intent.targets if isinstance(target, Card)
            )
            return f"return {names} to hand"
        raise RuntimeError("unknown hand/library batch operation")

    def move_batch_conflict_intent(
        self, player_id: str, intent_index: int, direction: int
    ) -> None:
        """Move one paradox effect earlier or later in the proposed order."""

        if not self.pending_batch_conflict_choices:
            raise RuntimeError("there is no batch conflict to order")
        choice = self.pending_batch_conflict_choices[0]
        if choice.conflict.chooser_id != player_id:
            raise RuntimeError("only the designated player may order this conflict")
        if direction not in {-1, 1}:
            raise ValueError("an ordering move must be earlier or later")
        try:
            old_index = choice.intent_indexes_first_to_last.index(intent_index)
        except ValueError as error:
            raise ValueError("that effect is not part of this conflict") from error
        new_index = old_index + direction
        if not 0 <= new_index < len(choice.intent_indexes_first_to_last):
            return
        (
            choice.intent_indexes_first_to_last[old_index],
            choice.intent_indexes_first_to_last[new_index],
        ) = (
            choice.intent_indexes_first_to_last[new_index],
            choice.intent_indexes_first_to_last[old_index],
        )

    def confirm_batch_conflict_order(self, player_id: str) -> tuple[Card, ...] | None:
        """Record one paradox order and commit after every conflict is ordered."""

        if not self.pending_batch_conflict_choices:
            raise RuntimeError("there is no batch conflict to confirm")
        choice = self.pending_batch_conflict_choices[0]
        if choice.conflict.chooser_id != player_id:
            raise RuntimeError("only the designated player may order this conflict")
        plan = self.pending_batch_resolution
        assert plan is not None
        order = tuple(choice.intent_indexes_first_to_last)
        for target_id in choice.conflict.target_ids:
            destination_order = tuple(
                intent_index
                for intent_index in order
                if self._batch_intent_destination(
                    plan.intents[intent_index]
                ) is not None
                and any(
                    target.id == target_id
                    for target in self._batch_destination_targets(
                        plan.intents[intent_index]
                    )
                )
            )
            if (
                choice.conflict.kind
                in {
                    BatchConflictKind.DESTINATION,
                    BatchConflictKind.AURA_ENTRY,
                    BatchConflictKind.COPY_ENTRY,
                }
                and len(destination_order) > 1
            ):
                plan.destination_orders[target_id] = destination_order
            if choice.conflict.kind is BatchConflictKind.TAPPED_STATE:
                plan.tapped_state_orders[target_id] = order
        if choice.conflict.kind is BatchConflictKind.POWER:
            plan.power_modifier_orders.append(order)
        elif choice.conflict.kind is BatchConflictKind.HAND_LIBRARY:
            plan.hand_library_orders.append(order)
        elif choice.conflict.kind is BatchConflictKind.LAND_TYPE:
            plan.land_type_orders.append(order)
        elif choice.conflict.kind is BatchConflictKind.TURN_SEQUENCE:
            plan.turn_sequence_orders.append(order)
        elif choice.conflict.kind is BatchConflictKind.SWORDS_READ:
            plan.swords_read_orders.append(order)
        elif choice.conflict.kind is BatchConflictKind.AURA_ENTRY:
            plan.aura_entry_orders.append(order)
        elif choice.conflict.kind is BatchConflictKind.COPY_ENTRY:
            plan.copy_entry_orders.append(order)
        elif choice.conflict.kind is BatchConflictKind.CHARACTERISTICS:
            plan.characteristic_orders.append(order)
        if choice.conflict.kind is BatchConflictKind.SWORDS_READ and any(
            self._batch_intent_is_battlefield_aura_entry(plan.intents[index])
            for index in order
        ):
            plan.aura_entry_orders.append(order)
        if (
            choice.conflict.kind is BatchConflictKind.COPY_ENTRY
            and any(
                self._batch_characteristic_snapshot(plan.intents[index])
                is not None
                for index in order
            )
        ):
            plan.characteristic_orders.append(order)
        self.pending_batch_conflict_choices.pop(0)
        if self.pending_batch_conflict_choices:
            return None
        resolved = self._commit_batch_resolution(plan)
        if plan.finalized and not self.pending_batch_destination_fallbacks:
            self.pending_batch_resolution = None
        if self.pending_damage is None and self.pending_destruction is None:
            self._restore_pending_context_priority()
            self._restore_commanded_spell_priority(plan)
        return resolved

    def _snapshot_ordered_batch_power_reads(
        self, plan: BatchResolutionPlan
    ) -> None:
        """Freeze the value each ordered Swords effect observes."""

        for order in plan.swords_read_orders:
            for position, intent_index in enumerate(order):
                intent = plan.intents[intent_index]
                if not self._batch_intent_reads_power(intent):
                    continue
                prior_intents = tuple(order[:position])
                for target in intent.targets:
                    if not isinstance(target, Card):
                        continue
                    power, controller_id = self._project_batch_swords_values(
                        plan, target, prior_intents
                    )
                    plan.swords_power_snapshots[(intent_index, target.id)] = max(
                        0, power
                    )
                    plan.swords_controller_snapshots[
                        (intent_index, target.id)
                    ] = controller_id

    def _snapshot_ordered_batch_characteristic_reads(
        self, plan: BatchResolutionPlan
    ) -> None:
        """Freeze each reader at its selected point in a paradox order."""

        for order in plan.characteristic_orders:
            for position, intent_index in enumerate(order):
                intent = plan.intents[intent_index]
                if self._batch_characteristic_snapshot(intent) is None:
                    continue
                plan.characteristic_snapshots[intent_index] = (
                    self._project_batch_characteristic_snapshot(
                        plan, intent, tuple(order[:position])
                    )
                )

    @staticmethod
    def _batch_intent_index(
        plan: BatchResolutionPlan,
        source: Card,
        declaration_sequence: int,
        operation_index: int,
    ) -> int | None:
        """Locate the planned intent corresponding to a live resolver item."""

        return next(
            (
                index
                for index, intent in enumerate(plan.intents)
                if intent.source is source
                and intent.declaration_sequence == declaration_sequence
                and intent.operation_index == operation_index
            ),
            None,
        )

    def _batch_destination_effect_applies(
        self,
        plan: BatchResolutionPlan,
        source: Card,
        declaration_sequence: int,
        operation_index: int,
        target: Card,
    ) -> bool:
        """Whether this operation has the chosen first destination."""

        order = plan.destination_orders.get(target.id)
        if not order:
            return True
        current_index = next(
            (
                index
                for index, intent in enumerate(plan.intents)
                if intent.source is source
                and intent.declaration_sequence == declaration_sequence
                and intent.operation_index == operation_index
            ),
            None,
        )
        if current_index is None:
            return True
        winning_destination = self._batch_intent_destination(
            plan.intents[order[0]]
        )
        return self._batch_intent_destination(
            plan.intents[current_index]
        ) is winning_destination

    def _batch_tapped_state_effect_is_deferred(
        self,
        plan: BatchResolutionPlan,
        source: Card,
        declaration_sequence: int,
        operation_index: int,
        target: Card,
    ) -> bool:
        order = plan.tapped_state_orders.get(target.id)
        if not order:
            return False
        return any(
            intent_index in order
            and intent.source is source
            and intent.declaration_sequence == declaration_sequence
            and intent.operation_index == operation_index
            for intent_index, intent in enumerate(plan.intents)
        )

    def _tap_land_for_pool_effect(
        self,
        spell: SpellOnStack,
        effect: TapLandsAndEmptyManaPoolEffect,
        permanent: Card,
    ) -> None:
        """Tap one land and perform Drain Power's production instruction."""

        if permanent.tapped:
            return
        mana_abilities = tuple(
            ability
            for ability in self.activated_abilities(permanent)
            if isinstance(ability, ActivatedManaAbility)
        )
        self._tap_permanent(permanent)
        if not effect.produce_land_mana:
            return
        caster = self.player(spell.caster_id)
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
                    spell.decision_maker_id,
                    permanent.id,
                    permanent.name,
                    options,
                )
            )

    def _resolve_ordered_batch_tapped_state_effects(
        self, plan: BatchResolutionPlan
    ) -> None:
        """Replay each chosen tap/untap paradox from first to last."""

        for target_id, order in plan.tapped_state_orders.items():
            target = next(
                (
                    card
                    for player in self.players
                    for card in player.battlefield
                    if card.id == target_id
                ),
                None,
            )
            if target is None:
                continue
            for intent_index in order:
                intent = plan.intents[intent_index]
                tapped = self._batch_intent_tapped_state(plan, intent)
                if tapped is None:
                    continue
                if isinstance(
                    intent.operation, TapLandsAndEmptyManaPoolEffect
                ):
                    spell = next(
                        spell
                        for spell in plan.spells
                        if spell.card is intent.source
                    )
                    self._tap_land_for_pool_effect(
                        spell, intent.operation, target
                    )
                elif tapped:
                    self._tap_permanent(target)
                else:
                    target.tapped = False

    def _batch_power_modifier_is_deferred(
        self,
        plan: BatchResolutionPlan,
        source: Card,
        declaration_sequence: int,
        operation_index: int,
    ) -> bool:
        ordered_indexes = {
            intent_index
            for order in plan.power_modifier_orders
            for intent_index in order
        }
        return any(
            intent_index in ordered_indexes
            and intent.source is source
            and intent.declaration_sequence == declaration_sequence
            and intent.operation_index == operation_index
            for intent_index, intent in enumerate(plan.intents)
        )

    def _apply_batch_power_modifier_intent(
        self, plan: BatchResolutionPlan, intent: BatchEffectIntent
    ) -> None:
        """Apply one deferred modifier at its player-selected timestamp."""

        operation = intent.operation
        if isinstance(operation, TemporaryPumpEffect):
            spell = next(
                spell for spell in plan.spells if spell.card is intent.source
            )
            power = operation.power + operation.power_per_x * spell.x_value
            toughness = (
                operation.toughness
                + operation.toughness_per_x * spell.x_value
            )
            for target in intent.targets:
                if not isinstance(target, Card):
                    continue
                self.temporary_creature_effects.setdefault(
                    target.id, []
                ).append(
                    self._timestamp_continuous_effect(
                        ContinuousEffect(
                            power=power,
                            toughness=toughness,
                            power_multiplier=operation.power_multiplier,
                            granted_abilities=operation.granted_abilities,
                        )
                    )
                )
                if operation.destroy_at_end_of_turn_if_attacked:
                    self.destroy_at_end_of_turn_if_attacked.add(target.id)
            return
        if isinstance(operation, ActivatedPumpAbility):
            for target in intent.targets:
                if not isinstance(target, Card):
                    continue
                self.temporary_creature_effects.setdefault(
                    target.id, []
                ).append(
                    self._timestamp_continuous_effect(
                        ContinuousEffect(
                            power=operation.power,
                            toughness=operation.toughness,
                            granted_abilities=operation.granted_abilities,
                        )
                    )
                )
            return
        if (
            intent.kind is BatchIntentKind.PERMANENT_ENTRY
            and intent.source.zone is Zone.BATTLEFIELD
        ):
            self.battlefield_entry_sequence += 1
            intent.source.battlefield_entry_sequence = (
                self.battlefield_entry_sequence
            )

    def _resolve_ordered_batch_power_modifiers(
        self, plan: BatchResolutionPlan
    ) -> None:
        """Apply every noncommuting power component first-to-last."""

        for order in plan.power_modifier_orders:
            for intent_index in order:
                self._apply_batch_power_modifier_intent(
                    plan, plan.intents[intent_index]
                )

    def _batch_land_type_intent_is_deferred(
        self,
        plan: BatchResolutionPlan,
        source: Card,
        declaration_sequence: int,
        operation_index: int,
    ) -> bool:
        ordered_indexes = {
            intent_index
            for order in plan.land_type_orders
            for intent_index in order
        }
        return any(
            intent_index in ordered_indexes
            and intent.source is source
            and intent.declaration_sequence == declaration_sequence
            and intent.operation_index == operation_index
            for intent_index, intent in enumerate(plan.intents)
        )

    def _apply_activated_land_type_setting(
        self,
        source: Card,
        controller_id: str,
        ability: ActivatedLandTypeAbility,
        targets: tuple[Card | PlayerState, ...],
    ) -> None:
        """Timestamp one Liege or Cyclopean Tomb land-type setting."""

        if source.zone is not Zone.BATTLEFIELD and not ability.persists_after_source_leaves:
            return
        for target in targets:
            if not isinstance(target, Card):
                continue
            self.battlefield_entry_sequence += 1
            if ability.persists_after_source_leaves:
                if source.persistent_effect_instance_id is None:
                    source.persistent_effect_instance_id = uuid4()
                mark = CyclopeanTombMark(
                    uuid4(),
                    source.persistent_effect_instance_id,
                    target.id,
                    self.battlefield_entry_sequence,
                    ability.replacement_subtype,
                )
                self.cyclopean_tomb_marks.append(mark)
                if source.zone is not Zone.BATTLEFIELD:
                    self.cyclopean_tomb_cleanup_controllers[
                        mark.effect_id
                    ] = controller_id
                target.counters["mire"] = target.counters.get("mire", 0) + 1
            else:
                target.land_type_marks[source.id] = (
                    ability.replacement_subtype,
                    self.battlefield_entry_sequence,
                )

    def _resolve_ordered_batch_land_type_settings(
        self, plan: BatchResolutionPlan
    ) -> None:
        """Timestamp competing land-type setters in the selected order."""

        seen: set[int] = set()
        for order in plan.land_type_orders:
            for intent_index in order:
                if intent_index in seen:
                    continue
                seen.add(intent_index)
                intent = plan.intents[intent_index]
                if intent.kind is BatchIntentKind.PERMANENT_ENTRY:
                    if intent.source.zone is Zone.BATTLEFIELD:
                        self.battlefield_entry_sequence += 1
                        intent.source.battlefield_entry_sequence = (
                            self.battlefield_entry_sequence
                        )
                    continue
                if isinstance(intent.operation, ActivatedLandTypeAbility):
                    self._apply_activated_land_type_setting(
                        intent.source,
                        intent.controller_id,
                        intent.operation,
                        intent.targets,
                    )

    def _batch_turn_sequence_intent_is_deferred(
        self,
        plan: BatchResolutionPlan,
        source: Card,
        declaration_sequence: int,
        operation_index: int,
    ) -> bool:
        ordered_indexes = {
            intent_index
            for order in plan.turn_sequence_orders
            for intent_index in order
        }
        return any(
            intent_index in ordered_indexes
            and intent.source is source
            and intent.declaration_sequence == declaration_sequence
            and intent.operation_index == operation_index
            for intent_index, intent in enumerate(plan.intents)
        )

    def _resolve_ordered_batch_turn_sequence_effects(
        self, plan: BatchResolutionPlan
    ) -> None:
        """Create extra turns in the selected effect order."""

        seen: set[int] = set()
        for order in plan.turn_sequence_orders:
            for intent_index in order:
                if intent_index in seen:
                    continue
                seen.add(intent_index)
                player_id = self._batch_intent_extra_turn_player(
                    plan.intents[intent_index]
                )
                if player_id is not None:
                    self.schedule_extra_turn(player_id)

    def _batch_hand_library_intent_is_deferred(
        self,
        plan: BatchResolutionPlan,
        source: Card,
        declaration_sequence: int,
        operation_index: int,
    ) -> bool:
        ordered_indexes = {
            intent_index
            for order in plan.hand_library_orders
            for intent_index in order
        }
        return any(
            intent_index in ordered_indexes
            and intent.source is source
            and intent.declaration_sequence == declaration_sequence
            and intent.operation_index == operation_index
            for intent_index, intent in enumerate(plan.intents)
        )

    def _batch_hand_library_choice_pending(self) -> bool:
        """Whether an ordered operation is awaiting a required player choice."""

        return bool(
            self.pending_discard_choices
            or self.pending_library_discard_choices
            or self.pending_natural_selection_choices
            or self.pending_library_search_choices
            or self.pending_balance is not None
            or self.pending_hand_reveals
            or self.pending_word_command_choices
        )

    def _apply_batch_hand_library_intent(
        self, plan: BatchResolutionPlan, intent: BatchEffectIntent
    ) -> None:
        """Apply one deferred hand/library operation at its chosen timestamp."""

        operation = intent.operation
        spell = next(
            (spell for spell in plan.spells if spell.card is intent.source),
            None,
        )
        if isinstance(operation, DrawCardsEffect):
            amount = operation.amount + operation.amount_per_x * (
                spell.x_value if spell is not None else 0
            )
            for target in intent.targets:
                if not isinstance(target, Card):
                    target.draw(amount)
            return
        if isinstance(operation, (ActivatedDrawAbility, ActivatedEventDrawAbility)):
            self.player(intent.controller_id).draw(operation.amount)
            return
        if isinstance(operation, GainLifeEffect):
            amount = operation.amount + operation.amount_per_x * (
                spell.x_value if spell is not None else 0
            )
            for target in intent.targets:
                if not isinstance(target, Card):
                    self._gain_life(target, amount)
            return
        if isinstance(operation, ActivatedEventLifeGainAbility):
            self._gain_life(
                self.player(intent.controller_id), operation.amount
            )
            return
        if isinstance(operation, DiscardCardsEffect):
            amount = operation.amount + operation.amount_per_x * (
                spell.x_value if spell is not None else 0
            )
            for target in intent.targets:
                if isinstance(target, Card):
                    continue
                if operation.random:
                    self._discard_random(
                        target, amount, source_name=intent.source.name
                    )
                elif target.hand:
                    self.pending_discard_choices.append(
                        PendingDiscardChoice(
                            target.id, amount, intent.source.name
                        )
                    )
            return
        if isinstance(operation, ActivatedDiscardAbility):
            controller = self.player(intent.controller_id)
            opponent = self.players[
                (self.players.index(controller) + 1) % len(self.players)
            ]
            if opponent.hand:
                self.pending_discard_choices.append(
                    PendingDiscardChoice(
                        opponent.id, operation.amount, intent.source.name
                    )
                )
            return
        if isinstance(operation, ActivatedRevealHandAbility):
            self._queue_opponent_hand_reveal(intent.controller_id)
            return
        if isinstance(operation, WordOfCommandEffect):
            opponent = next(
                player
                for player in self.players
                if player.id != intent.controller_id
            )
            self.pending_word_command_choices.append(
                PendingWordOfCommandChoice(
                    uuid4(),
                    intent.decision_maker_id,
                    opponent.id,
                )
            )
            return
        if isinstance(operation, DiscardHandsAndDrawEffect):
            for player in self.players:
                self._discard_forced(
                    player,
                    tuple(player.hand),
                    source_name=intent.source.name,
                    draw_after=operation.draw_count,
                )
            return
        if isinstance(operation, ShuffleHandAndGraveyardEffect):
            for player in self.players:
                recyclable = tuple(player.hand) + tuple(player.graveyard)
                for recyclable_card in recyclable:
                    self._move_card(recyclable_card, Zone.LIBRARY)
                player.shuffle_library(self.random)
            for player in self.players:
                player.draw(operation.draw_count)
            return
        if isinstance(operation, DiscardHandAnteAndDrawEffect):
            caster = self.player(intent.controller_id)
            self._discard_forced(
                caster,
                tuple(caster.hand),
                source_name=intent.source.name,
                draw_after=operation.draw_count,
                ante_after=True,
            )
            return
        if isinstance(operation, SwapLibraryTopWithAnteEffect):
            caster = self.player(intent.controller_id)
            if caster.library:
                target = next(
                    target for target in intent.targets if isinstance(target, Card)
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
            return
        if isinstance(operation, NaturalSelectionEffect):
            assert spell is not None
            target = next(
                target for target in intent.targets if not isinstance(target, Card)
            )
            self.pending_natural_selection_choices.append(
                PendingNaturalSelectionChoice(
                    spell.decision_maker_id,
                    target.id,
                    [card.id for card in reversed(target.library[-3:])],
                )
            )
            return
        if isinstance(operation, LibrarySearchEffect):
            assert spell is not None
            self.pending_library_search_choices.append(
                PendingLibrarySearchChoice(
                    spell.decision_maker_id,
                    intent.controller_id,
                    intent.source.name,
                    operation.card_types,
                    operation.destination,
                )
            )
            return
        if isinstance(operation, BalanceEffect):
            intent_index = next(
                index
                for index, candidate in enumerate(plan.intents)
                if candidate is intent
            )
            self._begin_balance(
                plan.characteristic_snapshots.get(intent_index)
            )
            return
        if isinstance(operation, MoveTargetsEffect):
            assert spell is not None
            caster = self.player(intent.controller_id)
            for target in intent.targets:
                if (
                    not isinstance(target, Card)
                    or not self._batch_destination_effect_applies(
                        plan,
                        intent.source,
                        intent.declaration_sequence,
                        intent.operation_index,
                        target,
                    )
                ):
                    continue
                if operation.under_caster_control:
                    target.controller_id = caster.id
                self._move_card(target, operation.destination)
            return
        raise RuntimeError("unknown deferred hand/library operation")

    def _continue_ordered_batch_hand_library_effects(
        self, plan: BatchResolutionPlan
    ) -> bool:
        """Run chosen operations until complete or one needs player input."""

        if not plan.pending_hand_library_intents:
            return True
        if self._batch_hand_library_choice_pending():
            return False
        while plan.pending_hand_library_intents:
            intent_index = plan.pending_hand_library_intents.pop(0)
            self._apply_batch_hand_library_intent(
                plan, plan.intents[intent_index]
            )
            if self._batch_hand_library_choice_pending():
                return False
        return True

    def _restore_commanded_spell_priority(
        self, plan: BatchResolutionPlan
    ) -> None:
        """Restore a spell forced while its containing batch was suspended."""

        commanded_id = plan.commanded_spell_interruptible_id
        if (
            plan.finalized
            and commanded_id is not None
            and any(card.id == commanded_id for card in self.stack)
        ):
            self.interruptible_spell_id = commanded_id
            self.priority_player_index = (
                plan.commanded_spell_priority_player_index
            )
            self.consecutive_passes = 0

    def _resume_ordered_batch_hand_library_effects(self) -> None:
        """Resume a batch after its current interactive operation completes."""

        plan = self.pending_batch_resolution
        if (
            plan is None
            or plan.finalized
            or not plan.base_effects_applied
            or self._batch_hand_library_choice_pending()
        ):
            return
        self._commit_batch_resolution(plan)
        if plan.finalized and not self.pending_batch_destination_fallbacks:
            self.pending_batch_resolution = None
        if self.pending_damage is None and self.pending_destruction is None:
            self._restore_pending_context_priority()
            self._restore_commanded_spell_priority(plan)

    def _resume_deferred_batch_entries(self) -> None:
        """Resume targeted permanent entries after destruction is known."""

        plan = self.pending_batch_resolution
        if (
            plan is None
            or plan.finalized
            or not (
                plan.pending_aura_entry_intents
                or plan.pending_copy_entry_intents
            )
            or self.pending_damage is not None
            or self.pending_destruction is not None
        ):
            return
        self._commit_batch_resolution(plan)
        if plan.finalized and not self.pending_batch_destination_fallbacks:
            self.pending_batch_resolution = None

    def _prepare_batch_destination_fallbacks(
        self, plan: BatchResolutionPlan
    ) -> None:
        """Remember later destinations if a first destruction regenerates."""

        self.pending_batch_destination_fallbacks.clear()
        for target_id, order in plan.destination_orders.items():
            if (
                len(order) > 1
                and self._batch_intent_destination(plan.intents[order[0]])
                is Zone.GRAVEYARD
            ):
                self.pending_batch_destination_fallbacks[target_id] = order[1:]

    def _resolve_regenerated_batch_destination_fallbacks(
        self, regenerated_card_ids: set[UUID]
    ) -> None:
        """Apply the next ordered destination when destruction was replaced."""

        plan = self.pending_batch_resolution
        if plan is None or not self.pending_batch_destination_fallbacks:
            return
        for target_id in tuple(self.pending_batch_destination_fallbacks):
            if target_id not in regenerated_card_ids:
                self.pending_batch_destination_fallbacks.pop(target_id, None)
                continue
            target = next(
                (
                    card
                    for player in self.players
                    for card in player.battlefield
                    if card.id == target_id
                ),
                None,
            )
            order = self.pending_batch_destination_fallbacks.pop(target_id)
            if target is None or not order:
                continue
            destination = self._batch_intent_destination(plan.intents[order[0]])
            matching_intents = tuple(
                intent
                for intent in plan.intents
                if self._batch_intent_destination(intent) is destination
                and target in self._batch_destination_targets(intent)
            )
            if destination is Zone.EXILE:
                life_awards = [
                    (
                        self.player(target.controller_id or target.owner_id),
                        max(0, self.creature_power(target)),
                    )
                    for intent in matching_intents
                    if isinstance(intent.operation, ExileTargetsEffect)
                    and intent.operation.controller_gains_life_equal_to_power
                ]
                self._move_card(target, Zone.EXILE)
                for player, amount in life_awards:
                    self._gain_life(player, amount)
                continue
            move_intent = next(
                (
                    intent
                    for intent in matching_intents
                    if isinstance(intent.operation, MoveTargetsEffect)
                ),
                None,
            )
            if move_intent is None or destination is None:
                continue
            effect = move_intent.operation
            if effect.under_caster_control:
                target.controller_id = move_intent.controller_id
            self._move_card(target, destination)
            if destination is Zone.BATTLEFIELD:
                target.entered_battlefield_turn = self.turn_number
        if (
            not self.pending_batch_destination_fallbacks
            and plan.finalized
            and not plan.pending_aura_entry_intents
            and not plan.pending_copy_entry_intents
        ):
            self.pending_batch_resolution = None

    def _batch_aura_entry_disposition(
        self, plan: BatchResolutionPlan, intent_index: int
    ) -> str:
        """Return ``normal``, ``skip``, or ``defer`` for an Aura entry."""

        intent = plan.intents[intent_index]
        if not self._batch_intent_is_battlefield_aura_entry(intent):
            return "normal"
        target = next(
            target for target in intent.targets if isinstance(target, Card)
        )
        for order in plan.aura_entry_orders:
            if intent_index not in order:
                continue
            aura_position = order.index(intent_index)
            earlier_removals = [
                index
                for index in order[:aura_position]
                if self._batch_intent_destination(plan.intents[index])
                not in {None, Zone.BATTLEFIELD}
                and target in self._batch_destination_targets(
                    plan.intents[index]
                )
            ]
            if not earlier_removals:
                return "normal"
            first_destination = self._batch_intent_destination(
                plan.intents[earlier_removals[0]]
            )
            return "defer" if first_destination is Zone.GRAVEYARD else "skip"
        return "normal"

    def _batch_copy_entry_disposition(
        self, plan: BatchResolutionPlan, intent_index: int
    ) -> str:
        """Return ``normal``, ``skip``, or ``defer`` for a copy entry."""

        intent = plan.intents[intent_index]
        if not self._batch_intent_is_copy_entry(intent):
            return "normal"
        target = next(
            target for target in intent.targets if isinstance(target, Card)
        )
        for order in plan.copy_entry_orders:
            if intent_index not in order:
                continue
            copy_position = order.index(intent_index)
            earlier_removals = [
                index
                for index in order[:copy_position]
                if self._batch_intent_destination(plan.intents[index])
                not in {None, Zone.BATTLEFIELD}
                and target in self._batch_destination_targets(
                    plan.intents[index]
                )
            ]
            if not earlier_removals:
                return "normal"
            first_destination = self._batch_intent_destination(
                plan.intents[earlier_removals[0]]
            )
            return "defer" if first_destination is Zone.GRAVEYARD else "skip"
        return "normal"

    def _resolve_one_batch_copy_entry(
        self, plan: BatchResolutionPlan, intent_index: int
    ) -> None:
        """Copy a still-present model and put its copy permanent into play."""

        intent = plan.intents[intent_index]
        spell = next(
            spell for spell in plan.spells if spell.card is intent.source
        )
        card = spell.card
        target = next(
            target for target in intent.targets if isinstance(target, Card)
        )
        if card.zone is not Zone.STACK or target.zone is not Zone.BATTLEFIELD:
            return
        copies_artifact = card.definition.copies_artifact
        copied_animated_creature = bool(
            card.definition.copies_creature
            and self.creature_has_animate_dead(target)
        )
        if copies_artifact:
            self._copy_artifact_definition(card, target)
        else:
            self._copy_creature_definition(card, target)
        self._move_card(card, Zone.BATTLEFIELD)
        if card.definition.x_enters_with_counter is not None:
            card.counters[card.definition.x_enters_with_counter] = spell.x_value
        card.entered_battlefield_turn = self.turn_number
        cast_definition = card.printed_definition or card.definition
        if (
            CardType.CREATURE in cast_definition.card_types
            and CardType.ARTIFACT not in cast_definition.card_types
        ):
            card.summoned_turn = self.turn_number
        if copied_animated_creature:
            self._destroy_permanents((card,))

    def _resolve_deferred_batch_copy_entries(
        self, plan: BatchResolutionPlan
    ) -> None:
        """Resolve copy entries after an earlier destruction is settled."""

        for intent_index in plan.pending_copy_entry_intents:
            self._resolve_one_batch_copy_entry(plan, intent_index)
        plan.pending_copy_entry_intents.clear()

    def _resolve_deferred_batch_aura_entries(
        self, plan: BatchResolutionPlan
    ) -> None:
        """Attach Auras whose earlier destruction failed to remove a target."""

        for intent_index in plan.pending_aura_entry_intents:
            intent = plan.intents[intent_index]
            spell = next(
                spell for spell in plan.spells if spell.card is intent.source
            )
            target = next(
                target
                for target in intent.targets
                if isinstance(target, Card)
            )
            card = spell.card
            if card.zone is not Zone.STACK or target.zone is not Zone.BATTLEFIELD:
                continue
            self._move_card(card, Zone.BATTLEFIELD)
            card.entered_battlefield_turn = self.turn_number
            card.enchanted_card_id = target.id
            if any(
                effect.controls_attached_card
                for effect in card.definition.continuous_effects
            ):
                self._reconcile_control_effects()
            if card.definition.consecrates_attached_land:
                self._destroy_permanents(
                    aura
                    for player in self.players
                    for aura in tuple(player.battlefield)
                    if aura is not card
                    and aura.enchanted_card_id == target.id
                )
            if card.definition.taps_attached_on_entry:
                self._tap_permanent(target)
            if card.definition.damages_attached_on_entry:
                self._deal_damage(
                    target,
                    card.definition.damages_attached_on_entry,
                    card.name,
                    source_card=card,
                    source_controller_id=spell.caster_id,
                )
        plan.pending_aura_entry_intents.clear()

    def _resolve_batch_permanent_spells(
        self,
        plan: BatchResolutionPlan,
    ) -> None:
        """Move legal permanent spells into play as one batch."""

        legality = plan.legality
        control_aura_entered = False
        # Slow permanents enter as part of the same instant. This lets their
        # continuous effects participate in the final state of the batch.
        for spell in plan.spells:
            card = spell.card
            resolved_targets = legality.spell_targets[card.id]
            if legality.spells[card.id] and card.definition.is_permanent:
                intent_index = next(
                    index
                    for index, intent in enumerate(plan.intents)
                    if intent.kind is BatchIntentKind.PERMANENT_ENTRY
                    and intent.source is card
                )
                aura_disposition = self._batch_aura_entry_disposition(
                    plan, intent_index
                )
                if aura_disposition != "normal":
                    if aura_disposition == "defer":
                        plan.pending_aura_entry_intents.append(intent_index)
                    continue
                copy_disposition = self._batch_copy_entry_disposition(
                    plan, intent_index
                )
                if copy_disposition != "normal":
                    if copy_disposition == "defer":
                        plan.pending_copy_entry_intents.append(intent_index)
                    continue
                if self._batch_intent_is_copy_entry(plan.intents[intent_index]):
                    self._resolve_one_batch_copy_entry(plan, intent_index)
                    continue
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
                            chooser_id=spell.decision_maker_id,
                            attachment_id=card.id,
                        ):
                            self._move_card(card, Zone.GRAVEYARD)
                        continue
                    target.controller_id = spell.caster_id
                    self._move_card(target, Zone.BATTLEFIELD)
                    target.entered_battlefield_turn = self.turn_number
                    card.enchanted_card_id = target.id
                    continue
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
                if (
                    card.enchanted_card_id is not None
                    and any(
                        effect.controls_attached_card
                        for effect in card.definition.continuous_effects
                    )
                ):
                    control_aura_entered = True
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
                    and not self._batch_tapped_state_effect_is_deferred(
                        plan,
                        card,
                        spell.declaration_sequence,
                        0,
                        spell.targets[0],
                    )
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
                cast_definition = card.printed_definition or card.definition
                if (
                    CardType.CREATURE in cast_definition.card_types
                    and CardType.ARTIFACT not in cast_definition.card_types
                ):
                    card.summoned_turn = self.turn_number
        # Aura attachments are established above as part of permanent entry.
        # Reconcile control only after every permanent in the simultaneous
        # batch has entered, so all control-changing Auras see the complete
        # result of that batch.
        if control_aura_entered:
            self._reconcile_control_effects()

    def _resolve_batch_spell_effects(
        self,
        plan: BatchResolutionPlan,
        consequences: BatchConsequences,
    ) -> None:
        """Apply nonpermanent spell effects and collect deferred results."""

        legality = plan.legality
        for spell in plan.spells:
            card = spell.card
            if not legality.spells[card.id] or card.definition.is_permanent:
                continue
            caster = self.player(spell.caster_id)
            resolved_targets = legality.spell_targets[card.id]
            for operation_index, effect in enumerate(
                card.definition.spell_effects
            ):
                if self._batch_hand_library_intent_is_deferred(
                    plan,
                    card,
                    spell.declaration_sequence,
                    operation_index,
                ):
                    continue
                intent_index = self._batch_intent_index(
                    plan,
                    card,
                    spell.declaration_sequence,
                    operation_index,
                )
                characteristic_snapshot = (
                    plan.characteristic_snapshots.get(intent_index)
                    if intent_index is not None
                    else None
                )
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
                    for recipient in legality.spell_targets[card.id]:
                        self._deal_damage(
                            recipient,
                            share,
                            card.name,
                            source_id=uuid4(),
                            source_controller_id=spell.caster_id,
                            source_colors=self.card_colors(card),
                        )
                elif isinstance(effect, DrainLifeEffect):
                    toughness_by_target = dict(
                        characteristic_snapshot.toughness_by_target
                        if characteristic_snapshot is not None
                        else ()
                    )
                    for recipient in resolved_targets:
                        cap = (
                            toughness_by_target.get(
                                recipient.id,
                                self.creature_toughness(recipient),
                            )
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
                    if self._batch_power_modifier_is_deferred(
                        plan,
                        card,
                        spell.declaration_sequence,
                        operation_index,
                    ):
                        continue
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
                                self._timestamp_continuous_effect(
                                    ContinuousEffect(
                                        power=power,
                                        toughness=toughness,
                                        power_multiplier=effect.power_multiplier,
                                        granted_abilities=effect.granted_abilities,
                                    )
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
                    consequences.regeneration.extend(
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
                elif isinstance(effect, WordOfCommandEffect):
                    opponent = next(
                        player for player in self.players if player.id != caster.id
                    )
                    self.pending_word_command_choices.append(
                        PendingWordOfCommandChoice(
                            uuid4(),
                            spell.decision_maker_id,
                            opponent.id,
                        )
                    )
                elif isinstance(effect, NaturalSelectionEffect):
                    target = next(
                        item for item in resolved_targets if not isinstance(item, Card)
                    )
                    self.pending_natural_selection_choices.append(
                        PendingNaturalSelectionChoice(
                            spell.decision_maker_id,
                            target.id,
                            [card.id for card in reversed(target.library[-3:])],
                        )
                    )
                elif isinstance(effect, LibrarySearchEffect):
                    self.pending_library_search_choices.append(
                        PendingLibrarySearchChoice(
                            spell.decision_maker_id,
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
                elif isinstance(effect, FalseOrdersEffect):
                    if (
                        self.combat is not None
                        and self.combat.step is CombatStep.BLOCKER_RESPONSE
                    ):
                        self.pending_false_orders_choices.extend(
                            PendingFalseOrdersChoice(
                                spell.decision_maker_id,
                                target.id,
                                card.name,
                            )
                            for target in resolved_targets
                            if isinstance(target, Card)
                            and target.controller_id
                            == self.combat.defending_player_id
                        )
                elif isinstance(effect, CamouflageEffect):
                    self.apply_camouflage(spell.caster_id)
                elif isinstance(effect, BalanceEffect):
                    self._begin_balance(characteristic_snapshot)
                elif isinstance(effect, ExtraTurnEffect):
                    if not self._batch_turn_sequence_intent_is_deferred(
                        plan,
                        card,
                        spell.declaration_sequence,
                        operation_index,
                    ):
                        self.schedule_extra_turn(spell.caster_id)
                elif isinstance(effect, GlobalDamageEffect):
                    amount = effect.amount + effect.amount_per_x * spell.x_value
                    snapshotted_ids = (
                        set(characteristic_snapshot.target_ids)
                        if characteristic_snapshot is not None
                        else None
                    )
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
                            if (
                                snapshotted_ids is not None
                                and creature.id not in snapshotted_ids
                            ):
                                continue
                            if CardType.CREATURE not in self.card_types(creature):
                                if snapshotted_ids is None:
                                    continue
                            if snapshotted_ids is None:
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
                    consequences.destruction.extend(
                        (target, effect.regeneration_allowed)
                        for target in resolved_targets
                        if isinstance(target, Card)
                        and self._batch_destination_effect_applies(
                            plan,
                            card,
                            spell.declaration_sequence,
                            operation_index,
                            target,
                        )
                    )
                elif isinstance(effect, DestroyAllEffect):
                    snapshotted_ids = (
                        set(characteristic_snapshot.target_ids)
                        if characteristic_snapshot is not None
                        else None
                    )
                    effect = replace(
                        effect,
                        subtypes=frozenset(
                            self.land_word(card, subtype)
                            for subtype in effect.subtypes
                        ),
                    )
                    consequences.destruction.extend(
                        (permanent, effect.regeneration_allowed)
                        for player in self.players
                        for permanent in tuple(player.battlefield)
                        if (
                            permanent.id in snapshotted_ids
                            if snapshotted_ids is not None
                            else effect.matches(
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
                        and self._batch_destination_effect_applies(
                            plan,
                            card,
                            spell.declaration_sequence,
                            operation_index,
                            permanent,
                        )
                    )
                elif isinstance(effect, MoveTargetsEffect):
                    for target in resolved_targets:
                        if not isinstance(target, Card):
                            continue
                        if not self._batch_destination_effect_applies(
                            plan,
                            card,
                            spell.declaration_sequence,
                            operation_index,
                            target,
                        ):
                            continue
                        if (
                            effect.destination is Zone.BATTLEFIELD
                            and target.definition.copies_creature
                        ):
                            self.queue_creature_copy_entry(
                                target,
                                caster.id,
                                chooser_id=spell.decision_maker_id,
                            )
                            continue
                        if effect.under_caster_control:
                            target.controller_id = caster.id
                        self._move_card(target, effect.destination)
                        if effect.destination is Zone.BATTLEFIELD:
                            target.entered_battlefield_turn = self.turn_number
                elif isinstance(effect, ExileTargetsEffect):
                    intent_index = next(
                        (
                            index
                            for index, intent in enumerate(plan.intents)
                            if intent.source is card
                            and intent.declaration_sequence
                            == spell.declaration_sequence
                            and intent.operation_index == operation_index
                        ),
                        None,
                    )
                    for target in resolved_targets:
                        if isinstance(
                            target, Card
                        ) and self._batch_destination_effect_applies(
                            plan,
                            card,
                            spell.declaration_sequence,
                            operation_index,
                            target,
                        ):
                            snapshot = (
                                plan.swords_power_snapshots.get(
                                    (intent_index, target.id)
                                )
                                if intent_index is not None
                                else None
                            )
                            controller_snapshot = (
                                plan.swords_controller_snapshots.get(
                                    (intent_index, target.id)
                                )
                                if intent_index is not None
                                else None
                            )
                            consequences.exile.append(
                                (
                                    target,
                                    effect,
                                    snapshot,
                                    controller_snapshot,
                                )
                            )
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
                            if self._batch_tapped_state_effect_is_deferred(
                                plan,
                                card,
                                spell.declaration_sequence,
                                operation_index,
                                target,
                            ):
                                continue
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
                                    if self._batch_tapped_state_effect_is_deferred(
                                        plan,
                                        card,
                                        spell.declaration_sequence,
                                        operation_index,
                                        permanent,
                                    ):
                                        continue
                                    self._tap_land_for_pool_effect(
                                        spell, effect, permanent
                                    )
                        if effect.transfer_to_caster:
                            for color in Color:
                                amount = target.mana_pool.amount(color)
                                if amount:
                                    caster.mana_pool.add(color, amount)
                            target.mana_pool.empty()
                        else:
                            target.mana_pool.empty()
    def _resolve_batch_activated_abilities(
        self,
        plan: BatchResolutionPlan,
        consequences: BatchConsequences,
    ) -> None:
        """Apply legal activated abilities in the simultaneous batch."""

        for declared, is_legal in zip(
            plan.abilities, plan.legality.abilities
        ):
            if not is_legal:
                continue
            if self._batch_hand_library_intent_is_deferred(
                plan,
                declared.source,
                declared.declaration_sequence,
                0,
            ):
                continue
            if self._batch_land_type_intent_is_deferred(
                plan,
                declared.source,
                declared.declaration_sequence,
                0,
            ):
                continue
            intent_index = self._batch_intent_index(
                plan,
                declared.source,
                declared.declaration_sequence,
                0,
            )
            characteristic_snapshot = (
                plan.characteristic_snapshots.get(intent_index)
                if intent_index is not None
                else None
            )
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
                snapshotted_ids = (
                    set(characteristic_snapshot.target_ids)
                    if characteristic_snapshot is not None
                    else None
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
                        if (
                            permanent.id in snapshotted_ids
                            if snapshotted_ids is not None
                            else CardType.CREATURE in self.card_types(permanent)
                        ):
                            self._deal_damage(
                                permanent,
                                damage,
                                declared.source_name,
                                source_card=declared.source,
                                source_controller_id=declared.controller_id,
                            )
            elif isinstance(declared.ability, ActivatedDestroyAbility):
                consequences.destruction.extend(
                    (target, declared.ability.regeneration_allowed)
                    for target in declared.targets
                    if isinstance(target, Card)
                    and self._batch_destination_effect_applies(
                        plan,
                        declared.source,
                        declared.declaration_sequence,
                        0,
                        target,
                    )
                )
            elif isinstance(declared.ability, ActivatedDestroyAllAbility):
                snapshotted_ids = (
                    set(characteristic_snapshot.target_ids)
                    if characteristic_snapshot is not None
                    else None
                )
                consequences.destruction.extend(
                    (permanent, declared.ability.regeneration_allowed)
                    for player in self.players
                    for permanent in tuple(player.battlefield)
                    if (
                        permanent.id in snapshotted_ids
                        if snapshotted_ids is not None
                        else self.card_types(permanent)
                        & declared.ability.card_types
                    )
                    and self._batch_destination_effect_applies(
                        plan,
                        declared.source,
                        declared.declaration_sequence,
                        0,
                        permanent,
                    )
                )
            elif isinstance(declared.ability, ActivatedTapAbility):
                for target in declared.targets:
                    if isinstance(target, Card):
                        if self._batch_tapped_state_effect_is_deferred(
                            plan,
                            declared.source,
                            declared.declaration_sequence,
                            0,
                            target,
                        ):
                            continue
                        self._tap_permanent(target)
            elif isinstance(declared.ability, ActivatedUnblockableAbility):
                for target in declared.targets:
                    if isinstance(target, Card):
                        self.temporary_creature_effects.setdefault(
                            target.id, []
                        ).append(
                            self._timestamp_continuous_effect(
                                ContinuousEffect(unblockable=True)
                            )
                        )
            elif isinstance(declared.ability, ActivatedTemporaryAbility):
                for target in declared.targets:
                    if not isinstance(target, Card):
                        continue
                    self.temporary_creature_effects.setdefault(
                        target.id, []
                    ).append(
                        self._timestamp_continuous_effect(
                            ContinuousEffect(
                                granted_abilities=(
                                    declared.ability.granted_abilities
                                )
                            )
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
                if (
                    declared.source.zone is Zone.GRAVEYARD
                    and self._batch_destination_effect_applies(
                        plan,
                        declared.source,
                        declared.declaration_sequence,
                        0,
                        declared.source,
                    )
                ):
                    declared.source.controller_id = declared.controller_id
                    self._move_card(declared.source, Zone.BATTLEFIELD)
                    declared.source.entered_battlefield_turn = self.turn_number
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
                self._apply_activated_land_type_setting(
                    declared.source,
                    declared.controller_id,
                    declared.ability,
                    declared.targets,
                )
            elif isinstance(declared.ability, ActivatedExtraTurnAbility):
                if not self._batch_turn_sequence_intent_is_deferred(
                    plan,
                    declared.source,
                    declared.declaration_sequence,
                    0,
                ):
                    self.schedule_extra_turn(declared.controller_id)
            elif isinstance(declared.ability, ActivatedUntapAbility):
                for target in declared.targets:
                    if isinstance(target, Card):
                        if self._batch_tapped_state_effect_is_deferred(
                            plan,
                            declared.source,
                            declared.declaration_sequence,
                            0,
                            target,
                        ):
                            continue
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
                    self._timestamp_continuous_effect(
                        ContinuousEffect(
                            granted_card_types=frozenset({CardType.CREATURE}),
                            base_power=declared.ability.power,
                            base_toughness=declared.ability.toughness,
                        )
                        )
                    )
            elif isinstance(declared.ability, ActivatedPumpAbility):
                if self._batch_power_modifier_is_deferred(
                    plan,
                    declared.source,
                    declared.declaration_sequence,
                    0,
                ):
                    continue
                for target in declared.targets:
                    if isinstance(target, Card):
                        self.temporary_creature_effects.setdefault(
                            target.id, []
                        ).append(
                            self._timestamp_continuous_effect(
                                ContinuousEffect(
                                    power=declared.ability.power,
                                    toughness=declared.ability.toughness,
                                    granted_abilities=(
                                        declared.ability.granted_abilities
                                    ),
                                )
                            )
                        )
            else:
                raise AssertionError(
                    f"unhandled batch ability: {declared.ability!r}"
                )

    def _apply_batch_zone_and_incident_results(
        self,
        consequences: BatchConsequences,
    ) -> None:
        """Apply deferred exile, destruction, and regeneration results."""

        # Swords to Plowshares counts the creature's full power immediately
        # before it leaves play.  Pump spells and abilities announced in
        # response belong to this same Beta batch, so all of their modifiers
        # must exist before that power is measured.  Snapshot every result
        # before moving any target, since multiple exile effects in one batch
        # are simultaneous as well.
        exile_results = [
            (
                target,
                self.player(
                    controller_snapshot
                    or target.controller_id
                    or target.owner_id
                ),
                (
                    (
                        power_snapshot
                        if power_snapshot is not None
                        else max(0, self.creature_power(target))
                    )
                    if effect.controller_gains_life_equal_to_power
                    else 0
                ),
            )
            for target, effect, power_snapshot, controller_snapshot
            in consequences.exile
        ]
        for target, controller, life_gain in exile_results:
            self._move_card(target, Zone.EXILE)
            self._gain_life(controller, life_gain)

        destruction_by_card: dict[Card, bool] = {}
        for card, regeneration_allowed in consequences.destruction:
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
        for target in consequences.regeneration:
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

    def _finish_batch_resolution(
        self,
        spells: tuple[SpellOnStack, ...],
        caught_event_ids: set[UUID],
    ) -> None:
        """Move resolved spells off the stack and stabilize once."""

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

    def _commit_batch_resolution(
        self, plan: BatchResolutionPlan
    ) -> tuple[Card, ...]:
        """Apply a previously frozen batch plan using existing semantics."""

        if plan.finalized:
            return plan.cards
        if not plan.base_effects_applied:
            self.interruptible_spell_id = None
            self._prepare_batch_destination_fallbacks(plan)
            self._snapshot_ordered_batch_power_reads(plan)
            self._snapshot_ordered_batch_characteristic_reads(plan)
            self._begin_damage_incident(DamageIncidentKind.FAST_EFFECT_BATCH)
            self._resolve_batch_permanent_spells(plan)
            self._resolve_batch_spell_effects(plan, plan.consequences)
            self._resolve_batch_activated_abilities(plan, plan.consequences)
            self._resolve_ordered_batch_tapped_state_effects(plan)
            self._resolve_ordered_batch_power_modifiers(plan)
            self._resolve_ordered_batch_land_type_settings(plan)
            self._resolve_ordered_batch_turn_sequence_effects(plan)
            plan.pending_hand_library_intents = list(
                dict.fromkeys(
                    intent_index
                    for order in plan.hand_library_orders
                    for intent_index in order
                )
            )
            plan.base_effects_applied = True
        if not self._continue_ordered_batch_hand_library_effects(plan):
            return plan.cards
        if not plan.zone_results_applied:
            plan.zone_results_applied = True
            self._apply_batch_zone_and_incident_results(plan.consequences)
            if plan.finalized:
                return plan.cards
        if plan.pending_aura_entry_intents or plan.pending_copy_entry_intents:
            if self.pending_damage is not None or self.pending_destruction is not None:
                return plan.cards
            if plan.pending_aura_entry_intents:
                self._resolve_deferred_batch_aura_entries(plan)
            if plan.pending_copy_entry_intents:
                self._resolve_deferred_batch_copy_entries(plan)
        if (
            self.pending_damage is None
            and self.pending_destruction is None
            and self.pending_batch_destination_fallbacks
        ):
            self.pending_batch_destination_fallbacks.clear()
            self.pending_batch_resolution = None
        self._finish_batch_resolution(
            plan.spells, set(plan.caught_event_ids)
        )
        plan.finalized = True
        return plan.cards

    def _resolve_batch(self) -> tuple[Card, ...]:
        """Apply one 1993 fast-effect batch, then stabilize exactly once."""

        plan = self._plan_batch_resolution()
        conflicts = self._detect_batch_conflicts(plan)
        if conflicts:
            self.pending_batch_resolution = plan
            self.pending_batch_conflict_choices = [
                PendingBatchConflictChoice(
                    conflict,
                    list(conflict.intent_indexes),
                )
                for conflict in conflicts
            ]
            self.priority_player_index = None
            self.consecutive_passes = 0
            return ()
        return self._commit_batch_resolution(plan)
