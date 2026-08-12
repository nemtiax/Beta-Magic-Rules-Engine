"""Qt Quick hotseat UI for the Beta Magic rules engine.

Run with ``python -m beta_magic.ui``.
"""

from __future__ import annotations

import argparse
from functools import partial
import signal
import sys
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

from PySide6.QtCore import QLoggingCategory, QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from .cards import Card
from .abilities import ActivatedGlobalDamageAbility, ActivatedRedirectDamageAbility
from .decks import (
    AEGIS_WARDS_DECK,
    ARCANE_DEPTHS_DECK,
    COPPER_CONTROL_DECK,
    COPPER_PRESSURE_DECK,
    ELEMENTAL_SURGE_DECK,
    MOONLIT_HORDE_DECK,
    RADIANT_CHARGE_DECK,
    SPECTRUM_ASSAULT_DECK,
    IVORY_LAYERS_DECK,
    SHADOW_COATS_DECK,
    STONEFIRE_DECK,
    VERDANT_TIDES_DECK,
    make_demo_game,
    make_enchantment_test_game,
    make_protection_test_game,
    make_test_game,
    make_timed_event_test_game,
    make_x_test_game,
    make_aura_test_game,
    make_banding_test_game,
)
from .events import DamageEvent, GameEvent, ManaBurnEvent, SpellCastEvent
from .effects import (
    AttachedLandTypeEffect,
    ReverseDamageEffect,
    UpkeepCreatureSacrificeEffect,
)
from .game import GameState, PlayerState
from .types import CardType, Color, CombatStep, TurnPhase, Zone
from .ui_presentation import UiPresentationBuilder, mana_text
from .ui_combat import CombatUiController
from .ui_choices import TransientChoiceState
from .ui_messages import UiMessageStore


class GameViewModel(QObject):
    """Qt-facing adapter; the rules engine itself remains UI-independent."""

    stateChanged = Signal()

    def __init__(
        self,
        game: GameState | None = None,
        *,
        game_factory: Callable[[], GameState] | None = None,
    ) -> None:
        super().__init__()
        self._combat_ui = CombatUiController()
        self._choices = TransientChoiceState()
        self._presentation = UiPresentationBuilder(self)
        self._game_factory = game_factory or make_demo_game
        self.game = game or self._game_factory()
        self.game.pause_for_damage_windows = True
        self.perspective_index = 0
        self._messages = UiMessageStore(player.id for player in self.game.players)
        self.selected_card_ids: set[UUID] = set()
        self._auto_pass_turns: dict[str, int] = {}
        self._message = "Double-click a card to play, cast, or tap it."

    @property
    def _message(self) -> str:
        player_id = self.game.players[self.perspective_index].id
        return self._messages.message_for(player_id)

    @_message.setter
    def _message(self, message: str) -> None:
        self._messages.broadcast(message)

    def _prompt(
        self,
        player_id: str,
        message: str,
        *,
        observer_message: str | None = None,
    ) -> None:
        self._messages.prompt(
            player_id, message, observer_message=observer_message
        )

    def _prompt_current(self, message: str, observer_message: str) -> None:
        self._prompt(
            self.game.players[self.perspective_index].id,
            message,
            observer_message=observer_message,
        )

    def _tell_current(self, message: str) -> None:
        """Show a local validation or interaction message only to this player."""

        player_id = self.game.players[self.perspective_index].id
        self._messages.tell(player_id, message)

    @Property("QVariantMap", notify=stateChanged)
    def state(self) -> dict[str, Any]:
        return self._presentation.build()

    def _player_data(
        self, player: PlayerState, *, reveal_hand: bool
    ) -> dict[str, Any]:
        """Compatibility delegate for UI-focused tests and extensions."""

        return self._presentation._player_data(player, reveal_hand=reveal_hand)

    def _card_data(self, card: Card) -> dict[str, Any]:
        """Compatibility delegate for UI-focused tests and extensions."""

        return self._presentation._card_data(card)

    def _card_colors(self, card: Card) -> tuple[str, str]:
        """Compatibility delegate for UI-focused tests and extensions."""

        return self._presentation._card_colors(card)

    def _perspective_card(self, card_id: str) -> Card | None:
        try:
            wanted = UUID(card_id)
        except ValueError:
            return None
        player = self.game.players[self.perspective_index]
        return next(
            (
                card
                for card in (*player.hand, *player.battlefield)
                if card.id == wanted
            ),
            None,
        )

    def _battlefield_card(self, card_id: str) -> Card | None:
        try:
            wanted = UUID(card_id)
        except ValueError:
            return None
        return next(
            (
                card
                for player in self.game.players
                for card in player.battlefield
                if card.id == wanted
            ),
            None,
        )

    def _selected_cards(self) -> list[Card]:
        player = self.game.players[self.perspective_index]
        return [
            card
            for card in (*player.hand, *player.battlefield)
            if card.id in self.selected_card_ids
        ]

    def _run(self, action: Callable[[], Any], success: str) -> bool:
        event_checkpoint = len(self.game.events)
        try:
            action()
            self._apply_auto_passes()
        except (ValueError, RuntimeError) as error:
            self._tell_current(str(error))
            self.stateChanged.emit()
            return False
        event_messages = self._event_messages(self.game.events[event_checkpoint:])
        self._message = "; ".join(event_messages) if event_messages else success


        self.selected_card_ids.clear()
        self.stateChanged.emit()
        return True

    def _apply_auto_passes(self) -> None:
        """Pass priority for opted-in players until a choice or manual pass is due."""

        while self.game.priority_player_index is not None:
            player = self.game.players[self.game.priority_player_index]
            if self._auto_pass_turns.get(player.id) != self.game.turn_number:
                return
            if (
                self.game.pending_cast is not None
                or self.game.pending_activation is not None
                or self.game.pending_prevention is not None
                or self.game.pending_redirection is not None
                or self.game.pending_turn_choice is not None
                or self.game.pending_discard_choices
                or self.game.pending_balance is not None
                or self.game.pending_untap_choice is not None
                or self.game.pending_upkeep_land_loss is not None
            ):
                return
            if (
                self.game.timed_events
                and self.game.upkeep_payment_required
                and self.game.timed_events[0].payment_decision is None
                and self.game.timed_events[0].affected_player_id == player.id
            ):
                return
            self.game.pass_priority(player.id)

    def _event_messages(self, events: list[GameEvent]) -> list[str]:
        messages: list[str] = []
        damage_by_player: dict[tuple[str, str], int] = {}
        burn_by_player: dict[str, int] = {}
        for event in events:
            if isinstance(event, SpellCastEvent):
                spell = self._card_by_id(event.card_id)
                target_verb = (
                    " enchanting "
                    if spell is not None
                    and CardType.ENCHANTMENT in spell.definition.card_types
                    else " targeting "
                )
                target_text = (
                    target_verb + ", ".join(event.target_names)
                    if event.target_names
                    else ""
                )
                messages.append(f"Cast {event.card_name}{target_text}")
            elif isinstance(event, DamageEvent) and event.player_id is not None:
                key = (event.player_id, event.source)
                damage_by_player[key] = (
                    damage_by_player.get(key, 0) + event.amount
                )
            elif isinstance(event, ManaBurnEvent):
                burn_by_player[event.player_id] = (
                    burn_by_player.get(event.player_id, 0) + event.amount
                )
        for player in self.game.players:
            for (player_id, source), damage in damage_by_player.items():
                if player_id != player.id:
                    continue
                if source == "combat":
                    messages.append(f"{player.name} took {damage} combat damage")
                else:
                    messages.append(
                        f"{player.name} took {damage} damage from {source}"
                    )
            mana_burn = burn_by_player.get(player.id, 0)
            if mana_burn:
                messages.append(f"{player.name} took {mana_burn} mana burn")
        return messages

    def _card_by_id(self, card_id: UUID) -> Card | None:
        cards = (
            card
            for player in self.game.players
            for card in (
                *player.library,
                *player.hand,
                *player.battlefield,
                *player.graveyard,
                *player.exile,
                *player.ante,
            )
        )
        return next(
            (card for card in (*cards, *self.game.stack) if card.id == card_id),
            None,
        )

    @Slot(str)
    def toggleCard(self, card_id: str) -> None:
        if (
            self.game.pending_cast is not None
            or self.game.pending_activation is not None
        ):
            target = self._card_by_id(UUID(card_id))
            if target is None:
                self._tell_current("Choose a legal card as the target.")
                self.stateChanged.emit()
                return
            if self.game.pending_activation is not None:
                source = self.game.pending_activation.source
                if self._run(
                    lambda: self.game.complete_pending_activation((target,)),
                    f"Activated {source.name} targeting {target.name}.",
                ):
                    self.stateChanged.emit()
                return
            spell = self.game.pending_cast.spell
            verb = (
                "enchanting"
                if CardType.ENCHANTMENT in spell.definition.card_types
                and target.zone is Zone.BATTLEFIELD
                else "targeting"
            )
            if self._run(
                lambda: self.game.complete_pending_cast((target,)),
                f"Cast {spell.name} {verb} {target.name}.",
            ):
                self.stateChanged.emit()
            return

        card = self._perspective_card(card_id)
        if self.game.pending_upkeep_land_loss is not None:
            candidate = self._card_by_id(UUID(card_id))
            if (
                candidate is not None
                and candidate.id
                in self.game.pending_upkeep_land_loss.candidate_ids
            ):
                card = candidate
        combat = self.game.combat
        perspective_id = self.game.players[self.perspective_index].id
        drafting_blocks = self._combat_ui.is_drafting(self.game, perspective_id)
        if drafting_blocks:
            candidate = self._card_by_id(UUID(card_id))
            if self._combat_ui.selectable_card(self.game, perspective_id, candidate):
                card = candidate
            elif candidate is not None:
                self._tell_current(
                    "Select an attacker or an untapped defending creature."
                )
                self.stateChanged.emit()
                return
        if card is None:
            return
        if self.game.pending_upkeep_land_loss is not None:
            choice = self.game.pending_upkeep_land_loss
            if card.id not in choice.candidate_ids:
                self._tell_current(
                    f"Choose one of the eligible lands for {choice.source_name}."
                )
                self.stateChanged.emit()
                return
        if self.game.pending_balance is not None:
            choice = self.game.pending_balance.current_choice
            assert choice is not None
            if card.id not in choice.candidate_ids:
                self._tell_current(
                    f"Choose one of {self.game.player(choice.player_id).name}'s "
                    f"snapshotted {choice.category} cards."
                )
                self.stateChanged.emit()
                return
        if self.game.pending_untap_choice is not None:
            choice = self.game.pending_untap_choice
            if card.id not in self.game._legal_current_untap_ids(choice):
                self._tell_current(
                    f"Choose one of {self.game.player(choice.player_id).name}'s "
                    f"eligible {choice.card_type.value}s."
                )
                self.stateChanged.emit()
                return
        if self.game.timed_events and isinstance(
            self.game.timed_events[0].effect, UpkeepCreatureSacrificeEffect
        ):
            event = self.game.timed_events[0]
            if self.game.upkeep_payment_required and card not in self.game.legal_upkeep_sacrifices(
                event.affected_player_id
            ):
                self._tell_current(
                    "Choose an eligible creature for the upkeep sacrifice."
                )
                self.stateChanged.emit()
                return
        if card.id in self.selected_card_ids:
            self.selected_card_ids.remove(card.id)
        else:
            self.selected_card_ids.add(card.id)
        player = self.game.players[self.perspective_index]
        self._prompt(
            player.id,
            f"Selected {len(self.selected_card_ids)} card(s).",
            observer_message=f"{player.name} is selecting cards.",
        )
        self.stateChanged.emit()

    @Slot(str)
    def activateCard(self, card_id: str) -> None:
        if (
            self.game.pending_cast is not None
            or self.game.pending_activation is not None
        ):
            self._tell_current("Choose the pending target first.")
            self.stateChanged.emit()
            return
        player = self.game.players[self.perspective_index]
        card = self._perspective_card(card_id)
        if card is None:
            return
        if card in player.hand and CardType.LAND in card.definition.card_types:
            self._run(lambda: self.game.play_land(card), f"Played {card.name}.")
        elif card in player.hand and (
            CardType.CREATURE in card.definition.card_types
            or CardType.ENCHANTMENT in card.definition.card_types
            or CardType.INSTANT in card.definition.card_types
            or CardType.INTERRUPT in card.definition.card_types
            or CardType.SORCERY in card.definition.card_types
            or CardType.ARTIFACT in card.definition.card_types
        ):
            if (
                card.definition.prevention_amount
                and self.game.pending_damage is not None
                and self.game.pending_damage.step.value == "prevention"
            ):
                self._run(
                    lambda: self.game.begin_prevention_spell(card),
                    f"Choose damage for {card.name} to prevent.",
                )
                self.stateChanged.emit()
                return
            if card.definition.mana_cost.x_symbols:
                try:
                    maximum = self.game.maximum_affordable_x(card)
                except (ValueError, RuntimeError) as error:
                    self._tell_current(str(error))
                else:
                    self._choices.begin_x(card, maximum)
                    self._prompt(
                        player.id,
                        f"Choose X for {card.name}.",
                        observer_message=f"{player.name} is choosing X for {card.name}.",
                    )
                self.stateChanged.emit()
                return
            if any(
                isinstance(effect, ReverseDamageEffect)
                for effect in card.definition.spell_effects
            ):
                choices = self.game.damage_source_choices(player.id)
                if not choices:
                    self._tell_current(
                        "No damage source can be reversed this turn."
                    )
                else:
                    self._choices.damage_source_card_id = card.id
                    self._prompt(
                        player.id,
                        f"Choose a damage source for {card.name}.",
                        observer_message=(
                            f"{player.name} is choosing a damage source for {card.name}."
                        ),
                    )
                self.stateChanged.emit()
                return
            if any(
                isinstance(effect, AttachedLandTypeEffect)
                and effect.chosen_basic_subtype
                for effect in card.definition.land_type_effects
            ):
                self._choices.land_type_card_id = card.id
                self._prompt(
                    player.id,
                    f"Choose a basic land type for {card.name}.",
                    observer_message=(
                        f"{player.name} is choosing a land type for {card.name}."
                    ),
                )
                self.stateChanged.emit()
                return
            if card.definition.casting_modes:
                self._choices.mode_card_id = card.id
                self._prompt(
                    player.id,
                    f"Choose how to cast {card.name}.",
                    observer_message=f"{player.name} is choosing how to cast {card.name}.",
                )
                self.stateChanged.emit()
                return
            try:
                pending = self.game.begin_cast(card)
            except (ValueError, RuntimeError) as error:
                self._tell_current(str(error))
            else:
                self._apply_auto_passes()
                self.selected_card_ids.clear()
                if pending is not None:
                    self._prompt(
                        player.id,
                        f"Choose a target in play for {card.name}.",
                        observer_message=(
                            f"{player.name} is choosing a target for {card.name}."
                        ),
                    )
                else:
                    self._message = f"Cast {card.name}."
            self.stateChanged.emit()
        elif card in player.battlefield and CardType.LAND in card.definition.card_types:
            abilities = self.game.activated_abilities(card)
            if len(abilities) == 1:
                self.activateAbility(card_id, 0)
            elif abilities:
                self._tell_current(f"Choose an ability for {card.name}.")
                self.stateChanged.emit()
            else:
                self._tell_current(f"{card.name} has no activated abilities.")
                self.stateChanged.emit()
        else:
            self._tell_current(f"{card.name} has no double-click action.")
            self.stateChanged.emit()

    @Slot(int)
    def adjustX(self, delta: int) -> None:
        if self._choices.x_card_id is None:
            return
        self._choices.adjust_x(delta)
        self.stateChanged.emit()

    @Slot()
    def confirmXCast(self) -> None:
        if self._choices.x_card_id is None:
            return
        card = self._card_by_id(self._choices.x_card_id)
        if card is None:
            self.cancelXCast()
            return
        x_value = self._choices.x_value
        ability_index = self._choices.x_ability_index
        try:
            if ability_index is None:
                pending = self.game.begin_cast(card, x_value=x_value)
            else:
                player = self.game.players[self.perspective_index]
                pending = self.game.activate_ability(
                    player.id,
                    card,
                    ability_index,
                    amount=x_value,
                )
        except (ValueError, RuntimeError) as error:
            self._tell_current(str(error))
        else:
            self._apply_auto_passes()
            self._choices.clear_x()
            if pending is not None:
                player = self.game.players[self.perspective_index]
                self._prompt_current(
                    f"Choose a target for {card.name} (X={x_value}).",
                    f"{player.name} is choosing a target for {card.name}.",
                )
            elif ability_index is None:
                self._message = f"Cast {card.name} with X={x_value}."
            else:
                self._message = (
                    f"Activated {card.name} for {x_value} damage."
                )
        self.stateChanged.emit()

    @Slot()
    def cancelXCast(self) -> None:
        was_ability = self._choices.x_ability_index is not None
        self._choices.clear_x()
        self._message = (
            "Cancelled activation." if was_ability else "Cancelled casting."
        )
        self.stateChanged.emit()

    @Slot(str)
    def chooseLandType(self, subtype: str) -> None:
        if self._choices.land_type_card_id is None:
            return
        card = self._card_by_id(self._choices.land_type_card_id)
        if card is None:
            self.cancelLandTypeChoice()
            return
        try:
            pending = self.game.begin_cast(card, land_subtype=subtype)
        except (ValueError, RuntimeError) as error:
            self._tell_current(str(error))
        else:
            self._apply_auto_passes()
            self._choices.land_type_card_id = None
            if pending is not None:
                player = self.game.players[self.perspective_index]
                self._prompt_current(
                    f"Choose a target in play for {card.name} ({subtype}).",
                    f"{player.name} is choosing a target for {card.name}.",
                )
            else:
                self._message = f"Cast {card.name}, choosing {subtype}."
        self.stateChanged.emit()

    @Slot()
    def cancelLandTypeChoice(self) -> None:
        self._choices.land_type_card_id = None
        self._message = "Land-type choice cancelled."
        self.stateChanged.emit()

    @Slot(str)
    def chooseCastingMode(self, mode: str) -> None:
        if self._choices.mode_card_id is None:
            return
        card = self._card_by_id(self._choices.mode_card_id)
        if card is None:
            self.cancelCastingMode()
            return
        try:
            pending = self.game.begin_cast(card, mode=mode)
        except (ValueError, RuntimeError) as error:
            self._tell_current(str(error))
        else:
            self._apply_auto_passes()
            self._choices.mode_card_id = None
            if pending is not None:
                player = self.game.players[self.perspective_index]
                self._prompt_current(
                    f"Choose a target for {card.name} ({mode}).",
                    f"{player.name} is choosing a target for {card.name}.",
                )
            else:
                self._message = f"Cast {card.name} ({mode})."
        self.stateChanged.emit()

    @Slot()
    def cancelCastingMode(self) -> None:
        self._choices.mode_card_id = None
        self._message = "Casting-mode choice cancelled."
        self.stateChanged.emit()

    @Slot(str)
    def chooseDamageSource(self, source_key: str) -> None:
        if self._choices.damage_source_card_id is None:
            return
        card = self._card_by_id(self._choices.damage_source_card_id)
        if card is None:
            self.cancelDamageSourceChoice()
            return
        try:
            self.game.begin_cast(card, damage_source_key=source_key)
        except (ValueError, RuntimeError) as error:
            self._tell_current(str(error))
        else:
            self._apply_auto_passes()
            self._choices.damage_source_card_id = None
            self._message = f"Cast {card.name}."
        self.stateChanged.emit()

    @Slot()
    def cancelDamageSourceChoice(self) -> None:
        self._choices.damage_source_card_id = None
        self._message = "Damage-source choice cancelled."
        self.stateChanged.emit()

    @Slot(str, int)
    def activateAbility(self, card_id: str, ability_index: int) -> None:
        if (
            self.game.pending_cast is not None
            or self.game.pending_activation is not None
        ):
            self._tell_current("Choose the pending target first.")
            self.stateChanged.emit()
            return
        player = self.game.players[self.perspective_index]
        card = self._perspective_card(card_id) or self._battlefield_card(card_id)
        if card is None:
            return
        try:
            ability = self.game.activated_abilities(card)[ability_index]
        except IndexError:
            self._tell_current(f"{card.name} has no such activated ability.")
            self.stateChanged.emit()
            return
        if (
            card not in player.battlefield
            and not (
                isinstance(ability, ActivatedRedirectDamageAbility)
                and ability.owner_activates
                and card.owner_id == player.id
            )
        ):
            return
        if isinstance(ability, ActivatedGlobalDamageAbility):
            try:
                maximum = self.game.maximum_affordable_ability_amount(
                    player.id, card, ability_index
                )
            except (ValueError, RuntimeError) as error:
                self._tell_current(str(error))
            else:
                self._choices.begin_x_ability(card, ability_index, maximum)
                self._prompt(
                    player.id,
                    f"Choose damage for {card.name}.",
                    observer_message=(
                        f"{player.name} is choosing damage for {card.name}."
                    ),
                )
            self.stateChanged.emit()
            return
        pending: list[object] = []
        if self._run(
            lambda: pending.append(
                self.game.activate_ability(player.id, card, ability_index)
            ),
            f"{card.name}: {ability.label}.",
        ) and pending[0] is not None:
            self._prompt(
                player.id,
                f"Choose a target for {card.name}'s ability.",
                observer_message=(
                    f"{player.name} is choosing a target for {card.name}'s ability."
                ),
            )
            self.stateChanged.emit()
        elif self.game.pending_prevention is not None:
            prevention_name = (
                "life loss"
                if self.game.pending_prevention.prevents_life_loss
                else "damage"
            )
            self._prompt(
                player.id,
                f"Choose {prevention_name} for {card.name} to prevent.",
                observer_message=(
                    f"{player.name} is assigning {card.name}'s prevention."
                ),
            )
            self.stateChanged.emit()
        elif self.game.pending_redirection is not None:
            self._prompt(
                player.id,
                f"Choose creature damage for {card.name} to redirect.",
                observer_message=(
                    f"{player.name} is assigning {card.name}'s redirection."
                ),
            )
            self.stateChanged.emit()

    @Slot(str)
    def chooseDamagePacket(self, packet_id: str) -> None:
        player = self.game.players[self.perspective_index]
        prevents_life_loss = (
            self.game.pending_prevention is not None
            and self.game.pending_prevention.prevents_life_loss
        )
        prevention_name = "life loss" if prevents_life_loss else "damage"
        prevented: list[int] = []
        if self._run(
            lambda: prevented.append(
                self.game.prevent_damage(player.id, UUID(packet_id))
            ),
            f"Prevented {prevention_name}.",
        ):
            self._message = f"Prevented {prevented[0]} {prevention_name}."
            if self.game.pending_prevention is not None:
                remaining = self.game.pending_prevention.remaining
                remaining_text = "all" if remaining is None else str(remaining)
                self._prompt(
                    player.id,
                    f"Prevented {prevented[0]} {prevention_name}; {remaining_text} prevention remains.",
                    observer_message=(
                        f"{player.name} prevented {prevented[0]} damage and is "
                        "continuing prevention assignment."
                    ),
                )
            self.stateChanged.emit()

    @Slot()
    def finishPrevention(self) -> None:
        player = self.game.players[self.perspective_index]
        self._run(
            lambda: self.game.finish_prevention(player.id),
            "Finished assigning damage prevention.",
        )

    @Slot()
    def cancelPrevention(self) -> None:
        player = self.game.players[self.perspective_index]
        self._run(
            lambda: self.game.cancel_prevention(player.id),
            "Cancelled damage prevention.",
        )

    @Slot(str)
    def chooseRedirectionPacket(self, packet_id: str) -> None:
        player = self.game.players[self.perspective_index]
        pending = self.game.pending_redirection
        if pending is None:
            return
        ability = self.game.activated_abilities(pending.source)[
            pending.ability_index
        ]
        assert isinstance(ability, ActivatedRedirectDamageAbility)
        if ability.any_amount:
            packet = next(
                (
                    candidate
                    for candidate in self.game.legal_redirection_packets()
                    if str(candidate.id) == packet_id
                ),
                None,
            )
            if packet is None:
                return
            self._choices.begin_redirection_amount(packet.id, packet.remaining)
            self.stateChanged.emit()
            return
        redirected: list[int] = []
        if self._run(
            lambda: redirected.append(
                self.game.redirect_damage(player.id, UUID(packet_id))
            ),
            "Redirected damage.",
        ):
            self._message = f"Redirected {redirected[0]} damage to {player.name}."
            self.stateChanged.emit()

    @Slot(int)
    def adjustRedirectionAmount(self, delta: int) -> None:
        if self._choices.redirection_packet_id is None:
            return
        self._choices.adjust_redirection(delta)
        self.stateChanged.emit()

    @Slot()
    def confirmRedirectionAmount(self) -> None:
        if self._choices.redirection_packet_id is None:
            return
        player = self.game.players[self.perspective_index]
        amount = self._choices.redirection_amount
        packet_id = self._choices.redirection_packet_id
        if self._run(
            lambda: self.game.redirect_damage(player.id, packet_id, amount),
            f"Redirected {amount} damage.",
        ):
            self._choices.clear_redirection_amount()
            self.stateChanged.emit()

    @Slot()
    def cancelRedirectionAmount(self) -> None:
        self._choices.clear_redirection_amount()
        self.stateChanged.emit()

    @Slot()
    def cancelRedirection(self) -> None:
        player = self.game.players[self.perspective_index]
        self._run(
            lambda: self.game.cancel_redirection(player.id),
            "Cancelled damage redirection.",
        )
        self._choices.clear_redirection_amount()

    @Slot()
    def advance(self) -> None:
        active_player = self.game.active_player
        opponent = next(
            player for player in self.game.players if player.id != active_player.id
        )
        immediate = bool(
            self.game.combat is not None
            or self.game.current_phase is TurnPhase.UNTAP
        )
        phase_name = (
            self.game.current_phase.value.title()
            if self.game.current_phase is not None
            else "phase"
        )

        def action() -> None:
            if self.game.combat is None:
                self.game.propose_phase_advance()
            elif self.game.combat.step is CombatStep.BLOCKER_RESPONSE:
                self.game.advance_combat()
            elif self.game.combat.step is CombatStep.DAMAGE:
                self.game.deal_combat_damage(self._default_damage_assignments())
            else:
                raise RuntimeError("complete the current combat declaration first")

        if self._run(
            action,
            (
                "Advanced the game."
                if immediate
                else f"Proposed ending {phase_name}."
            ),
        ) and not immediate and self.game.pending_phase_advance is not None:
            self._prompt(
                active_player.id,
                f"Proposed ending {phase_name}; waiting for {opponent.name} to pass.",
                observer_message=(
                    f"{active_player.name} proposed ending {phase_name}. "
                    "Last chance to play fast effects, or pass priority."
                ),
            )
            self.stateChanged.emit()

    @Slot(str)
    def chooseTimeVaultTurn(self, vault_id: str) -> None:
        choice = self.game.pending_turn_choice
        if choice is None:
            return
        vault = self._card_by_id(UUID(vault_id)) if vault_id else None
        action = "Skipped the turn to ready Time Vault later."
        if vault is None:
            action = f"{choice.player_name} takes the upcoming turn."
        self._run(
            lambda: self.game.choose_time_vault_skip(
                choice.player_id, vault
            ),
            action,
        )

    @Slot()
    def cancelTarget(self) -> None:
        if (
            self.game.pending_cast is None
            and self.game.pending_activation is None
        ):
            self._tell_current("There is no pending target selection.")
            self.stateChanged.emit()
            return
        if self.game.pending_activation is not None:
            source_name = self.game.pending_activation.source.name
            self.game.cancel_pending_activation()
            self._message = f"Cancelled {source_name}'s ability."
        else:
            spell_name = self.game.pending_cast.spell.name
            self.game.cancel_pending_cast()
            self._message = f"Cancelled casting {spell_name}."
        self.stateChanged.emit()

    @Slot()
    def passPriority(self) -> None:
        player = self.game.players[self.perspective_index]
        resolved: list[tuple[Card, ...] | None] = []
        damage_incident = self.game.pending_damage
        destruction_incident = self.game.pending_destruction
        closing_phase = self.game.pending_phase_advance
        closing_combat_response = bool(
            self.game.combat is not None
            and self.game.combat.step in {
                CombatStep.ATTACK_RESPONSE,
                CombatStep.ATTACKER_RESPONSE,
                CombatStep.BLOCKER_RESPONSE,
            }
        )
        batch_names = [
            *[card.name for card in self.game.stack],
            *[
                f"{ability.source_name} ability"
                for ability in self.game.batch_abilities
            ],
        ]
        timed_event = (
            self.game.timed_events[0].label
            if self.game.timed_events and not self.game.stack
            else ""
        )
        success = f"{player.name} passed priority."

        if not self._run(
            lambda: resolved.append(self.game.pass_priority(player.id)),
            success,
        ):
            return
        if (
            resolved
            and resolved[0] is None
            and self.game.priority_player_index is not None
        ):
            receiver = self.game.players[self.game.priority_player_index]
            self._prompt(
                receiver.id,
                f"{player.name} passed priority. You may act, or pass.",
                observer_message=(
                    f"You passed priority; waiting for {receiver.name}."
                ),
            )
            self.stateChanged.emit()
        elif (
            destruction_incident is not None
            and self.game.pending_destruction is None
        ):
            saved = [
                target.card_name
                for target in destruction_incident.targets
                if target.card_id in destruction_incident.regenerated_card_ids
            ]
            self._message = (
                "Regenerated " + ", ".join(saved) + "."
                if saved
                else "Resolved destruction."
            )
            self.stateChanged.emit()

        elif damage_incident is not None and self.game.pending_damage is None:
            summaries = []
            for packet in damage_incident.packets:
                if packet.remaining <= 0:
                    continue
                if packet.recipient_kind.value == "player":
                    suffix = (
                        "combat damage"
                        if packet.combat
                        else f"damage from {packet.source_name}"
                    )
                    summaries.append(
                        f"{packet.recipient_name} took "
                        f"{packet.remaining} {suffix}"
                    )
            existing = self._message if "mana burn" in self._message else ""
            self._message = "; ".join((*summaries, existing) if existing else summaries)
            if not self._message:
                self._message = "Completed damage resolution."
            self.stateChanged.emit()
        elif resolved and resolved[0] == () and timed_event:
            self._message = f"Resolved timed event: {timed_event}."
            self.stateChanged.emit()
        elif closing_phase is not None and self.game.pending_phase_advance is None:
            self._message = f"Advanced from {closing_phase.value.title()}."
            self.stateChanged.emit()
        elif closing_combat_response and resolved and resolved[0] == ():
            self._message = ""
            self.stateChanged.emit()
        elif (
            resolved
            and resolved[0] is not None
            and batch_names
            and self._message == success
        ):
            names = ", ".join(batch_names)
            self._message = f"Resolved batch: {names}."
            self.stateChanged.emit()

    @Slot()
    def autoPassTurn(self) -> None:
        player = self.game.players[self.perspective_index]
        if self.game.priority_player_index != self.perspective_index:
            self._tell_current(f"{player.name} does not currently have priority.")
            self.stateChanged.emit()
            return
        self._auto_pass_turns[player.id] = self.game.turn_number
        if self._run(
            lambda: None,
            "Auto-pass enabled for this turn.",
        ):
            self._prompt(
                player.id,
                "You will automatically pass priority for the rest of this turn.",
                observer_message=(
                    f"{player.name} will automatically pass priority for the "
                    "rest of this turn."
                ),
            )
            self.stateChanged.emit()

    @Slot(bool)
    def chooseUpkeepPayment(self, pay: bool) -> None:
        player = self.game.players[self.perspective_index]
        choice = "Paid" if pay else "Declined"
        self._run(
            lambda: self.game.choose_upkeep_payment(player.id, pay=pay),
            f"{choice} the upkeep cost.",
        )

    @Slot(int)
    def choosePartialUpkeepPayment(self, amount: int) -> None:
        player = self.game.players[self.perspective_index]
        self._run(
            lambda: self.game.choose_partial_upkeep_payment(player.id, amount),
            f"Paid {amount} mana toward upkeep.",
        )

    @Slot(int)
    def chooseUpkeepCounterPurchase(self, amount: int) -> None:
        player = self.game.players[self.perspective_index]
        self._run(
            lambda: self.game.choose_upkeep_counter_purchase(player.id, amount),
            f"Bought {amount} counter(s) during upkeep.",
        )

    @Slot(int)
    def chooseCounterDamagePayment(self, amount: int) -> None:
        player = self.game.players[self.perspective_index]
        self._run(
            lambda: self.game.choose_counter_damage_payment(player.id, amount),
            f"Paid to preserve {amount} counter(s).",
        )

    @Slot(str)
    def targetPlayer(self, player_id: str) -> None:
        if (
            self.game.pending_cast is None
            and self.game.pending_activation is None
        ):
            self._tell_current(
                "There is no spell or ability waiting for a target."
            )
            self.stateChanged.emit()
            return
        try:
            target = self.game.player(player_id)
        except KeyError:
            self._tell_current("That player is not in this game.")
            self.stateChanged.emit()
            return
        if self.game.pending_activation is not None:
            source = self.game.pending_activation.source
            self._run(
                lambda: self.game.complete_pending_activation((target,)),
                f"Activated {source.name} targeting {target.name}.",
            )
            return
        spell = self.game.pending_cast.spell
        self._run(
            lambda: self.game.complete_pending_cast((target,)),
            f"Cast {spell.name} targeting {target.name}.",
        )

    def _default_damage_assignments(self) -> dict[Card, dict[Card, int]]:
        return self._combat_ui.default_damage_assignments(self.game)

    @Slot(str, str, int)
    def adjustCombatDamage(
        self, source_id: str, recipient_id: str, delta: int
    ) -> None:
        try:
            self._combat_ui.adjust_damage_assignment(
                self.game,
                self.game.players[self.perspective_index].id,
                UUID(source_id),
                UUID(recipient_id),
                delta,
            )
        except (ValueError, RuntimeError) as error:
            self._tell_current(str(error))
        self.stateChanged.emit()

    @Slot()
    def confirmCombatDamage(self) -> None:
        player = self.game.players[self.perspective_index]
        try:
            complete = self._combat_ui.confirm_damage_assignments(
                self.game, player.id
            )
        except (ValueError, RuntimeError) as error:
            self._tell_current(str(error))
            self.stateChanged.emit()
            return
        if not complete:
            next_player_id = self._combat_ui.pending_damage_assignment_player_ids(
                self.game
            )[0]
            self.perspective_index = next(
                index
                for index, candidate in enumerate(self.game.players)
                if candidate.id == next_player_id
            )
            next_player = self.game.player(next_player_id)
            self._prompt(
                next_player_id,
                "Assign your combat damage.",
                observer_message=f"Waiting for {next_player.name} to assign damage.",
            )
            self.stateChanged.emit()
            return
        assignments = self._combat_ui.damage_assignments(self.game)
        self._combat_ui.mark_damage_submitted()
        if not self._run(
            lambda: self.game.deal_combat_damage(assignments),
            "Combat damage assigned.",
        ):
            self._combat_ui.mark_damage_submitted(False)
            self.stateChanged.emit()

    @Slot()
    def discardSelected(self) -> None:
        cards = self._selected_cards()
        if self.game.pending_discard_choices:
            choice = self.game.pending_discard_choices[0]
            required = min(choice.amount, len(self.game.player(choice.player_id).hand))
            if len(cards) != required:
                self._tell_current(
                    f"Select exactly {required} card(s) to discard."
                )
                self.stateChanged.emit()
                return
            self._run(
                lambda: self.game.choose_discard(choice.player_id, cards),
                f"Discarded {required} card(s).",
            )
            return
        if len(cards) != 1:
            self._tell_current("Select exactly one card to discard.")
            self.stateChanged.emit()
            return
        self._run(lambda: self.game.discard(cards[0]), f"Discarded {cards[0].name}.")

    @Slot(bool)
    def chooseDemonicAttorney(self, concede: bool) -> None:
        if not self.game.pending_demonic_attorney_choices:
            self._tell_current("There is no Demonic Attorney choice pending.")
            self.stateChanged.emit()
            return
        player = self.game.players[self.perspective_index]
        message = (
            f"{player.name} conceded to Demonic Attorney."
            if concede
            else "Each player added a card to the ante."
        )
        self._run(
            lambda: self.game.choose_demonic_attorney(
                player.id, concede=concede
            ),
            message,
        )

    @Slot(str, int)
    def moveNaturalSelectionCard(self, card_id: str, delta: int) -> None:
        player = self.game.players[self.perspective_index]
        self._run(
            lambda: self.game.move_natural_selection_card(
                player.id, UUID(card_id), delta
            ),
            "Adjusted the proposed library order.",
        )

    @Slot(bool)
    def chooseNaturalSelection(self, shuffle: bool) -> None:
        player = self.game.players[self.perspective_index]
        self._run(
            lambda: self.game.choose_natural_selection(
                player.id, shuffle=shuffle
            ),
            (
                "Shuffled the selected library."
                if shuffle
                else "Reordered the top of the selected library."
            ),
        )

    @Slot(str)
    def setLibrarySearchFilter(self, text: str) -> None:
        self._choices.library_search_filter = text
        selected = self._choices.library_search_selected_id
        if selected is not None and all(
            card.id != selected
            for card in self.game.legal_library_search_cards()
            if text.casefold().strip() in card.name.casefold()
        ):
            self._choices.library_search_selected_id = None
        self.stateChanged.emit()

    @Slot(str)
    def selectLibrarySearchCard(self, card_id: str) -> None:
        candidate = self._card_by_id(UUID(card_id))
        if candidate not in self.game.legal_library_search_cards():
            self._tell_current("Choose an eligible card from the library.")
        else:
            self._choices.library_search_selected_id = candidate.id
        self.stateChanged.emit()

    @Slot()
    def confirmLibrarySearch(self) -> None:
        selected = self._choices.library_search_selected_id
        card = self._card_by_id(selected) if selected is not None else None
        if card is None:
            self._tell_current("Select a card to put into your hand.")
            self.stateChanged.emit()
            return
        player = self.game.players[self.perspective_index]
        if self._run(
            lambda: self.game.choose_library_search_card(player.id, card),
            "Searched the library and chose a card privately.",
        ):
            self._choices.clear_library_search()

    @Slot()
    def chooseBalanceSelected(self) -> None:
        choice = (
            self.game.pending_balance.current_choice
            if self.game.pending_balance is not None
            else None
        )
        if choice is None:
            self._tell_current("There is no pending Balance choice.")
            self.stateChanged.emit()
            return
        cards = self._selected_cards()
        if len(cards) != choice.amount:
            self._tell_current(
                f"Select exactly {choice.amount} {choice.category} card(s)."
            )
            self.stateChanged.emit()
            return
        self._run(
            lambda: self.game.choose_balance_cards(choice.player_id, cards),
            "Balance selection recorded; continue with the next prompt.",
        )

    @Slot()
    def chooseUntapSelected(self) -> None:
        choice = self.game.pending_untap_choice
        if choice is None:
            self._tell_current("There is no pending untap choice.")
            self.stateChanged.emit()
            return
        cards = self._selected_cards()
        required = min(
            choice.maximum
            - self.game._selected_untap_count(choice, choice.card_type),
            len(self.game._legal_current_untap_ids(choice)),
        )
        if len(cards) != required:
            self._tell_current(
                f"Select exactly {required} permanent(s) to untap."
            )
            self.stateChanged.emit()
            return
        self._run(
            lambda: self.game.choose_untap_cards(choice.player_id, tuple(cards)),
            "Untap selection recorded.",
        )

    @Slot(int)
    def chooseCounterRewind(self, amount: int) -> None:
        player = self.game.players[self.perspective_index]
        self._run(
            lambda: self.game.choose_counter_rewind(player.id, amount),
            f"Replaced {amount} counter(s).",
        )

    @Slot()
    def chooseUpkeepSacrifice(self) -> None:
        if not self.game.timed_events:
            self._tell_current("There is no upkeep sacrifice pending.")
            self.stateChanged.emit()
            return
        event = self.game.timed_events[0]
        cards = self._selected_cards()
        if len(cards) != 1:
            self._tell_current(
                "Select exactly one eligible creature to sacrifice."
            )
            self.stateChanged.emit()
            return
        self._run(
            lambda: self.game.choose_upkeep_sacrifice(
                event.affected_player_id, cards[0]
            ),
            f"Sacrificed {cards[0].name} for {event.source_name}.",
        )

    @Slot()
    def chooseUpkeepLand(self) -> None:
        choice = self.game.pending_upkeep_land_loss
        if choice is None:
            self._tell_current("There is no pending upkeep land choice.")
            self.stateChanged.emit()
            return
        cards = [
            card
            for player in self.game.players
            for card in player.battlefield
            if card.id in self.selected_card_ids
            and card.id in choice.candidate_ids
        ]
        if len(cards) != 1 or cards[0].id not in choice.candidate_ids:
            self._tell_current("Select exactly one eligible land.")
            self.stateChanged.emit()
            return
        land = cards[0]
        self._run(
            lambda: self.game.choose_upkeep_land_loss(choice.chooser_id, land),
            f"Chose {land.name} to be lost to {choice.source_name}.",
        )

    @Slot()
    def beginCombat(self) -> None:
        attacker = self.game.active_player
        defender = next(
            player for player in self.game.players if player.id != attacker.id
        )
        if self._run(
            self.game.begin_combat,
            "Attack announced.",
        ):
            self._prompt(
                attacker.id,
                f"Attack announced; waiting for {defender.name} to respond.",
                observer_message=(
                    f"{attacker.name} announced an attack. Play pre-attacker "
                    "fast effects, or pass priority."
                ),
            )
            self.stateChanged.emit()

    @Slot()
    def declareAttackers(self) -> None:
        cards = self._combat_ui.drafted_attackers(
            self.game, self.selected_card_ids
        )
        bands = self._combat_ui.attacking_bands(self.game)
        attacker = self.game.active_player
        if self._run(
            lambda: self.game.declare_attackers(cards, bands=bands),
            f"{len(cards)} attacker(s) declared.",
        ):
            self._prompt(
                attacker.id,
                f"Declared {len(cards)} attacker(s). You may play fast effects or pass.",
                observer_message=(
                    f"{attacker.name} declared {len(cards)} attacker(s). Waiting for "
                    f"{attacker.name} to act or pass before blockers."
                ),
            )
            self.stateChanged.emit()

    @Slot()
    def setAttackingBand(self) -> None:
        try:
            message = self._combat_ui.set_attacking_band(
                self.game, self.selected_card_ids
            )
        except (ValueError, RuntimeError) as error:
            self._tell_current(str(error))
            self.stateChanged.emit()
            return
        if message.startswith("Created"):
            self.selected_card_ids.clear()
        self._tell_current(message)
        self.stateChanged.emit()

    @Slot()
    def setBlocks(self) -> None:
        try:
            message = self._combat_ui.set_blocks(self.game, self.selected_card_ids)
        except (ValueError, RuntimeError) as error:
            self._tell_current(str(error))
            self.stateChanged.emit()
            return
        self.selected_card_ids.clear()
        player = self.game.players[self.perspective_index]
        self._prompt(
            player.id,
            message,
            observer_message=f"{player.name} is arranging blockers.",
        )
        self.stateChanged.emit()

    @Slot()
    def declareBlockers(self) -> None:
        try:
            assignments = self._combat_ui.blocker_assignments(self.game)
        except RuntimeError as error:
            self._tell_current(str(error))
            self.stateChanged.emit()
            return
        count = len(assignments)
        defender = self.game.player(self.game.combat.defending_player_id)
        attacker = self.game.player(self.game.combat.attacking_player_id)
        if self._run(
            lambda: self.game.declare_blockers(assignments),
            f"{count} blocker(s) declared.",
        ):
            self._combat_ui.reset()
            self._prompt(
                attacker.id,
                f"{defender.name} declared {count} blocker(s). You may play fast "
                "effects or pass before damage.",
                observer_message=(
                    f"Declared {count} blocker(s); waiting for {attacker.name} "
                    "to act or pass."
                ),
            )
            self.stateChanged.emit()

    @Slot()
    def switchPerspective(self) -> None:
        self.perspective_index = 1 - self.perspective_index
        self.selected_card_ids.clear()
        self.stateChanged.emit()

    @Slot()
    def finishHandReveal(self) -> None:
        player = self.game.players[self.perspective_index]
        if self._run(
            lambda: self.game.finish_hand_reveal(player.id),
            "Finished looking at opponent's hand.",
        ):
            self._message = "Finished looking at opponent's hand."
        self.stateChanged.emit()

    @Slot(str)
    def chooseDrainPowerMana(self, color: str) -> None:
        player = self.game.players[self.perspective_index]
        if self._run(
            lambda: self.game.choose_drain_power_mana(player.id, Color(color)),
            f"Chose {color} for Drain Power.",
        ):
            self._message = f"Chose {color} mana for Drain Power."
        self.stateChanged.emit()

    @Slot(str, int)
    def choosePowerSinkMana(self, land_id: str, ability_index: int) -> None:
        player = self.game.players[self.perspective_index]
        if self._run(
            lambda: self.game.choose_power_sink_mana(
                player.id, UUID(land_id), ability_index
            ),
            "Paid mana toward Power Sink.",
        ):
            self._message = "Paid mana toward Power Sink."
        self.stateChanged.emit()

    @Slot()
    def newGame(self) -> None:
        self.game = self._game_factory()
        self.game.pause_for_damage_windows = True
        self.perspective_index = 0
        self._messages.reset(player.id for player in self.game.players)
        self.selected_card_ids.clear()
        self._choices.reset()
        self._auto_pass_turns.clear()
        self._combat_ui.reset()
        self._message = "Started a new game."
        self.stateChanged.emit()


def create_engine(view_model: GameViewModel | None = None) -> QQmlApplicationEngine:
    # Native platform styles do not necessarily permit replacing control
    # backgrounds. Basic is fully customizable and consistent across platforms.
    QQuickStyle.setStyle("Basic")
    engine = QQmlApplicationEngine()
    bridge = view_model or GameViewModel()
    bridge.setParent(engine)
    # Keep both Qt and Python ownership explicit. A bare temporary context
    # property can otherwise be garbage-collected, leaving QML with null.
    engine.game_view_model = bridge
    engine.rootContext().setContextProperty("gameBridge", bridge)
    qml_file = Path(__file__).with_name("qml") / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    return engine


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Beta Magic rules-engine UI")
    deck_group = parser.add_mutually_exclusive_group()
    deck_group.add_argument(
        "--test-decks",
        action="store_true",
        help="use deterministic 20-card decks containing supported mechanics",
    )
    parser.add_argument(
        "--ante",
        action="store_true",
        help="ante one face-up card from each shuffled deck before drawing",
    )
    deck_group.add_argument(
        "--enchantment-test-decks",
        action="store_true",
        help="use deterministic 20-card decks focused on global enchantments",
    )
    deck_group.add_argument(
        "--timed-event-test-decks",
        action="store_true",
        help="use deterministic 20-card decks focused on Copper Tablet",
    )
    deck_group.add_argument(
        "--x-test-decks",
        action="store_true",
        help="use deterministic 20-card decks focused on X spells",
    )
    deck_group.add_argument(
        "--protection-test-decks",
        action="store_true",
        help="use deterministic 20-card decks focused on protection",
    )
    deck_group.add_argument(
        "--aura-test-decks",
        action="store_true",
        help="use deterministic 20-card decks focused on stacked Auras",
    )
    deck_group.add_argument(
        "--banding-test-decks",
        action="store_true",
        help="use deterministic 20-card decks focused on Banding",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # Windows can temporarily lock the clipboard while another application is
    # copying. Qt retries successfully, but its per-attempt warning is noisy.
    QLoggingCategory.setFilterRules("qt.qpa.mime.warning=false")
    # Keep application arguments separate from our CLI so Qt does not need to
    # interpret options owned by the game.
    app = QGuiApplication([sys.argv[0]])
    app.setApplicationName("Beta Magic")
    if args.banding_test_decks:
        game_factory = make_banding_test_game
    elif args.aura_test_decks:
        game_factory = make_aura_test_game
    elif args.protection_test_decks:
        game_factory = make_protection_test_game
    elif args.x_test_decks:
        game_factory = make_x_test_game
    elif args.timed_event_test_decks:
        game_factory = make_timed_event_test_game
    elif args.enchantment_test_decks:
        game_factory = make_enchantment_test_game
    elif args.test_decks:
        game_factory = make_test_game
    else:
        game_factory = make_demo_game
    if args.ante:
        game_factory = partial(game_factory, ante=True)
    game = game_factory()
    engine = create_engine(GameViewModel(game, game_factory=game_factory))
    if not engine.rootObjects():
        return 1
    previous_sigint_handler = signal.signal(
        signal.SIGINT, lambda _signum, _frame: app.quit()
    )
    try:
        return app.exec()
    finally:
        signal.signal(signal.SIGINT, previous_sigint_handler)


if __name__ == "__main__":
    raise SystemExit(main())
