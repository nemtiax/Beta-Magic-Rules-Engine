"""Damage and destruction incident coordination for the game-state facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from .abilities import (
    ActivatedPreventDamageAbility,
    ActivatedRedirectDamageAbility,
    ActivatedRegenerationAbility,
)
from .cards import Card
from .damage import (
    DamageIncident,
    DamageIncidentKind,
    DamagePacket,
    DamageRecipientKind,
    DamageResolutionStep,
)
from .destruction import DestructionResolutionStep
from .events import DamageEvent
from .rule_events import RuleEventKind, RuleEventOpportunity
from .types import CardType, Color, CombatStep, Zone

if TYPE_CHECKING:
    from .game import PlayerState


@dataclass(slots=True)
class PendingPrevention:
    """A prevention spell or ability assigning points to damage packets."""

    source: Card
    controller_id: str
    remaining: int | None
    ability_index: int | None = None
    recipient_id: UUID | str | None = None
    source_color: Color | None = None
    controller_only: bool = False
    paid: bool = False


@dataclass(slots=True)
class PendingRedirection:
    """A Jade Monolith-style ability waiting for a damage packet."""

    source: Card
    controller_id: str
    ability_index: int


class DamageDestructionMixin:
    """Coordinate damage packets, response windows, and destruction incidents."""

    __slots__ = ()

    def _validate_redirection_activation(
        self, player_id: str, card: Card, ability_index: int
    ) -> tuple[PlayerState, ActivatedRedirectDamageAbility]:
        incident = self.pending_damage
        if (
            incident is None
            or incident.step is not DamageResolutionStep.REDIRECTION
        ):
            raise RuntimeError(
                "damage redirection can only be used during the redirection window"
            )
        player = self.player(player_id)
        if (
            self.priority_player_index is None
            or player is not self.players[self.priority_player_index]
        ):
            raise RuntimeError(
                f"{self.players[self.priority_player_index].name} has priority"
            )
        ability = self.activated_abilities(card)[ability_index]
        if not isinstance(ability, ActivatedRedirectDamageAbility):
            raise ValueError("that ability does not redirect damage")
        in_play = any(card in candidate.battlefield for candidate in self.players)
        authorized_id = card.owner_id if ability.owner_activates else card.controller_id
        if not in_play or authorized_id != player_id:
            raise ValueError("that player cannot activate this redirection ability")
        if not player.mana_pool.can_pay(ability.mana_cost):
            raise RuntimeError(f"not enough mana to activate {card.name}")
        if not self._legal_redirection_packets(card, player, ability):
            raise RuntimeError("there is no eligible damage to redirect")
        return player, ability

    def _legal_redirection_packets(
        self,
        source: Card,
        player: PlayerState,
        ability: ActivatedRedirectDamageAbility,
    ) -> list[DamagePacket]:
        assert self.pending_damage is not None
        if ability.bidirectional_with_owner:
            return [
                packet
                for packet in self.pending_damage.packets
                if packet.remaining
                and (
                    (
                        packet.recipient_kind is DamageRecipientKind.CREATURE
                        and packet.recipient_id == source.id
                    )
                    or (
                        packet.recipient_kind is DamageRecipientKind.PLAYER
                        and packet.recipient_id == player.id
                    )
                )
            ]
        return [
            packet
            for packet in self.pending_damage.packets
            if packet.remaining
            and packet.recipient_kind is DamageRecipientKind.CREATURE
            and (not ability.source_only or packet.recipient_id == source.id)
        ]

    def legal_redirection_packets(self) -> list[DamagePacket]:
        if self.pending_redirection is None or self.pending_damage is None:
            return []
        pending = self.pending_redirection
        ability = self.activated_abilities(pending.source)[
            pending.ability_index
        ]
        assert isinstance(ability, ActivatedRedirectDamageAbility)
        return self._legal_redirection_packets(
            pending.source, self.player(pending.controller_id), ability
        )

    def redirect_damage(
        self, player_id: str, packet_id: UUID, amount: int | None = None
    ) -> int:
        pending = self.pending_redirection
        incident = self.pending_damage
        if pending is None or incident is None:
            raise RuntimeError("there is no pending damage redirection")
        if pending.controller_id != player_id:
            raise ValueError("only the ability's controller may choose")
        packet = next(
            (
                candidate
                for candidate in self.legal_redirection_packets()
                if candidate.id == packet_id
            ),
            None,
        )
        if packet is None:
            raise ValueError("that damage packet cannot be redirected")
        ability = self.activated_abilities(pending.source)[
            pending.ability_index
        ]
        assert isinstance(ability, ActivatedRedirectDamageAbility)
        player = self.player(player_id)
        player.mana_pool.pay(ability.mana_cost)
        if amount is None:
            amount = packet.remaining
        if amount < 1 or amount > packet.remaining:
            raise ValueError("redirected amount must fit within the damage packet")
        if not ability.any_amount and amount != packet.remaining:
            raise ValueError("this ability must redirect all remaining damage")
        packet.redirected += amount
        if ability.bidirectional_with_owner:
            to_creature = packet.recipient_kind is DamageRecipientKind.PLAYER
            recipient_kind = (
                DamageRecipientKind.CREATURE
                if to_creature
                else DamageRecipientKind.PLAYER
            )
            recipient_id = pending.source.id if to_creature else player.id
            recipient_name = pending.source.name if to_creature else player.name
        else:
            recipient_kind = DamageRecipientKind.PLAYER
            recipient_id = player.id
            recipient_name = player.name
        incident.redirected_packets.append(
            DamagePacket(
                amount=amount,
                recipient_kind=recipient_kind,
                recipient_id=recipient_id,
                recipient_name=recipient_name,
                source_name=packet.source_name,
                source_id=packet.source_id,
                source_controller_id=packet.source_controller_id,
                colors=packet.colors,
                combat=packet.combat,
                trample=packet.trample,
                first_strike=packet.first_strike,
            )
        )
        self.pending_redirection = None
        self.priority_player_index = (
            self.players.index(player) + 1
        ) % len(self.players)
        self.consecutive_passes = 0
        return amount

    def cancel_redirection(self, player_id: str) -> None:
        pending = self.pending_redirection
        if pending is None:
            raise RuntimeError("there is no pending damage redirection")
        if pending.controller_id != player_id:
            raise ValueError("only the ability's controller may cancel")
        self.pending_redirection = None

    def _validate_prevention_activation(
        self, player_id: str, card: Card, ability_index: int
    ) -> tuple[PlayerState, ActivatedPreventDamageAbility]:
        incident = self.pending_damage
        if (
            incident is None
            or incident.step is not DamageResolutionStep.PREVENTION
        ):
            raise RuntimeError(
                "damage prevention can only be used during the prevention window"
            )
        player = self.player(player_id)
        if (
            self.priority_player_index is None
            or player is not self.players[self.priority_player_index]
        ):
            raise RuntimeError(
                f"{self.players[self.priority_player_index].name} has priority"
            )
        if card not in player.battlefield or card.controller_id != player_id:
            raise ValueError("a player can only activate a permanent they control")
        ability = self.activated_abilities(card)[ability_index]
        if not isinstance(ability, ActivatedPreventDamageAbility):
            raise ValueError("that ability does not prevent damage")
        if ability.tap_cost and card.tapped:
            raise RuntimeError(f"{card.name} is already tapped")
        if (
            ability.tap_cost
            and CardType.CREATURE in self.card_types(card)
            and self.has_summoning_sickness(card)
        ):
            raise RuntimeError(
                f"{card.name} did not begin the turn under its controller's control"
            )
        if not player.mana_pool.can_pay(ability.mana_cost):
            raise RuntimeError(f"not enough mana to activate {card.name}")
        return player, ability

    def begin_prevention_spell(self, card: Card) -> PendingPrevention:
        """Declare a prevention-mode instant during the FAQ prevention step."""

        self._require_no_pending_action(allow_stack=True, allow_damage=True)
        incident = self.pending_damage
        if (
            incident is None
            or incident.step is not DamageResolutionStep.PREVENTION
        ):
            raise RuntimeError(
                "this mode can only be cast during the prevention window"
            )
        caster = self._caster_for(card)
        if (
            self.priority_player_index is None
            or caster is not self.players[self.priority_player_index]
        ):
            raise RuntimeError(
                f"{self.players[self.priority_player_index].name} has priority"
            )
        if card.definition.prevention_amount < 1:
            raise ValueError(f"{card.name} has no damage-prevention mode")
        if not caster.mana_pool.can_pay(card.definition.mana_cost):
            raise RuntimeError(f"not enough mana to cast {card.name}")
        self.pending_prevention = PendingPrevention(
            card, caster.id, card.definition.prevention_amount
        )
        return self.pending_prevention

    def prevent_damage(self, player_id: str, packet_id: UUID) -> int:
        """Assign as much pending prevention as possible to one damage packet."""

        pending = self.pending_prevention
        incident = self.pending_damage
        if pending is None or incident is None:
            raise RuntimeError("there is no pending damage prevention")
        if player_id != pending.controller_id:
            raise ValueError("only the prevention effect's controller may choose")
        packet = next(
            (candidate for candidate in incident.packets if candidate.id == packet_id),
            None,
        )
        if packet is None or packet.remaining <= 0:
            raise ValueError("that damage packet cannot be prevented")
        if (
            pending.controller_only
            and (
                packet.recipient_kind is not DamageRecipientKind.PLAYER
                or packet.recipient_id != pending.controller_id
            )
        ):
            raise ValueError("this effect only prevents damage to its controller")
        if (
            pending.source_color is not None
            and pending.source_color not in packet.colors
        ):
            raise ValueError(
                "this effect cannot prevent damage of that source's color"
            )
        if (
            pending.recipient_id is not None
            and packet.recipient_id != pending.recipient_id
        ):
            raise ValueError("this effect must prevent damage to a single target")
        if not pending.paid:
            if pending.ability_index is None:
                caster = self.player(pending.controller_id)
                caster.mana_pool.pay(pending.source.definition.mana_cost)
                self._move_card(pending.source, Zone.GRAVEYARD)
            else:
                ability = self.activated_abilities(pending.source)[
                    pending.ability_index
                ]
                assert isinstance(ability, ActivatedPreventDamageAbility)
                self.player(pending.controller_id).mana_pool.pay(
                    ability.mana_cost
                )
                if ability.tap_cost:
                    self._tap_permanent(pending.source)
            pending.paid = True
            pending.recipient_id = packet.recipient_id
        amount = (
            packet.remaining
            if pending.remaining is None
            else min(pending.remaining, packet.remaining)
        )
        packet.prevented += amount
        if pending.remaining is not None:
            pending.remaining -= amount
        if pending.remaining is None or pending.remaining == 0:
            self.finish_prevention(player_id)
        return amount

    def legal_prevention_packets(self) -> list[DamagePacket]:
        """Damage packets currently selectable by the pending prevention effect."""

        pending = self.pending_prevention
        incident = self.pending_damage
        if pending is None or incident is None:
            return []
        return [
            packet
            for packet in incident.packets
            if packet.remaining
            and (
                pending.recipient_id is None
                or packet.recipient_id == pending.recipient_id
            )
            and (
                not pending.controller_only
                or (
                    packet.recipient_kind is DamageRecipientKind.PLAYER
                    and packet.recipient_id == pending.controller_id
                )
            )
            and (
                pending.source_color is None
                or pending.source_color in packet.colors
            )
        ]

    def finish_prevention(self, player_id: str) -> None:
        """Finish assigning an optional 'up to' prevention effect."""

        pending = self.pending_prevention
        if pending is None:
            raise RuntimeError("there is no pending damage prevention")
        if pending.controller_id != player_id:
            raise ValueError("only the prevention effect's controller may finish")
        if not pending.paid:
            raise RuntimeError("choose at least one damage packet first")
        player = self.player(player_id)
        self.pending_prevention = None
        self.priority_player_index = (
            self.players.index(player) + 1
        ) % len(self.players)
        self.consecutive_passes = 0

    def cancel_prevention(self, player_id: str) -> None:
        """Cancel a prevention declaration before any cost or effect is applied."""

        pending = self.pending_prevention
        if pending is None:
            raise RuntimeError("there is no pending damage prevention")
        if pending.controller_id != player_id:
            raise ValueError("only the prevention effect's controller may cancel")
        if pending.paid:
            raise RuntimeError("damage prevention already assigned; finish it instead")
        self.pending_prevention = None

    def _validate_regeneration_activation(
        self, player_id: str, card: Card, ability_index: int
    ) -> tuple[PlayerState, ActivatedRegenerationAbility, Card]:
        """Validate regeneration at the point lethal damage would kill a creature."""

        in_damage_window = (
            self.pending_damage is not None
            and self.pending_damage.step is DamageResolutionStep.REGENERATION
        )
        in_destruction_window = (
            self.pending_destruction is not None
            and self.pending_destruction.step
            is DestructionResolutionStep.REGENERATION
        )
        if not (in_damage_window or in_destruction_window):
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
            raise ValueError("a player can only activate a permanent they control")
        try:
            ability = self.activated_abilities(card)[ability_index]
        except IndexError as error:
            raise ValueError(f"{card.name} has no such activated ability") from error
        if not isinstance(ability, ActivatedRegenerationAbility):
            raise ValueError("that ability does not regenerate its source")
        affected_card = (
            self._attached_creature(card)
            if ability.affects_attached_creature
            else card
        )
        if in_damage_window and self.creature_toughness(affected_card) <= 0:
            raise RuntimeError("regeneration cannot save a creature with zero toughness")
        if (
            in_damage_window
            and affected_card.damage < self.creature_toughness(affected_card)
        ):
            raise RuntimeError(f"{affected_card.name} is not facing lethal damage")
        if in_destruction_window:
            destruction_target = next(
                (
                    target
                    for target in self.pending_destruction.targets
                    if target.card_id == affected_card.id
                ),
                None,
            )
            if destruction_target is None:
                raise RuntimeError(f"{affected_card.name} is not facing destruction")
            if not destruction_target.regeneration_allowed:
                raise RuntimeError(
                    f"{affected_card.name} cannot regenerate from this destruction"
                )
        if not player.mana_pool.can_pay(ability.mana_cost):
            raise RuntimeError(f"not enough mana to regenerate {card.name}")
        return player, ability, affected_card

    def _pass_damage_priority(self, player_id: str) -> None:
        """Pass in the current prevention, redirection, or regeneration window."""

        if self.pending_prevention is not None:
            raise RuntimeError("finish choosing damage prevention first")
        if self.pending_redirection is not None:
            raise RuntimeError("finish choosing damage redirection first")
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

    def _pass_destruction_priority(self, player_id: str) -> None:
        """Pass in a destroy effect's dedicated regeneration window."""

        incident = self.pending_destruction
        if (
            incident is None
            or incident.step is not DestructionResolutionStep.REGENERATION
            or self.priority_player_index is None
        ):
            raise RuntimeError("there is no destruction window awaiting priority")
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
        self._finish_destruction_incident()

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
        source_colors: frozenset[Color] | None = None,
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
                    if not isinstance(recipient, Card)
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
                    self.card_colors(source_card)
                    if source_card is not None
                    else source_colors or frozenset()
                ),
                combat=combat,
                trample=trample,
                first_strike=first_strike,
                prevented=(
                    amount
                    if isinstance(recipient, Card)
                    and self._is_protected_from(
                        recipient,
                        (
                            self.card_colors(source_card)
                            if source_card is not None
                            else source_colors or frozenset()
                        ),
                    )
                    else 0
                ),
            )
        )
        if resolve_immediately:
            self._resolve_damage_incident()

    def _resolve_damage_incident(self) -> DamageIncident | None:
        """Open the first FAQ damage window, auto-skipping empty windows."""

        incident = self.pending_damage
        if incident is None:
            raise RuntimeError("there is no damage incident to resolve")
        if not incident.packets:
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
            CardType.CREATURE in self.card_types(card)
            and self.creature_toughness(card) > 0
            and card.damage >= self.creature_toughness(card)
            and any(
                isinstance(ability, ActivatedRegenerationAbility)
                for ability in self.activated_abilities(card)
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
            self._redirect_unblocked_combat_damage()
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
        self.pending_damage = None
        self.check_state_based_actions()
        for player in self.players:
            for card in player.battlefield:
                counters = incident.surviving_damage_triggers.get(card.id, 0)
                if counters:
                    card.plus_one_counters += counters
        incident.step = DamageResolutionStep.COMPLETE
        self.resolved_damage_incidents.append(incident)
        self.consecutive_passes = 0
        if incident.redirected_packets:
            redirected = DamageIncident(
                incident.kind,
                packets=incident.redirected_packets,
            )
            self.pending_damage = redirected
            self._resolve_damage_incident()
            return
        if self.event_opportunities:
            self.deferred_damage_continuation = incident
            self.priority_player_index = self.active_player_index
            return
        self.priority_player_index = (
            self.active_player_index
            if self.pending_phase_advance is not None
            else None
        )
        self._continue_after_damage_incident(incident)

    def _redirect_unblocked_combat_damage(self) -> None:
        """Apply mandatory Veteran Bodyguard redirection after prevention."""

        incident = self.pending_damage
        assert incident is not None
        for packet in incident.packets:
            if (
                not packet.remaining
                or packet.recipient_kind is not DamageRecipientKind.PLAYER
                or not packet.combat
                or packet.trample
            ):
                continue
            bodyguards = [
                permanent
                for player in self.players
                for permanent in player.battlefield
                if permanent.controller_id == packet.recipient_id
                and permanent.definition.redirects_unblocked_combat_damage
            ]
            if not bodyguards:
                continue
            amount = packet.remaining
            packet.redirected += amount
            for bodyguard in bodyguards:
                incident.redirected_packets.append(
                    DamagePacket(
                        amount=amount,
                        recipient_kind=DamageRecipientKind.CREATURE,
                        recipient_id=bodyguard.id,
                        recipient_name=bodyguard.name,
                        source_name=packet.source_name,
                        source_id=packet.source_id,
                        source_controller_id=packet.source_controller_id,
                        colors=packet.colors,
                        combat=packet.combat,
                        trample=False,
                        first_strike=packet.first_strike,
                    )
                )

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
                source = next(
                    (
                        card
                        for player in self.players
                        for card in player.battlefield
                        if card.id == packet.source_id
                    ),
                    None,
                )
                if (
                    packet.combat
                    and source is not None
                    and source.definition.combat_player_damage_random_discard
                ):
                    self.event_opportunities.append(
                        RuleEventOpportunity(
                            RuleEventKind.COMBAT_PLAYER_DAMAGED,
                            f"{source.name} damaged {recipient.name}",
                            source_id=source.id,
                            source_name=source.name,
                            source_controller_id=packet.source_controller_id,
                            affected_player_id=recipient.id,
                            random_discard=(
                                source.definition.combat_player_damage_random_discard
                            ),
                        )
                    )
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
            if recipient.definition.grows_after_surviving_damage:
                incident.surviving_damage_triggers[recipient.id] = (
                    incident.surviving_damage_triggers.get(recipient.id, 0) + 1
                )
            self.events.append(
                DamageEvent(
                    amount=amount,
                    source=event_source,
                    card_id=recipient.id,
                    card_name=recipient.name,
                )
            )
        for player in self.players:
            for card in player.battlefield:
                if card.id in incident.regenerated_card_ids:
                    self._tap_permanent(card)
                    card.damage = 0

    def _continue_after_damage_incident(self, incident: DamageIncident) -> None:
        """Resume a rule action that was split by interactive damage windows."""

        if self.pending_destruction is not None:
            self._open_destruction_incident()
            return
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

    def _open_destruction_incident(self) -> None:
        """Open or auto-resolve an ordinary destruction regeneration window."""

        incident = self.pending_destruction
        if (
            incident is None
            or incident.step is not DestructionResolutionStep.WAITING
        ):
            return
        incident.step = DestructionResolutionStep.REGENERATION
        has_regenerable_target = any(
            target.regeneration_allowed for target in incident.targets
        )
        if has_regenerable_target and (
            self.pause_for_damage_windows or self._destruction_can_regenerate()
        ):
            self.priority_player_index = self.active_player_index
            self.consecutive_passes = 0
            return
        self._finish_destruction_incident()

    def _destruction_can_regenerate(self) -> bool:
        assert self.pending_destruction is not None
        target_ids = {
            target.card_id
            for target in self.pending_destruction.targets
            if target.regeneration_allowed
        }
        return any(
            card.id in target_ids
            and any(
                isinstance(ability, ActivatedRegenerationAbility)
                for ability in self.activated_abilities(card)
            )
            for player in self.players
            for card in player.battlefield
        )

    def _finish_destruction_incident(self) -> None:
        incident = self.pending_destruction
        if incident is None:
            raise RuntimeError("there is no destruction incident to finish")
        target_ids = {
            target.card_id
            for target in incident.targets
            if target.card_id not in incident.regenerated_card_ids
        }
        doomed = [
            card
            for player in self.players
            for card in tuple(player.battlefield)
            if card.id in target_ids
        ]
        resume_interrupts = self.resume_interrupts_after_destruction
        self.resume_interrupts_after_destruction = False
        self.pending_destruction = None
        self._destroy_permanents(doomed)
        self.check_state_based_actions()
        incident.step = DestructionResolutionStep.COMPLETE
        self.resolved_destruction_incidents.append(incident)
        self.consecutive_passes = 0
        if resume_interrupts and self.stack:
            underlying = self.stack_spells[self.stack[-1].id]
            self.priority_player_index = self.players.index(
                self.player(underlying.caster_id)
            )
        else:
            self.priority_player_index = (
                self.active_player_index
                if self.timed_events or self.event_opportunities
                or self.pending_phase_advance is not None
                else None
            )
