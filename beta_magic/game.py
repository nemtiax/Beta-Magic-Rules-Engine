"""Player zones and top-level game state."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Iterable
from uuid import UUID

from .cards import (
    ActivatedAbility,
    ActivatedDamageAbility,
    ActivatedDestroyAbility,
    ActivatedManaAbility,
    ActivatedPumpAbility,
    ActivatedRegenerationAbility,
    TargetedActivatedAbility,
    Card,
    CardDefinition,
    ContinuousEffect,
    DamageEffect,
    DestroyAllEffect,
    DestroyTargetsEffect,
    EffectRecipient,
    EffectScope,
    TargetRequirement,
    TemporaryPumpEffect,
    MoveTargetsEffect,
    UpkeepDamageEffect,
    UpkeepDamageRecipient,
    UpkeepCostEffect,
    UpkeepEffect,
    UpkeepFailure,
    VariableStatKind,
)
from .events import (
    CardMovedEvent,
    DamageEvent,
    GameEvent,
    ManaBurnEvent,
    SpellCastEvent,
)
from .damage import (
    DamageIncident,
    DamageIncidentKind,
    DamagePacket,
    DamageRecipientKind,
    DamageResolutionStep,
)
from .mana import ManaPool
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
class CombatState:
    """Mutable state for one attack nested inside the Main phase."""

    attacking_player_id: str
    defending_player_id: str
    step: CombatStep = CombatStep.ATTACK_RESPONSE
    attackers: list[Card] = field(default_factory=list)
    blockers: dict[UUID, list[Card]] = field(default_factory=dict)
    damage_allocations: dict[Card, dict[Card, int]] = field(default_factory=dict)
    regenerated_card_ids: set[UUID] = field(default_factory=set)


@dataclass(slots=True)
class PendingCast:
    """A spell whose caster still needs to supply its required targets."""

    spell: Card
    caster_id: str


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
    ability: TargetedActivatedAbility
    targets: tuple[Card | PlayerState, ...]


@dataclass(slots=True)
class SpellOnStack:
    """Casting choices retained until a spell resolves."""

    card: Card
    caster_id: str
    targets: tuple[Card | PlayerState, ...] = ()


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
        if isinstance(self.effect, UpkeepCostEffect):
            consequence = (
                f"take {self.effect.damage} damage"
                if self.effect.failure is UpkeepFailure.DAMAGE_CONTROLLER
                else "destroy it"
            )
            return (
                f"{self.source_name}: pay {self.effect.mana_cost.compact} "
                f"or {consequence}"
            )
        return (
            f"{self.source_name}: {self.effect.amount} damage to "
            f"{self.affected_player_name}"
        )


@dataclass(slots=True)
class GameState:
    players: list[PlayerState]
    active_player_index: int = 0
    turn_number: int = 0
    status: GameStatus = GameStatus.NOT_STARTED
    stack: list[Card] = field(default_factory=list)
    stack_spells: dict[UUID, SpellOnStack] = field(default_factory=dict)
    priority_player_index: int | None = None
    consecutive_passes: int = 0
    current_phase: TurnPhase | None = None
    lands_played_this_turn: int = 0
    attacks_this_turn: int = 0
    combat: CombatState | None = None
    pending_cast: PendingCast | None = None
    pending_activation: PendingActivation | None = None
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
    pause_for_damage_windows: bool = False

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
        if self.pending_damage is not None and not allow_damage:
            raise RuntimeError("finish resolving the pending damage incident first")
        if (self.stack or self.batch_abilities) and not allow_stack:
            raise RuntimeError("both players must pass priority to resolve the batch")
        if self.timed_events and not allow_stack:
            raise RuntimeError(
                "both players must pass priority to resolve the timed event"
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
            target = self.player(card.controller_id or card.owner_id).battlefield
        else:
            target = self.player(card.owner_id).cards_in(destination)

        card.zone = destination
        if destination is not Zone.BATTLEFIELD:
            card.tapped = False
            card.damage = 0
            card.controller_id = card.owner_id
            card.entered_battlefield_turn = None
            card.enchanted_card_id = None
        target.append(card)
        self.events.append(
            CardMovedEvent(card.id, card.name, source_zone, destination)
        )

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

    def move_card(self, card: Card, destination: Zone) -> None:
        """Move a card through the engine and then stabilize the battlefield."""

        self._require_no_pending_action()
        self._move_card(card, destination)
        self.check_state_based_actions()

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
        self.status = GameStatus.IN_PROGRESS
        self.lands_played_this_turn = 0
        self.attacks_this_turn = 0
        self._enter_phase(TurnPhase.UNTAP)

    def next_turn(self) -> PlayerState:
        self._require_no_pending_action()
        if self.status is not GameStatus.IN_PROGRESS:
            raise RuntimeError("turns can only advance during a game")
        if self.current_phase is not TurnPhase.END:
            raise RuntimeError("a new turn can only begin after the End phase")
        self._empty_mana_pools()
        self._finish_turn_effects()
        self._clear_creature_damage()
        self.temporary_creature_effects.clear()
        self.ability_activations_this_turn.clear()
        self.check_state_based_actions()
        self.active_player_index = (self.active_player_index + 1) % len(self.players)
        self.turn_number += 1
        self.lands_played_this_turn = 0
        self.attacks_this_turn = 0
        self._enter_phase(TurnPhase.UNTAP)
        return self.active_player

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

        abilities = card.definition.activated_abilities
        if len(abilities) != 1:
            raise ValueError(f"{card.name} requires a mana ability choice")
        self.activate_ability(player_id, card, 0)

    def activate_ability(
        self, player_id: str, card: Card, ability_index: int
    ) -> PendingActivation | None:
        """Pay a permanent ability's costs and apply its effect."""

        try:
            selected_ability = card.definition.activated_abilities[ability_index]
        except IndexError as error:
            raise ValueError(f"{card.name} has no such activated ability") from error
        if isinstance(selected_ability, ActivatedRegenerationAbility):
            player, ability = self._validate_regeneration_activation(
                player_id, card, ability_index
            )
            player.mana_pool.pay(ability.mana_cost)
            card.tapped = True
            card.damage = 0
            assert self.pending_damage is not None
            self.pending_damage.regenerated_card_ids.add(card.id)
            if self.combat is not None:
                self.combat.regenerated_card_ids.add(card.id)
            self.priority_player_index = (
                self.players.index(player) + 1
            ) % len(self.players)
            self.consecutive_passes = 0
            return None

        player, ability = self._validate_ability_activation(
            player_id, card, ability_index
        )
        if isinstance(ability, (ActivatedDamageAbility, ActivatedDestroyAbility)):
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
            if self.pending_damage is not None:
                self.consecutive_passes = 0
            if ability.sacrifice_source:
                # Black Lotus destroys itself as part of its own ability. The
                # era's ruling makes that destruction non-regenerable.
                self._move_card(card, Zone.GRAVEYARD)
                self.check_state_based_actions()
            return None

        player.mana_pool.pay(ability.mana_cost)
        affected_card = (
            self._attached_creature(card)
            if ability.affects_attached_creature
            else card
        )
        self.temporary_creature_effects.setdefault(affected_card.id, []).append(
            ContinuousEffect(
                power=ability.power,
                toughness=ability.toughness,
                granted_abilities=ability.granted_abilities,
            )
        )
        activations = self.ability_activations_this_turn.get(card.id, 0) + 1
        self.ability_activations_this_turn[card.id] = activations
        if (
            ability.safe_activations_per_turn is not None
            and activations > ability.safe_activations_per_turn
        ):
            self.destroy_at_end_of_turn.add(card.id)
        self.check_state_based_actions()
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
            ability = card.definition.activated_abilities[ability_index]
        except IndexError as error:
            raise ValueError(f"{card.name} has no such activated ability") from error
        if not isinstance(
            ability,
            (
                ActivatedManaAbility,
                ActivatedPumpAbility,
                ActivatedDamageAbility,
                ActivatedDestroyAbility,
            ),
        ):
            raise ValueError("unsupported activated ability")
        if (
            self.pending_damage is not None
            and not isinstance(ability, ActivatedManaAbility)
        ):
            raise RuntimeError(
                "only mana and regeneration abilities can be used "
                "during damage resolution"
            )
        if (
            isinstance(ability, ActivatedPumpAbility)
            and ability.affects_attached_creature
        ):
            self._attached_creature(card)
        if (
            isinstance(ability, (ActivatedPumpAbility, ActivatedDestroyAbility))
            and not player.mana_pool.can_pay(ability.mana_cost)
        ):
            raise RuntimeError(
                f"not enough mana to activate {card.name}: {ability.label}"
            )
        has_tap_cost = (
            isinstance(ability, ActivatedManaAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedDamageAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedDestroyAbility) and ability.tap_cost
        )
        if has_tap_cost and card.tapped:
            raise RuntimeError(f"{card.name} is already tapped")
        if (
            has_tap_cost
            and CardType.CREATURE in card.definition.card_types
            and card.entered_battlefield_turn == self.turn_number
        ):
            raise RuntimeError(
                f"{card.name} did not begin the turn under its controller's control"
            )
        return player, ability

    def _validate_regeneration_activation(
        self, player_id: str, card: Card, ability_index: int
    ) -> tuple[PlayerState, ActivatedRegenerationAbility]:
        """Validate regeneration at the point lethal damage would kill a creature."""

        if (
            self.pending_damage is None
            or self.pending_damage.step is not DamageResolutionStep.REGENERATION
        ):
            raise RuntimeError(
                "regeneration can only be used during the regeneration window"
            )
        player = self.player(player_id)
        if (
            self.priority_player_index is None
            or player is not self.players[self.priority_player_index]
        ):
            priority_name = (
                self.players[self.priority_player_index].name
                if self.priority_player_index is not None
                else "no player"
            )
            raise RuntimeError(f"{priority_name} has priority")
        if card not in player.battlefield or card.controller_id != player_id:
            raise ValueError("a player can only regenerate a creature they control")
        try:
            ability = card.definition.activated_abilities[ability_index]
        except IndexError as error:
            raise ValueError(f"{card.name} has no such activated ability") from error
        if not isinstance(ability, ActivatedRegenerationAbility):
            raise ValueError("that ability does not regenerate its source")
        if self.creature_toughness(card) <= 0:
            raise RuntimeError("regeneration cannot save a creature with zero toughness")
        if (
            card.damage < self.creature_toughness(card)
            and card.id not in self.pending_damage.destroyed_card_ids
        ):
            raise RuntimeError(f"{card.name} is not facing death or destruction")
        if not player.mana_pool.can_pay(ability.mana_cost):
            raise RuntimeError(f"not enough mana to regenerate {card.name}")
        return player, ability

    def _attached_creature(self, aura: Card) -> Card:
        """Return the in-play creature currently enchanted by an Aura."""

        if aura.enchanted_card_id is None:
            raise ValueError(f"{aura.name} is not enchanting a creature")
        for player in self.players:
            for permanent in player.battlefield:
                if (
                    permanent.id == aura.enchanted_card_id
                    and CardType.CREATURE in permanent.definition.card_types
                ):
                    return permanent
        raise ValueError(f"{aura.name}'s enchanted creature is not in play")

    def can_activate_ability(
        self, player_id: str, card: Card, ability_index: int
    ) -> bool:
        """Whether an ability can currently be activated without changing state."""

        try:
            ability = card.definition.activated_abilities[ability_index]
            if isinstance(ability, ActivatedRegenerationAbility):
                self._validate_regeneration_activation(
                    player_id, card, ability_index
                )
            else:
                self._validate_ability_activation(player_id, card, ability_index)
        except (KeyError, ValueError, RuntimeError):
            return False
        return True

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

    def cast_creature(self, card: Card) -> None:
        """Pay for and resolve a creature spell from the active player's hand."""

        self._require_no_pending_action()
        self._validate_permanent_cast(card, CardType.CREATURE)
        self._resolve_permanent_spell(card, ())

    def _validate_permanent_cast(
        self, card: Card, expected_type: CardType | None = None
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
        if not player.mana_pool.can_pay(card.definition.mana_cost):
            raise RuntimeError(f"not enough mana to cast {card.name}")

    def _validate_enchantment_cast(self, card: Card) -> None:
        self._validate_permanent_cast(card, CardType.ENCHANTMENT)

    def _caster_for(self, card: Card) -> PlayerState:
        for player in self.players:
            if card in player.hand:
                return player
        raise ValueError("the spell must be in a player's hand")

    def _validate_nonpermanent_cast(self, card: Card) -> PlayerState:
        if self.status is not GameStatus.IN_PROGRESS:
            raise RuntimeError("spells can only be cast during a game")
        caster = self._caster_for(card)
        is_instant = CardType.INSTANT in card.definition.card_types
        is_sorcery = CardType.SORCERY in card.definition.card_types
        if not (is_instant or is_sorcery):
            raise ValueError(f"{card.name} is not an instant or sorcery")
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
        if not caster.mana_pool.can_pay(card.definition.mana_cost):
            raise RuntimeError(f"not enough mana to cast {card.name}")
        return caster

    def _validate_cast(self, card: Card) -> PlayerState:
        caster = self._caster_for(card)
        if (
            self.priority_player_index is not None
            and caster is not self.players[self.priority_player_index]
        ):
            raise RuntimeError(
                f"{self.players[self.priority_player_index].name} has priority"
            )
        if card.definition.is_permanent:
            self._validate_permanent_cast(card)
            return caster
        return self._validate_nonpermanent_cast(card)

    def begin_cast(self, card: Card) -> PendingCast | None:
        """Cast an untargeted spell or wait for the spell's targets."""

        self._require_no_pending_action(allow_stack=True)
        caster = self._validate_cast(card)
        if card.definition.target_requirement is not None:
            if not self.legal_targets_for(card) and not self.legal_player_targets_for(card):
                raise RuntimeError(f"there are no legal targets for {card.name}")
            self.pending_cast = PendingCast(card, caster.id)
            return self.pending_cast
        self._cast_spell(card, (), caster)
        return None

    def legal_targets_for(self, card: Card | None = None) -> list[Card]:
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
        caster_id = (
            self.pending_cast.caster_id
            if self.pending_cast is not None
            and self.pending_cast.spell is spell
            else pending_ability.controller_id
            if pending_ability is not None
            else spell.controller_id or spell.owner_id
        )
        if requirement.zone is Zone.STACK:
            candidates = self.stack
        else:
            candidates = [
                candidate
                for player in self.players
                for candidate in player.cards_in(requirement.zone)
            ]
        return [
            candidate
            for candidate in candidates
            if self._requirement_accepts_card(requirement, candidate, caster_id)
        ]

    def _requirement_accepts_card(
        self,
        requirement: TargetRequirement,
        card: Card,
        caster_id: str | None = None,
        *,
        check_tapped: bool = True,
    ) -> bool:
        if not requirement.accepts_card(card, check_tapped=check_tapped):
            return False
        if requirement.owner_only and card.owner_id != caster_id:
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
        return list(self.players)

    @staticmethod
    def _pending_ability_requirement(
        pending: PendingActivation | None,
    ) -> TargetRequirement | None:
        if pending is None:
            return None
        ability = pending.source.definition.activated_abilities[
            pending.ability_index
        ]
        return (
            ability.target_requirement
            if isinstance(ability, (ActivatedDamageAbility, ActivatedDestroyAbility))
            else None
        )

    def complete_pending_activation(
        self, targets: Iterable[Card | PlayerState]
    ) -> None:
        """Choose targets, pay tap costs, and declare an activated fast effect."""

        if self.pending_activation is None:
            raise RuntimeError("there is no activated ability waiting for targets")
        pending = self.pending_activation
        ability = pending.source.definition.activated_abilities[
            pending.ability_index
        ]
        assert isinstance(ability, (ActivatedDamageAbility, ActivatedDestroyAbility))
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
            pending.source.tapped = True
        if isinstance(ability, ActivatedDestroyAbility):
            player.mana_pool.pay(ability.mana_cost)
        self.batch_abilities.append(
            AbilityOnStack(
                pending.source,
                pending.source.name,
                player.id,
                ability,
                chosen,
            )
        )
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
        if len(chosen) != requirement.count:
            raise ValueError(
                f"{pending.spell.name} requires {requirement.count} target(s)"
            )
        target_keys = {
            ("card", target.id)
            if isinstance(target, Card)
            else ("player", target.id)
            for target in chosen
        }
        if len(target_keys) != len(chosen):
            raise ValueError("the same card cannot be chosen as a target twice")
        legal_cards = self.legal_targets_for(pending.spell)
        legal_players = self.legal_player_targets_for(pending.spell)
        if any(
            target not in (
                legal_cards if isinstance(target, Card) else legal_players
            )
            for target in chosen
        ):
            raise ValueError(f"illegal target for {pending.spell.name}")
        caster = self.player(pending.caster_id)
        validated_caster = self._validate_cast(pending.spell)
        if caster is not validated_caster:
            raise RuntimeError("the pending spell's caster has changed")
        self.pending_cast = None
        self._cast_spell(pending.spell, chosen, caster)

    def cancel_pending_cast(self) -> None:
        if self.pending_cast is None:
            raise RuntimeError("there is no pending spell to cancel")
        self.pending_cast = None

    def _resolve_permanent_spell(
        self, card: Card, targets: tuple[Card, ...]
    ) -> None:
        player = self.active_player
        player.mana_pool.pay(card.definition.mana_cost)
        card.controller_id = player.id
        self._move_card(card, Zone.BATTLEFIELD)
        card.entered_battlefield_turn = self.turn_number
        card.enchanted_card_id = targets[0].id if targets else None
        self.events.append(
            SpellCastEvent(
                card_id=card.id,
                card_name=card.name,
                caster_id=player.id,
                target_ids=tuple(target.id for target in targets),
                target_names=tuple(target.name for target in targets),
            )
        )
        self.check_state_based_actions()

    def _cast_spell(
        self,
        card: Card,
        targets: tuple[Card | PlayerState, ...],
        caster: PlayerState,
    ) -> None:
        """Pay for a spell and add it to the current response batch."""

        caster.mana_pool.pay(card.definition.mana_cost)
        card.controller_id = caster.id
        self._move_card(card, Zone.STACK)
        self.stack_spells[card.id] = SpellOnStack(card, caster.id, targets)
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
                    if isinstance(target, PlayerState)
                ),
                target_names=tuple(target.name for target in targets),
            )
        )
        self.priority_player_index = (
            self.players.index(caster) + 1
        ) % len(self.players)
        self.consecutive_passes = 0

    def pass_priority(self, player_id: str) -> tuple[Card, ...] | None:
        """Pass once; unanimous passes resolve a batch or pending timed event."""

        if self.pending_damage is not None:
            self._pass_damage_priority(player_id)
            return None
        self._require_no_pending_action(allow_stack=True)
        if (
            not self.stack
            and not self.batch_abilities
            and not self.timed_events
            or self.priority_player_index is None
        ):
            raise RuntimeError("there is no batch or timed event waiting to resolve")
        player = self.player(player_id)
        if player is not self.players[self.priority_player_index]:
            raise RuntimeError(
                f"{self.players[self.priority_player_index].name} has priority"
            )
        if (
            not self.stack
            and not self.batch_abilities
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
            resolved = self._resolve_batch()
            if self.pending_damage is None:
                self.consecutive_passes = 0
                self.priority_player_index = (
                    self.active_player_index if self.timed_events else None
                )
            return resolved

        self._resolve_timed_event()
        if self.pending_damage is None:
            self.consecutive_passes = 0
            self.priority_player_index = (
                self.active_player_index if self.timed_events else None
            )
        return ()

    def _pass_damage_priority(self, player_id: str) -> None:
        """Pass in the current prevention, redirection, or regeneration window."""

        if self.priority_player_index is None:
            raise RuntimeError("the damage window has no priority player")
        player = self.player(player_id)
        if player is not self.players[self.priority_player_index]:
            raise RuntimeError(
                f"{self.players[self.priority_player_index].name} has priority"
            )
        self.consecutive_passes += 1
        if self.consecutive_passes < len(self.players):
            self.priority_player_index = (
                self.priority_player_index + 1
            ) % len(self.players)
            return
        self._advance_damage_resolution()

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
            isinstance(event.effect, UpkeepCostEffect)
            and event.affected_player_id == player_id
            and event.payment_decision is None
            and self._timed_event_source(event) is not None
            and self.player(player_id).mana_pool.can_pay(event.effect.mana_cost)
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
        if not isinstance(event.effect, UpkeepCostEffect):
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
            player.mana_pool.pay(event.effect.mana_cost)
        event.payment_decision = pay
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
        return bool(
            isinstance(event.effect, UpkeepCostEffect)
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
        if source.tapped and CardType.ARTIFACT in source.definition.card_types:
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

    def _resolve_batch(self) -> tuple[Card, ...]:
        """Apply one 1993 fast-effect batch, then stabilize exactly once."""

        cards = tuple(self.stack)
        spells = tuple(self.stack_spells[card.id] for card in cards)
        abilities = tuple(self.batch_abilities)
        self._begin_damage_incident(DamageIncidentKind.FAST_EFFECT_BATCH)

        # Target validity is fixed before any member of the simultaneous batch
        # changes zones or characteristics.
        legal: dict[UUID, bool] = {}
        for spell in spells:
            requirement = spell.card.definition.target_requirement
            legal[spell.card.id] = requirement is None or all(
                (
                    self._requirement_accepts_card(
                        requirement, target, spell.caster_id
                    )
                    if isinstance(target, Card)
                    else requirement.players and target in self.players
                )
                for target in spell.targets
            )
        legal_abilities = [
            all(
                (
                    self._requirement_accepts_card(
                        ability.ability.target_requirement,
                        target,
                        ability.controller_id,
                        check_tapped=False,
                    )
                    if isinstance(target, Card)
                    else ability.ability.target_requirement.players
                    and target in self.players
                )
                for target in ability.targets
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

        pending_destruction: list[Card] = []
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
                    for target in spell.targets:
                        if isinstance(target, Card):
                            self.temporary_creature_effects.setdefault(
                                target.id, []
                            ).append(
                                ContinuousEffect(
                                    power=effect.power,
                                    toughness=effect.toughness,
                                )
                            )
                elif isinstance(effect, DestroyTargetsEffect):
                    pending_destruction.extend(
                        target
                        for target in spell.targets
                        if isinstance(target, Card)
                    )
                elif isinstance(effect, DestroyAllEffect):
                    pending_destruction.extend(
                        permanent
                        for player in self.players
                        for permanent in tuple(player.battlefield)
                        if effect.matches(permanent)
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
            else:
                pending_destruction.extend(
                    target
                    for target in declared.targets
                    if isinstance(target, Card)
                )

        assert self.pending_damage is not None
        self.pending_damage.destroyed_card_ids.update(
            card.id
            for card in pending_destruction
            if card.zone is Zone.BATTLEFIELD
        )
        self._resolve_damage_incident()

        for spell in spells:
            card = spell.card
            self.stack_spells.pop(card.id, None)
            if card.zone is Zone.STACK:
                self._move_card(card, Zone.GRAVEYARD)
        self.batch_abilities.clear()
        self.check_state_based_actions()
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
                    if effect.matches(permanent)
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

    def _begin_damage_incident(self, kind: DamageIncidentKind) -> None:
        if self.pending_damage is not None:
            raise RuntimeError("a damage incident is already accumulating")
        self.pending_damage = DamageIncident(kind)

    def _deal_damage(
        self,
        recipient: Card | PlayerState,
        amount: int,
        source: str,
        *,
        source_card: Card | None = None,
        source_controller_id: str | None = None,
        combat: bool = False,
        trample: bool = False,
        first_strike: bool = False,
    ) -> None:
        """Describe damage and add it to the current simultaneous incident."""

        if amount <= 0:
            return
        resolve_immediately = self.pending_damage is None
        if resolve_immediately:
            self._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        assert self.pending_damage is not None
        self.pending_damage.packets.append(
            DamagePacket(
                amount=amount,
                recipient_kind=(
                    DamageRecipientKind.PLAYER
                    if isinstance(recipient, PlayerState)
                    else DamageRecipientKind.CREATURE
                ),
                recipient_id=recipient.id,
                recipient_name=recipient.name,
                source_name=source_card.name if source_card is not None else source,
                source_id=source_card.id if source_card is not None else None,
                source_controller_id=(
                    source_controller_id
                    if source_controller_id is not None
                    else source_card.controller_id
                    if source_card is not None
                    else None
                ),
                colors=(
                    source_card.definition.colors
                    if source_card is not None
                    else frozenset()
                ),
                combat=combat,
                trample=trample,
                first_strike=first_strike,
            )
        )
        if resolve_immediately:
            self._resolve_damage_incident()

    def _resolve_damage_incident(self) -> DamageIncident | None:
        """Open the first FAQ damage window, auto-skipping empty windows."""

        incident = self.pending_damage
        if incident is None:
            raise RuntimeError("there is no damage incident to resolve")
        if not incident.packets and not incident.destroyed_card_ids:
            self.pending_damage = None
            return None

        incident.step = DamageResolutionStep.PREVENTION
        if self._damage_window_requires_priority():
            self.priority_player_index = self.active_player_index
            self.consecutive_passes = 0
            return incident

        while (
            self.pending_damage is not None
            and not self._damage_window_requires_priority()
        ):
            self._advance_damage_resolution()
        return incident

    def _damage_window_requires_priority(self) -> bool:
        incident = self.pending_damage
        if incident is None:
            return False
        if self.pause_for_damage_windows:
            return True
        if incident.step is not DamageResolutionStep.REGENERATION:
            return False
        return any(
            CardType.CREATURE in card.definition.card_types
            and self.creature_toughness(card) > 0
            and (
                card.damage >= self.creature_toughness(card)
                or card.id in incident.destroyed_card_ids
            )
            and any(
                isinstance(ability, ActivatedRegenerationAbility)
                for ability in card.definition.activated_abilities
            )
            for player in self.players
            for card in player.battlefield
        )

    def _advance_damage_resolution(self) -> None:
        """Advance one completed damage window or finalize the incident."""

        incident = self.pending_damage
        if incident is None:
            raise RuntimeError("there is no damage incident to advance")
        if incident.step is DamageResolutionStep.PREVENTION:
            incident.step = DamageResolutionStep.REDIRECTION
            self.priority_player_index = self.active_player_index
            self.consecutive_passes = 0
            return
        if incident.step is DamageResolutionStep.REDIRECTION:
            self._apply_pending_damage()
            incident.step = DamageResolutionStep.REGENERATION
            self.priority_player_index = self.active_player_index
            self.consecutive_passes = 0
            return
        if incident.step is not DamageResolutionStep.REGENERATION:
            raise RuntimeError("the damage incident is not in an actionable window")

        incident.step = DamageResolutionStep.DEATH
        destroyed = [
            card
            for player in self.players
            for card in tuple(player.battlefield)
            if card.id in incident.destroyed_card_ids
            and card.id not in incident.regenerated_card_ids
        ]
        self.pending_damage = None
        self._destroy_permanents(destroyed)
        self.check_state_based_actions()
        incident.step = DamageResolutionStep.COMPLETE
        self.resolved_damage_incidents.append(incident)
        self.priority_player_index = None
        self.consecutive_passes = 0
        self._continue_after_damage_incident(incident)

    def _apply_pending_damage(self) -> None:
        """Apply unprevented packets after the redirection window."""

        incident = self.pending_damage
        assert incident is not None
        # Creature recipients are handled before players, as required by the
        # FAQ. Packet order remains intact within each recipient category.
        for packet in sorted(
            incident.packets,
            key=lambda packet: (
                packet.recipient_kind is DamageRecipientKind.PLAYER
            ),
        ):
            amount = packet.remaining
            if not amount:
                continue
            event_source = "combat" if packet.combat else packet.source_name
            if packet.recipient_kind is DamageRecipientKind.PLAYER:
                recipient = self.player(str(packet.recipient_id))
                recipient.life -= amount
                self.events.append(
                    DamageEvent(
                        amount=amount,
                        source=event_source,
                        player_id=recipient.id,
                    )
                )
                if recipient.life <= 0:
                    recipient.has_lost = True
                continue
            recipient = next(
                (
                    card
                    for player in self.players
                    for card in player.battlefield
                    if card.id == packet.recipient_id
                ),
                None,
            )
            if recipient is None:
                continue
            recipient.damage += amount
            self.events.append(
                DamageEvent(
                    amount=amount,
                    source=event_source,
                    card_id=recipient.id,
                    card_name=recipient.name,
                )
            )

    def _continue_after_damage_incident(self, incident: DamageIncident) -> None:
        """Resume a rule action that was split by interactive damage windows."""

        if self.combat is None or self.combat.step is not CombatStep.DAMAGE:
            return
        defender = self.player(self.combat.defending_player_id)
        if incident.kind is DamageIncidentKind.FIRST_STRIKE_COMBAT:
            opened = self._deal_combat_damage_wave(
                first_strike=False,
                allocations=self.combat.damage_allocations,
                defender=defender,
            )
            if opened:
                return
        elif incident.kind is not DamageIncidentKind.COMBAT:
            return
        self._finish_combat_damage()

    def legal_enchantment_targets(self, card: Card) -> list[Card]:
        """Compatibility wrapper for callers using the older Aura API."""

        self._validate_enchantment_cast(card)
        return self.legal_targets_for(card)

    def cast_enchantment(self, card: Card, target: Card | None = None) -> None:
        """Compatibility wrapper for directly casting an enchantment."""

        self._require_no_pending_action()
        self._validate_enchantment_cast(card)
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
        self._resolve_permanent_spell(card, targets)

    def creature_power(self, creature: Card) -> int:
        """Return current power after applying continuous bonuses."""

        base = self._variable_creature_base_stat(creature)
        if base is None:
            base = creature.definition.power or 0
        return base + self._creature_bonus(creature)[0]

    def creature_toughness(self, creature: Card) -> int:
        """Return current toughness after applying continuous bonuses."""

        base = self._variable_creature_base_stat(creature)
        if base is None:
            base = creature.definition.toughness or 0
        return base + self._creature_bonus(creature)[1]

    def _variable_creature_base_stat(self, creature: Card) -> int | None:
        """Return the shared */* value, or ``None`` for a numeric creature."""

        variable = creature.definition.variable_stats
        if variable is None:
            return None
        controller = self.player(creature.controller_id or creature.owner_id)
        if variable.kind is VariableStatKind.CONTROLLED_NON_WALL_CREATURES:
            return sum(
                CardType.CREATURE in permanent.definition.card_types
                and "Wall" not in permanent.definition.subtypes
                for permanent in controller.battlefield
            )
        if variable.kind is VariableStatKind.CONTROLLED_LAND_SUBTYPE:
            return sum(
                CardType.LAND in permanent.definition.card_types
                and variable.subtype in permanent.definition.subtypes
                for permanent in controller.battlefield
            )
        return sum(
            CardType.CREATURE in permanent.definition.card_types
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

    def _continuous_effects_for(
        self, creature: Card
    ) -> Iterable[ContinuousEffect]:
        yield from self.temporary_creature_effects.get(creature.id, ())
        attacking = self.combat is not None and creature in self.combat.attackers
        for player in self.players:
            for source in player.battlefield:
                for effect in source.definition.continuous_effects:
                    if (
                        effect.scope is EffectScope.ATTACHED_CARD
                        and source.enchanted_card_id != creature.id
                    ):
                        continue
                    if (
                        effect.color is not None
                        and effect.color not in creature.definition.colors
                    ):
                        continue
                    if (
                        effect.subtype is not None
                        and effect.subtype not in creature.definition.subtypes
                    ):
                        continue
                    if effect.exclude_source and source is creature:
                        continue
                    if (
                        effect.controller_only
                        and creature.controller_id != source.controller_id
                    ):
                        continue
                    if effect.attacking_only and not attacking:
                        continue
                    yield effect

    def _creature_bonus(self, creature: Card) -> tuple[int, int]:
        effects = tuple(self._continuous_effects_for(creature))
        return (
            sum(effect.power for effect in effects),
            sum(effect.toughness for effect in effects),
        )

    def begin_combat(self) -> CombatStep:
        """Begin the turn's single optional attack during the Main phase."""

        self._require_no_pending_action()
        if self.status is not GameStatus.IN_PROGRESS:
            raise RuntimeError("combat can only begin during a game")
        if self.current_phase is not TurnPhase.MAIN:
            raise RuntimeError("an attack can only begin during the Main phase")
        if self.combat is not None:
            raise RuntimeError("an attack is already in progress")
        if self.attacks_this_turn:
            raise RuntimeError("the active player has already attacked this turn")

        defender_index = (self.active_player_index + 1) % len(self.players)
        self.combat = CombatState(
            attacking_player_id=self.active_player.id,
            defending_player_id=self.players[defender_index].id,
        )
        return self.combat.step

    def declare_attackers(self, attackers: Iterable[Card]) -> CombatStep:
        self._require_no_pending_action()
        if self.combat is None or self.combat.step is not CombatStep.ATTACK_RESPONSE:
            raise RuntimeError("the game is not waiting for attackers")
        chosen = list(attackers)
        if len({card.id for card in chosen}) != len(chosen):
            raise ValueError("an attacking creature may only be declared once")
        for card in chosen:
            if card not in self.active_player.battlefield:
                raise ValueError(f"{card.name} is not controlled by the attacker")
            if CardType.CREATURE not in card.definition.card_types:
                raise ValueError(f"{card.name} is not a creature")
            if "Wall" in card.definition.subtypes:
                raise ValueError(f"{card.name} is a Wall and cannot attack")
            if card.tapped:
                raise ValueError(f"{card.name} is tapped")
            if card.entered_battlefield_turn == self.turn_number:
                raise ValueError(f"{card.name} did not begin the turn in play")

        # The pre-attack response window has closed. Mana burn happens before
        # the atomic declaration, during which no actions can be taken.
        self._empty_mana_pools()
        for card in chosen:
            card.tapped = True
        self.combat.attackers = chosen
        self.combat.blockers = {card.id: [] for card in chosen}
        self.combat.step = CombatStep.ATTACKER_RESPONSE
        self.attacks_this_turn += 1
        return self.combat.step

    def declare_blockers(self, assignments: dict[Card, Card]) -> CombatStep:
        """Declare each blocker and the attacker it blocks.

        Several blockers may be assigned to one attacker, while each blocker
        may appear only once in the mapping.
        """

        self._require_no_pending_action()
        if self.combat is None or self.combat.step is not CombatStep.ATTACKER_RESPONSE:
            raise RuntimeError("the game is not waiting for blockers")
        defender = self.player(self.combat.defending_player_id)
        attackers = {card.id: card for card in self.combat.attackers}
        for blocker, attacker in assignments.items():
            if blocker not in defender.battlefield:
                raise ValueError(f"{blocker.name} is not controlled by the defender")
            if CardType.CREATURE not in blocker.definition.card_types:
                raise ValueError(f"{blocker.name} is not a creature")
            if blocker.tapped:
                raise ValueError(f"{blocker.name} is tapped and cannot block")
            if attacker.id not in attackers:
                raise ValueError(f"{attacker.name} is not attacking")
            landwalk_subtypes = {
                ability.landwalk_subtype
                for ability in self.creature_abilities(attacker)
                if ability.landwalk_subtype is not None
            }
            defending_land_subtypes = {
                subtype
                for permanent in defender.battlefield
                if CardType.LAND in permanent.definition.card_types
                for subtype in permanent.definition.subtypes
            }
            active_landwalk = landwalk_subtypes & defending_land_subtypes
            if active_landwalk:
                land_type = sorted(active_landwalk)[0]
                raise ValueError(
                    f"{attacker.name} has {land_type.lower()}walk and cannot "
                    f"be blocked while the defender controls a {land_type}"
                )
            if (
                KeywordAbility.FLYING in self.creature_abilities(attacker)
                and KeywordAbility.FLYING not in self.creature_abilities(blocker)
            ):
                raise ValueError(
                    f"{blocker.name} cannot block a creature with Flying"
                )

        for blocker, attacker in assignments.items():
            self.combat.blockers[attacker.id].append(blocker)
        self.combat.step = CombatStep.BLOCKER_RESPONSE
        return self.combat.step

    def advance_combat(self) -> CombatStep:
        """Close the post-blocker response window and begin damage."""

        self._require_no_pending_action()
        if self.combat is None:
            raise RuntimeError("no attack is in progress")
        if self.combat.step is not CombatStep.BLOCKER_RESPONSE:
            raise RuntimeError("combat cannot be advanced from the current step")
        self.combat.step = CombatStep.DAMAGE
        return self.combat.step

    def deal_combat_damage(
        self, assignments: dict[Card, dict[Card, int]] | None = None
    ) -> None:
        """Deal first-strike and regular combat damage, then finish the attack.

        Damage assignments are only required when an attacker is blocked by
        more than one creature. The attacker's full power must be distributed
        among creatures blocking it, as required by the Beta rules.
        """

        self._require_no_pending_action()
        if self.combat is None or self.combat.step is not CombatStep.DAMAGE:
            raise RuntimeError("combat is not in the Damage Dealing step")
        assignments = assignments or {}
        defender = self.player(self.combat.defending_player_id)
        allocations = self._validate_damage_assignments(assignments)
        self.combat.damage_allocations = allocations

        opened = self._deal_combat_damage_wave(
            first_strike=True, allocations=allocations, defender=defender
        )
        if opened:
            return
        if self.combat is None:
            return
        opened = self._deal_combat_damage_wave(
            first_strike=False, allocations=allocations, defender=defender
        )
        if opened:
            return
        if self.combat is None:
            return
        self._finish_combat_damage()

    def _finish_combat_damage(self) -> None:
        self._empty_mana_pools()
        self.combat = None

    def _validate_damage_assignments(
        self, assignments: dict[Card, dict[Card, int]]
    ) -> dict[Card, dict[Card, int]]:
        """Validate all attacker choices before any combat damage is applied."""

        assert self.combat is not None
        allocations: dict[Card, dict[Card, int]] = {}
        for attacker in self.combat.attackers:
            if attacker.zone is not Zone.BATTLEFIELD:
                continue
            power = max(0, self.creature_power(attacker))
            blockers = self.combat.blockers[attacker.id]
            living_blockers = [
                blocker for blocker in blockers if blocker.zone is Zone.BATTLEFIELD
            ]
            if not living_blockers:
                allocations[attacker] = {}
                continue
            allocation = assignments.get(attacker)
            if len(living_blockers) == 1 and allocation is None:
                allocation = {living_blockers[0]: power}
            if allocation is None:
                raise ValueError(
                    f"damage must be assigned among creatures blocking {attacker.name}"
                )
            if set(allocation) - set(living_blockers):
                raise ValueError("combat damage was assigned to a creature not blocking")
            if any(amount < 0 for amount in allocation.values()):
                raise ValueError("combat damage assignments cannot be negative")
            if sum(allocation.values()) != power:
                raise ValueError(f"{attacker.name} must assign all {power} damage")
            allocations[attacker] = allocation
        return allocations

    def _deal_combat_damage_wave(
        self,
        *,
        first_strike: bool,
        allocations: dict[Card, dict[Card, int]],
        defender: PlayerState,
    ) -> bool:
        """Deal one simultaneous damage wave and remove lethal creatures."""

        assert self.combat is not None
        self._begin_damage_incident(
            DamageIncidentKind.FIRST_STRIKE_COMBAT
            if first_strike
            else DamageIncidentKind.COMBAT
        )

        for attacker in self.combat.attackers:
            if attacker.zone is not Zone.BATTLEFIELD:
                continue
            attacker_regenerated = (
                attacker.id in self.combat.regenerated_card_ids
            )
            blockers = self.combat.blockers[attacker.id]
            living_blockers = [
                blocker for blocker in blockers if blocker.zone is Zone.BATTLEFIELD
            ]
            attacker_has_first_strike = (
                KeywordAbility.FIRST_STRIKE in self.creature_abilities(attacker)
            )
            if not attacker_regenerated and attacker_has_first_strike is first_strike:
                if not blockers:
                    self._deal_damage(
                        defender,
                        max(0, self.creature_power(attacker)),
                        attacker.name,
                        source_card=attacker,
                        combat=True,
                        first_strike=first_strike,
                    )
                elif (
                    KeywordAbility.TRAMPLE in self.creature_abilities(attacker)
                    and not living_blockers
                ):
                    # Once blocked, a normal creature remains blocked even if
                    # every blocker leaves combat. Beta Trample redirects all
                    # of its damage past the now-nonexistent blockers.
                    self._deal_damage(
                        defender,
                        max(0, self.creature_power(attacker)),
                        attacker.name,
                        source_card=attacker,
                        combat=True,
                        trample=True,
                        first_strike=first_strike,
                    )
                else:
                    for blocker, amount in allocations.get(attacker, {}).items():
                        if blocker.zone is Zone.BATTLEFIELD:
                            if KeywordAbility.TRAMPLE in self.creature_abilities(attacker):
                                toughness_left = max(
                                    0,
                                    self.creature_toughness(blocker)
                                    - blocker.damage,
                                )
                                blocker_damage = min(amount, toughness_left)
                                self._deal_damage(
                                    defender,
                                    amount - blocker_damage,
                                    attacker.name,
                                    source_card=attacker,
                                    combat=True,
                                    trample=True,
                                    first_strike=first_strike,
                                )
                            else:
                                blocker_damage = amount
                            self._deal_damage(
                                blocker,
                                blocker_damage,
                                attacker.name,
                                source_card=attacker,
                                combat=True,
                                trample=(
                                    KeywordAbility.TRAMPLE
                                    in self.creature_abilities(attacker)
                                ),
                                first_strike=first_strike,
                            )
                        elif KeywordAbility.TRAMPLE in self.creature_abilities(attacker):
                            self._deal_damage(
                                defender,
                                amount,
                                attacker.name,
                                source_card=attacker,
                                combat=True,
                                trample=True,
                                first_strike=first_strike,
                            )
            for blocker in living_blockers:
                blocker_has_first_strike = (
                    KeywordAbility.FIRST_STRIKE in self.creature_abilities(blocker)
                )
                if (
                    not attacker_regenerated
                    and blocker.id not in self.combat.regenerated_card_ids
                    and not blocker.tapped
                    and blocker_has_first_strike is first_strike
                ):
                    self._deal_damage(
                        attacker,
                        max(0, self.creature_power(blocker)),
                        blocker.name,
                        source_card=blocker,
                        combat=True,
                        first_strike=first_strike,
                    )

        incident = self._resolve_damage_incident()
        if incident is None:
            return False
        # Auto-resolved incidents are already complete; paused incidents will
        # resume combat from _continue_after_damage_incident.
        return incident.step is not DamageResolutionStep.COMPLETE

    def check_state_based_actions(self) -> None:
        """Repeatedly remove creatures with nonpositive or lethally damaged toughness."""

        while True:
            doomed = [
                card
                for player in self.players
                for card in player.battlefield
                if CardType.CREATURE in card.definition.card_types
                and (
                    self.creature_toughness(card) <= 0
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
            self.active_player.untap_all()
        elif phase is TurnPhase.UPKEEP:
            self._queue_upkeep_events()
        elif phase is TurnPhase.DRAW:
            self.active_player.draw()

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
                if (
                    source.tapped
                    and CardType.ARTIFACT in source.definition.card_types
                    and isinstance(effect, UpkeepDamageEffect)
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
        if bool(self.stack or self.timed_events) != (
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
