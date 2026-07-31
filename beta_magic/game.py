"""Player zones and top-level game state."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Iterable
from uuid import UUID

from .abilities import (
    ActivatedAbility,
    ActivatedDamageAbility,
    ActivatedDrawAbility,
    ActivatedEventLifeGainAbility,
    ActivatedDestroyAbility,
    ActivatedManaAbility,
    ActivatedPumpAbility,
    ActivatedPreventDamageAbility,
    ActivatedRegenerationAbility,
    ActivatedTapAbility,
    ActivatedUnblockableAbility,
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
from .combat import CombatMixin, CombatState
from .incident_resolution import DamageDestructionMixin, PendingPrevention
from .turn_flow import PendingTimedEvent, TurnFlowMixin
from .effects import (
    AddManaEffect,
    ContinuousEffect,
    CounterTargetSpellEffect,
    ChangeTargetColorEffect,
    DamageEffect,
    DestroyAllEffect,
    DestroyTargetsEffect,
    EffectRecipient,
    DrawCardsEffect,
    GainLifeEffect,
    GlobalDamageEffect,
    TemporaryPumpEffect,
    RegenerateTargetsEffect,
    MoveTargetsEffect,
    SetTappedEffect,
)
from .events import (
    CardMovedEvent,
    GameEvent,
    SpellCastEvent,
)
from .damage import (
    DamageIncident,
    DamageIncidentKind,
    DamageRecipientKind,
)
from .destruction import (
    DestructionIncident,
    DestructionTarget,
)
from .mana import ManaPool
from .rule_events import RuleEventKind, RuleEventOpportunity
from .types import (
    CardType,
    CombatStep,
    GameStatus,
    KeywordAbility,
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
        source = self.cards_in(card.zone)
        if card not in source:
            raise ValueError(f"{card.name} is not in its recorded {card.zone.value}")
        target = self.cards_in(destination)
        source.remove(card)
        card.zone = destination
        if destination is not Zone.BATTLEFIELD:
            card.tapped = False
            card.damage = 0
            card.controller_id = card.owner_id
            card.enchanted_card_id = None
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
            card.tapped = False


@dataclass(slots=True)
class GameState(
    TargetingCastingMixin,
    CombatMixin,
    DamageDestructionMixin,
    TurnFlowMixin,
    CharacteristicsMixin,
):
    players: list[PlayerState]
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
    combat: CombatState | None = None
    pending_cast: PendingCast | None = None
    pending_activation: PendingActivation | None = None
    pending_prevention: PendingPrevention | None = None
    batch_abilities: list[AbilityOnStack] = field(default_factory=list)
    events: list[GameEvent] = field(default_factory=list)
    temporary_creature_effects: dict[UUID, list[ContinuousEffect]] = field(
        default_factory=dict
    )
    ability_activations_this_turn: dict[UUID, int] = field(default_factory=dict)
    destroy_at_end_of_turn: set[UUID] = field(default_factory=set)
    timed_events: list[PendingTimedEvent] = field(default_factory=list)
    pending_damage: DamageIncident | None = None
    resolved_damage_incidents: list[DamageIncident] = field(default_factory=list)
    pending_destruction: DestructionIncident | None = None
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
            ):
                cards = player.cards_in(zone)
                if card in cards:
                    return player, cards
        raise ValueError(f"{card.name} is not in a game zone")

    def _move_card(self, card: Card, destination: Zone) -> None:
        """Perform one zone transition without recursively stabilizing the game."""

        _, source = self._locate_card(card)
        source_zone = card.zone
        source.remove(card)

        if destination is Zone.STACK:
            target = self.stack
        elif destination is Zone.BATTLEFIELD:
            card.base_controller_id = card.controller_id or card.owner_id
            self.battlefield_entry_sequence += 1
            card.battlefield_entry_sequence = self.battlefield_entry_sequence
            target = self.player(card.controller_id or card.owner_id).battlefield
        else:
            target = self.player(card.owner_id).cards_in(destination)

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
        target.append(card)
        self.events.append(
            CardMovedEvent(card.id, card.name, source_zone, destination)
        )

        if (
            source_zone is Zone.BATTLEFIELD
            and destination is Zone.GRAVEYARD
            and CardType.CREATURE in self.card_types(card)
        ):
            self._record_creature_death_opportunity(card)

        if source_zone is Zone.BATTLEFIELD:
            self.temporary_creature_effects.pop(card.id, None)
            self.ability_activations_this_turn.pop(card.id, None)
            self.destroy_at_end_of_turn.discard(card.id)
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
            if aura.enchanted_card_id in desired_controllers:
                desired_controllers[aura.enchanted_card_id] = (
                    aura.controller_id or aura.owner_id
                )
        for permanent in battlefield:
            desired = desired_controllers[permanent.id]
            if permanent.controller_id != desired:
                self._change_controller(permanent, desired)

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
        """Play the active player's one land for the turn."""

        self._require_no_pending_action()
        if self.status is not GameStatus.IN_PROGRESS:
            raise RuntimeError("lands can only be played during a game")
        if self.current_phase is not TurnPhase.MAIN:
            raise RuntimeError("lands can only be played during the Main phase")
        if self.combat is not None:
            raise RuntimeError("lands cannot be played during an attack")
        if self.lands_played_this_turn:
            raise RuntimeError("the active player has already played a land this turn")
        if card not in self.active_player.hand:
            raise ValueError("the land must be in the active player's hand")
        if CardType.LAND not in card.definition.card_types:
            raise ValueError(f"{card.name} is not a land")

        card.controller_id = self.active_player.id
        self._move_card(card, Zone.BATTLEFIELD)
        card.entered_battlefield_turn = self.turn_number
        self.lands_played_this_turn += 1
        self.check_state_based_actions()

    def tap_land_for_mana(self, player_id: str, card: Card) -> None:
        """Compatibility shortcut for lands with exactly one mana ability."""

        abilities = self.activated_abilities(card)
        if len(abilities) != 1:
            raise ValueError(f"{card.name} requires a mana ability choice")
        self.activate_ability(player_id, card, 0)

    def _record_spell_cast_opportunity(self, spell: Card) -> None:
        """Expose one catchable event for a successfully cast spell."""

        matching = any(
            isinstance(ability, ActivatedEventLifeGainAbility)
            and ability.spell_color is not None
            and ability.spell_color in self.card_colors(spell)
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

        self.event_opportunities = [
            event
            for event in self.event_opportunities
            if event.spell_id != spell.id
        ]
        self._record_spell_cast_opportunity(spell)

    def _record_creature_death_opportunity(self, creature: Card) -> None:
        """Expose a post-regeneration death event if Soul Net is in play."""

        matching = any(
            isinstance(ability, ActivatedEventLifeGainAbility)
            and ability.creature_death
            for player in self.players
            for permanent in player.battlefield
            for ability in self.activated_abilities(permanent)
        )
        if not matching:
            return
        self.event_opportunities.append(
            RuleEventOpportunity(
                RuleEventKind.CREATURE_DEATH,
                f"{creature.name} died",
                card_id=creature.id,
            )
        )
        if self.priority_player_index is None:
            self.priority_player_index = self.active_player_index
            self.consecutive_passes = 0

    def _matching_event_opportunities(
        self, source: Card, ability: ActivatedEventLifeGainAbility
    ) -> list[RuleEventOpportunity]:
        return [
            event
            for event in self.event_opportunities
            if (source.id, event.id) not in self.event_ability_uses
            and (
                (
                    event.kind is RuleEventKind.SPELL_CAST
                    and ability.spell_color in event.spell_colors
                )
                or (
                    event.kind is RuleEventKind.CREATURE_DEATH
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
        self.event_opportunities = [
            event for event in self.event_opportunities if event.id not in closing
        ]
        self.event_ability_uses = {
            use for use in self.event_ability_uses if use[1] not in closing
        }
        if not self.event_opportunities and self.deferred_damage_continuation:
            incident = self.deferred_damage_continuation
            self.deferred_damage_continuation = None
            self._continue_after_damage_incident(incident)

    def activate_ability(
        self, player_id: str, card: Card, ability_index: int
    ) -> PendingActivation | None:
        """Pay a permanent ability's costs and apply its effect."""

        try:
            selected_ability = self.activated_abilities(card)[ability_index]
        except IndexError as error:
            raise ValueError(f"{card.name} has no such activated ability") from error
        if isinstance(selected_ability, ActivatedPreventDamageAbility):
            player, ability = self._validate_prevention_activation(
                player_id, card, ability_index
            )
            self.pending_prevention = PendingPrevention(
                card,
                player.id,
                ability.amount,
                ability_index=ability_index,
                source_color=ability.source_color,
                controller_only=ability.controller_only,
            )
            return None
        if isinstance(selected_ability, ActivatedRegenerationAbility):
            player, ability, affected_card = self._validate_regeneration_activation(
                player_id, card, ability_index
            )
            player.mana_pool.pay(ability.mana_cost)
            affected_card.tapped = True
            affected_card.damage = 0
            if self.pending_damage is not None:
                self.pending_damage.regenerated_card_ids.add(affected_card.id)
            else:
                assert self.pending_destruction is not None
                self.pending_destruction.regenerated_card_ids.add(affected_card.id)
            if self.combat is not None:
                self.combat.regenerated_card_ids.add(affected_card.id)
            self.priority_player_index = (
                self.players.index(player) + 1
            ) % len(self.players)
            self.consecutive_passes = 0
            return None

        player, ability = self._validate_ability_activation(
            player_id, card, ability_index
        )
        if isinstance(
            ability,
            (
                ActivatedDamageAbility,
                ActivatedDestroyAbility,
                ActivatedTapAbility,
                ActivatedUnblockableAbility,
            ),
        ):
            pending = PendingActivation(card, player.id, ability_index)
            self.pending_activation = pending
            if (
                not self.legal_targets_for()
                and not self.legal_player_targets_for()
            ):
                self.pending_activation = None
                raise RuntimeError(f"there are no legal targets for {card.name}")
            return pending
        if isinstance(ability, ActivatedManaAbility):
            if ability.tap_cost:
                card.tapped = True
            player.mana_pool.add(ability.color, ability.amount)
            # Producing mana is an interrupt-speed action. It resolves
            # immediately and does not surrender priority or close the
            # current spell's interrupt window, but any earlier passes no
            # longer count toward resolving that window.
            self.consecutive_passes = 0
            if ability.sacrifice_source:
                # Black Lotus destroys itself as part of its own ability. The
                # era's ruling makes that destruction non-regenerable.
                self._move_card(card, Zone.GRAVEYARD)
            self.check_state_based_actions()
            return None
        if isinstance(ability, ActivatedDrawAbility):
            player.mana_pool.pay(ability.mana_cost)
            if ability.tap_cost:
                card.tapped = True
            self.batch_abilities.append(
                AbilityOnStack(
                    card,
                    card.name,
                    player.id,
                    ability,
                    (),
                )
            )
            self.interruptible_spell_id = None
            self.priority_player_index = (
                self.players.index(player) + 1
            ) % len(self.players)
            self.consecutive_passes = 0
            return None
        if isinstance(ability, ActivatedEventLifeGainAbility):
            opportunity = self._matching_event_opportunities(card, ability)[0]
            player.mana_pool.pay(ability.mana_cost)
            self.event_ability_uses.add((card.id, opportunity.id))
            self.batch_abilities.append(
                AbilityOnStack(card, card.name, player.id, ability, ())
            )
            self.interruptible_spell_id = None
            self.priority_player_index = (
                self.players.index(player) + 1
            ) % len(self.players)
            self.consecutive_passes = 0
            return None

        player.mana_pool.pay(ability.mana_cost)
        affected_card = (
            self._attached_creature(card)
            if ability.affects_attached_creature
            else card
        )
        self.batch_abilities.append(
            AbilityOnStack(
                card,
                card.name,
                player.id,
                ability,
                (affected_card,),
            )
        )
        self.interruptible_spell_id = None
        activations = self.ability_activations_this_turn.get(card.id, 0) + 1
        self.ability_activations_this_turn[card.id] = activations
        if (
            ability.safe_activations_per_turn is not None
            and activations > ability.safe_activations_per_turn
        ):
            self.destroy_at_end_of_turn.add(card.id)
        self.priority_player_index = (
            self.players.index(player) + 1
        ) % len(self.players)
        self.consecutive_passes = 0
        return None

    def _validate_ability_activation(
        self, player_id: str, card: Card, ability_index: int
    ) -> tuple[PlayerState, ActivatedAbility]:
        """Return an ability and controller after validating all activation costs."""

        self._require_no_pending_action(allow_stack=True, allow_damage=True)
        if self.status is not GameStatus.IN_PROGRESS:
            raise RuntimeError("mana can only be produced during a game")
        if self.current_phase is TurnPhase.UNTAP:
            raise RuntimeError("abilities cannot be activated during the Untap phase")
        player = self.player(player_id)
        if (
            self.priority_player_index is not None
            and player is not self.players[self.priority_player_index]
        ):
            raise RuntimeError(
                f"{self.players[self.priority_player_index].name} has priority"
            )
        if card not in player.battlefield or card.zone is not Zone.BATTLEFIELD:
            raise ValueError("the permanent must be on that player's battlefield")
        if card.controller_id != player_id:
            raise ValueError("a player can only activate a permanent they control")
        if ability_index < 0:
            raise ValueError(f"{card.name} has no such activated ability")
        try:
            ability = self.activated_abilities(card)[ability_index]
        except IndexError as error:
            raise ValueError(f"{card.name} has no such activated ability") from error
        if not isinstance(
            ability,
            (
                ActivatedManaAbility,
                ActivatedPumpAbility,
                ActivatedDamageAbility,
                ActivatedDestroyAbility,
                ActivatedTapAbility,
                ActivatedUnblockableAbility,
                ActivatedDrawAbility,
                ActivatedEventLifeGainAbility,
                ActivatedPreventDamageAbility,
            ),
        ):
            raise ValueError("unsupported activated ability")
        if (
            (
                self.pending_damage is not None
                or self.pending_destruction is not None
            )
            and not isinstance(
                ability, (ActivatedManaAbility, ActivatedPreventDamageAbility)
            )
        ):
            raise RuntimeError(
                "only mana, prevention, and regeneration abilities can be used "
                "during damage resolution"
            )
        if (
            isinstance(ability, ActivatedPumpAbility)
            and ability.affects_attached_creature
        ):
            self._attached_creature(card)
        if (
            isinstance(
                ability,
                (
                    ActivatedPumpAbility,
                    ActivatedDamageAbility,
                    ActivatedDestroyAbility,
                    ActivatedTapAbility,
                    ActivatedUnblockableAbility,
                    ActivatedDrawAbility,
                    ActivatedEventLifeGainAbility,
                ),
            )
            and not player.mana_pool.can_pay(ability.mana_cost)
        ):
            raise RuntimeError(
                f"not enough mana to activate {card.name}: {ability.label}"
            )
        if isinstance(ability, ActivatedEventLifeGainAbility):
            if card.tapped and CardType.ARTIFACT in card.definition.card_types:
                raise RuntimeError(f"{card.name} is tapped and cannot be used")
            if not self._matching_event_opportunities(card, ability):
                raise RuntimeError(
                    f"{card.name} has no matching event to catch"
                )
        has_tap_cost = (
            isinstance(ability, ActivatedManaAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedDamageAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedDestroyAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedTapAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedUnblockableAbility)
            and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedDrawAbility) and ability.tap_cost
        )
        if has_tap_cost and card.tapped:
            raise RuntimeError(f"{card.name} is already tapped")
        if (
            has_tap_cost
            and CardType.CREATURE in card.definition.card_types
            and self.has_summoning_sickness(card)
        ):
            raise RuntimeError(
                f"{card.name} did not begin the turn under its controller's control"
            )
        return player, ability

    def _attached_creature(self, aura: Card) -> Card:
        """Return the in-play creature currently enchanted by an Aura."""

        if aura.enchanted_card_id is None:
            raise ValueError(f"{aura.name} is not enchanting a creature")
        for player in self.players:
            for permanent in player.battlefield:
                if (
                    permanent.id == aura.enchanted_card_id
                    and CardType.CREATURE in self.card_types(permanent)
                ):
                    return permanent
        raise ValueError(f"{aura.name}'s enchanted creature is not in play")

    def can_activate_ability(
        self, player_id: str, card: Card, ability_index: int
    ) -> bool:
        """Whether an ability can currently be activated without changing state."""

        try:
            ability = self.activated_abilities(card)[ability_index]
            if isinstance(ability, ActivatedRegenerationAbility):
                self._validate_regeneration_activation(
                    player_id, card, ability_index
                )
            else:
                self._validate_ability_activation(player_id, card, ability_index)
        except (KeyError, ValueError, RuntimeError):
            return False
        return True

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
            resolved = self._resolve_batch()
            if (
                self.pending_damage is None
                and self.pending_destruction is None
            ):
                self.consecutive_passes = 0
                self.priority_player_index = (
                    self.active_player_index
                    if self.timed_events or self.event_opportunities
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
                    else None
                )
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
                else None
            )
        return ()

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
        elif self.batch_abilities or self.event_opportunities:
            self.priority_player_index = self.active_player_index
        else:
            self.priority_player_index = None
        self.check_state_based_actions()
        return (interrupt,)

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
                    ability.ability, ActivatedEventLifeGainAbility
                )
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
                        self._deal_damage(
                            recipient,
                            effect.amount,
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
                        if isinstance(target, PlayerState):
                            target.life += amount
                elif isinstance(effect, DrawCardsEffect):
                    amount = effect.amount + effect.amount_per_x * spell.x_value
                    for target in spell.targets:
                        if isinstance(target, PlayerState):
                            target.draw(amount)
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
                elif isinstance(effect, SetTappedEffect):
                    tapped = spell.chosen_mode == "Tap"
                    for target in spell.targets:
                        if isinstance(target, Card):
                            target.tapped = tapped

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
            elif isinstance(declared.ability, ActivatedDestroyAbility):
                pending_destruction.extend(
                    (target, declared.ability.regeneration_allowed)
                    for target in declared.targets
                    if isinstance(target, Card)
                )
            elif isinstance(declared.ability, ActivatedTapAbility):
                for target in declared.targets:
                    if isinstance(target, Card):
                        target.tapped = True
            elif isinstance(declared.ability, ActivatedUnblockableAbility):
                for target in declared.targets:
                    if isinstance(target, Card):
                        self.temporary_creature_effects.setdefault(
                            target.id, []
                        ).append(ContinuousEffect(unblockable=True))
            elif isinstance(declared.ability, ActivatedDrawAbility):
                self.player(declared.controller_id).draw(
                    declared.ability.amount
                )
            elif isinstance(
                declared.ability, ActivatedEventLifeGainAbility
            ):
                self.player(declared.controller_id).life += (
                    declared.ability.amount
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
            DestructionTarget(card.id, card.name, regeneration_allowed)
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
                    target.tapped = True
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

    def _destroy_permanents(self, permanents: Iterable[Card]) -> None:
        """Single resolution hook for future regeneration/replacement handling."""

        for permanent in tuple(permanents):
            if permanent.zone is Zone.BATTLEFIELD:
                self._move_card(permanent, Zone.GRAVEYARD)

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
            doomed = [
                card
                for player in self.players
                for card in player.battlefield
                if CardType.CREATURE in self.card_types(card)
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
            for creature in doomed:
                if creature.zone is Zone.BATTLEFIELD:
                    self._put_creature_in_graveyard(creature)

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
