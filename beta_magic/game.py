"""Player zones and top-level game state."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from random import Random
from typing import Callable, Iterable
from uuid import UUID

from .ability_activation import AbilityActivationMixin
from .abilities import (
    ActivatedEventDrawAbility,
    ActivatedEventLifeGainAbility,
)
from .cards import Card, CardDefinition
from .casting import (
    AbilityOnStack,
    PendingActivation,
    PendingCast,
    SpellOnStack,
    TargetingCastingMixin,
)
from .characteristics import CharacteristicsMixin
from .combat import AttackRequirement, CombatMixin, CombatState
from .incident_resolution import (
    DamageDestructionMixin,
    PendingPrevention,
    PendingRedirection,
    PendingCounterDamageChoice,
    PendingLichChoice,
)
from .turn_flow import (
    PendingDrawChoice,
    PendingGraveyardReturnChoice,
    PendingTimedEvent,
    PendingTurnChoice,
    PendingUntapChoice,
    PendingUpkeepLandLossChoice,
    PendingDoppelgangerChoice,
    TurnFlowMixin,
)
from .effects import (
    ContinuousEffect,
    AttachedEventDamageEffect,
    LandEventDamageEffect,
    DrainLifeEffect,
)
from .events import (
    CardMovedEvent,
    GameEvent,
)
from .damage import (
    DamageIncident,
    DamageIncidentKind,
    DamageRecipientKind,
    PlayerDamageRecord,
)
from .destruction import (
    DestructionIncident,
)
from .priority_resolution import (
    BalanceChoice,
    PendingBalance,
    PendingDiscardChoice,
    PendingDrainPowerChoice,
    PendingDemonicAttorneyChoice,
    PendingNaturalSelectionChoice,
    PendingLibrarySearchChoice,
    PendingPowerSinkPayment,
    PriorityBatchResolutionMixin,
)
from .mana import ManaCost, ManaPool
from .rule_events import RuleEventKind, RuleEventOpportunity
from .types import (
    CardType,
    Color,
    CombatStep,
    GameStatus,
    TurnPhase,
    Zone,
)


@dataclass(slots=True)
class PlayerState:
    id: str
    name: str
    life: int = 20
    library: list[Card] = field(default_factory=list)
    hand: list[Card] = field(default_factory=list)
    battlefield: list[Card] = field(default_factory=list)
    graveyard: list[Card] = field(default_factory=list)
    exile: list[Card] = field(default_factory=list)
    ante: list[Card] = field(default_factory=list)
    mana_pool: ManaPool = field(default_factory=ManaPool)
    has_lost: bool = False

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("a player must have an id")
        if not self.name.strip():
            raise ValueError("a player must have a name")

    @classmethod
    def with_deck(
        cls, id: str, name: str, deck: Iterable[CardDefinition], *, life: int = 20
    ) -> PlayerState:
        player = cls(id=id, name=name, life=life)
        player.library.extend(Card(definition=definition, owner_id=id) for definition in deck)
        return player

    def cards_in(self, zone: Zone) -> list[Card]:
        zones = {
            Zone.LIBRARY: self.library,
            Zone.HAND: self.hand,
            Zone.BATTLEFIELD: self.battlefield,
            Zone.GRAVEYARD: self.graveyard,
            Zone.EXILE: self.exile,
            Zone.ANTE: self.ante,
        }
        try:
            return zones[zone]
        except KeyError as error:
            raise ValueError(f"{zone.value} is not a player-owned zone") from error

    def shuffle_library(self, random: Random | None = None) -> None:
        (random or Random()).shuffle(self.library)

    def draw(self, count: int = 1) -> list[Card]:
        if count < 0:
            raise ValueError("draw count cannot be negative")
        drawn: list[Card] = []
        for _ in range(count):
            if not self.library:
                self.has_lost = True
                break
            card = self.library.pop()
            card.zone = Zone.HAND
            card.tapped = False
            card.damage = 0
            self.hand.append(card)
            drawn.append(card)
        return drawn

    def move_card(self, card: Card, destination: Zone) -> None:
        source_zone = card.zone
        source = self.cards_in(card.zone)
        if card not in source:
            raise ValueError(f"{card.name} is not in its recorded {card.zone.value}")
        target = self.cards_in(destination)
        source.remove(card)

        token_leaves_battlefield = (
            card.is_token
            and source_zone is Zone.BATTLEFIELD
            and destination is not Zone.BATTLEFIELD
        )
        spell_copy_leaves_stack = (
            card.is_spell_copy
            and source_zone is Zone.STACK
            and destination is not Zone.STACK
        )
        card.zone = destination
        if destination is not Zone.BATTLEFIELD:
            card.tapped = False
            card.damage = 0
            card.plus_one_counters = 0
            card.counters.clear()
            card.controller_id = card.owner_id
            card.summoned_turn = None
            card.enchanted_card_id = None
        if not token_leaves_battlefield and not spell_copy_leaves_stack:
            target.append(card)

    @property
    def discard_required(self) -> int:
        """Number of cards that must be discarded at the end of the turn."""

        return max(0, len(self.hand) - 7)

    def discard(self, card: Card) -> None:
        if card not in self.hand:
            raise ValueError(f"{card.name} is not in {self.name}'s hand")
        self.move_card(card, Zone.GRAVEYARD)

    def untap_all(self) -> None:
        """Untap this player's lands, creatures, and artifacts in play."""

        for card in self.battlefield:
            if card.definition.untaps_normally:
                card.tapped = False


@dataclass(frozen=True, slots=True)
class PendingHandReveal:
    """A resolved look effect waiting for its viewer to dismiss the snapshot."""

    viewer_id: str
    target_id: str
    cards: tuple[Card, ...]


@dataclass(slots=True)
class PendingGraveyardOrderChoice:
    """An owner orders cards simultaneously added to their graveyard."""

    player_id: str
    card_ids_bottom_to_top: list[UUID]


@dataclass(frozen=True, slots=True)
class PendingKudzuChoice:
    """The destroyed land's former controller must reattach Kudzu."""

    chooser_id: str
    kudzu_id: UUID
    candidate_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class PendingCreatureCopyChoice:
    """A Clone entering outside casting must choose its copied creature."""

    chooser_id: str
    clone_id: UUID
    candidate_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class AnteAward:
    """A completed duel's ante disposition for an external collection layer."""

    winner_id: str | None
    card_ids: tuple[UUID, ...]
    original_owner_ids: tuple[str, ...]

    @property
    def is_draw(self) -> bool:
        return self.winner_id is None


@dataclass(slots=True)
class GameState(
    TargetingCastingMixin,
    AbilityActivationMixin,
    PriorityBatchResolutionMixin,
    CombatMixin,
    DamageDestructionMixin,
    TurnFlowMixin,
    CharacteristicsMixin,
):
    players: list[PlayerState]
    ante_enabled: bool = False
    ante_award: AnteAward | None = None
    ante_award_hook: Callable[[AnteAward], None] | None = field(
        default=None, repr=False, compare=False
    )
    active_player_index: int = 0
    turn_number: int = 0
    status: GameStatus = GameStatus.NOT_STARTED
    stack: list[Card] = field(default_factory=list)
    stack_spells: dict[UUID, SpellOnStack] = field(default_factory=dict)
    interruptible_spell_id: UUID | None = None
    priority_player_index: int | None = None
    consecutive_passes: int = 0
    current_phase: TurnPhase | None = None
    lands_played_this_turn: int = 0
    attacks_this_turn: int = 0
    active_player_untapped_lands_at_turn_start: int = 0
    attack_requirements: dict[UUID, AttackRequirement] = field(default_factory=dict)
    attacked_this_turn: set[UUID] = field(default_factory=set)
    prevent_combat_damage_this_turn: bool = False
    channel_active_players: set[str] = field(default_factory=set)
    island_sanctuary_protected_players: set[str] = field(default_factory=set)
    vampire_damage_marks: dict[UUID, set[UUID]] = field(default_factory=dict)
    creature_deaths_this_turn: int = 0
    player_damage_history: list[PlayerDamageRecord] = field(default_factory=list)
    combat: CombatState | None = None
    pending_cast: PendingCast | None = None
    pending_activation: PendingActivation | None = None
    pending_prevention: PendingPrevention | None = None
    life_loss_prevention: dict[str, int] = field(default_factory=dict)
    pending_redirection: PendingRedirection | None = None
    pending_counter_damage_choice: PendingCounterDamageChoice | None = None
    pending_lich_choices: list[PendingLichChoice] = field(default_factory=list)
    batch_abilities: list[AbilityOnStack] = field(default_factory=list)
    interrupt_abilities: list[AbilityOnStack] = field(default_factory=list)
    events: list[GameEvent] = field(default_factory=list)
    temporary_creature_effects: dict[UUID, list[ContinuousEffect]] = field(
        default_factory=dict
    )
    combat_creature_effects: dict[UUID, list[ContinuousEffect]] = field(
        default_factory=dict
    )
    ability_activations_this_turn: dict[UUID, int] = field(default_factory=dict)
    destroy_at_end_of_turn: set[UUID] = field(default_factory=set)
    destroy_at_end_of_turn_if_attacked: set[UUID] = field(default_factory=set)
    disintegrated_this_turn: set[UUID] = field(default_factory=set)
    timed_events: list[PendingTimedEvent] = field(default_factory=list)
    pending_damage: DamageIncident | None = None
    resolved_damage_incidents: list[DamageIncident] = field(default_factory=list)
    pending_destruction: DestructionIncident | None = None
    resume_interrupts_after_destruction: bool = False
    resolved_destruction_incidents: list[DestructionIncident] = field(
        default_factory=list
    )
    pause_for_damage_windows: bool = False
    battlefield_entry_sequence: int = 0
    event_opportunities: list[RuleEventOpportunity] = field(
        default_factory=list
    )
    event_ability_uses: set[tuple[UUID, UUID]] = field(default_factory=set)
    deferred_damage_continuation: DamageIncident | None = None
    upcoming_turns: list[str] = field(default_factory=list)
    next_natural_player_index: int = 1
    pending_turn_choice: PendingTurnChoice | None = None
    pending_draw_choice: PendingDrawChoice | None = None
    pending_graveyard_return_choice: PendingGraveyardReturnChoice | None = None
    graveyard_returns_done_this_upkeep: bool = False
    pending_graveyard_order_choices: list[PendingGraveyardOrderChoice] = field(
        default_factory=list
    )
    pending_kudzu_choices: list[PendingKudzuChoice] = field(default_factory=list)
    pending_creature_copy_choices: list[PendingCreatureCopyChoice] = field(
        default_factory=list
    )
    pending_doppelganger_choices: list[PendingDoppelgangerChoice] = field(
        default_factory=list
    )
    pending_untap_choice: PendingUntapChoice | None = None
    pending_counter_rewinds: list[UUID] = field(default_factory=list)
    rewound_during_untap: set[UUID] = field(default_factory=set)
    pending_upkeep_land_loss: PendingUpkeepLandLossChoice | None = None
    pending_phase_advance: TurnPhase | None = None
    vaults_untapping_next_turn: dict[str, set[UUID]] = field(
        default_factory=dict
    )
    upkeep_payments_this_turn: set[UUID] = field(default_factory=set)
    unpaid_tap_upkeep_ids: set[UUID] = field(default_factory=set)
    pending_discard_choices: list[PendingDiscardChoice] = field(default_factory=list)
    pending_balance: PendingBalance | None = None
    pending_hand_reveals: list[PendingHandReveal] = field(default_factory=list)
    pending_drain_power_choices: list[PendingDrainPowerChoice] = field(
        default_factory=list
    )
    pending_power_sink_payment: PendingPowerSinkPayment | None = None
    pending_demonic_attorney_choices: list[PendingDemonicAttorneyChoice] = field(
        default_factory=list
    )
    pending_natural_selection_choices: list[PendingNaturalSelectionChoice] = field(
        default_factory=list
    )
    pending_library_search_choices: list[PendingLibrarySearchChoice] = field(
        default_factory=list
    )
    random: Random = field(default_factory=Random, repr=False)

    def __post_init__(self) -> None:
        if len(self.players) < 2:
            raise ValueError("a game requires at least two players")
        ids = [player.id for player in self.players]
        if len(ids) != len(set(ids)):
            raise ValueError("player ids must be unique")
        if not 0 <= self.active_player_index < len(self.players):
            raise ValueError("active player index is out of range")
        if self.status is GameStatus.NOT_STARTED and self.current_phase is not None:
            raise ValueError("a game that has not started cannot have a current phase")
        if self.status is GameStatus.IN_PROGRESS and self.current_phase is None:
            raise ValueError("a game in progress must have a current phase")
        self.validate()

    @property
    def active_player(self) -> PlayerState:
        return self.players[self.active_player_index]

    def player(self, player_id: str) -> PlayerState:
        for player in self.players:
            if player.id == player_id:
                return player
        raise KeyError(player_id)

    def _mana_payment_substitutions(
        self, player: PlayerState
    ) -> tuple[tuple[Color, Color], ...]:
        return tuple(
            (effect.source_color, effect.paid_as_color)
            for permanent in player.battlefield
            if self.continuous_permanent_is_active(permanent)
            for effect in permanent.definition.mana_payment_effects
        )

    def can_pay_mana(self, player: PlayerState, cost: ManaCost) -> bool:
        """Whether a player can pay a cost under current continuous effects."""

        return player.mana_pool.can_pay(
            cost, self._mana_payment_substitutions(player)
        )

    def pay_mana(self, player: PlayerState, cost: ManaCost) -> None:
        """Pay a cost using all currently active mana substitutions."""

        player.mana_pool.pay(cost, self._mana_payment_substitutions(player))

    def spell_mana_cost(
        self, card: Card, x_value: int = 0, target_count: int = 1
    ) -> ManaCost:
        """Return a spell's payable cost after battlefield surcharges."""

        drains_life = any(
            isinstance(effect, DrainLifeEffect)
            for effect in card.definition.spell_effects
        )
        printed = card.definition.mana_cost
        cost = (
            ManaCost(
                generic=printed.generic,
                white=printed.white,
                blue=printed.blue,
                black=printed.black + x_value,
                red=printed.red,
                green=printed.green,
            )
            if drains_life
            else printed.with_x(x_value)
        )
        surcharge = sum(
            permanent.definition.increases_white_spell_cost
            for owner in self.players
            for permanent in owner.battlefield
            if self.continuous_permanent_is_active(permanent)
            and Color.WHITE in self.card_colors(card)
        )
        target_surcharge = (
            max(0, target_count - 1)
            * card.definition.additional_mana_per_target_beyond_first
        )
        return ManaCost(
            generic=cost.generic + surcharge + target_surcharge,
            white=cost.white,
            blue=cost.blue,
            black=cost.black,
            red=cost.red,
            green=cost.green,
            x_symbols=cost.x_symbols,
        )

    def spell_casting_cost_value(self, card: Card, x_value: int = 0) -> int:
        """Casting cost used by era effects; Drain Life's extra B is excluded."""

        if any(
            isinstance(effect, DrainLifeEffect)
            for effect in card.definition.spell_effects
        ):
            return card.definition.mana_cost.with_x(0).mana_value
        return card.definition.mana_cost.with_x(x_value).mana_value

    def ability_mana_cost(self, source: Card, base_cost: ManaCost) -> ManaCost:
        """Return an activated ability cost after card-specific surcharges."""

        surcharge = (
            sum(
                permanent.definition.increases_circle_activation_cost
                for owner in self.players
                for permanent in owner.battlefield
                if self.continuous_permanent_is_active(permanent)
            )
            if source.definition.is_circle_of_protection
            else 0
        )
        return ManaCost(
            generic=base_cost.generic + surcharge,
            white=base_cost.white,
            blue=base_cost.blue,
            black=base_cost.black,
            red=base_cost.red,
            green=base_cost.green,
            x_symbols=base_cost.x_symbols,
        )

    def _lose_life(
        self, player: PlayerState, amount: int, *, preventable: bool = True
    ) -> tuple[int, int]:
        """Apply direct life loss, consuming any Conservator-style prevention."""

        if amount < 0:
            raise ValueError("life loss cannot be negative")
        if self._lich_count(player.id):
            # A Lich controller has no life points to lose. Damage still
            # creates the card-destruction obligation in incident resolution.
            return 0, 0
        prevented = (
            min(amount, self.life_loss_prevention.get(player.id, 0))
            if preventable else 0
        )
        if preventable:
            remaining = self.life_loss_prevention.get(player.id, 0) - prevented
            if remaining:
                self.life_loss_prevention[player.id] = remaining
            else:
                self.life_loss_prevention.pop(player.id, None)
        lost = amount - prevented
        player.life -= lost
        if lost:
            for permanent in player.battlefield:
                counter_name = permanent.definition.counters_on_controller_life_loss
                if counter_name is not None:
                    permanent.counters[counter_name] = (
                        permanent.counters.get(counter_name, 0) + lost
                    )
        if player.life <= 0:
            player.has_lost = True
        return lost, prevented

    def maximum_channel_mana(self, player_id: str) -> int:
        """Return how much life the player can currently convert with Channel."""

        player = self.player(player_id)
        if (
            player_id not in self.channel_active_players
            or player.has_lost
            or self._lich_count(player_id)
        ):
            return 0
        return max(0, player.life)

    def channel_life_for_mana(self, player_id: str, amount: int) -> None:
        """Use Channel's turn-long interrupt-speed mana action."""

        self._require_no_pending_action(allow_stack=True, allow_damage=True)
        if self.status is not GameStatus.IN_PROGRESS:
            raise RuntimeError("Channel can only be used during a game")
        if self.current_phase is TurnPhase.UNTAP:
            raise RuntimeError("Channel cannot be used during the Untap phase")
        if self.combat is not None and self.combat.step in {
            CombatStep.DECLARE_ATTACKERS,
            CombatStep.DECLARE_BLOCKERS,
        }:
            raise RuntimeError("Channel cannot be used during combat declarations")
        player = self.player(player_id)
        if (
            self.priority_player_index is not None
            and player is not self.players[self.priority_player_index]
        ):
            raise RuntimeError(
                f"{self.players[self.priority_player_index].name} has priority"
            )
        maximum = self.maximum_channel_mana(player_id)
        if not 1 <= amount <= maximum:
            raise ValueError(f"choose an amount from 1 to {maximum}")
        lost, prevented = self._lose_life(player, amount, preventable=False)
        assert lost == amount and prevented == 0
        player.mana_pool.colorless += amount

    def _lich_count(self, player_id: str) -> int:
        """Return the number of Liches currently controlled by one player."""

        return sum(
            card.definition.is_lich
            for card in self.player(player_id).battlefield
            if (card.controller_id or card.owner_id) == player_id
        )

    def _gain_life(self, player: PlayerState, amount: int) -> int:
        """Gain life, or draw once per point for each Lich instead."""

        if amount < 0:
            raise ValueError("life gain cannot be negative")
        liches = self._lich_count(player.id)
        if liches:
            player.draw(amount * liches)
            return 0
        player.life += amount
        return amount

    @staticmethod
    def _damage_source_key(source_id: UUID | None, source_name: str) -> str:
        return str(source_id) if source_id is not None else f"name:{source_name}"

    def damage_source_choices(self, player_id: str) -> list[tuple[str, str, int]]:
        """Return the still-reversible damage sources for one player."""

        self.player(player_id)
        grouped: dict[str, tuple[str, int]] = {}
        for record in self.player_damage_history:
            if record.player_id != player_id:
                continue
            name, amount = grouped.get(record.source_key, (record.source_name, 0))
            grouped[record.source_key] = (name, amount + record.remaining)
        if self.pending_damage is not None:
            for packet in self.pending_damage.packets:
                if (
                    packet.recipient_kind is not DamageRecipientKind.PLAYER
                    or packet.recipient_id != player_id
                    or packet.remaining <= 0
                ):
                    continue
                key = self._damage_source_key(packet.source_id, packet.source_name)
                name, amount = grouped.get(key, (packet.source_name, 0))
                grouped[key] = (name, amount + packet.remaining)
        return [
            (key, name, amount)
            for key, (name, amount) in grouped.items()
        ]

    def _consume_player_damage(
        self, player_id: str, *, source_key: str | None = None
    ) -> list[tuple[PlayerDamageRecord, int]]:
        consumed: list[tuple[PlayerDamageRecord, int]] = []
        for record in self.player_damage_history:
            if (
                record.player_id != player_id
                or record.remaining <= 0
                or source_key is not None
                and record.source_key != source_key
            ):
                continue
            amount = record.remaining
            record.reversed_amount += amount
            consumed.append((record, amount))
        return consumed

    def _require_no_pending_action(
        self, *, allow_stack: bool = False, allow_damage: bool = False
    ) -> None:
        if self.pending_cast is not None:
            raise RuntimeError(
                f"choose targets for {self.pending_cast.spell.name} first"
            )
        if self.pending_activation is not None:
            raise RuntimeError(
                f"choose targets for {self.pending_activation.source.name}'s ability first"
            )
        if self.pending_prevention is not None:
            raise RuntimeError(
                f"choose damage for {self.pending_prevention.source.name} first"
            )
        if self.pending_redirection is not None:
            raise RuntimeError(
                f"choose damage for {self.pending_redirection.source.name} first"
            )
        if self.pending_turn_choice is not None:
            raise RuntimeError("choose whether to skip the upcoming turn first")
        if self.pending_draw_choice is not None:
            raise RuntimeError("choose how many draw-phase draws to skip first")
        if self.pending_graveyard_return_choice is not None:
            raise RuntimeError("choose whether to return Nether Shadow first")
        if self.pending_graveyard_order_choices:
            choice = self.pending_graveyard_order_choices[0]
            raise RuntimeError(
                f"{self.player(choice.player_id).name} must order cards in their "
                "graveyard first"
            )
        if self.pending_kudzu_choices:
            choice = self.pending_kudzu_choices[0]
            raise RuntimeError(
                f"{self.player(choice.chooser_id).name} must move Kudzu to "
                "another land first"
            )
        if self.pending_creature_copy_choices:
            choice = self.pending_creature_copy_choices[0]
            raise RuntimeError(
                f"{self.player(choice.chooser_id).name} must choose a creature "
                "for Clone first"
            )
        if self.pending_doppelganger_choices:
            choice = self.pending_doppelganger_choices[0]
            raise RuntimeError(
                f"{self.player(choice.chooser_id).name} must choose whether "
                "to change Vesuvan Doppelganger first"
            )
        if self.pending_untap_choice is not None:
            choice = self.pending_untap_choice
            raise RuntimeError(
                f"{self.player(choice.player_id).name} must choose permanents "
                f"to untap under the {choice.card_type.value} limit first"
            )
        if self.pending_counter_damage_choice is not None:
            raise RuntimeError(
                f"{self.player(self.pending_counter_damage_choice.controller_id).name} "
                "must choose how many damage counters to preserve first"
            )
        if self.pending_lich_choices:
            choice = self.pending_lich_choices[0]
            raise RuntimeError(
                f"{self.player(choice.player_id).name} must choose "
                f"{choice.amount} card(s) to destroy for Lich first"
            )
        if self.pending_counter_rewinds:
            raise RuntimeError(
                f"{self.active_player.name} must choose whether to rewind "
                "Clockwork Beast first"
            )
        if self.pending_upkeep_land_loss is not None:
            choice = self.pending_upkeep_land_loss
            raise RuntimeError(
                f"{self.player(choice.chooser_id).name} must choose a land "
                f"for {choice.source_name} first"
            )
        if self.pending_discard_choices:
            choice = self.pending_discard_choices[0]
            raise RuntimeError(
                f"{self.player(choice.player_id).name} must choose cards to discard first"
            )
        if self.pending_balance is not None:
            choice = self.pending_balance.current_choice
            assert choice is not None
            raise RuntimeError(
                f"{self.player(choice.player_id).name} must choose "
                f"{choice.amount} {choice.category} card(s) for Balance first"
            )
        if self.pending_hand_reveals:
            reveal = self.pending_hand_reveals[0]
            raise RuntimeError(
                f"{self.player(reveal.viewer_id).name} must finish looking at "
                f"{self.player(reveal.target_id).name}'s hand first"
            )
        if self.pending_drain_power_choices:
            choice = self.pending_drain_power_choices[0]
            raise RuntimeError(
                f"{self.player(choice.caster_id).name} must choose mana for "
                f"{choice.land_name} first"
            )
        if self.pending_power_sink_payment is not None:
            payment = self.pending_power_sink_payment
            raise RuntimeError(
                f"{self.player(payment.payer_id).name} must finish paying "
                f"Power Sink first"
            )
        if self.pending_demonic_attorney_choices:
            choice = self.pending_demonic_attorney_choices[0]
            raise RuntimeError(
                f"{self.player(choice.opponent_id).name} must answer "
                "Demonic Attorney first"
            )
        if self.pending_natural_selection_choices:
            choice = self.pending_natural_selection_choices[0]
            raise RuntimeError(
                f"{self.player(choice.chooser_id).name} must finish "
                "Natural Selection first"
            )
        if self.pending_library_search_choices:
            choice = self.pending_library_search_choices[0]
            raise RuntimeError(
                f"{self.player(choice.chooser_id).name} must finish searching "
                f"for {choice.source_name} first"
            )
        if self.pending_damage is not None and not allow_damage:
            raise RuntimeError("finish resolving the pending damage incident first")
        if self.pending_destruction is not None and not allow_damage:
            raise RuntimeError(
                "finish resolving the pending destruction incident first"
            )
        if (self.stack or self.batch_abilities) and not allow_stack:
            raise RuntimeError("both players must pass priority to resolve the batch")
        if self.timed_events and not allow_stack:
            raise RuntimeError(
                "both players must pass priority to resolve the timed event"
            )
        if self.event_opportunities and not allow_stack:
            raise RuntimeError(
                "both players must pass priority on the pending rules event"
            )

    def finish_hand_reveal(self, player_id: str) -> None:
        """Dismiss the oldest resolved private hand snapshot."""

        if not self.pending_hand_reveals:
            raise RuntimeError("there is no revealed hand to dismiss")
        reveal = self.pending_hand_reveals[0]
        if reveal.viewer_id != player_id:
            raise ValueError("only the player looking at the hand may dismiss it")
        self.pending_hand_reveals.pop(0)

    def _queue_opponent_hand_reveal(self, viewer_id: str) -> None:
        """Snapshot the next opponent's hand for a resolved look effect."""

        viewer = self.player(viewer_id)
        viewer_index = self.players.index(viewer)
        target = self.players[(viewer_index + 1) % len(self.players)]
        self.pending_hand_reveals.append(
            PendingHandReveal(viewer.id, target.id, tuple(target.hand))
        )

    def _locate_card(self, card: Card) -> tuple[PlayerState | None, list[Card]]:
        if card in self.stack:
            return None, self.stack
        for player in self.players:
            for zone in (
                Zone.LIBRARY,
                Zone.HAND,
                Zone.BATTLEFIELD,
                Zone.GRAVEYARD,
                Zone.EXILE,
                Zone.ANTE,
            ):
                cards = player.cards_in(zone)
                if card in cards:
                    return player, cards
        raise ValueError(f"{card.name} is not in a game zone")

    def _graveyard_lengths(self) -> dict[str, int]:
        return {player.id: len(player.graveyard) for player in self.players}

    def _queue_new_graveyard_order_choices(
        self, prior_lengths: dict[str, int]
    ) -> None:
        """Pause for each owner whose simultaneous move added multiple cards."""

        already_queued = {
            card_id
            for choice in self.pending_graveyard_order_choices
            for card_id in choice.card_ids_bottom_to_top
        }
        for player in self.players:
            added = [
                card for card in player.graveyard[prior_lengths[player.id]:]
                if card.id not in already_queued
            ]
            if len(added) > 1:
                self.pending_graveyard_order_choices.append(
                    PendingGraveyardOrderChoice(
                        player.id, [card.id for card in added]
                    )
                )

    def move_graveyard_order_card(
        self, player_id: str, card: Card, direction: int
    ) -> None:
        """Move one card up or down in the pending bottom-to-top order."""

        if not self.pending_graveyard_order_choices:
            raise RuntimeError("there is no graveyard order choice")
        choice = self.pending_graveyard_order_choices[0]
        if choice.player_id != player_id:
            raise RuntimeError(f"{self.player(choice.player_id).name} must choose")
        if direction not in {-1, 1}:
            raise ValueError("graveyard order movement must be up or down")
        try:
            index = choice.card_ids_bottom_to_top.index(card.id)
        except ValueError as error:
            raise ValueError("that card is not in the simultaneous group") from error
        destination = index + direction
        if not 0 <= destination < len(choice.card_ids_bottom_to_top):
            return
        choice.card_ids_bottom_to_top[index], choice.card_ids_bottom_to_top[destination] = (
            choice.card_ids_bottom_to_top[destination],
            choice.card_ids_bottom_to_top[index],
        )

    def confirm_graveyard_order(self, player_id: str) -> None:
        """Commit the displayed bottom-to-top order to the owner's graveyard."""

        if not self.pending_graveyard_order_choices:
            raise RuntimeError("there is no graveyard order choice")
        choice = self.pending_graveyard_order_choices[0]
        if choice.player_id != player_id:
            raise RuntimeError(f"{self.player(choice.player_id).name} must choose")
        player = self.player(player_id)
        cards = {card.id: card for card in player.graveyard}
        if not set(choice.card_ids_bottom_to_top) <= cards.keys():
            raise RuntimeError("a card awaiting graveyard ordering is no longer there")
        chosen = [cards[card_id] for card_id in choice.card_ids_bottom_to_top]
        chosen_ids = set(choice.card_ids_bottom_to_top)
        positions = [
            index for index, card in enumerate(player.graveyard)
            if card.id in chosen_ids
        ]
        for index, card in zip(positions, chosen):
            player.graveyard[index] = card
        self.pending_graveyard_order_choices.pop(0)

    def _move_card(
        self,
        card: Card,
        destination: Zone,
        *,
        record_land_loss: bool = True,
    ) -> None:
        """Perform one zone transition without recursively stabilizing the game."""

        _, source = self._locate_card(card)
        source_zone = card.zone
        was_land = CardType.LAND in self.card_types(card)
        was_creature = CardType.CREATURE in self.card_types(card)
        if (
            source_zone is Zone.BATTLEFIELD
            and destination is Zone.GRAVEYARD
            and card.id in self.disintegrated_this_turn
        ):
            destination = Zone.EXILE
        prior_controller_id = card.controller_id or card.owner_id
        lich_destroyed = bool(
            card.definition.is_lich
            and source_zone is Zone.BATTLEFIELD
            and destination is Zone.GRAVEYARD
        )
        prior_toughness = self.creature_toughness(card) if was_creature else 0
        creature_bonds = tuple(
            (attachment, effect)
            for player in self.players
            for attachment in player.battlefield
            if attachment.enchanted_card_id == card.id
            for effect in attachment.definition.attached_event_damage_effects
            if effect.when_destroyed
        )
        land_loss_sources = (
            self._land_event_sources(land_lost=True)
            if record_land_loss
            and was_land
            and source_zone is Zone.BATTLEFIELD
            and destination is Zone.GRAVEYARD
            else ()
        )
        source.remove(card)

        if source_zone is Zone.BATTLEFIELD and destination is not Zone.BATTLEFIELD:
            if card.printed_definition is not None:
                card.definition = card.printed_definition
                card.printed_definition = None

        if destination is Zone.STACK:
            target = self.stack
        elif destination is Zone.BATTLEFIELD:
            card.base_controller_id = card.controller_id or card.owner_id
            self.battlefield_entry_sequence += 1
            card.battlefield_entry_sequence = self.battlefield_entry_sequence
            target = self.player(card.controller_id or card.owner_id).battlefield
        else:
            target = self.player(card.owner_id).cards_in(destination)

        token_leaves_battlefield = (
            card.is_token
            and source_zone is Zone.BATTLEFIELD
            and destination is not Zone.BATTLEFIELD
        )

        spell_copy_leaves_stack = (
            card.is_spell_copy
            and source_zone is Zone.STACK
            and destination is not Zone.STACK
        )

        card.zone = destination
        if destination is not Zone.BATTLEFIELD:
            card.tapped = False
            card.damage = 0
            card.controller_id = card.owner_id
            card.base_controller_id = card.owner_id
            card.controller_at_turn_start_id = None
            card.entered_battlefield_turn = None
            card.battlefield_entry_sequence = None
            card.enchanted_card_id = None
            card.chosen_land_subtype = None
            card.color_override = None
            card.plus_one_counters = 0
            card.counters.clear()
            card.summoned_turn = None
            card.land_type_marks.clear()
            card.copied_card_id = None
            card.copied_card_entry_sequence = None
        if not token_leaves_battlefield and not spell_copy_leaves_stack:
            target.append(card)
        if destination is Zone.BATTLEFIELD and card.definition.enters_tapped:
            card.tapped = True
        if destination is Zone.BATTLEFIELD:
            card.counters = dict(card.definition.initial_counters)
            if card.definition.is_lich:
                controller = self.player(card.controller_id or card.owner_id)
                lost = max(0, controller.life)
                controller.life = 0
                if lost:
                    for permanent in controller.battlefield:
                        counter_name = (
                            permanent.definition.counters_on_controller_life_loss
                        )
                        if counter_name is not None:
                            permanent.counters[counter_name] = (
                                permanent.counters.get(counter_name, 0) + lost
                            )
        self.events.append(
            CardMovedEvent(card.id, card.name, source_zone, destination)
        )
        if lich_destroyed:
            self.player(prior_controller_id).has_lost = True
        if was_land and destination is Zone.BATTLEFIELD:
            self._record_land_event_opportunities(
                card.controller_id or card.owner_id,
                card.name,
                self._land_event_sources(land_enters=True),
                RuleEventKind.LAND_ENTERED,
            )
        if land_loss_sources:
            self._record_land_event_opportunities(
                prior_controller_id,
                card.name,
                land_loss_sources,
                RuleEventKind.LAND_LOST,
            )

        if (
            source_zone is Zone.BATTLEFIELD
            and destination is Zone.GRAVEYARD
            and was_creature
        ):
            self.creature_deaths_this_turn += 1
            divisor = card.definition.owner_life_loss_on_death_divisor
            if divisor is not None:
                owner = self.player(card.owner_id)
                self._lose_life(owner, (owner.life + divisor - 1) // divisor)
            self._record_creature_death_opportunity(
                card,
                prior_controller_id=prior_controller_id,
                prior_toughness=prior_toughness,
                creature_bonds=creature_bonds,
            )

        if source_zone is Zone.BATTLEFIELD:
            self.vampire_damage_marks.pop(card.id, None)
            for vampire_ids in self.vampire_damage_marks.values():
                vampire_ids.discard(card.id)
            for player in self.players:
                for permanent in player.battlefield:
                    permanent.land_type_marks.pop(card.id, None)
            self.temporary_creature_effects.pop(card.id, None)
            self.combat_creature_effects.pop(card.id, None)
            self.ability_activations_this_turn.pop(card.id, None)
            self.destroy_at_end_of_turn.discard(card.id)
            self.destroy_at_end_of_turn_if_attacked.discard(card.id)
            self.disintegrated_this_turn.discard(card.id)
            self.unpaid_tap_upkeep_ids.discard(card.id)
            attachments = [
                attachment
                for player in self.players
                for attachment in player.battlefield
                if attachment.enchanted_card_id == card.id
            ]
            for attachment in attachments:
                self._move_card(attachment, Zone.GRAVEYARD)
            self._reconcile_control_effects()

    def _reconcile_control_effects(self) -> None:
        """Apply the newest attached control effect to each permanent."""

        battlefield = [
            permanent
            for player in self.players
            for permanent in player.battlefield
        ]
        desired_controllers = {
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
            if not self.continuous_permanent_is_active(aura):
                continue
            if aura.enchanted_card_id in desired_controllers:
                desired_controllers[aura.enchanted_card_id] = (
                    aura.controller_id or aura.owner_id
                )
        for permanent in battlefield:
            desired = desired_controllers[permanent.id]
            if permanent.controller_id != desired:
                self._change_controller(permanent, desired)

    def _copy_artifact_definition(self, card: Card, target: Card) -> None:
        """Apply Copy Artifact's battlefield-only copy characteristics."""

        card.printed_definition = card.definition
        card.definition = replace(
            target.definition,
            card_types=(
                target.definition.card_types
                | frozenset({CardType.ARTIFACT, CardType.ENCHANTMENT})
            ),
            colors=frozenset({Color.BLUE}),
            copies_artifact=False,
        )

    def _copy_creature_definition(self, card: Card, target: Card) -> None:
        """Apply Clone's copyable creature characteristics while in play."""

        source_is_doppelganger = bool(
            card.definition.is_vesuvan_doppelganger
            or card.printed_definition is not None
            and card.printed_definition.is_vesuvan_doppelganger
        )
        result_is_doppelganger = bool(
            source_is_doppelganger
            or target.definition.is_vesuvan_doppelganger
        )
        if card.printed_definition is None:
            card.printed_definition = card.definition
        card.definition = replace(
            target.definition,
            colors=(
                frozenset({Color.BLUE})
                if result_is_doppelganger
                else self.card_colors(target)
            ),
            initial_counters=(),
            copies_artifact=False,
            copies_creature=False,
            is_vesuvan_doppelganger=result_is_doppelganger,
        )
        card.copied_card_id = target.id
        card.copied_card_entry_sequence = target.battlefield_entry_sequence

    def _doppelganger_copy_candidates(self, source: Card) -> tuple[Card, ...]:
        """Return legal different printed creatures for an upkeep switch."""

        return tuple(
            candidate
            for player in self.players
            for candidate in player.battlefield
            if candidate is not source
            and not (
                candidate.id == source.copied_card_id
                and candidate.battlefield_entry_sequence
                == source.copied_card_entry_sequence
            )
            and CardType.CREATURE in candidate.definition.card_types
            and not self._is_protected_from(candidate, frozenset({Color.BLUE}))
        )

    def _queue_doppelganger_choices(self) -> None:
        """Offer each active-player Doppelganger one pre-upkeep switch."""

        self.pending_doppelganger_choices = [
            PendingDoppelgangerChoice(
                self.active_player.id,
                permanent.id,
                tuple(
                    candidate.id
                    for candidate in self._doppelganger_copy_candidates(permanent)
                ),
            )
            for permanent in tuple(self.active_player.battlefield)
            if permanent.definition.is_vesuvan_doppelganger
        ]

    def choose_doppelganger_creature(
        self, player_id: str, creature: Card | None
    ) -> None:
        """Keep the current form or perform the upkeep copy transition."""

        if not self.pending_doppelganger_choices:
            raise RuntimeError("there is no pending Doppelganger choice")
        choice = self.pending_doppelganger_choices[0]
        if choice.chooser_id != player_id:
            raise RuntimeError(f"{self.player(choice.chooser_id).name} must choose")
        source = next(
            (
                card
                for card in self.player(player_id).battlefield
                if card.id == choice.doppelganger_id
            ),
            None,
        )
        if source is None or not source.definition.is_vesuvan_doppelganger:
            self.pending_doppelganger_choices.pop(0)
        else:
            if creature is not None and (
                creature.id not in choice.candidate_ids
                or creature not in self._doppelganger_copy_candidates(source)
            ):
                raise ValueError("Vesuvan Doppelganger cannot copy that creature")
            self.pending_doppelganger_choices.pop(0)
            if creature is not None:
                # The old copied creature is treated as leaving play. Clear
                # state gained from that form, while leaving external effects,
                # attachments, damage, and tapped orientation intact.
                for player in self.players:
                    for permanent in player.battlefield:
                        permanent.land_type_marks.pop(source.id, None)
                source.counters.clear()
                source.plus_one_counters = 0
                self.ability_activations_this_turn.pop(source.id, None)
                self._copy_creature_definition(source, creature)
                self._reconcile_control_effects()
                self.check_state_based_actions()
        if not self.pending_doppelganger_choices:
            self._queue_upkeep_events()
            self._refresh_graveyard_return_choice()

    def _creature_copy_candidates(self, clone: Card) -> tuple[Card, ...]:
        requirement = clone.definition.target_requirement
        assert requirement is not None
        return tuple(
            candidate
            for player in self.players
            for candidate in player.battlefield
            if self._requirement_accepts_card(
                requirement,
                candidate,
                clone.controller_id or clone.owner_id,
                source_colors=self.card_colors(clone),
            )
        )

    def queue_creature_copy_entry(self, clone: Card, controller_id: str) -> bool:
        """Pause a non-cast Clone entry for its mandatory creature choice."""

        clone.controller_id = controller_id
        candidates = self._creature_copy_candidates(clone)
        if not candidates:
            return False
        self.pending_creature_copy_choices.append(
            PendingCreatureCopyChoice(
                controller_id, clone.id, tuple(card.id for card in candidates)
            )
        )
        return True

    def choose_clone_creature(self, player_id: str, creature: Card) -> None:
        """Complete a Clone entry that was initiated from a non-stack zone."""

        if not self.pending_creature_copy_choices:
            raise RuntimeError("there is no pending Clone choice")
        choice = self.pending_creature_copy_choices[0]
        if choice.chooser_id != player_id:
            raise RuntimeError(f"{self.player(choice.chooser_id).name} must choose")
        clone = next(
            (
                card
                for player in self.players
                for zone in (Zone.GRAVEYARD, Zone.HAND, Zone.EXILE)
                for card in player.cards_in(zone)
                if card.id == choice.clone_id
            ),
            None,
        )
        if (
            clone is None
            or creature.id not in choice.candidate_ids
            or creature not in self._creature_copy_candidates(clone)
        ):
            raise ValueError("Clone cannot copy that creature")
        self.pending_creature_copy_choices.pop(0)
        self._copy_creature_definition(clone, creature)
        self._move_card(clone, Zone.BATTLEFIELD)
        clone.entered_battlefield_turn = self.turn_number
        clone.summoned_turn = self.turn_number
        self.check_state_based_actions()

    def _change_controller(self, permanent: Card, controller_id: str) -> None:
        """Transfer a battlefield permanent without changing its owner."""

        old_controller_id = permanent.controller_id or permanent.owner_id
        old_battlefield = self.player(old_controller_id).battlefield
        if permanent not in old_battlefield:
            raise ValueError(
                f"{permanent.name} is not on its controller's battlefield"
            )
        if permanent.controller_at_turn_start_id is None:
            permanent.controller_at_turn_start_id = old_controller_id
        old_battlefield.remove(permanent)
        permanent.controller_id = controller_id
        self.player(controller_id).battlefield.append(permanent)

    def move_card(self, card: Card, destination: Zone) -> None:
        """Move a card through the engine and then stabilize the battlefield."""

        self._require_no_pending_action()
        self._move_card(card, destination)
        self.check_state_based_actions()

    def play_land(self, card: Card) -> None:
        """Play a land, applying the shared normal/Fastbond allowance."""

        self._require_no_pending_action()
        if self.status is not GameStatus.IN_PROGRESS:
            raise RuntimeError("lands can only be played during a game")
        if self.current_phase is not TurnPhase.MAIN:
            raise RuntimeError("lands can only be played during the Main phase")
        if self.combat is not None:
            raise RuntimeError("lands cannot be played during an attack")
        if (
            self.priority_player_index is not None
            and self.priority_player_index != self.active_player_index
        ):
            raise RuntimeError(
                f"{self.players[self.priority_player_index].name} has priority"
            )
        fastbonds = tuple(
            permanent
            for permanent in self.active_player.battlefield
            if permanent.definition.fastbond_damage
        )
        if self.lands_played_this_turn and not fastbonds:
            raise RuntimeError("the active player has already played a land this turn")
        if card not in self.active_player.hand:
            raise ValueError("the land must be in the active player's hand")
        if CardType.LAND not in card.definition.card_types:
            raise ValueError(f"{card.name} is not a land")

        card.controller_id = self.active_player.id
        self._move_card(card, Zone.BATTLEFIELD)
        card.entered_battlefield_turn = self.turn_number
        is_additional_land = self.lands_played_this_turn > 0
        self.lands_played_this_turn += 1
        if is_additional_land:
            self._begin_damage_incident(DamageIncidentKind.RULE_EVENT)
            for fastbond in fastbonds:
                self._deal_damage(
                    self.active_player,
                    fastbond.definition.fastbond_damage,
                    fastbond.name,
                    source_card=fastbond,
                    source_controller_id=self.active_player.id,
                )
            self._resolve_damage_incident()
        self.check_state_based_actions()

    def tap_land_for_mana(self, player_id: str, card: Card) -> None:
        """Compatibility shortcut for lands with exactly one mana ability."""

        abilities = self.activated_abilities(card)
        if len(abilities) != 1:
            raise ValueError(f"{card.name} requires a mana ability choice")
        self.activate_ability(player_id, card, 0)

    def _record_spell_cast_opportunity(self, spell: Card) -> None:
        """Expose one catchable event for a successfully cast spell."""

        caster_id = spell.controller_id or spell.owner_id
        matching = any(
            (
                isinstance(ability, ActivatedEventLifeGainAbility)
                and ability.spell_color is not None
                and ability.spell_color in self.card_colors(spell)
            )
            or (
                isinstance(ability, ActivatedEventDrawAbility)
                and CardType.ENCHANTMENT in spell.definition.card_types
                and permanent.id != spell.id
                and permanent.controller_id == caster_id
            )
            for player in self.players
            for permanent in player.battlefield
            for ability in self.activated_abilities(permanent)
        )
        if not matching:
            return
        self.event_opportunities.append(
            RuleEventOpportunity(
                RuleEventKind.SPELL_CAST,
                f"{spell.name} was cast",
                spell_id=spell.id,
                spell_colors=self.card_colors(spell),
                spell_card_types=spell.definition.card_types,
                spell_caster_id=caster_id,
            )
        )
        if self.priority_player_index is None:
            caster = self.player(spell.controller_id or spell.owner_id)
            self.priority_player_index = (
                self.players.index(caster) + 1
            ) % len(self.players)
            self.consecutive_passes = 0

    def _refresh_spell_cast_opportunity(self, spell: Card) -> None:
        """Re-evaluate color-sensitive cast events after a Lace resolves."""

        self._discard_spell_cast_opportunities(spell.id)
        self._record_spell_cast_opportunity(spell)

    def _discard_spell_cast_opportunities(self, spell_id: UUID) -> None:
        """Invalidate cast-event claims when a spell is changed or countered."""

        removed = {
            event.id
            for event in self.event_opportunities
            if event.spell_id == spell_id
        }
        self.event_opportunities = [
            event for event in self.event_opportunities if event.id not in removed
        ]
        self.event_ability_uses = {
            use for use in self.event_ability_uses if use[1] not in removed
        }

    def _record_creature_death_opportunity(
        self,
        creature: Card,
        *,
        prior_controller_id: str,
        prior_toughness: int,
        creature_bonds: tuple[
            tuple[Card, AttachedEventDamageEffect], ...
        ] = (),
    ) -> None:
        """Expose a post-regeneration death event if Soul Net is in play."""

        for vampire_id in self.vampire_damage_marks.get(creature.id, ()):
            vampire = next(
                (
                    card
                    for player in self.players
                    for card in player.battlefield
                    if card.id == vampire_id
                    and card.definition.grows_when_damaged_creature_dies
                ),
                None,
            )
            if vampire is not None:
                vampire.plus_one_counters += 1

        matching = any(
            isinstance(ability, ActivatedEventLifeGainAbility)
            and ability.creature_death
            for player in self.players
            for permanent in player.battlefield
            for ability in self.activated_abilities(permanent)
        )
        if not matching and not creature_bonds:
            return
        if matching:
            self.event_opportunities.append(
                RuleEventOpportunity(
                    RuleEventKind.CREATURE_DEATH,
                    f"{creature.name} died",
                    card_id=creature.id,
                )
            )
        for source, effect in creature_bonds:
            self.event_opportunities.append(
                RuleEventOpportunity(
                    RuleEventKind.CREATURE_DEATH,
                    f"{source.name}: {creature.name} was destroyed",
                    card_id=creature.id,
                    damage=(
                        max(0, prior_toughness)
                        if effect.amount_from_toughness
                        else effect.amount
                    ),
                    source_id=source.id,
                    source_name=source.name,
                    source_controller_id=source.controller_id,
                    affected_player_id=prior_controller_id,
                    damage_colors=self.card_colors(source),
                )
            )
        if self.priority_player_index is None:
            self.priority_player_index = self.active_player_index
            self.consecutive_passes = 0

    def _tap_permanent(self, permanent: Card) -> bool:
        """Tap once and expose matching attached and global event effects."""

        if permanent.tapped:
            return False
        permanent.tapped = True
        permanent_controller_id = permanent.controller_id or permanent.owner_id
        permanent_controller = self.player(permanent_controller_id)
        for player in self.players:
            for source in player.battlefield:
                if source.enchanted_card_id != permanent.id:
                    continue
                for effect in source.definition.attached_tap_mana_effects:
                    permanent_controller.mana_pool.add(effect.color, effect.amount)
                for effect in source.definition.attached_event_damage_effects:
                    if not effect.when_tapped:
                        continue
                    self.event_opportunities.append(
                        RuleEventOpportunity(
                            RuleEventKind.PERMANENT_TAPPED,
                            f"{source.name}: {permanent.name} was tapped",
                            card_id=permanent.id,
                            damage=effect.amount,
                            source_id=source.id,
                            source_name=source.name,
                            source_controller_id=source.controller_id,
                            affected_player_id=(
                                permanent.controller_id or permanent.owner_id
                            ),
                            damage_colors=self.card_colors(source),
                        )
                    )
                if source.definition.destroys_attached_land_when_tapped:
                    self.event_opportunities.append(
                        RuleEventOpportunity(
                            RuleEventKind.PERMANENT_TAPPED,
                            f"{source.name}: {permanent.name} was tapped",
                            card_id=permanent.id,
                            source_id=source.id,
                            source_name=source.name,
                            source_controller_id=source.controller_id,
                            affected_player_id=permanent_controller_id,
                            kudzu_land_destruction=True,
                        )
                    )
        if CardType.LAND in permanent.definition.card_types:
            for player in self.players:
                for source in player.battlefield:
                    if not self.continuous_permanent_is_active(source):
                        continue
                    for effect in source.definition.land_tap_mana_effects:
                        if effect.land_subtype not in self.land_subtypes(permanent):
                            continue
                        recipient = self.player(
                            permanent.owner_id
                            if effect.owner_receives
                            else permanent_controller_id
                        )
                        recipient.mana_pool.add(effect.color, effect.amount)
                    source_controller_id = source.controller_id or source.owner_id
                    for effect in source.definition.permanent_tapped_effects:
                        if (
                            effect.land_subtype is not None
                            and effect.land_subtype
                            not in self.land_subtypes(permanent)
                        ):
                            continue
                        if (
                            effect.opponent_controlled_only
                            and permanent_controller_id == source_controller_id
                        ):
                            continue
                        self.event_opportunities.append(
                            RuleEventOpportunity(
                                RuleEventKind.PERMANENT_TAPPED,
                                f"{source.name}: {permanent.name} was tapped",
                                card_id=permanent.id,
                                damage=effect.damage,
                                life_gain=effect.life_gain,
                                source_id=source.id,
                                source_name=source.name,
                                source_controller_id=source_controller_id,
                                affected_player_id=(
                                    permanent_controller_id
                                    if effect.damage
                                    else source_controller_id
                                ),
                                damage_colors=self.card_colors(source),
                            )
                        )
        if self.event_opportunities and self.priority_player_index is None:
            self.priority_player_index = self.active_player_index
            self.consecutive_passes = 0
        return True

    def _land_event_sources(
        self, *, land_enters: bool = False, land_lost: bool = False
    ) -> tuple[tuple[Card, LandEventDamageEffect], ...]:
        return tuple(
            (permanent, effect)
            for player in self.players
            for permanent in player.battlefield
            if self.continuous_permanent_is_active(permanent)
            for effect in permanent.definition.land_event_effects
            if effect.land_enters is land_enters
            and effect.land_lost is land_lost
        )

    def _record_land_event_opportunities(
        self,
        affected_player_id: str,
        land_name: str,
        sources: Iterable[tuple[Card, LandEventDamageEffect]],
        kind: RuleEventKind,
    ) -> None:
        added = False
        for source, effect in sources:
            self.event_opportunities.append(
                RuleEventOpportunity(
                    kind,
                    f"{source.name}: {land_name} "
                    + ("entered play" if kind is RuleEventKind.LAND_ENTERED else "was lost"),
                    damage=effect.amount,
                    source_id=source.id,
                    source_name=source.name,
                    source_controller_id=source.controller_id,
                    affected_player_id=affected_player_id,
                )
            )
            added = True
        if added and self.priority_player_index is None:
            self.priority_player_index = self.active_player_index
            self.consecutive_passes = 0

    def _matching_event_opportunities(
        self,
        source: Card,
        ability: ActivatedEventLifeGainAbility | ActivatedEventDrawAbility,
    ) -> list[RuleEventOpportunity]:
        return [
            event
            for event in self.event_opportunities
            if (source.id, event.id) not in self.event_ability_uses
            and (
                (
                    event.kind is RuleEventKind.SPELL_CAST
                    and (
                        isinstance(ability, ActivatedEventLifeGainAbility)
                        and ability.spell_color in event.spell_colors
                        or isinstance(ability, ActivatedEventDrawAbility)
                        and CardType.ENCHANTMENT in event.spell_card_types
                        and event.spell_caster_id == source.controller_id
                    )
                )
                or (
                    event.kind is RuleEventKind.CREATURE_DEATH
                    and isinstance(ability, ActivatedEventLifeGainAbility)
                    and ability.creature_death
                )
            )
        ]

    def _close_event_opportunities(
        self, event_ids: set[UUID] | None = None
    ) -> None:
        closing = (
            {event.id for event in self.event_opportunities}
            if event_ids is None
            else event_ids
        )
        damaging = [
            event
            for event in self.event_opportunities
            if event.id in closing and event.damage
        ]
        life_gaining = [
            event
            for event in self.event_opportunities
            if event.id in closing and event.life_gain
        ]
        discarding = [
            event for event in self.event_opportunities
            if event.id in closing and event.random_discard
        ]
        kudzu_events = [
            event
            for event in self.event_opportunities
            if event.id in closing and event.kudzu_land_destruction
        ]
        if self.pending_damage is not None:
            closing -= {event.id for event in damaging}
            damaging = []
        self.event_opportunities = [
            event for event in self.event_opportunities if event.id not in closing
        ]
        self.event_ability_uses = {
            use for use in self.event_ability_uses if use[1] not in closing
        }
        for event in life_gaining:
            assert event.affected_player_id is not None
            self._gain_life(
                self.player(event.affected_player_id), event.life_gain
            )
        if damaging:
            self._begin_damage_incident(DamageIncidentKind.RULE_EVENT)
            for event in damaging:
                assert event.affected_player_id is not None
                self._deal_damage(
                    self.player(event.affected_player_id),
                    event.damage,
                    event.source_name or "rules event",
                    source_id=event.source_id,
                    source_controller_id=event.source_controller_id,
                    source_colors=event.damage_colors,
                )
            self._resolve_damage_incident()
        for event in discarding:
            assert event.affected_player_id is not None
            self._discard_random(
                self.player(event.affected_player_id), event.random_discard
            )
        if kudzu_events:
            self._resolve_kudzu_events(kudzu_events)
        if not self.event_opportunities and self.deferred_damage_continuation:
            incident = self.deferred_damage_continuation
            self.deferred_damage_continuation = None
            self._continue_after_damage_incident(incident)

    def _resolve_kudzu_events(
        self, events: Iterable[RuleEventOpportunity]
    ) -> None:
        """Destroy tapped enchanted lands and queue Kudzu's mandatory moves."""

        pending: list[tuple[Card, str]] = []
        lands: dict[UUID, Card] = {}
        battlefield = tuple(
            card for player in self.players for card in player.battlefield
        )
        for event in events:
            source = next(
                (card for card in battlefield if card.id == event.source_id), None
            )
            land = next(
                (card for card in battlefield if card.id == event.card_id), None
            )
            if source is None or land is None or source.enchanted_card_id != land.id:
                continue
            if CardType.LAND not in self.card_types(land):
                continue
            chooser_id = land.controller_id or land.owner_id
            source.enchanted_card_id = None
            pending.append((source, chooser_id))
            lands[land.id] = land
        if lands:
            # The historical ruling treats Kudzu as destroying itself and says
            # that this destruction cannot be prevented, so no regeneration
            # incident is opened for the land.
            self._destroy_permanents(lands.values())
        for source, chooser_id in pending:
            if source.zone is not Zone.BATTLEFIELD:
                continue
            self._change_controller(source, chooser_id)
            candidates = tuple(
                card.id
                for player in self.players
                for card in player.battlefield
                if CardType.LAND in self.card_types(card)
                and not self.land_is_consecrated(card)
                and self._requirement_accepts_card(
                    source.definition.target_requirement,
                    card,
                    chooser_id,
                    source_colors=self.card_colors(source),
                )
            )
            if candidates:
                self.pending_kudzu_choices.append(
                    PendingKudzuChoice(chooser_id, source.id, candidates)
                )
            else:
                self._move_card(source, Zone.GRAVEYARD)

    def choose_kudzu_land(self, player_id: str, land: Card) -> None:
        """Move the front pending Kudzu to the selected legal land."""

        if not self.pending_kudzu_choices:
            raise RuntimeError("there is no pending Kudzu choice")
        choice = self.pending_kudzu_choices[0]
        if choice.chooser_id != player_id:
            raise RuntimeError(f"{self.player(choice.chooser_id).name} must choose")
        source = next(
            (
                card
                for player in self.players
                for card in player.battlefield
                if card.id == choice.kudzu_id
            ),
            None,
        )
        if (
            source is None
            or land.id not in choice.candidate_ids
            or land.zone is not Zone.BATTLEFIELD
            or CardType.LAND not in self.card_types(land)
            or self.land_is_consecrated(land)
            or not self._requirement_accepts_card(
                source.definition.target_requirement,
                land,
                player_id,
                source_colors=self.card_colors(source),
            )
        ):
            raise ValueError("Kudzu cannot be placed on that land")
        source.enchanted_card_id = land.id
        self.pending_kudzu_choices.pop(0)

    def _destroy_permanents(self, permanents: Iterable[Card]) -> None:
        """Single resolution hook for future regeneration/replacement handling."""

        graveyard_lengths = self._graveyard_lengths()
        doomed = tuple(
            permanent
            for permanent in permanents
            if permanent.zone is Zone.BATTLEFIELD
            and not self.land_is_consecrated(permanent)
        )
        land_losses = [
            (
                permanent,
                permanent.controller_id or permanent.owner_id,
                self._land_event_sources(land_lost=True),
            )
            for permanent in doomed
            if CardType.LAND in self.card_types(permanent)
        ]
        for permanent in doomed:
            if permanent.zone is Zone.BATTLEFIELD:
                self._move_card(
                    permanent, Zone.GRAVEYARD, record_land_loss=False
                )
        for permanent, controller_id, sources in land_losses:
            self._record_land_event_opportunities(
                controller_id,
                permanent.name,
                sources,
                RuleEventKind.LAND_LOST,
            )
        self._queue_new_graveyard_order_choices(graveyard_lengths)

    def legal_enchantment_targets(self, card: Card) -> list[Card]:
        """Compatibility wrapper for callers using the older Aura API."""

        self._validate_enchantment_cast(card)
        return self.legal_targets_for(card)

    def cast_enchantment(
        self,
        card: Card,
        target: Card | None = None,
        *,
        land_subtype: str | None = None,
    ) -> None:
        """Compatibility wrapper for directly casting an enchantment."""

        self._require_no_pending_action()
        self._validate_enchantment_cast(card)
        self._validate_land_type_choice(card, land_subtype)
        requirement = card.definition.target_requirement
        if requirement is not None:
            if target is None or target not in self.legal_targets_for(card):
                raise ValueError(
                    "an Enchant Creature spell must target a creature in play"
                )
            targets = (target,)
        else:
            if target is not None:
                raise ValueError(f"{card.name} does not require a target")
            targets = ()
        self._resolve_permanent_spell(
            card, targets, chosen_land_subtype=land_subtype
        )

    def check_state_based_actions(self) -> None:
        """Repeatedly remove creatures with nonpositive or lethally damaged toughness."""

        while True:
            # Existing engine fixtures commonly use empty libraries as compact
            # test scaffolds. Ante games opt into complete duel finalization;
            # non-ante callers may invoke ``finish_game`` explicitly.
            if self.ante_enabled and self._finish_if_players_lost():
                return
            doomed = [
                card
                for player in self.players
                for card in player.battlefield
                if CardType.CREATURE in self.card_types(card)
                and not self.land_is_consecrated(card)
                and (
                    self.creature_toughness(card) <= 0
                    or (
                        card.definition.landhome is not None
                        and not self.player_controls_land_subtype(
                            card.controller_id or card.owner_id,
                            card.definition.landhome.land_subtype,
                        )
                    )
                    or (
                        self.pending_damage is None
                        and card.damage >= self.creature_toughness(card)
                    )
                )
            ]
            if not doomed:
                return
            graveyard_lengths = self._graveyard_lengths()
            for creature in doomed:
                if creature.zone is Zone.BATTLEFIELD:
                    self._put_creature_in_graveyard(creature)
            self._queue_new_graveyard_order_choices(graveyard_lengths)

    def concede(self, player_id: str) -> None:
        """Concede the duel and award the ante to the remaining player."""

        if self.status is not GameStatus.IN_PROGRESS:
            raise RuntimeError("only an active duel can be conceded")
        self.player(player_id).has_lost = True
        self._finish_if_players_lost()

    def finish_game(self) -> AnteAward:
        """Finalize the current loss state and publish the ante disposition."""

        if not any(player.has_lost for player in self.players):
            raise RuntimeError("the duel has no losing player")
        self._finish_if_players_lost()
        assert self.ante_award is not None
        return self.ante_award

    def _finish_if_players_lost(self) -> bool:
        """Finish a decided duel and publish its ante disposition once."""

        if self.status is not GameStatus.IN_PROGRESS:
            return self.status is GameStatus.FINISHED
        if not any(player.has_lost for player in self.players):
            return False
        survivors = [player for player in self.players if not player.has_lost]
        winner_id = survivors[0].id if len(survivors) == 1 else None
        self.status = GameStatus.FINISHED
        self.priority_player_index = None
        cards = tuple(card for player in self.players for card in player.ante)
        self.ante_award = AnteAward(
            winner_id,
            tuple(card.id for card in cards),
            tuple(card.owner_id for card in cards),
        )
        if self.ante_award_hook is not None:
            self.ante_award_hook(self.ante_award)
        return True

    def put_permanent_in_graveyard(self, permanent: Card) -> None:
        """Move a permanent to its owner's graveyard, then update battlefield state."""

        self._require_no_pending_action()
        if permanent.zone is not Zone.BATTLEFIELD:
            raise ValueError(f"{permanent.name} is not in play")
        controller = self.player(permanent.controller_id or permanent.owner_id)
        if permanent not in controller.battlefield:
            raise ValueError(f"{permanent.name} is not on its controller's battlefield")
        self._move_card(permanent, Zone.GRAVEYARD)
        self.check_state_based_actions()

    def _put_creature_in_graveyard(self, creature: Card) -> None:
        self._move_card(creature, Zone.GRAVEYARD)

    def validate(self) -> None:
        """Check structural invariants useful after any future rules action."""

        seen: set[object] = set()
        valid_owners = {player.id for player in self.players}
        battlefield_ids = {
            card.id for player in self.players for card in player.battlefield
        }
        for player in self.players:
            for zone in (
                Zone.LIBRARY,
                Zone.HAND,
                Zone.BATTLEFIELD,
                Zone.GRAVEYARD,
                Zone.EXILE,
                Zone.ANTE,
            ):
                for card in player.cards_in(zone):
                    if card.id in seen:
                        raise ValueError(f"card {card.id} occurs in more than one zone")
                    seen.add(card.id)
                    if card.zone is not zone:
                        raise ValueError(f"{card.name} has inconsistent zone data")
                    if card.owner_id not in valid_owners:
                        raise ValueError(f"{card.name} has an unknown owner")
                    if zone is Zone.BATTLEFIELD and card.controller_id != player.id:
                        raise ValueError(f"{card.name} is not on its controller's battlefield")
                    if (
                        card.enchanted_card_id is not None
                        and card.enchanted_card_id not in battlefield_ids
                    ):
                        raise ValueError(f"{card.name} is attached to a card not in play")
        for card in self.stack:
            if card.id in seen:
                raise ValueError(f"card {card.id} occurs in more than one zone")
            seen.add(card.id)
            if card.zone is not Zone.STACK:
                raise ValueError(f"{card.name} has inconsistent zone data")
        if set(self.stack_spells) != {card.id for card in self.stack}:
            raise ValueError("response batch cards and casting choices disagree")
        if (
            self.interruptible_spell_id is not None
            and self.interruptible_spell_id not in self.stack_spells
        ):
            raise ValueError("interrupt window refers to a spell not being cast")
        if bool(
            self.stack
            or self.batch_abilities
            or self.timed_events
            or self.event_opportunities
            or self.pending_damage
            or self.pending_destruction
        ) != (
            self.priority_player_index is not None
        ):
            raise ValueError("response batch priority state is inconsistent")
        if self.priority_player_index is not None and not (
            0 <= self.priority_player_index < len(self.players)
        ):
            raise ValueError("priority player index is out of range")
        if self.pending_cast is not None:
            caster = self.player(self.pending_cast.caster_id)
            spell = self.pending_cast.spell
            if spell not in caster.hand or spell.zone is not Zone.HAND:
                raise ValueError("the pending spell is not in its caster's hand")
            if spell.definition.target_requirement is None:
                raise ValueError("the pending spell does not require targets")
