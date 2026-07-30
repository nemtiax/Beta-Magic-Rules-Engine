"""Qt Quick hotseat UI for the Beta Magic rules engine.

Run with ``python -m beta_magic.ui``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from .cards import Card
from .decks import (
    AEGIS_WARDS_DECK,
    ARCANE_DEPTHS_DECK,
    COPPER_CONTROL_DECK,
    COPPER_PRESSURE_DECK,
    ELEMENTAL_SURGE_DECK,
    MOONLIT_HORDE_DECK,
    RADIANT_CHARGE_DECK,
    SPECTRUM_ASSAULT_DECK,
    STONEFIRE_DECK,
    VERDANT_TIDES_DECK,
    make_demo_game,
    make_enchantment_test_game,
    make_protection_test_game,
    make_test_game,
    make_timed_event_test_game,
    make_x_test_game,
)
from .events import DamageEvent, GameEvent, ManaBurnEvent, SpellCastEvent
from .effects import UpkeepCostEffect
from .game import GameState, PlayerState
from .types import CardType, CombatStep, Zone



def mana_text(player: PlayerState) -> str:
    values = zip(("W", "U", "B", "R", "G", "C"), player.mana_pool.amounts)
    available = [f"{symbol}:{amount}" for symbol, amount in values if amount]
    return " ".join(available) if available else "empty"


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
        self._game_factory = game_factory or make_demo_game
        self.game = game or self._game_factory()
        self.game.pause_for_damage_windows = True
        self.perspective_index = 0
        self.selected_card_ids: set[UUID] = set()
        self._x_card_id: UUID | None = None
        self._x_value = 0
        self._x_max = 0
        self._message = "Double-click a card to play, cast, or tap it."

    @Property("QVariantMap", notify=stateChanged)
    def state(self) -> dict[str, Any]:
        perspective = self.game.players[self.perspective_index]
        opponent = self.game.players[1 - self.perspective_index]
        combat = self.game.combat
        upkeep_event = (
            self.game.timed_events[0] if self.game.timed_events else None
        )
        upkeep_payment_required = bool(
            upkeep_event is not None
            and isinstance(upkeep_event.effect, UpkeepCostEffect)
            and upkeep_event.payment_decision is None
            and self.game.upkeep_payment_required
        )
        damage_incident = self.game.pending_damage
        destruction_incident = self.game.pending_destruction
        return {
            "turn": self.game.turn_number,
            "phase": (
                self.game.current_phase.value.replace("_", " ").title()
                if self.game.current_phase
                else "—"
            ),
            "combatStep": (
                combat.step.value.replace("_", " ").title() if combat else ""
            ),
            "activePlayer": self.game.active_player.name,
            "message": self._message,
            "targeting": (
                self.game.pending_cast is not None
                or self.game.pending_activation is not None
            ),
            "choosingX": self._x_card_id is not None,
            "xValue": self._x_value,
            "xMaximum": self._x_max,
            "xCardName": (
                self._card_by_id(self._x_card_id).name
                if self._x_card_id is not None
                and self._card_by_id(self._x_card_id) is not None
                else ""
            ),
            "stack": [
                *[
                    (
                        f"{card.name} "
                        f"(X={self.game.stack_spells[card.id].x_value})"
                        if card.definition.mana_cost.x_symbols
                        else card.name
                    )
                    for card in self.game.stack
                ],
                *[
                    f"{ability.source_name} ability"
                    for ability in self.game.batch_abilities
                ],
            ],
            "timedEvent": (
                self.game.timed_events[0].label
                if self.game.timed_events
                else ""
            ),
            "damageWindow": (
                damage_incident.step.value.replace("_", " ").title()
                if damage_incident is not None
                else ""
            ),
            "damageTotal": (
                damage_incident.total_remaining
                if damage_incident is not None
                else 0
            ),
            "damagePackets": (
                [
                    (
                        f"{packet.source_name}: {packet.remaining} to "
                        f"{packet.recipient_name}"
                    )
                    for packet in damage_incident.packets
                    if packet.remaining
                ]
                if damage_incident is not None
                else []
            ),
            "damagePacketChoices": (
                [
                    {
                        "id": str(packet.id),
                        "label": (
                            f"{packet.source_name}: {packet.remaining} to "
                            f"{packet.recipient_name}"
                        ),
                    }
                    for packet in self.game.legal_prevention_packets()
                ]
                if damage_incident is not None
                and self.game.pending_prevention is not None
                else []
            ),
            "choosingPrevention": self.game.pending_prevention is not None,
            "preventionRemaining": (
                (
                    self.game.pending_prevention.remaining
                    if self.game.pending_prevention.remaining is not None
                    else "all"
                )
                if self.game.pending_prevention is not None
                else 0
            ),
            "preventionPaid": (
                self.game.pending_prevention.paid
                if self.game.pending_prevention is not None
                else False
            ),
            "destructionWindow": (
                destruction_incident.step.value.replace("_", " ").title()
                if destruction_incident is not None
                else ""
            ),
            "destructionTargets": (
                [
                    target.card_name
                    + (
                        ""
                        if target.regeneration_allowed
                        else " (cannot regenerate)"
                    )
                    for target in destruction_incident.targets
                ]
                if destruction_incident is not None
                else []
            ),
            "upkeepPaymentRequired": upkeep_payment_required,
            "upkeepPaymentPlayer": (
                upkeep_event.affected_player_id
                if upkeep_payment_required and upkeep_event is not None
                else ""
            ),
            "canPayUpkeep": (
                self.game.can_pay_upkeep_cost(upkeep_event.affected_player_id)
                if upkeep_payment_required and upkeep_event is not None
                else False
            ),
            "priorityPlayer": (
                self.game.players[self.game.priority_player_index].name
                if self.game.priority_player_index is not None
                else ""
            ),
            "hasPriority": (
                self.game.priority_player_index == self.perspective_index
            ),
            "perspective": self._player_data(perspective, reveal_hand=True),
            "opponent": self._player_data(opponent, reveal_hand=False),
            "attackers": [
                {"id": str(card.id), "label": card.name}
                for card in (combat.attackers if combat else [])
            ],
        }

    def _player_data(
        self, player: PlayerState, *, reveal_hand: bool
    ) -> dict[str, Any]:
        graveyard_targeting = (
            self.game.pending_cast is not None
            and self.game.pending_cast.spell.definition.target_requirement is not None
            and self.game.pending_cast.spell.definition.target_requirement.zone
            is Zone.GRAVEYARD
        )
        return {
            "id": player.id,
            "name": player.name,
            "life": player.life,
            "mana": mana_text(player),
            "legalTarget": player in self.game.legal_player_targets_for(),
            "libraryCount": len(player.library),
            "handCount": len(player.hand),
            "hand": [self._card_data(card) for card in player.hand]
            if reveal_hand
            else [],
            "battlefield": [self._card_data(card) for card in player.battlefield],
            "battlefieldNonlands": [
                self._card_data(card)
                for card in player.battlefield
                if CardType.LAND not in card.definition.card_types
            ],
            "battlefieldLands": [
                self._card_data(card)
                for card in player.battlefield
                if CardType.LAND in card.definition.card_types
            ],
            "graveyard": [
                self._card_data(card)
                for card in (
                    player.graveyard
                    if graveyard_targeting
                    else player.graveyard[-5:]
                )
            ],
            "graveyardCount": len(player.graveyard),
            "exile": [self._card_data(card) for card in player.exile[-5:]],
            "exileCount": len(player.exile),
        }

    def _card_data(self, card: Card) -> dict[str, Any]:
        background, foreground = self._card_colors(card)
        enchanted_card = next(
            (
                permanent
                for player in self.game.players
                for permanent in player.battlefield
                if permanent.id == card.enchanted_card_id
            ),
            None,
        )
        return {
            "id": str(card.id),
            "name": card.name,
            "background": background,
            "foreground": foreground,
            "tapped": card.tapped,
            "selected": card.id in self.selected_card_ids,
            "legalTarget": card in self.game.legal_targets_for(),
            "isCreature": CardType.CREATURE in card.definition.card_types,
            "power": (
                self.game.creature_power(card)
                if CardType.CREATURE in card.definition.card_types
                and card.zone is Zone.BATTLEFIELD
                and (
                    card.definition.power is not None
                    or card.definition.variable_stats is not None
                )
                else "*"
                if card.definition.variable_stats is not None
                else card.definition.power
                if card.definition.power is not None
                else -1
            ),
            "toughness": (
                self.game.creature_toughness(card)
                if CardType.CREATURE in card.definition.card_types
                and card.zone is Zone.BATTLEFIELD
                and (
                    card.definition.toughness is not None
                    or card.definition.variable_stats is not None
                )
                else "*"
                if card.definition.variable_stats is not None
                else card.definition.toughness
                if card.definition.toughness is not None
                else -1
            ),
            "damage": card.damage,
            "manaCost": (
                card.definition.mana_cost.compact
                or (
                    "0"
                    if CardType.ARTIFACT in card.definition.card_types
                    and CardType.LAND not in card.definition.card_types
                    else ""
                )
            ),
            "typeLine": " ".join(
                (
                    *card.definition.supertypes,
                    *(t.value for t in sorted(
                        card.definition.card_types, key=lambda card_type: card_type.value
                    )),
                )
            )
            + (
                " — " + " ".join(card.definition.subtypes)
                if card.definition.subtypes
                else ""
            ),
            "abilities": ", ".join(
                ability.value
                for ability in sorted(
                    self.game.creature_abilities(card)
                    if CardType.CREATURE in card.definition.card_types
                    and card.zone is Zone.BATTLEFIELD
                    else card.definition.abilities,
                    key=lambda ability: ability.value,
                )
            ),
            "rulesText": card.definition.rules_text,
            "attachedTo": enchanted_card.name if enchanted_card else "",
            "activatedAbilities": [
                {
                    "index": index,
                    "label": ability.label,
                    "enabled": (
                        card.controller_id is not None
                        and self.game.can_activate_ability(
                            card.controller_id, card, index
                        )
                    ),
                }
                for index, ability in enumerate(
                    self.game.activated_abilities(card)
                )
            ]
            if card.zone is Zone.BATTLEFIELD
            else [],
        }

    @staticmethod
    def _card_colors(card: Card) -> tuple[str, str]:
        color = card.definition.produces_mana
        if color is None and len(card.definition.colors) == 1:
            color = next(iter(card.definition.colors))
        palette = {
            "W": ("#f1edcf", "#29271e"),
            "U": ("#79b9dc", "#102b3a"),
            "B": ("#4c4654", "#f4f0f5"),
            "R": ("#d96b52", "#32140e"),
            "G": ("#76a66f", "#102a12"),
            "C": ("#aaa69f", "#222222"),
        }
        if color is not None:
            return palette[color.value]
        if CardType.ARTIFACT in card.definition.card_types:
            return palette["C"]
        return "#c8bda8", "#222222"

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
        except (ValueError, RuntimeError) as error:
            self._message = str(error)
            self.stateChanged.emit()
            return False
        event_messages = self._event_messages(self.game.events[event_checkpoint:])
        self._message = "; ".join(event_messages) if event_messages else success
        self.selected_card_ids.clear()
        self.stateChanged.emit()
        return True

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
                self._message = "Choose a legal card as the target."
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
        if card is None:
            return
        if card.id in self.selected_card_ids:
            self.selected_card_ids.remove(card.id)
        else:
            self.selected_card_ids.add(card.id)
        self._message = f"Selected {len(self.selected_card_ids)} card(s)."
        self.stateChanged.emit()

    @Slot(str)
    def activateCard(self, card_id: str) -> None:
        if (
            self.game.pending_cast is not None
            or self.game.pending_activation is not None
        ):
            self._message = "Choose the pending target first."
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
                    self._x_max = self.game.maximum_affordable_x(card)
                except (ValueError, RuntimeError) as error:
                    self._message = str(error)
                else:
                    self._x_card_id = card.id
                    self._x_value = self._x_max
                    self._message = f"Choose X for {card.name}."
                self.stateChanged.emit()
                return
            try:
                pending = self.game.begin_cast(card)
            except (ValueError, RuntimeError) as error:
                self._message = str(error)
            else:
                self.selected_card_ids.clear()
                self._message = (
                    f"Choose a target in play for {card.name}."
                    if pending is not None
                    else f"Cast {card.name}."
                )
            self.stateChanged.emit()
        elif card in player.battlefield and CardType.LAND in card.definition.card_types:
            abilities = self.game.activated_abilities(card)
            if len(abilities) == 1:
                self.activateAbility(card_id, 0)
            elif abilities:
                self._message = f"Choose an ability for {card.name}."
                self.stateChanged.emit()
            else:
                self._message = f"{card.name} has no activated abilities."
                self.stateChanged.emit()
        else:
            self._message = f"{card.name} has no double-click action."
            self.stateChanged.emit()

    @Slot(int)
    def adjustX(self, delta: int) -> None:
        if self._x_card_id is None:
            return
        self._x_value = max(0, min(self._x_max, self._x_value + delta))
        self.stateChanged.emit()

    @Slot()
    def confirmXCast(self) -> None:
        if self._x_card_id is None:
            return
        card = self._card_by_id(self._x_card_id)
        if card is None:
            self.cancelXCast()
            return
        x_value = self._x_value
        try:
            pending = self.game.begin_cast(card, x_value=x_value)
        except (ValueError, RuntimeError) as error:
            self._message = str(error)
        else:
            self._x_card_id = None
            self._message = (
                f"Choose a target for {card.name} (X={x_value})."
                if pending is not None
                else f"Cast {card.name} with X={x_value}."
            )
        self.stateChanged.emit()

    @Slot()
    def cancelXCast(self) -> None:
        self._x_card_id = None
        self._x_value = 0
        self._x_max = 0
        self._message = "Cancelled casting."
        self.stateChanged.emit()

    @Slot(str, int)
    def activateAbility(self, card_id: str, ability_index: int) -> None:
        if (
            self.game.pending_cast is not None
            or self.game.pending_activation is not None
        ):
            self._message = "Choose the pending target first."
            self.stateChanged.emit()
            return
        player = self.game.players[self.perspective_index]
        card = self._perspective_card(card_id)
        if card is None or card not in player.battlefield:
            return
        try:
            ability = self.game.activated_abilities(card)[ability_index]
        except IndexError:
            self._message = f"{card.name} has no such activated ability."
            self.stateChanged.emit()
            return
        pending: list[object] = []
        if self._run(
            lambda: pending.append(
                self.game.activate_ability(player.id, card, ability_index)
            ),
            f"{card.name}: {ability.label}.",
        ) and pending[0] is not None:
            self._message = f"Choose a target for {card.name}'s ability."
            self.stateChanged.emit()
        elif self.game.pending_prevention is not None:
            self._message = f"Choose damage for {card.name} to prevent."
            self.stateChanged.emit()

    @Slot(str)
    def chooseDamagePacket(self, packet_id: str) -> None:
        player = self.game.players[self.perspective_index]
        prevented: list[int] = []
        if self._run(
            lambda: prevented.append(
                self.game.prevent_damage(player.id, UUID(packet_id))
            ),
            "Prevented damage.",
        ):
            self._message = f"Prevented {prevented[0]} damage."
            if self.game.pending_prevention is not None:
                self._message += (
                    f" {self.game.pending_prevention.remaining} prevention remains."
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

    @Slot()
    def advance(self) -> None:
        def action() -> None:
            if self.game.combat is None:
                self.game.advance_phase()
            elif self.game.combat.step is CombatStep.BLOCKER_RESPONSE:
                self.game.advance_combat()
            elif self.game.combat.step is CombatStep.DAMAGE:
                self.game.deal_combat_damage(self._default_damage_assignments())
            else:
                raise RuntimeError("complete the current combat declaration first")

        self._run(action, "Advanced the game.")

    @Slot()
    def cancelTarget(self) -> None:
        if (
            self.game.pending_cast is None
            and self.game.pending_activation is None
        ):
            self._message = "There is no pending target selection."
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
        elif (
            resolved
            and resolved[0] is not None
            and self._message == success
        ):
            names = ", ".join(batch_names)
            self._message = f"Resolved batch: {names}."
            self.stateChanged.emit()

    @Slot(bool)
    def chooseUpkeepPayment(self, pay: bool) -> None:
        player = self.game.players[self.perspective_index]
        choice = "Paid" if pay else "Declined"
        self._run(
            lambda: self.game.choose_upkeep_payment(player.id, pay=pay),
            f"{choice} the upkeep cost.",
        )

    @Slot(str)
    def targetPlayer(self, player_id: str) -> None:
        if (
            self.game.pending_cast is None
            and self.game.pending_activation is None
        ):
            self._message = "There is no spell or ability waiting for a target."
            self.stateChanged.emit()
            return
        try:
            target = self.game.player(player_id)
        except KeyError:
            self._message = "That player is not in this game."
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
        """Choose a legal default until a richer damage-assignment dialog lands."""

        combat = self.game.combat
        if combat is None:
            return {}
        result: dict[Card, dict[Card, int]] = {}
        for attacker in combat.attackers:
            blockers = [
                blocker
                for blocker in combat.blockers[attacker.id]
                if blocker in self.game.player(combat.defending_player_id).battlefield
            ]
            if len(blockers) > 1:
                result[attacker] = {
                    blocker: max(0, self.game.creature_power(attacker))
                    if index == 0
                    else 0
                    for index, blocker in enumerate(blockers)
                }
        return result

    @Slot()
    def discardSelected(self) -> None:
        cards = self._selected_cards()
        if len(cards) != 1:
            self._message = "Select exactly one card to discard."
            self.stateChanged.emit()
            return
        self._run(lambda: self.game.discard(cards[0]), f"Discarded {cards[0].name}.")

    @Slot()
    def beginCombat(self) -> None:
        self._run(
            self.game.begin_combat,
            "Select creatures in play, then declare attackers.",
        )

    @Slot()
    def declareAttackers(self) -> None:
        cards = self._selected_cards()
        self._run(
            lambda: self.game.declare_attackers(cards),
            f"Declared {len(cards)} attacker(s). Switch to the defender.",
        )

    @Slot(str)
    def declareBlockers(self, attacker_id: str) -> None:
        cards = self._selected_cards()
        attacker = None
        if self.game.combat:
            attacker = next(
                (
                    card
                    for card in self.game.combat.attackers
                    if str(card.id) == attacker_id
                ),
                None,
            )
        if cards and attacker is None:
            self._message = "Choose the attacker to block."
            self.stateChanged.emit()
            return
        assignments = {card: attacker for card in cards} if attacker else {}
        self._run(
            lambda: self.game.declare_blockers(assignments),
            f"Declared {len(cards)} blocker(s).",
        )

    @Slot()
    def switchPerspective(self) -> None:
        self.perspective_index = 1 - self.perspective_index
        self.selected_card_ids.clear()
        self._message = (
            f"Now viewing {self.game.players[self.perspective_index].name}."
        )
        self.stateChanged.emit()

    @Slot()
    def newGame(self) -> None:
        self.game = self._game_factory()
        self.game.pause_for_damage_windows = True
        self.perspective_index = 0
        self.selected_card_ids.clear()
        self._x_card_id = None
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # Keep application arguments separate from our CLI so Qt does not need to
    # interpret options owned by the game.
    app = QGuiApplication([sys.argv[0]])
    app.setApplicationName("Beta Magic")
    if args.protection_test_decks:
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
    game = game_factory()
    engine = create_engine(GameViewModel(game, game_factory=game_factory))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
