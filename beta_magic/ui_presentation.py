"""Read-only QML presentation building for the hotseat UI."""

from __future__ import annotations

from typing import Any
from uuid import UUID
from .abilities import ActivatedRedirectDamageAbility
from .cards import Card
from .card_images import image_urls_for
from .effects import (
    CounterPurchaseUpkeepEffect,
    ChangeTextWordEffect,
    CounterRedemptionUpkeepEffect,
    OptionalUpkeepPaymentEffect,
    PartialUpkeepDamageEffect,
    UpkeepCostEffect,
    UpkeepCreatureSacrificeEffect,
)
from .game import PlayerState
from .types import BASIC_LAND_SUBTYPES, CardType, Color, CombatStep, TurnPhase, Zone


_BASIC_LAND_ORDER = {
    name: index for index, name in enumerate(BASIC_LAND_SUBTYPES)
}


def mana_text(player: PlayerState) -> str:
    values = zip(("W", "U", "B", "R", "G", "C"), player.mana_pool.amounts)
    available = [f"{symbol}:{amount}" for symbol, amount in values if amount]
    return " ".join(available) if available else "empty"


class UiPresentationBuilder:
    """Translate engine and transient view-model state into QML data."""

    def __init__(self, view_model: Any) -> None:
        self._view_model = view_model

    def __getattr__(self, name: str) -> Any:
        return getattr(self._view_model, name)

    def _text_word_kind(self) -> str:
        pending = self.game.pending_cast
        if pending is None:
            return ""
        effect = next(
            (
                effect
                for effect in pending.spell.definition.spell_effects
                if isinstance(effect, ChangeTextWordEffect)
            ),
            None,
        )
        return effect.word_kind if effect is not None else ""

    def _text_word_from_choices(self) -> list[str]:
        target = self._card_by_id(self._choices.word_target_id)
        if target is None:
            return []
        perspective_id = self.game.players[self.perspective_index].id
        if self.game.card_characteristics_are_hidden_from(
            target, perspective_id
        ):
            if self._text_word_kind() == "color":
                return [
                    color.name.title()
                    for color in Color
                    if color is not Color.COLORLESS
                ]
            return list(BASIC_LAND_SUBTYPES)
        if self._text_word_kind() == "color":
            return [color.name.title() for color in self.game.current_color_words(target)]
        return list(self.game.current_land_words(target))

    def _text_word_to_choices(self) -> list[str]:
        if self._text_word_kind() == "color":
            return [
                color.name.title()
                for color in Color
                if color is not Color.COLORLESS
            ]
        return list(BASIC_LAND_SUBTYPES)

    def build(self) -> dict[str, Any]:
        perspective = self.game.players[self.perspective_index]
        opponent = self.game.players[1 - self.perspective_index]
        combat = self.game.combat
        self._combat_ui.sync(self.game)
        undoable_land = self.game.undoable_land_tap(perspective.id)
        upkeep_event = (
            self.game.timed_events[0] if self.game.timed_events else None
        )
        upkeep_payment_required = bool(
            upkeep_event is not None
            and isinstance(
                upkeep_event.effect,
                (
                    UpkeepCostEffect,
                    OptionalUpkeepPaymentEffect,
                    CounterRedemptionUpkeepEffect,
                ),
            )
            and upkeep_event.payment_decision is None
            and self.game.upkeep_payment_required
        )
        upkeep_sacrifice_required = bool(
            upkeep_event is not None
            and isinstance(upkeep_event.effect, UpkeepCreatureSacrificeEffect)
            and upkeep_event.payment_decision is None
            and self.game.upkeep_payment_required
        )
        partial_upkeep_required = bool(
            upkeep_event is not None
            and isinstance(upkeep_event.effect, PartialUpkeepDamageEffect)
            and upkeep_event.payment_amount is None
            and self.game.upkeep_payment_required
        )
        counter_purchase_required = bool(
            upkeep_event is not None
            and isinstance(upkeep_event.effect, CounterPurchaseUpkeepEffect)
            and upkeep_event.payment_amount is None
            and self.game.upkeep_payment_required
        )
        counter_damage_choice = self.game.pending_counter_damage_choice
        damage_incident = self.game.pending_damage
        destruction_incident = self.game.pending_destruction
        target_decision_player_id = (
            self.game.pending_cast.decision_maker_id
            if self.game.pending_cast is not None
            else self.game.pending_activation.controller_id
            if self.game.pending_activation is not None
            else None
        )
        can_choose_stack_target = bool(
            target_decision_player_id == perspective.id
        )
        turn_choice = self.game.pending_turn_choice
        draw_choice = self.game.pending_draw_choice
        graveyard_return_choice = self.game.pending_graveyard_return_choice
        graveyard_order_choice = (
            self.game.pending_graveyard_order_choices[0]
            if self.game.pending_graveyard_order_choices else None
        )
        discard_choice = (
            self.game.pending_discard_choices[0]
            if self.game.pending_discard_choices else None
        )
        library_discard_choice = (
            self.game.pending_library_discard_choices[0]
            if self.game.pending_library_discard_choices else None
        )
        tomb_cleanup_choice = (
            self.game.pending_tomb_cleanup_choices[0]
            if self.game.pending_tomb_cleanup_choices else None
        )
        balance_choice = (
            self.game.pending_balance.current_choice
            if self.game.pending_balance is not None
            else None
        )
        lich_choice = (
            self.game.pending_lich_choices[0]
            if self.game.pending_lich_choices else None
        )
        untap_choice = self.game.pending_untap_choice
        counter_rewind = self.game.current_counter_rewind()
        upkeep_land_choice = self.game.pending_upkeep_land_loss
        timed_event_order_choice = self.game.pending_timed_event_order
        timed_event_order_items: list[dict[str, Any]] = []
        if timed_event_order_choice is not None:
            events_by_id = {event.id: event for event in self.game.timed_events}
            for event_id in timed_event_order_choice.event_ids_first_to_last:
                event = events_by_id.get(event_id)
                if event is None:
                    continue
                source = self.game._timed_event_source(event)
                timed_event_order_items.append({
                    "id": str(event.id),
                    "label": event.label,
                    "sourceCard": self._card_data(source) if source is not None else {},
                })
        batch_conflict_choice = (
            self.game.pending_batch_conflict_choices[0]
            if self.game.pending_batch_conflict_choices else None
        )
        batch_conflict_items: list[dict[str, Any]] = []
        if (
            batch_conflict_choice is not None
            and self.game.pending_batch_resolution is not None
        ):
            plan = self.game.pending_batch_resolution
            for intent_index in batch_conflict_choice.intent_indexes_first_to_last:
                intent = plan.intents[intent_index]
                batch_conflict_items.append({
                    "intentIndex": intent_index,
                    "label": self.game.batch_conflict_intent_label(
                        batch_conflict_choice, intent_index
                    ),
                    "sourceCard": self._card_data(intent.source),
                })
        kudzu_choice = (
            self.game.pending_kudzu_choices[0]
            if self.game.pending_kudzu_choices else None
        )
        creature_copy_choice = (
            self.game.pending_creature_copy_choices[0]
            if self.game.pending_creature_copy_choices else None
        )
        doppelganger_choice = (
            self.game.pending_doppelganger_choices[0]
            if self.game.pending_doppelganger_choices else None
        )
        hand_reveal = (
            self.game.pending_hand_reveals[0]
            if self.game.pending_hand_reveals else None
        )
        drain_power_choice = (
            self.game.pending_drain_power_choices[0]
            if self.game.pending_drain_power_choices else None
        )
        power_sink_payment = self.game.pending_power_sink_payment
        demonic_attorney_choice = (
            self.game.pending_demonic_attorney_choices[0]
            if self.game.pending_demonic_attorney_choices else None
        )
        word_command_choice = self.game.current_word_command()
        word_command_card = (
            self._card_by_id(word_command_choice.card_id)
            if word_command_choice is not None
            and word_command_choice.card_id is not None
            else None
        )
        word_command_can_choose = bool(
            word_command_choice is not None
            and word_command_choice.commander_id == perspective.id
        )
        word_commandable_ids = {
            card.id for card in self.game.word_commandable_cards()
        } if word_command_choice is not None else set()
        word_mana_options: list[dict[str, Any]] = []
        if word_command_choice is not None:
            for option in self.game.word_command_mana_options():
                produced = "".join(
                    color.value * option.production.amount(color)
                    for color in Color
                )
                word_mana_options.append({
                    "landId": str(option.land_id),
                    "abilityIndex": option.ability_index,
                    "label": f"{option.land_name} — {produced}",
                    "selected": (
                        self._choices.word_mana_activations.get(option.land_id)
                        == option.ability_index
                    ),
                })
        word_payment_valid = False
        word_spending_options: list[dict[str, Any]] = []
        if (
            word_command_can_choose
            and word_command_choice is not None
            and word_command_choice.stage == "choose_payment"
            and word_command_card is not None
        ):
            try:
                cost = self.game.spell_mana_cost(
                    word_command_card,
                    word_command_choice.x_value,
                    len(word_command_choice.targets) or 1,
                )
                plans = self.game.land_mana_payment_plans(
                    word_command_choice.commanded_player_id,
                    cost,
                    tuple(self._choices.word_mana_activations.items()),
                    require_exact_when_available=True,
                )
            except (ValueError, RuntimeError):
                pass
            else:
                seen_spending: set[tuple[int, ...]] = set()
                for plan in plans:
                    amounts = plan.spending.amounts
                    if amounts in seen_spending:
                        continue
                    seen_spending.add(amounts)
                    parts = [
                        f"{amount}{color.value}"
                        for color, amount in zip(Color, amounts)
                        if amount
                    ]
                    word_spending_options.append({
                        "key": ",".join(str(amount) for amount in amounts),
                        "label": "Spend " + " + ".join(parts),
                        "selected": self._choices.word_mana_spending == amounts,
                    })
                word_payment_valid = bool(
                    len(word_spending_options) == 1
                    or any(item["selected"] for item in word_spending_options)
                )
        natural_selection_choice = (
            self.game.pending_natural_selection_choices[0]
            if self.game.pending_natural_selection_choices else None
        )
        library_search_choice = (
            self.game.pending_library_search_choices[0]
            if self.game.pending_library_search_choices else None
        )
        mask_source = self._card_by_id(self._choices.mask_source_id)
        can_choose_mask = bool(
            mask_source is not None
            and mask_source.controller_id == perspective.id
        )
        false_orders_choice = (
            self.game.pending_false_orders_choices[0]
            if self.game.pending_false_orders_choices else None
        )
        river_choice_required = bool(
            combat is not None
            and combat.step in {
                CombatStep.RIVER_DEFENDER_ASSIGNMENT,
                CombatStep.RIVER_ATTACKER_ASSIGNMENT,
            }
        )
        river_choice_player_id = (
            self.game.river_choice_player_id() if river_choice_required else None
        )
        can_choose_river = bool(
            river_choice_required and river_choice_player_id == perspective.id
        )
        fireball_card = self._fireball_card()
        choosing_fireball = fireball_card is not None
        choosing_fork = self._fork_original() is not None
        channel_maximum = self.game.maximum_channel_mana(perspective.id)
        channel_timing_open = bool(
            self.game.current_phase is not TurnPhase.UNTAP
            and (
                self.game.priority_player_index is None
                or self.game.players[self.game.priority_player_index].id
                == perspective.id
            )
            and not (
                combat is not None
                and combat.step in {
                    CombatStep.DECLARE_ATTACKERS,
                    CombatStep.DECLARE_BLOCKERS,
                    CombatStep.RIVER_DEFENDER_ASSIGNMENT,
                    CombatStep.RIVER_ATTACKER_ASSIGNMENT,
                }
            )
        )
        channel_choice_free = not (
            self.game.pending_cast
            or self.game.pending_activation
            or self.game.pending_prevention
            or self.game.pending_redirection
            or self.game.pending_turn_choice
            or draw_choice is not None
            or graveyard_return_choice is not None
            or graveyard_order_choice is not None
            or batch_conflict_choice is not None
            or timed_event_order_choice is not None
            or self.game.pending_kudzu_choices
            or self.game.pending_creature_copy_choices
            or self.game.pending_doppelganger_choices
            or self.game.pending_discard_choices
            or self.game.pending_library_discard_choices
            or self.game.pending_tomb_cleanup_choices
            or self.game.pending_balance is not None
            or lich_choice is not None
            or hand_reveal is not None
            or drain_power_choice is not None
            or power_sink_payment is not None
            or demonic_attorney_choice is not None
            or word_command_choice is not None
            or natural_selection_choice is not None
            or library_search_choice is not None
            or false_orders_choice is not None
            or river_choice_required
            or choosing_fireball
            or choosing_fork
            or self._choices.guardian_angel_packet_id is not None
            or untap_choice is not None
            or counter_rewind is not None
            or upkeep_land_choice is not None
        )
        can_channel = bool(
            channel_maximum and channel_timing_open and channel_choice_free
        )
        can_act = bool(
            channel_choice_free
            and self.game.player_has_action_priority(perspective.id)
        )
        can_choose_fireball = self._can_choose_fireball()
        fireball_targets: list[dict[str, Any]] = []
        for key in self._choices.fireball_target_keys:
            kind, identifier = key.split(":", 1)
            target = (
                self._card_by_id(UUID(identifier))
                if kind == "card"
                else self.game.player(identifier)
            )
            if target is not None:
                fireball_targets.append(
                    {"key": key, "name": target.name, "kind": kind}
                )
        fork_targets: list[dict[str, Any]] = []
        for key in self._choices.fork_target_keys:
            kind, identifier = key.split(":", 1)
            target = (
                self._card_by_id(UUID(identifier))
                if kind == "card" else self.game.player(identifier)
            )
            if target is not None:
                fork_targets.append({"key": key, "name": target.name, "kind": kind})
        legal_search_cards = (
            self.game.legal_library_search_cards()
            if library_search_choice is not None else ()
        )
        search_filter = self._choices.library_search_filter.casefold().strip()
        filtered_search_cards = sorted(
            (
                card for card in legal_search_cards
                if not search_filter or search_filter in card.name.casefold()
            ),
            key=lambda card: (card.name.casefold(), str(card.id)),
        )
        combat_response = bool(
            combat is not None
            and combat.step in {
                CombatStep.ATTACK_RESPONSE,
                CombatStep.ATTACKER_RESPONSE,
                CombatStep.BLOCKER_RESPONSE,
            }
        )
        pending_priority = bool(
            self.game.stack
            or self.game.batch_abilities
            or self.game.timed_events
            or self.game.event_opportunities
            or damage_incident is not None
            or destruction_incident is not None
            or self.game.pending_phase_advance is not None
            or self.game.pending_action_response is not None
            or combat_response
        )
        idle = not (
            self.game.pending_cast
            or self.game.pending_activation
            or self.game.pending_prevention
            or self.game.pending_redirection
            or self.game.pending_turn_choice
            or draw_choice is not None
            or graveyard_return_choice is not None
            or graveyard_order_choice is not None
            or self.game.pending_discard_choices
            or self.game.pending_library_discard_choices
            or self.game.pending_tomb_cleanup_choices
            or self.game.pending_balance is not None
            or lich_choice is not None
            or hand_reveal is not None
            or drain_power_choice is not None
            or power_sink_payment is not None
            or demonic_attorney_choice is not None
            or word_command_choice is not None
            or natural_selection_choice is not None
            or library_search_choice is not None
            or false_orders_choice is not None
            or choosing_fireball
            or self._choices.guardian_angel_packet_id is not None
            or untap_choice is not None
            or counter_rewind is not None
            or upkeep_land_choice is not None
            or doppelganger_choice is not None
            or river_choice_required
            or self._choices.mask_source_id is not None
            or pending_priority
        )
        perspective_is_active = self.perspective_index == self.game.active_player_index
        can_begin_attack = bool(
            idle
            and perspective_is_active
            and self.game.current_phase is TurnPhase.MAIN
            and combat is None
            and not self.game.attacks_this_turn
        )
        can_declare_attackers = bool(
            idle
            and perspective_is_active
            and combat is not None
            and combat.step is CombatStep.DECLARE_ATTACKERS
        )
        can_declare_blockers = bool(
            idle
            and combat is not None
            and combat.step is CombatStep.DECLARE_BLOCKERS
            and combat.defending_player_id == perspective.id
        )
        can_choose_false_orders = bool(
            false_orders_choice is not None
            and false_orders_choice.chooser_id == perspective.id
            and combat is not None
        )
        setting_blockers = can_declare_blockers or can_choose_false_orders
        choosing_combat_damage = self._combat_ui.choosing_damage_assignment(
            self.game
        )
        combat_damage_rows = (
            self._combat_ui.damage_assignment_state(self.game, perspective.id)
            if choosing_combat_damage else []
        )
        for row in combat_damage_rows:
            source = self._card_by_id(UUID(row["sourceId"]))
            row["sourceCard"] = self._card_data(source) if source is not None else {}
            for recipient in row["recipients"]:
                card = self._card_by_id(UUID(recipient["id"]))
                recipient["cardData"] = (
                    self._card_data(card) if card is not None else {}
                )
        pending_damage_assigners = (
            self._combat_ui.pending_damage_assignment_player_ids(self.game)
            if choosing_combat_damage else []
        )
        selected_draft_blockers, selected_draft_attackers = (
            self._combat_ui.selected_groups(self.game, self.selected_card_ids)
            if setting_blockers else ([], [])
        )
        drafted_attacker_count = (
            len(
                self._combat_ui.drafted_attackers(
                    self.game, self.selected_card_ids
                )
            )
            if can_declare_attackers else 0
        )
        drafted_blocker_count = (
            len(self._combat_ui.blocker_assignments(self.game))
            if can_declare_blockers else 0
        )
        river_assigned_count, river_choice_count = (
            self._combat_ui.river_assignment_progress(self.game)
            if river_choice_required else (0, 0)
        )
        selected_river_count = (
            len(
                self.selected_card_ids
                & set(combat.river_choice_card_ids)
            )
            if combat is not None else 0
        )
        turn_discard_required = bool(
            idle
            and perspective_is_active
            and self.game.current_phase is TurnPhase.DISCARD
            and self.game.required_discards(self.game.active_player)
        )
        can_advance = bool(
            idle
            and perspective_is_active
            and (
                combat is None
                or combat.step in {CombatStep.BLOCKER_RESPONSE, CombatStep.DAMAGE}
            )
            and not turn_discard_required
        )
        if combat is not None and combat.step is CombatStep.BLOCKER_RESPONSE:
            advance_label = "Advance to damage"
        elif combat is not None and combat.step is CombatStep.DAMAGE:
            advance_label = "Resolve combat damage"
        elif self.game.current_phase is TurnPhase.END:
            advance_label = "End turn"
        elif self.game.current_phase is not None:
            destination = self.game.current_phase.next
            advance_label = (
                f"Advance to {destination.value.title()}"
                if destination is not None
                else "End turn"
            )
        else:
            advance_label = "Advance"
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
            "timeVaultChoice": turn_choice is not None,
            "drawSkipChoice": draw_choice is not None,
            "drawSkipPlayer": (
                draw_choice.player_id if draw_choice is not None else ""
            ),
            "drawSkipMaximum": (
                draw_choice.maximum_skips if draw_choice is not None else 0
            ),
            "drawSkipTotal": (
                draw_choice.total_draws if draw_choice is not None else 0
            ),
            "graveyardReturnChoice": graveyard_return_choice is not None,
            "graveyardReturnPlayer": (
                graveyard_return_choice.player_id
                if graveyard_return_choice is not None else ""
            ),
            "graveyardReturnCards": (
                [self._card_data(card) for card in self.game.legal_graveyard_returns()]
                if graveyard_return_choice is not None else []
            ),
            "graveyardOrderChoice": graveyard_order_choice is not None,
            "graveyardOrderPlayer": (
                graveyard_order_choice.player_id
                if graveyard_order_choice is not None else ""
            ),
            "graveyardOrderCards": (
                [
                    self._card_data(self._card_by_id(card_id))
                    for card_id in graveyard_order_choice.card_ids_bottom_to_top
                    if self._card_by_id(card_id) is not None
                ]
                if graveyard_order_choice is not None else []
            ),
            "timedEventOrderChoice": timed_event_order_choice is not None,
            "timedEventOrderPlayer": (
                timed_event_order_choice.player_id
                if timed_event_order_choice is not None else ""
            ),
            "timedEventOrderItems": timed_event_order_items,
            "batchConflictChoice": batch_conflict_choice is not None,
            "batchConflictPlayer": (
                batch_conflict_choice.conflict.chooser_id
                if batch_conflict_choice is not None else ""
            ),
            "batchConflictPlayerName": (
                self.game.player(
                    batch_conflict_choice.conflict.chooser_id
                ).name
                if batch_conflict_choice is not None else ""
            ),
            "batchConflictReason": (
                batch_conflict_choice.conflict.reason
                if batch_conflict_choice is not None else ""
            ),
            "batchConflictTitle": (
                "Order conflicting destinations"
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "destination"
                else "Order tap and untap effects"
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "tapped_state"
                else "Order power modifiers"
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "power"
                else "Order hand and library effects"
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "hand_library"
                else "Order land-type settings"
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "land_type"
                else "Order Swords resolution"
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "swords_read"
                else "Order Aura attachment"
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "aura_entry"
                else "Order copying and source removal"
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "copy_entry"
                else "Order characteristic-dependent effects"
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value
                == "characteristics"
                else "Order extra-turn effects"
            ),
            "batchConflictExplanation": (
                "Once an effect moves the card, later effects aimed at its "
                "old location do nothing."
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "destination"
                else "Each transition is applied in order; the final effect "
                "normally determines whether the permanent remains tapped."
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "tapped_state"
                else "Power changes are reapplied first-to-last whenever the "
                "creature's underlying power changes."
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "power"
                else "Resolve these operations first-to-last; choices caused "
                "by one operation finish before the next operation begins."
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "hand_library"
                else "Apply these settings first-to-last. The most recent "
                "applicable setting determines the land's basic type."
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "land_type"
                else "Apply these effects first-to-last. Swords uses the "
                "creature's power and controller at its position in this order."
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "swords_read"
                else "Apply these effects first-to-last. An Aura can attach "
                "only if its target is still in play when its turn arrives."
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "aura_entry"
                else "Apply these effects first-to-last. A copy permanent can "
                "enter only if its chosen model is still in play when its "
                "turn arrives."
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value == "copy_entry"
                else "Apply these effects first-to-last. Global effects read "
                "card types, abilities, power, and toughness at their chosen "
                "position in the order."
                if batch_conflict_choice is not None
                and batch_conflict_choice.conflict.kind.value
                == "characteristics"
                else "Apply these effects first-to-last. Each new extra turn "
                "is placed immediately after the current turn, ahead of "
                "extra turns that were already scheduled."
            ),
            "batchConflictItems": batch_conflict_items,
            "demonicAttorneyChoice": demonic_attorney_choice is not None,
            "demonicAttorneyOpponent": (
                self.game.player(demonic_attorney_choice.opponent_id).name
                if demonic_attorney_choice is not None else ""
            ),
            "canChooseDemonicAttorney": bool(
                demonic_attorney_choice is not None
                and demonic_attorney_choice.opponent_id == perspective.id
            ),
            "wordCommandPending": word_command_choice is not None,
            "wordCommandDialog": bool(
                word_command_choice is not None
                and word_command_choice.stage in {"choose_card", "choose_payment"}
                and self._choices.word_command_card_id is None
            ),
            "wordCommandStage": (
                word_command_choice.stage if word_command_choice is not None else ""
            ),
            "wordCommandCommander": (
                self.game.player(word_command_choice.commander_id).name
                if word_command_choice is not None else ""
            ),
            "wordCommandOpponent": (
                self.game.player(word_command_choice.commanded_player_id).name
                if word_command_choice is not None else ""
            ),
            "canChooseWordCommand": word_command_can_choose,
            "wordCommandCards": (
                [
                    {
                        **self._card_data(card),
                        "commandable": card.id in word_commandable_ids,
                    }
                    for card in self.game.player(
                        word_command_choice.commanded_player_id
                    ).hand
                ]
                if word_command_can_choose
                and word_command_choice is not None
                and word_command_choice.stage == "choose_card"
                else []
            ),
            "wordCommandHasLegalPlay": bool(word_commandable_ids),
            "wordCommandCard": (
                self._card_data(word_command_card)
                if word_command_card is not None else {}
            ),
            "wordCommandCost": (
                self.game.spell_mana_cost(
                    word_command_card,
                    word_command_choice.x_value,
                    len(word_command_choice.targets) or 1,
                ).compact
                if word_command_card is not None
                and word_command_choice is not None else ""
            ),
            "wordCommandManaPool": (
                mana_text(self.game.player(word_command_choice.commanded_player_id))
                if word_command_choice is not None else ""
            ),
            "wordCommandManaOptions": word_mana_options,
            "wordCommandSpendingOptions": word_spending_options,
            "wordCommandPaymentValid": word_payment_valid,
            "naturalSelectionChoice": natural_selection_choice is not None,
            "naturalSelectionChooser": (
                self.game.player(natural_selection_choice.chooser_id).name
                if natural_selection_choice is not None else ""
            ),
            "naturalSelectionTarget": (
                self.game.player(natural_selection_choice.target_player_id).name
                if natural_selection_choice is not None else ""
            ),
            "canChooseNaturalSelection": bool(
                natural_selection_choice is not None
                and natural_selection_choice.chooser_id == perspective.id
            ),
            "naturalSelectionCards": (
                [
                    self._card_data(self._card_by_id(card_id))
                    for card_id in natural_selection_choice.card_ids_top_first
                    if self._card_by_id(card_id) is not None
                ]
                if natural_selection_choice is not None
                and natural_selection_choice.chooser_id == perspective.id
                else []
            ),
            "librarySearchPending": library_search_choice is not None,
            "librarySearchSource": (
                library_search_choice.source_name
                if library_search_choice is not None else ""
            ),
            "librarySearchChooser": (
                self.game.player(library_search_choice.chooser_id).name
                if library_search_choice is not None else ""
            ),
            "canSearchLibrary": bool(
                library_search_choice is not None
                and library_search_choice.chooser_id == perspective.id
            ),
            "librarySearchFilter": self._choices.library_search_filter,
            "librarySearchTotal": len(legal_search_cards),
            "librarySearchShown": len(filtered_search_cards),
            "librarySearchSelectedId": (
                str(self._choices.library_search_selected_id)
                if self._choices.library_search_selected_id is not None else ""
            ),
            "librarySearchCards": (
                [self._card_data(card) for card in filtered_search_cards]
                if library_search_choice is not None
                and library_search_choice.chooser_id == perspective.id
                else []
            ),
            "choosingFireball": choosing_fireball,
            "canChooseFireball": can_choose_fireball,
            "fireballX": self._choices.fireball_x_value,
            "fireballXMaximum": self._choices.fireball_x_maximum,
            "fireballTargets": fireball_targets,
            "fireballTargetCount": len(fireball_targets),
            "fireballDamageEach": (
                self._choices.fireball_x_value // len(fireball_targets)
                if fireball_targets else 0
            ),
            "choosingFork": choosing_fork,
            "canChooseFork": self._can_choose_fork(),
            "forkOriginalName": (
                self._fork_original().name if self._fork_original() is not None else ""
            ),
            "forkX": self._choices.fork_x_value,
            "forkTargets": fork_targets,
            "forkTargetCount": len(fork_targets),
            "effectDiscardRequired": discard_choice is not None,
            "libraryDiscardChoice": library_discard_choice is not None,
            "tombCleanupChoice": tomb_cleanup_choice is not None,
            "tombCleanupPlayer": (
                tomb_cleanup_choice.player_id
                if tomb_cleanup_choice is not None else ""
            ),
            "tombCleanupMarks": (
                [
                    {
                        "id": str(mark.id),
                        "label": self._tomb_mark_label(mark),
                    }
                    for mark in self.game.cyclopean_tomb_marks
                    if mark.id in tomb_cleanup_choice.mark_ids
                ]
                if tomb_cleanup_choice is not None
                and tomb_cleanup_choice.player_id == perspective.id else []
            ),
            "libraryDiscardPlayer": (
                library_discard_choice.player_id
                if library_discard_choice is not None else ""
            ),
            "libraryDiscardSource": (
                library_discard_choice.source_name
                if library_discard_choice is not None else ""
            ),
            "libraryDiscardCards": (
                [
                    {
                        **self._card_data(self._card_by_id(card_id)),
                        "toLibrary": card_id in set(
                            library_discard_choice.library_ids_bottom_to_top
                        ),
                    }
                    for card_id in library_discard_choice.card_ids
                    if self._card_by_id(card_id) is not None
                ]
                if library_discard_choice is not None
                and library_discard_choice.player_id == perspective.id else []
            ),
            "libraryDiscardTopCards": (
                [
                    self._card_data(self._card_by_id(card_id))
                    for card_id in library_discard_choice.library_ids_bottom_to_top
                    if self._card_by_id(card_id) is not None
                ]
                if library_discard_choice is not None
                and library_discard_choice.player_id == perspective.id else []
            ),
            "balanceRequired": balance_choice is not None,
            "lichChoiceRequired": lich_choice is not None,
            "lichChoicePlayer": (
                self.game.player(lich_choice.player_id).name
                if lich_choice is not None else ""
            ),
            "lichChoiceCount": lich_choice.amount if lich_choice is not None else 0,
            "canChooseLich": bool(
                lich_choice is not None and lich_choice.player_id == perspective.id
            ),
            "untapChoiceRequired": untap_choice is not None,
            "counterRewindRequired": counter_rewind is not None,
            "counterRewindCanChoose": bool(
                counter_rewind is not None
                and perspective.id == self.game.active_player.id
            ),
            "counterRewindCard": (
                counter_rewind.name if counter_rewind is not None else ""
            ),
            "counterRewindMaximum": self.game.maximum_counter_rewind(),
            "counterDamageRequired": counter_damage_choice is not None,
            "counterDamagePlayer": (
                counter_damage_choice.controller_id if counter_damage_choice else ""
            ),
            "counterDamageCard": (
                counter_damage_choice.creature_name if counter_damage_choice else ""
            ),
            "counterDamageAmount": (
                counter_damage_choice.absorbed_amount if counter_damage_choice else 0
            ),
            "counterDamageMaximum": (
                counter_damage_choice.maximum_payment if counter_damage_choice else 0
            ),
            "upkeepLandChoiceRequired": upkeep_land_choice is not None,
            "upkeepLandChoicePlayer": (
                self.game.player(upkeep_land_choice.chooser_id).name
                if upkeep_land_choice is not None else ""
            ),
            "upkeepLandChoiceSource": (
                upkeep_land_choice.source_name
                if upkeep_land_choice is not None else ""
            ),
            "kudzuChoiceRequired": kudzu_choice is not None,
            "kudzuChoicePlayer": (
                self.game.player(kudzu_choice.chooser_id).name
                if kudzu_choice is not None else ""
            ),
            "canChooseKudzu": bool(
                kudzu_choice is not None
                and kudzu_choice.chooser_id == perspective.id
            ),
            "cloneChoiceRequired": creature_copy_choice is not None,
            "cloneChoicePlayer": (
                self.game.player(creature_copy_choice.chooser_id).name
                if creature_copy_choice is not None else ""
            ),
            "creatureCopyChoiceSource": (
                self._card_by_id(creature_copy_choice.clone_id).name
                if creature_copy_choice is not None
                and self._card_by_id(creature_copy_choice.clone_id) is not None
                else "copy creature"
            ),
            "canChooseClone": bool(
                creature_copy_choice is not None
                and creature_copy_choice.chooser_id == perspective.id
            ),
            "doppelgangerChoiceRequired": doppelganger_choice is not None,
            "doppelgangerChoicePlayer": (
                self.game.player(doppelganger_choice.chooser_id).name
                if doppelganger_choice is not None else ""
            ),
            "canChooseDoppelganger": bool(
                doppelganger_choice is not None
                and doppelganger_choice.chooser_id == perspective.id
            ),
            "canChooseUpkeepLand": bool(
                upkeep_land_choice is not None
                and upkeep_land_choice.chooser_id == perspective.id
            ),
            "untapChoiceType": (
                untap_choice.card_type.value if untap_choice is not None else ""
            ),
            "untapChoiceCount": (
                min(
                    untap_choice.maximum
                    - self.game._selected_untap_count(
                        untap_choice, untap_choice.card_type
                    ),
                    len(self.game._legal_current_untap_ids(untap_choice)),
                )
                if untap_choice is not None else 0
            ),
            "canChooseUntap": bool(
                untap_choice is not None and untap_choice.player_id == perspective.id
            ),
            "balancePlayer": (
                self.game.player(balance_choice.player_id).name
                if balance_choice is not None else ""
            ),
            "balanceCount": balance_choice.amount if balance_choice is not None else 0,
            "balanceCategory": (
                balance_choice.category if balance_choice is not None else ""
            ),
            "balanceProgress": (
                f"Balance choice {len(self.game.pending_balance.selections) + 1} "
                f"of {len(self.game.pending_balance.choices)}"
                if self.game.pending_balance is not None else ""
            ),
            "canChooseBalance": bool(
                balance_choice is not None
                and balance_choice.player_id == perspective.id
            ),
            "effectDiscardPlayer": (
                self.game.player(discard_choice.player_id).name
                if discard_choice is not None else ""
            ),
            "effectDiscardCount": (
                min(
                    discard_choice.amount,
                    len(self.game.player(discard_choice.player_id).hand),
                )
                if discard_choice is not None else 0
            ),
            "canDiscard": (
                turn_discard_required
                or (
                    discard_choice is not None
                    and discard_choice.player_id == perspective.id
                )
            ),
            "canAdvance": can_advance and not choosing_combat_damage,
            "canUndoLandTap": undoable_land is not None,
            "undoLandTapLabel": (
                f"Undo {undoable_land.name} tap"
                if undoable_land is not None else "Undo land tap"
            ),
            "canChannel": can_channel,
            "channelMaximum": channel_maximum,
            "advanceLabel": advance_label,
            "canBeginAttack": can_begin_attack,
            "canDeclareAttackers": can_declare_attackers,
            "declareAttackersLabel": (
                f"Declare {drafted_attacker_count} "
                f"{'attacker' if drafted_attacker_count == 1 else 'attackers'}"
            ),
            "canSetAttackingBand": bool(
                can_declare_attackers
                and self._combat_ui.can_set_attacking_band(
                    self.game, self.selected_card_ids
                )
            ),
            "attackingBandActionLabel": (
                self._combat_ui.attacking_band_action_label(
                    self.selected_card_ids
                )
            ),
            "canDeclareBlockers": can_declare_blockers,
            "declareBlockersLabel": (
                f"Declare {drafted_blocker_count} "
                f"{'blocker' if drafted_blocker_count == 1 else 'blockers'}"
            ),
            "canSetBlocks": bool(selected_draft_blockers),
            "settingBlockers": setting_blockers,
            "blockAssignmentLabel": (
                (
                    "Make block"
                    if selected_draft_attackers else "Make not block"
                )
                if false_orders_choice is not None
                else "Set blocks" if selected_draft_attackers else "Clear blocks"
            ),
            "falseOrdersChoiceRequired": false_orders_choice is not None,
            "canChooseFalseOrders": can_choose_false_orders,
            "riverChoiceRequired": river_choice_required,
            "canChooseRiverSides": can_choose_river,
            "canPlaceRiverSide": bool(
                can_choose_river and selected_river_count
            ),
            "canConfirmRiverSides": bool(
                can_choose_river
                and river_choice_count > 0
                and river_assigned_count == river_choice_count
            ),
            "riverChoiceProgress": (
                f"{river_assigned_count} of {river_choice_count} placed"
                if river_choice_required else ""
            ),
            "riverChoicePlayer": (
                self.game.player(river_choice_player_id).name
                if river_choice_player_id is not None else ""
            ),
            "riverChoiceRole": (
                "defenders"
                if combat is not None
                and combat.step is CombatStep.RIVER_DEFENDER_ASSIGNMENT
                else "attackers"
                if river_choice_required else ""
            ),
            "falseOrdersPlayer": (
                self.game.player(false_orders_choice.chooser_id).name
                if false_orders_choice is not None else ""
            ),
            "falseOrdersBlocker": (
                self._card_by_id(false_orders_choice.blocker_id).name
                if false_orders_choice is not None
                and self._card_by_id(false_orders_choice.blocker_id) is not None
                else "departed creature"
                if false_orders_choice is not None else ""
            ),
            "choosingCombatDamage": choosing_combat_damage,
            "combatDamageAssignments": combat_damage_rows,
            "combatDamageValid": all(
                row["valid"] for row in combat_damage_rows
            ) if combat_damage_rows else False,
            "combatDamageCanAssign": bool(combat_damage_rows),
            "combatDamageWaitingFor": (
                self.game.player(pending_damage_assigners[0]).name
                if pending_damage_assigners else ""
            ),
            "priorityRequired": (
                pending_priority
                and lich_choice is None
                and false_orders_choice is None
            ),
            "contextActionsVisible": bool(
                can_begin_attack
                or undoable_land is not None
                or can_declare_attackers
                or can_declare_blockers
                or false_orders_choice is not None
                or river_choice_required
                or self.game.pending_cast is not None
                or self.game.pending_activation is not None
                or upkeep_payment_required
                or upkeep_sacrifice_required
                or pending_priority
                or balance_choice is not None
                or lich_choice is not None
                or untap_choice is not None
                or upkeep_land_choice is not None
                or choosing_fireball
                or draw_choice is not None
                or graveyard_return_choice is not None
                or graveyard_order_choice is not None
                or can_channel
                or doppelganger_choice is not None
                or self._choices.mask_source_id is not None
                or self._auto_pass_turns.get(perspective.id)
                   == self.game.turn_number
            ),
            "timeVaultPlayer": (
                turn_choice.player_name if turn_choice is not None else ""
            ),
            "timeVaultChoices": (
                [
                    {
                        "id": str(card.id),
                        "label": f"Skip turn for {card.name}",
                    }
                    for owner in self.game.players
                    for card in owner.battlefield
                    if card.id in turn_choice.vault_ids
                ]
                if turn_choice is not None
                else []
            ),
            "targeting": (
                self._can_choose_pending_cast()
                or self.game.pending_activation is not None
                or can_choose_fireball
                or self._choices.mask_target_required
            ),
            "canCancelTarget": bool(
                (
                    self.game.pending_cast is not None
                    and self._can_choose_pending_cast()
                    and self.game.pending_cast.word_command_id is None
                )
                or self.game.pending_activation is not None
                or self._choices.mask_target_required
            ),
            "choosingX": self._choices.x_card_id is not None,
            "maskCreatureChoiceRequired": bool(
                can_choose_mask
                and
                self._choices.mask_source_id is not None
                and self._choices.mask_creature_id is None
            ),
            "canChooseMask": can_choose_mask,
            "choosingMaskX": bool(
                can_choose_mask
                and self._choices.mask_creature_id is not None
                and not self._choices.mask_target_required
            ),
            "maskCreatureName": (
                self._card_by_id(self._choices.mask_creature_id).name
                if can_choose_mask
                and self._choices.mask_creature_id is not None
                and self._card_by_id(self._choices.mask_creature_id) is not None
                else ""
            ),
            "maskX": self._choices.mask_x_value,
            "maskXMaximum": self._choices.mask_x_maximum,
            "maskCreatureX": self._choices.mask_creature_x_value,
            "maskCreatureXMaximum": self._choices.mask_creature_x_maximum,
            "maskCreatureHasX": bool(
                self._choices.mask_creature_id is not None
                and self._card_by_id(self._choices.mask_creature_id) is not None
                and self._card_by_id(
                    self._choices.mask_creature_id
                ).definition.mana_cost.x_symbols
            ),
            "choosingLandType": self._choices.land_type_card_id is not None,
            "choosingTextWords": self._choices.word_target_id is not None,
            "textWordCardName": (
                self.game.pending_cast.spell.name
                if self._choices.word_target_id is not None
                and self.game.pending_cast is not None
                else ""
            ),
            "textWordTargetName": (
                self._card_by_id(self._choices.word_target_id).name
                if self._choices.word_target_id is not None
                and self._card_by_id(self._choices.word_target_id) is not None
                else ""
            ),
            "textWordKind": self._text_word_kind(),
            "textWordFromChoices": self._text_word_from_choices(),
            "textWordToChoices": self._text_word_to_choices(),
            "choosingMode": self._choices.mode_card_id is not None,
            "choosingDamageSource": self._choices.damage_source_card_id is not None,
            "damageSourceCardName": (
                self._card_by_id(self._choices.damage_source_card_id).name
                if self._choices.damage_source_card_id is not None
                and self._card_by_id(self._choices.damage_source_card_id) is not None
                else ""
            ),
            "damageSourceChoices": [
                {
                    "key": key,
                    "label": f"{name} — {amount} damage",
                }
                for key, name, amount in self.game.damage_source_choices(
                    word_command_choice.commanded_player_id
                    if word_command_choice is not None
                    and self._is_configuring_word_card()
                    else perspective.id
                )
            ],
            "modeChoices": (
                list(self._card_by_id(self._choices.mode_card_id).definition.casting_modes)
                if self._choices.mode_card_id is not None
                and self._card_by_id(self._choices.mode_card_id) is not None
                else []
            ),
            "modeCardName": (
                self._card_by_id(self._choices.mode_card_id).name
                if self._choices.mode_card_id is not None
                and self._card_by_id(self._choices.mode_card_id) is not None
                else ""
            ),
            "landTypeChoices": list(BASIC_LAND_SUBTYPES),
            "landTypeCardName": (
                self._card_by_id(self._choices.land_type_card_id).name
                if self._choices.land_type_card_id is not None
                and self._card_by_id(self._choices.land_type_card_id) is not None
                else ""
            ),
            "xValue": self._choices.x_value,
            "xMaximum": self._choices.x_maximum,
            "xMinimum": self._choices.x_minimum,
            "xIsAbility": self._choices.x_ability_index is not None,
            "xCardName": (
                self._card_by_id(self._choices.x_card_id).name
                if self._choices.x_card_id is not None
                and self._card_by_id(self._choices.x_card_id) is not None
                else ""
            ),
            "stack": [
                *[
                    (
                        f"{self._displayed_card_name(card)} "
                        f"(X={self.game.stack_spells[card.id].x_value})"
                        if card.definition.mana_cost.x_symbols
                        and not self.game.card_characteristics_are_hidden_from(
                            card, perspective.id
                        )
                        else self._displayed_card_name(card)
                    )
                    for card in self.game.stack
                ],
                *[
                    f"{ability.source_name} ability"
                    for ability in self.game.batch_abilities
                ],
            ],
            "stackCards": [
                {
                    "id": str(card.id),
                    "label": (
                        f"{self._displayed_card_name(card)} (X={self.game.stack_spells[card.id].x_value})"
                        if card.definition.mana_cost.x_symbols
                        and not self.game.card_characteristics_are_hidden_from(
                            card, perspective.id
                        )
                        else self._displayed_card_name(card)
                    ),
                    "legalTarget": bool(
                        (
                            self.game.pending_cast is None
                            or self._can_choose_pending_cast()
                        )
                        and card in self.game.legal_targets_for()
                    ),
                }
                for card in self.game.stack
            ],
            "stackTargetChoices": [
                {
                    "id": str(card.id),
                    "label": (
                        f"{self._displayed_card_name(card)} "
                        f"(X={self.game.stack_spells[card.id].x_value})"
                        if card.definition.mana_cost.x_symbols
                        and not self.game.card_characteristics_are_hidden_from(
                            card, perspective.id
                        )
                        else self._displayed_card_name(card)
                    ),
                }
                for card in self.game.stack
                if can_choose_stack_target
                and card in self.game.legal_targets_for()
            ],
            "choosingStackTarget": bool(
                can_choose_stack_target
                and any(
                    card in self.game.legal_targets_for()
                    for card in self.game.stack
                )
            ),
            "timedEvent": (
                self.game.timed_events[0].label
                if self.game.timed_events
                else ""
            ),
            "rulesEvents": [
                event.label for event in self.game.event_opportunities
            ],
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
            "canChoosePrevention": bool(
                self.game.pending_prevention is not None
                and self.game.pending_prevention.controller_id == perspective.id
            ),
            "preventionSource": (
                self.game.pending_prevention.source.name
                if self.game.pending_prevention is not None else ""
            ),
            "preventingLifeLoss": (
                self.game.pending_prevention is not None
                and self.game.pending_prevention.prevents_life_loss
            ),
            "choosingRedirection": self.game.pending_redirection is not None,
            "canChooseRedirection": bool(
                self.game.pending_redirection is not None
                and self.game.pending_redirection.controller_id == perspective.id
            ),
            "redirectionSource": (
                self.game.pending_redirection.source.name
                if self.game.pending_redirection is not None else ""
            ),
            "choosingRedirectionAmount": self._choices.redirection_packet_id is not None,
            "redirectionAmount": self._choices.redirection_amount,
            "redirectionMaximum": self._choices.redirection_maximum,
            "redirectionPacketChoices": (
                [
                    {
                        "id": str(packet.id),
                        "label": (
                            f"{packet.source_name}: {packet.remaining} to "
                            f"{packet.recipient_name}"
                        ),
                    }
                    for packet in self.game.legal_redirection_packets()
                ]
                if self.game.pending_redirection is not None
                else []
            ),
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
            "guardianAngelOptions": [
                {
                    "id": str(packet.id),
                    "label": (
                        f"{packet.source_name}: up to {maximum} to "
                        f"{packet.recipient_name}"
                    ),
                }
                for packet, maximum
                in self.game.guardian_angel_payment_options(perspective.id)
            ],
            "choosingGuardianAngelPayment": (
                self._choices.guardian_angel_packet_id is not None
            ),
            "guardianAngelAmount": self._choices.guardian_angel_amount,
            "guardianAngelMaximum": self._choices.guardian_angel_maximum,
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
            "upkeepCounterRedemption": bool(
                upkeep_payment_required
                and upkeep_event is not None
                and isinstance(upkeep_event.effect, CounterRedemptionUpkeepEffect)
            ),
            "partialUpkeepRequired": partial_upkeep_required,
            "counterPurchaseRequired": counter_purchase_required,
            "counterPurchasePlayer": (
                upkeep_event.affected_player_id
                if counter_purchase_required and upkeep_event is not None else ""
            ),
            "counterPurchaseCard": (
                upkeep_event.source_name
                if counter_purchase_required and upkeep_event is not None else ""
            ),
            "counterPurchaseMaximum": (
                self.game.maximum_upkeep_counter_purchase(upkeep_event.affected_player_id)
                if counter_purchase_required and upkeep_event is not None else 0
            ),
            "partialUpkeepPlayer": (
                upkeep_event.affected_player_id
                if partial_upkeep_required and upkeep_event is not None
                else ""
            ),
            "partialUpkeepMaximum": (
                upkeep_event.effect.maximum_payment
                if partial_upkeep_required and upkeep_event is not None
                else 0
            ),
            "partialUpkeepAffordable": (
                self.game.maximum_partial_upkeep_payment(
                    upkeep_event.affected_player_id
                )
                if partial_upkeep_required and upkeep_event is not None
                else 0
            ),
            "upkeepSacrificeRequired": upkeep_sacrifice_required,
            "upkeepSacrificePlayer": (
                upkeep_event.affected_player_id
                if upkeep_sacrifice_required and upkeep_event is not None
                else ""
            ),
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
            "priorityPassLabel": (
                "Pass interrupts"
                if self.game.interruptible_spell_id is not None
                else "Pass priority"
            ),
            "canAct": can_act,
            "hasPriority": (
                self.game.priority_player_index == self.perspective_index
            ),
            "autoPassingTurn": (
                self._auto_pass_turns.get(perspective.id)
                == self.game.turn_number
            ),
            "handRevealPending": hand_reveal is not None,
            "handRevealCanView": (
                hand_reveal is not None
                and hand_reveal.viewer_id == perspective.id
            ),
            "handRevealViewer": (
                self.game.player(hand_reveal.viewer_id).name
                if hand_reveal is not None else ""
            ),
            "handRevealTarget": (
                self.game.player(hand_reveal.target_id).name
                if hand_reveal is not None else ""
            ),
            "handRevealCards": (
                [self._card_data(card) for card in hand_reveal.cards]
                if hand_reveal is not None
                and hand_reveal.viewer_id == perspective.id
                else []
            ),
            "drainPowerChoice": drain_power_choice is not None,
            "drainPowerCanChoose": (
                drain_power_choice is not None
                and drain_power_choice.decision_maker_id == perspective.id
            ),
            "drainPowerChooser": (
                self.game.player(drain_power_choice.decision_maker_id).name
                if drain_power_choice is not None else ""
            ),
            "drainPowerLand": (
                drain_power_choice.land_name
                if drain_power_choice is not None else ""
            ),
            "drainPowerManaChoices": (
                [
                    {"color": color.value, "label": color.value * amount}
                    for color, amount in drain_power_choice.mana_options
                ]
                if drain_power_choice is not None else []
            ),
            "powerSinkPayment": power_sink_payment is not None,
            "powerSinkCanChoose": (
                power_sink_payment is not None
                and power_sink_payment.payer_id == perspective.id
            ),
            "powerSinkPayer": (
                self.game.player(power_sink_payment.payer_id).name
                if power_sink_payment is not None else ""
            ),
            "powerSinkRemaining": (
                power_sink_payment.remaining
                if power_sink_payment is not None else 0
            ),
            "powerSinkManaChoices": (
                [
                    {
                        "landId": str(land.id),
                        "abilityIndex": ability_index,
                        "label": f"{land.name} → {color.value * amount}",
                    }
                    for land, ability_index, color, amount
                    in self.game.power_sink_mana_choices()
                ]
                if power_sink_payment is not None else []
            ),
            "perspective": self._player_data(perspective, reveal_hand=True),
            "opponent": self._player_data(opponent, reveal_hand=False),
            "attackers": [
                {
                    "id": str(card.id),
                    "label": (
                        "Face-down creature"
                        if self.game.card_characteristics_are_hidden_from(
                            card, perspective.id
                        )
                        else card.name
                    ),
                }
                for card in (combat.attackers if combat else [])
            ],
        }

    def _player_data(
        self, player: PlayerState, *, reveal_hand: bool
    ) -> dict[str, Any]:
        battlefield_roots = [
            card for card in player.battlefield
            if card.enchanted_card_id is None
        ]
        river_order = {"L": 0, "": 1, "R": 2}
        camouflage_order = (
            {
                card.id: index
                for index, card in enumerate(self.game.combat.attackers)
                if card.id in self.game.combat.camouflaged_attacker_ids
            }
            if self.game.combat is not None
            else {}
        )
        battlefield_nonlands = sorted(
            (
                card
                for card in battlefield_roots
                if (
                    CardType.LAND not in card.definition.card_types
                    or card.id in camouflage_order
                )
            ),
            key=lambda card: (
                river_order.get(self._river_side_label(card), 1),
                CardType.CREATURE not in self.game.card_types(card),
                0 if card.id in camouflage_order else 1,
                camouflage_order.get(card.id, 0),
            ),
        )
        battlefield_lands = sorted(
            (
                card
                for card in battlefield_roots
                if (
                    CardType.LAND in card.definition.card_types
                    and card.id not in camouflage_order
                )
            ),
            key=lambda card: (
                river_order.get(self._river_side_label(card), 1),
                0
                if self._displayed_card_name(card) in _BASIC_LAND_ORDER
                else 1,
                _BASIC_LAND_ORDER.get(
                    self._displayed_card_name(card),
                    len(_BASIC_LAND_ORDER),
                ),
                self._displayed_card_name(card).casefold(),
            ),
        )
        land_columns: list[dict[str, Any]] = []
        for land in battlefield_lands:
            displayed_name = self._displayed_card_name(land)
            if (
                not land_columns
                or land_columns[-1]["name"] != displayed_name
                or land_columns[-1]["side"] != self._river_side_label(land)
                or len(land_columns[-1]["cards"]) == 4
            ):
                land_columns.append({
                    "name": displayed_name,
                    "side": self._river_side_label(land),
                    "cards": [],
                })
            land_columns[-1]["cards"].append(self._card_data(land))
        return {
            "id": player.id,
            "name": player.name,
            "life": player.life,
            "mana": mana_text(player),
            "legalTarget": (
                bool(
                    (
                        self.game.pending_cast is None
                        or self._can_choose_pending_cast()
                    )
                    and player in self.game.legal_player_targets_for()
                )
                or self._can_choose_fireball()
                or bool(
                    self._can_choose_fork()
                    and player in self.game.fork_copy_target_options(
                        self._fork_original()
                    )[1]
                )
            ),
            "selectedTarget": (
                f"player:{player.id}" in self._choices.fireball_target_keys
                or f"player:{player.id}" in self._choices.fork_target_keys
            ),
            "libraryCount": len(player.library),
            "handCount": len(player.hand),
            "hand": [self._card_data(card) for card in player.hand]
            if reveal_hand
            else [],
            "battlefield": [self._card_data(card) for card in player.battlefield],
            "battlefieldNonlands": [
                self._card_data(card) for card in battlefield_nonlands
            ],
            "battlefieldLands": [
                self._card_data(card) for card in battlefield_lands
            ],
            "battlefieldLandColumns": land_columns,
            "graveyard": [
                self._card_data(card) for card in player.graveyard
            ],
            "graveyardCount": len(player.graveyard),
            "exile": [self._card_data(card) for card in player.exile],
            "exileCount": len(player.exile),
            "ante": [self._card_data(card) for card in player.ante],
            "anteCount": len(player.ante),
        }

    def _tomb_mark_label(self, mark: Any) -> str:
        land = self._card_by_id(mark.land_id)
        land_name = (
            self._displayed_card_name(land)
            if land is not None
            else "Departed land"
        )
        siblings = sorted(
            (
                item for item in self.game.cyclopean_tomb_marks
                if item.effect_id == mark.effect_id
                and item.land_id == mark.land_id
            ),
            key=lambda item: item.sequence,
        )
        if len(siblings) == 1:
            return land_name
        position = siblings.index(mark) + 1
        age = "oldest" if position == 1 else "newest" if position == len(siblings) else ""
        suffix = f" ({age})" if age else ""
        return f"{land_name} — mire {position} of {len(siblings)}{suffix}"

    def _card_data(self, card: Card) -> dict[str, Any]:
        perspective_id = self.game.players[self.perspective_index].id
        characteristics_hidden = self.game.card_characteristics_are_hidden_from(
            card, perspective_id
        )
        face_down_hidden = card.is_face_down and characteristics_hidden
        copied_characteristics_hidden = (
            not card.is_face_down and characteristics_hidden
        )
        background, foreground = self._card_colors(card)
        image_urls = image_urls_for(card.name)
        current_card_types = self.game.card_types(card)
        displayed_name = self._displayed_card_name(card)
        displayed_subtypes = (
            self.game.land_subtypes(card)
            if card.zone is Zone.BATTLEFIELD
            and CardType.LAND in card.definition.card_types
            else card.definition.subtypes
        )
        enchanted_card = next(
            (
                permanent
                for player in self.game.players
                for permanent in player.battlefield
                if permanent.id == card.enchanted_card_id
            ),
            None,
        )
        balance_choice = (
            self.game.pending_balance.current_choice
            if self.game.pending_balance is not None
            else None
        )
        lich_choice = (
            self.game.pending_lich_choices[0]
            if self.game.pending_lich_choices else None
        )
        upkeep_sacrifices = (
            self.game.legal_upkeep_sacrifices(
                self.game.timed_events[0].affected_player_id
            )
            if self.game.timed_events
            and isinstance(
                self.game.timed_events[0].effect,
                UpkeepCreatureSacrificeEffect,
            )
            else []
        )
        upkeep_land_choice = self.game.pending_upkeep_land_loss
        kudzu_choice = (
            self.game.pending_kudzu_choices[0]
            if self.game.pending_kudzu_choices else None
        )
        creature_copy_choice = (
            self.game.pending_creature_copy_choices[0]
            if self.game.pending_creature_copy_choices else None
        )
        doppelganger_choice = (
            self.game.pending_doppelganger_choices[0]
            if self.game.pending_doppelganger_choices else None
        )
        combat_role, combat_label, combat_detail = self._combat_ui.card_status(
            self.game, card
        )
        attacker_selection_active = self._combat_ui.is_drafting_attackers(
            self.game, self.game.players[self.perspective_index].id
        )
        river_choice_active = self._combat_ui.is_choosing_river_sides(
            self.game, perspective_id
        )
        river_side = self._river_side_label(card)
        mask = self._card_by_id(self._choices.mask_source_id)
        mask_choice_active = bool(
            mask is not None
            and mask.controller_id == perspective_id
            and
            self._choices.mask_source_id is not None
            and self._choices.mask_creature_id is None
        )
        mask_choice_eligible = False
        if mask_choice_active and card.zone is Zone.HAND:
            if mask is not None:
                try:
                    mask_choice_eligible = card in (
                        self.game.legal_illusionary_mask_creatures(
                            perspective_id,
                            mask,
                            self._choices.mask_ability_index,
                        )
                    )
                except (ValueError, RuntimeError):
                    mask_choice_eligible = False
        mask_target_eligible = False
        if self._choices.mask_target_required:
            masked_creature = self._card_by_id(
                self._choices.mask_creature_id
            )
            if masked_creature is not None:
                mask_target_eligible = card in self.game.legal_targets_for(
                    masked_creature
                )
        result = {
            "id": str(card.id),
            "name": displayed_name,
            "isToken": card.is_token,
            "isFaceDown": card.is_face_down,
            "faceDownHidden": face_down_hidden,
            "copiedCharacteristicsHidden": copied_characteristics_hidden,
            "background": background,
            "foreground": foreground,
            "artCropUrl": image_urls.get("art_crop", ""),
            "fullCardUrl": image_urls.get("full_card", ""),
            "tapped": card.tapped,
            "actionEnabled": self.game.player_has_action_priority(
                perspective_id
            ),
            "attackerSelectionActive": attacker_selection_active,
            "attackerEligible": bool(
                attacker_selection_active
                and self.game.can_declare_attacker(card)
            ),
            "riverChoiceActive": river_choice_active,
            "riverChoiceEligible": self._combat_ui.river_selectable_card(
                self.game, perspective_id, card
            ),
            "riverSide": river_side,
            "maskChoiceActive": mask_choice_active,
            "maskChoiceEligible": mask_choice_eligible,
            "selected": (
                card.id in self.selected_card_ids
                or f"card:{card.id}" in self._choices.fireball_target_keys
                or f"card:{card.id}" in self._choices.fork_target_keys
            ),
            "legalTarget": (
                bool(
                    (
                        self.game.pending_cast is None
                        or self._can_choose_pending_cast()
                    )
                    and card in self.game.legal_targets_for()
                )
                or mask_target_eligible
                or card in self._fireball_legal_cards()
                or card in self._fork_legal_cards()
                or bool(
                    kudzu_choice is not None
                    and card.id in kudzu_choice.candidate_ids
                )
                or bool(
                    creature_copy_choice is not None
                    and card.id in creature_copy_choice.candidate_ids
                )
                or bool(
                    doppelganger_choice is not None
                    and card.id in doppelganger_choice.candidate_ids
                )
            ),
            "balanceEligible": bool(
                balance_choice is not None
                and card.id in balance_choice.candidate_ids
                and card in self.game.player(balance_choice.player_id).cards_in(
                    Zone.HAND
                    if balance_choice.category == "hand"
                    else Zone.BATTLEFIELD
                )
            ),
            "lichEligible": bool(
                lich_choice is not None
                and card.id in lich_choice.candidate_ids
                and card.zone is Zone.BATTLEFIELD
            ),
            "upkeepSacrificeEligible": card in upkeep_sacrifices,
            "upkeepLandChoiceEligible": bool(
                upkeep_land_choice is not None
                and card.id in upkeep_land_choice.candidate_ids
            ),
            "combatRole": combat_role,
            "combatLabel": combat_label,
            "combatDetail": combat_detail,
            "isCreature": CardType.CREATURE in current_card_types,
            "power": (
                self.game.creature_power(card)
                if CardType.CREATURE in current_card_types
                and card.zone is Zone.BATTLEFIELD
                else "*"
                if card.definition.variable_stats is not None
                else card.definition.power
                if card.definition.power is not None
                else -1
            ),
            "toughness": (
                self.game.creature_toughness(card)
                if CardType.CREATURE in current_card_types
                and card.zone is Zone.BATTLEFIELD
                else "*"
                if card.definition.variable_stats is not None
                else card.definition.toughness
                if card.definition.toughness is not None
                else -1
            ),
            "damage": card.damage,
            "counters": [
                {"name": name, "amount": amount}
                for name, amount in card.counters.items()
                if amount
            ],
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
                        current_card_types, key=lambda card_type: card_type.value
                    )),
                )
            )
            + (
                " — " + " ".join(displayed_subtypes)
                if displayed_subtypes
                else ""
            ),
            "abilities": ", ".join(
                ability.value
                for ability in sorted(
                    self.game.creature_abilities(card)
                    if CardType.CREATURE in current_card_types
                    and card.zone is Zone.BATTLEFIELD
                    else card.definition.abilities,
                    key=lambda ability: ability.value,
                )
            ),
            "rulesText": self._displayed_rules_text(card),
            "attachedTo": (
                self._displayed_card_name(enchanted_card)
                if enchanted_card is not None
                else ""
            ),
            "attachments": [
                (
                    self._concealed_attachment_data(attachment)
                    if face_down_hidden
                    else self._card_data(attachment)
                )
                for owner in self.game.players
                for attachment in owner.battlefield
                if attachment.enchanted_card_id == card.id
            ],
            "activatedAbilities": [
                {
                    "index": index,
                    "label": ability.label,
                    "enabled": (
                        (
                            card.owner_id
                            if isinstance(
                                ability, ActivatedRedirectDamageAbility
                            )
                            and ability.owner_activates
                            else card.controller_id
                        )
                        is not None
                        and self.game.can_activate_ability(
                            (
                                card.owner_id
                                if isinstance(
                                    ability, ActivatedRedirectDamageAbility
                                )
                                and ability.owner_activates
                                else card.controller_id
                            ),
                            card,
                            index,
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
        if face_down_hidden:
            result.update(
                {
                    "name": "Face-down creature",
                    "background": "#343943",
                    "foreground": "#f1f3f5",
                    "artCropUrl": "",
                    "fullCardUrl": "",
                    "manaCost": "",
                    "typeLine": "Creature",
                    "abilities": "",
                    "rulesText": (
                        "Its identity and characteristics are concealed."
                    ),
                    "power": "?",
                    "toughness": "?",
                    "activatedAbilities": [],
                    "combatDetail": "",
                    "attachedTo": "",
                }
            )
            status = ["Face down; only its known game state is shown."]
            if card.tapped:
                status.append("Tapped")
            if card.counters:
                counters = ", ".join(
                    f"{amount} {name}"
                    for name, amount in card.counters.items()
                    if amount
                )
                if counters:
                    status.append(f"Counters: {counters}")
            if result["attachments"]:
                status.append(
                    f"Attached enchantments: {len(result['attachments'])}"
                )
            result["previewStatus"] = "\n".join(status)
            return result
        if copied_characteristics_hidden:
            printed = card.printed_definition or card.definition
            printed_images = image_urls_for(printed.name)
            result.update(
                {
                    "name": printed.name,
                    "background": "#79b9dc",
                    "foreground": "#102b3a",
                    "artCropUrl": printed_images.get("art_crop", ""),
                    "fullCardUrl": printed_images.get("full_card", ""),
                    "manaCost": printed.mana_cost.compact,
                    "typeLine": " ".join(
                        (
                            *printed.supertypes,
                            *(
                                card_type.value
                                for card_type in sorted(
                                    printed.card_types,
                                    key=lambda item: item.value,
                                )
                            ),
                        )
                    )
                    + (
                        " — " + " ".join(printed.subtypes)
                        if printed.subtypes else ""
                    ),
                    "abilities": "",
                    "rulesText": printed.rules_text,
                    "power": "?",
                    "toughness": "?",
                    "activatedAbilities": [],
                    "combatDetail": "",
                }
            )
            result["previewStatus"] = (
                "Copied a face-down creature; its copied power, toughness, "
                "and abilities are concealed."
            )
            return result
        preview_status = []
        if card.zone is Zone.BATTLEFIELD:
            if result["isCreature"]:
                preview_status.append(
                    f"Current power/toughness: {result['power']}/{result['toughness']}"
                )
            if card.damage:
                preview_status.append(f"Damage marked: {card.damage}")
            if card.tapped:
                preview_status.append("Tapped")
            if enchanted_card is not None:
                preview_status.append(
                    f"Enchanting {self._displayed_card_name(enchanted_card)}"
                )
            if card.chosen_land_subtype is not None:
                preview_status.append(
                    f"Chosen land type: {card.chosen_land_subtype}"
                )
            if displayed_name != card.name:
                preview_status.append(f"Current name: {displayed_name}")
            if card.counters:
                counters = ", ".join(
                    f"{amount} {name}" for name, amount in card.counters.items() if amount
                )
                if counters:
                    preview_status.append(f"Counters: {counters}")
            if combat_detail:
                preview_status.append(combat_detail)
            if river_side:
                bank = "left" if river_side == "L" else "right"
                preview_status.append(f"Raging River: {bank} side")
        if result["rulesText"] != card.definition.rules_text:
            preview_status.append(result["rulesText"].split("\n\n")[-1])
        result["previewStatus"] = "\n".join(preview_status)
        return result

    def _concealed_attachment_data(self, attachment: Card) -> dict[str, Any]:
        """Show that an Aura exists without disclosing its face."""

        result = self._card_data(attachment)
        result.update(
            {
                "name": "Face-down enchantment",
                "background": "#343943",
                "foreground": "#f1f3f5",
                "artCropUrl": "",
                "fullCardUrl": "",
                "manaCost": "",
                "typeLine": "Enchantment",
                "abilities": "",
                "rulesText": (
                    "An enchantment is attached here, but its identity is "
                    "concealed with the creature."
                ),
                "power": -1,
                "toughness": -1,
                "activatedAbilities": [],
                "attachedTo": "Face-down creature",
                "attachments": [],
                "previewStatus": "Attached to a face-down creature.",
            }
        )
        return result

    def _displayed_card_name(self, card: Card) -> str:
        """Return a land's current rules name for battlefield presentation."""

        perspective_id = self.game.players[self.perspective_index].id
        if self.game.card_characteristics_are_hidden_from(card, perspective_id):
            return "Face-down creature"

        if (
            card.zone is Zone.BATTLEFIELD
            and CardType.LAND in card.definition.card_types
        ):
            subtypes = self.game.land_subtypes(card)
            if len(subtypes) == 1 and subtypes[0] in _BASIC_LAND_ORDER:
                return subtypes[0]
        return card.name

    def _river_side_label(self, card: Card) -> str:
        side = self._combat_ui.river_side_for(self.game, card)
        return side.value if side is not None else ""

    @staticmethod
    def _displayed_rules_text(card: Card) -> str:
        changes = [
            f"{printed.name.lower()} -> {current.name.lower()}"
            for printed, current in card.color_word_changes.items()
        ]
        changes.extend(
            f"{printed} -> {current}"
            for printed, current in card.land_word_changes.items()
        )
        if not changes:
            return card.definition.rules_text
        summary = "; ".join(changes)
        return f"{card.definition.rules_text}\n\nCurrent text changes: {summary}."

    def _card_colors(self, card: Card) -> tuple[str, str]:
        current_colors = self.game.card_colors(card)
        color = None
        if len(current_colors) == 1:
            color = next(iter(current_colors))
        elif card.color_override is None:
            color = card.definition.produces_mana
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
