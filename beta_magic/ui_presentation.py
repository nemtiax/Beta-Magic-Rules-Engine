"""Read-only QML presentation building for the hotseat UI."""

from __future__ import annotations

from typing import Any
from uuid import UUID
from .abilities import ActivatedRedirectDamageAbility
from .cards import Card
from .effects import (
    OptionalUpkeepPaymentEffect,
    UpkeepCostEffect,
    UpkeepCreatureSacrificeEffect,
)
from .game import PlayerState
from .types import BASIC_LAND_SUBTYPES, CardType, CombatStep, TurnPhase, Zone


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

    def build(self) -> dict[str, Any]:
        perspective = self.game.players[self.perspective_index]
        opponent = self.game.players[1 - self.perspective_index]
        combat = self.game.combat
        self._combat_ui.sync(self.game)
        upkeep_event = (
            self.game.timed_events[0] if self.game.timed_events else None
        )
        upkeep_payment_required = bool(
            upkeep_event is not None
            and isinstance(
                upkeep_event.effect,
                (UpkeepCostEffect, OptionalUpkeepPaymentEffect),
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
        damage_incident = self.game.pending_damage
        destruction_incident = self.game.pending_destruction
        turn_choice = self.game.pending_turn_choice
        discard_choice = (
            self.game.pending_discard_choices[0]
            if self.game.pending_discard_choices else None
        )
        balance_choice = (
            self.game.pending_balance.current_choice
            if self.game.pending_balance is not None
            else None
        )
        untap_choice = self.game.pending_untap_choice
        upkeep_land_choice = self.game.pending_upkeep_land_loss
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
            or combat_response
        )
        idle = not (
            self.game.pending_cast
            or self.game.pending_activation
            or self.game.pending_prevention
            or self.game.pending_redirection
            or self.game.pending_turn_choice
            or self.game.pending_discard_choices
            or self.game.pending_balance is not None
            or untap_choice is not None
            or upkeep_land_choice is not None
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
            if can_declare_blockers else ([], [])
        )
        turn_discard_required = bool(
            idle
            and perspective_is_active
            and self.game.current_phase is TurnPhase.DISCARD
            and self.game.active_player.discard_required
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
            "effectDiscardRequired": discard_choice is not None,
            "balanceRequired": balance_choice is not None,
            "untapChoiceRequired": untap_choice is not None,
            "upkeepLandChoiceRequired": upkeep_land_choice is not None,
            "upkeepLandChoicePlayer": (
                self.game.player(upkeep_land_choice.chooser_id).name
                if upkeep_land_choice is not None else ""
            ),
            "upkeepLandChoiceSource": (
                upkeep_land_choice.source_name
                if upkeep_land_choice is not None else ""
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
            "advanceLabel": advance_label,
            "canBeginAttack": can_begin_attack,
            "canDeclareAttackers": can_declare_attackers,
            "canSetAttackingBand": bool(
                can_declare_attackers and len(self.selected_card_ids) >= 2
            ),
            "attackingBandActionLabel": (
                self._combat_ui.attacking_band_action_label(
                    self.selected_card_ids
                )
            ),
            "canDeclareBlockers": can_declare_blockers,
            "canSetBlocks": bool(selected_draft_blockers),
            "settingBlockers": can_declare_blockers,
            "blockAssignmentLabel": (
                "Set blocks" if selected_draft_attackers else "Clear blocks"
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
            "priorityRequired": pending_priority,
            "contextActionsVisible": bool(
                can_begin_attack
                or can_declare_attackers
                or can_declare_blockers
                or self.game.pending_cast is not None
                or self.game.pending_activation is not None
                or upkeep_payment_required
                or upkeep_sacrifice_required
                or pending_priority
                or balance_choice is not None
                or untap_choice is not None
                or upkeep_land_choice is not None
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
                self.game.pending_cast is not None
                or self.game.pending_activation is not None
            ),
            "choosingX": self._choices.x_card_id is not None,
            "choosingLandType": self._choices.land_type_card_id is not None,
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
                    perspective.id
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
            "stackCards": [
                {
                    "id": str(card.id),
                    "label": (
                        f"{card.name} (X={self.game.stack_spells[card.id].x_value})"
                        if card.definition.mana_cost.x_symbols
                        else card.name
                    ),
                    "legalTarget": card in self.game.legal_targets_for(),
                }
                for card in self.game.stack
            ],
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
            "choosingRedirection": self.game.pending_redirection is not None,
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
            "hasPriority": (
                self.game.priority_player_index == self.perspective_index
            ),
            "autoPassingTurn": (
                self._auto_pass_turns.get(perspective.id)
                == self.game.turn_number
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
        battlefield_roots = [
            card for card in player.battlefield
            if card.enchanted_card_id is None
        ]
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
                for card in battlefield_roots
                if CardType.LAND not in card.definition.card_types
            ],
            "battlefieldLands": [
                self._card_data(card)
                for card in battlefield_roots
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
        current_card_types = self.game.card_types(card)
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
        combat_role, combat_label, combat_detail = self._combat_ui.card_status(
            self.game, card
        )
        return {
            "id": str(card.id),
            "name": card.name,
            "background": background,
            "foreground": foreground,
            "tapped": card.tapped,
            "selected": card.id in self.selected_card_ids,
            "legalTarget": card in self.game.legal_targets_for(),
            "balanceEligible": bool(
                balance_choice is not None
                and card.id in balance_choice.candidate_ids
                and card in self.game.player(balance_choice.player_id).cards_in(
                    Zone.HAND
                    if balance_choice.category == "hand"
                    else Zone.BATTLEFIELD
                )
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
                if CardType.CREATURE in current_card_types
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
            "rulesText": card.definition.rules_text,
            "attachedTo": enchanted_card.name if enchanted_card else "",
            "attachments": [
                self._card_data(attachment)
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

    def _combat_card_status(self, card: Card) -> tuple[str, str, str]:
        """Compatibility delegate for presentation-focused extensions."""

        return self._combat_ui.card_status(self.game, card)

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
