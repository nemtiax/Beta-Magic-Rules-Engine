"""Combat-specific coordination for the hotseat UI."""

from __future__ import annotations

from typing import Iterable
from uuid import UUID

from .cards import Card
from .game import GameState
from .types import CardType, CombatStep, KeywordAbility, RiverSide, Zone


class CombatUiController:
    """Own provisional combat choices without mutating the rules engine."""

    def __init__(self) -> None:
        self._draft_combat_id: int | None = None
        self._false_orders_choice_id: int | None = None
        self._blocker_draft: dict[UUID, tuple[UUID, ...]] = {}
        self._attacking_band_draft: list[tuple[UUID, ...]] = []
        self._river_choice_key: tuple[CombatStep, tuple[UUID, ...]] | None = None
        self._river_side_draft: dict[UUID, RiverSide] = {}
        self._damage_combat_id: int | None = None
        self._damage_assignments: dict[UUID, dict[UUID, int]] = {}
        self._damage_submitted = False
        self._damage_confirmed_player_ids: set[str] = set()

    def reset(self) -> None:
        self._draft_combat_id = None
        self._false_orders_choice_id = None
        self._blocker_draft.clear()
        self._attacking_band_draft.clear()
        self._river_choice_key = None
        self._river_side_draft.clear()
        self._damage_combat_id = None
        self._damage_assignments.clear()
        self._damage_submitted = False
        self._damage_confirmed_player_ids.clear()

    def sync(self, game: GameState) -> None:
        combat = game.combat
        combat_id = id(combat) if combat is not None else None
        if combat_id != self._draft_combat_id:
            self._draft_combat_id = combat_id
            self._blocker_draft.clear()
            self._attacking_band_draft.clear()
        river_choice_key = (
            (combat.step, combat.river_choice_card_ids)
            if combat is not None
            and combat.step in {
                CombatStep.RIVER_DEFENDER_ASSIGNMENT,
                CombatStep.RIVER_ATTACKER_ASSIGNMENT,
            }
            else None
        )
        if river_choice_key != self._river_choice_key:
            self._river_choice_key = river_choice_key
            self._river_side_draft.clear()
        false_orders_choice = (
            game.pending_false_orders_choices[0]
            if game.pending_false_orders_choices else None
        )
        false_orders_choice_id = (
            id(false_orders_choice) if false_orders_choice is not None else None
        )
        if false_orders_choice_id != self._false_orders_choice_id:
            self._false_orders_choice_id = false_orders_choice_id
            self._blocker_draft.clear()
            if false_orders_choice is not None:
                self._blocker_draft[false_orders_choice.blocker_id] = tuple(
                    attacker.id
                    for attacker in game.false_orders_current_assignment()
                )
        if combat_id != self._damage_combat_id:
            self._damage_combat_id = combat_id
            self._damage_assignments.clear()
            self._damage_submitted = False
            self._damage_confirmed_player_ids.clear()
        if combat is not None and combat.step is CombatStep.DECLARE_BLOCKERS:
            defender = game.player(combat.defending_player_id)
            for blocker in defender.battlefield:
                if blocker.id in combat.blaze_of_glory_blocker_ids:
                    self._blocker_draft.setdefault(
                        blocker.id,
                        tuple(
                            attacker.id
                            for attacker in game.required_blaze_blocks(blocker)
                        ),
                    )
            for blocker in defender.battlefield:
                options = game.lure_block_options(blocker)
                if not options:
                    continue
                drafted = self._blocker_draft.get(blocker.id, ())
                if not any(option.id in drafted for option in options):
                    self._blocker_draft.setdefault(
                        blocker.id, (options[0].id,)
                    )
        if (combat is not None and combat.step is CombatStep.DAMAGE
                and not self._damage_submitted and not self._damage_assignments):
            self._initialize_damage_assignments(game)

    def draft_for(self, blocker_id: UUID) -> tuple[UUID, ...]:
        return self._blocker_draft.get(blocker_id, ())

    def is_choosing_river_sides(
        self, game: GameState, perspective_id: str
    ) -> bool:
        return bool(
            game.combat is not None
            and game.combat.step in {
                CombatStep.RIVER_DEFENDER_ASSIGNMENT,
                CombatStep.RIVER_ATTACKER_ASSIGNMENT,
            }
            and game.river_choice_player_id() == perspective_id
        )

    def river_selectable_card(
        self, game: GameState, perspective_id: str, card: Card | None
    ) -> bool:
        return bool(
            card is not None
            and self.is_choosing_river_sides(game, perspective_id)
            and game.combat is not None
            and card.id in game.combat.river_choice_card_ids
        )

    def set_river_side(
        self,
        game: GameState,
        perspective_id: str,
        selected_ids: set[UUID],
        side: RiverSide | str,
    ) -> str:
        self.sync(game)
        if not self.is_choosing_river_sides(game, perspective_id):
            raise RuntimeError("the other player must choose the River sides")
        assert game.combat is not None
        chosen = set(game.combat.river_choice_card_ids) & selected_ids
        if not chosen:
            raise ValueError("select at least one highlighted creature")
        normalized = side if isinstance(side, RiverSide) else RiverSide(side)
        for card_id in chosen:
            self._river_side_draft[card_id] = normalized
        bank = "left" if normalized is RiverSide.LEFT else "right"
        return f"Placed {len(chosen)} creature(s) on the {bank}."

    def river_side_for(self, game: GameState, card: Card) -> RiverSide | None:
        self.sync(game)
        return self._river_side_draft.get(
            card.id, game.raging_river_side(card)
        )

    def river_assignment_progress(self, game: GameState) -> tuple[int, int]:
        self.sync(game)
        if game.combat is None:
            return 0, 0
        candidate_ids = set(game.combat.river_choice_card_ids)
        return (
            len(candidate_ids & self._river_side_draft.keys()),
            len(candidate_ids),
        )

    def river_assignments(self, game: GameState) -> dict[Card, RiverSide]:
        self.sync(game)
        if game.combat is None:
            raise RuntimeError("there is no combat in progress")
        cards = {
            card.id: card
            for player in game.players
            for card in player.battlefield
        }
        return {
            cards[card_id]: side
            for card_id, side in self._river_side_draft.items()
            if card_id in cards
            and card_id in game.combat.river_choice_card_ids
        }

    def set_attacking_band(
        self, game: GameState, selected_ids: set[UUID]
    ) -> str:
        self.sync(game)
        combat = game.combat
        if combat is None or combat.step is not CombatStep.DECLARE_ATTACKERS:
            raise RuntimeError("The game is not waiting for attacking bands.")
        selected = tuple(
            card.id
            for card in game.active_player.battlefield
            if card.id in selected_ids
        )
        if len(selected) < 2:
            raise ValueError("Select at least two creatures to form a band.")
        selected_set = set(selected)
        existing = next(
            (
                band
                for band in self._attacking_band_draft
                if set(band) == selected_set
            ),
            None,
        )
        if existing is not None:
            self._attacking_band_draft.remove(existing)
            return "Disbanded the selected attackers."
        selected_cards = tuple(
            card
            for card in game.active_player.battlefield
            if card.id in selected_set
        )
        if not all(game.can_declare_attacker(card) for card in selected_cards):
            raise ValueError("Every member of a band must be eligible to attack.")
        if not game.can_form_attacking_band(selected_cards):
            raise ValueError(
                "All but at most one creature in an attacking band must have Banding."
            )
        shortened = [
            tuple(card_id for card_id in band if card_id not in selected_set)
            for band in self._attacking_band_draft
        ]
        self._attacking_band_draft = [band for band in shortened if len(band) >= 2]
        self._attacking_band_draft.append(selected)
        return f"Created a band of {len(selected)} attackers."

    def can_set_attacking_band(
        self, game: GameState, selected_ids: set[UUID]
    ) -> bool:
        """Whether the current selection may be banded or disbanded."""

        self.sync(game)
        selected = tuple(
            card
            for card in game.active_player.battlefield
            if card.id in selected_ids
        )
        selected_set = {card.id for card in selected}
        if any(
            set(band) == selected_set
            for band in self._attacking_band_draft
        ):
            return True
        return game.can_form_attacking_band(selected)

    def attacking_bands(self, game: GameState) -> list[tuple[Card, ...]]:
        cards = {card.id: card for card in game.active_player.battlefield}
        return [
            tuple(cards[card_id] for card_id in band if card_id in cards)
            for band in self._attacking_band_draft
        ]

    def attacking_band_action_label(self, selected_ids: set[UUID]) -> str:
        selected = set(selected_ids)
        if any(set(band) == selected for band in self._attacking_band_draft):
            return "Disband selected"
        return "Band selected"

    def drafted_attackers(
        self, game: GameState, selected_ids: set[UUID]
    ) -> list[Card]:
        ids = set(selected_ids)
        ids.update(
            card_id for band in self._attacking_band_draft for card_id in band
        )
        return [card for card in game.active_player.battlefield if card.id in ids]

    def is_drafting_attackers(
        self, game: GameState, perspective_id: str
    ) -> bool:
        combat = game.combat
        return bool(
            combat is not None
            and combat.step is CombatStep.DECLARE_ATTACKERS
            and game.active_player.id == perspective_id
        )

    def selectable_attacker(
        self,
        game: GameState,
        perspective_id: str,
        card: Card | None,
    ) -> bool:
        return bool(
            card is not None
            and self.is_drafting_attackers(game, perspective_id)
            and game.can_declare_attacker(card)
        )

    def is_drafting(self, game: GameState, perspective_id: str) -> bool:
        combat = game.combat
        false_orders_choice = (
            game.pending_false_orders_choices[0]
            if game.pending_false_orders_choices else None
        )
        return bool(
            combat is not None
            and (
                (
                    combat.step is CombatStep.DECLARE_BLOCKERS
                    and combat.defending_player_id == perspective_id
                )
                or (
                    false_orders_choice is not None
                    and false_orders_choice.chooser_id == perspective_id
                )
            )
        )

    def selectable_card(self, game: GameState, perspective_id: str,
                        card: Card | None) -> bool:
        if card is None or not self.is_drafting(game, perspective_id):
            return False
        combat = game.combat
        assert combat is not None
        false_orders_choice = (
            game.pending_false_orders_choices[0]
            if game.pending_false_orders_choices else None
        )
        if false_orders_choice is not None:
            return bool(
                card.id == false_orders_choice.blocker_id
                or card in game.legal_false_orders_attackers()
            )
        defender = game.player(combat.defending_player_id)
        return card in combat.attackers or (
            card in defender.battlefield
            and CardType.CREATURE in game.card_types(card)
            and not card.tapped
        )

    def selected_groups(self, game: GameState, selected_ids: set[UUID]
                        ) -> tuple[list[Card], list[Card]]:
        combat = game.combat
        if combat is None:
            return [], []
        false_orders_choice = (
            game.pending_false_orders_choices[0]
            if game.pending_false_orders_choices else None
        )
        if false_orders_choice is not None:
            blocker = next(
                (
                    card
                    for card in game.player(combat.defending_player_id).battlefield
                    if card.id == false_orders_choice.blocker_id
                ),
                None,
            )
            attackers = [
                card for card in combat.attackers if card.id in selected_ids
            ]
            return ([blocker] if blocker is not None else []), attackers
        if combat.step is not CombatStep.DECLARE_BLOCKERS:
            return [], []
        defender = game.player(combat.defending_player_id)
        blockers = [card for card in defender.battlefield
                    if card.id in selected_ids
                    and CardType.CREATURE in game.card_types(card)
                    and not card.tapped]
        attackers = [card for card in combat.attackers if card.id in selected_ids]
        return blockers, attackers

    def set_blocks(self, game: GameState, selected_ids: set[UUID]) -> str:
        self.sync(game)
        combat = game.combat
        if combat is None or (
            not game.pending_false_orders_choices
            and combat.step is not CombatStep.DECLARE_BLOCKERS
        ):
            raise RuntimeError("The game is not waiting for blocker assignments.")
        blockers, attackers = self.selected_groups(game, selected_ids)
        if not blockers:
            raise ValueError("Select at least one defending creature.")
        attacker_ids = tuple(card.id for card in attackers)
        for blocker in blockers:
            self._blocker_draft[blocker.id] = attacker_ids
        verb = "Set" if attackers else "Cleared"
        return f"{verb} {len(blockers)} blocker assignment(s)."

    def blocker_assignments(self, game: GameState) -> dict[Card, tuple[Card, ...]]:
        combat = game.combat
        if combat is None or combat.step is not CombatStep.DECLARE_BLOCKERS:
            raise RuntimeError("The game is not waiting for blockers.")
        defender = game.player(combat.defending_player_id)
        attackers = {card.id: card for card in combat.attackers}
        return {blocker: tuple(attackers[attacker_id]
                              for attacker_id in attacker_ids
                              if attacker_id in attackers)
                for blocker in defender.battlefield
                if (attacker_ids := self._blocker_draft.get(blocker.id))}

    def false_orders_assignment(self, game: GameState) -> tuple[Card, ...]:
        """Return the proposed assignment for the pending affected blocker."""

        self.sync(game)
        if not game.pending_false_orders_choices or game.combat is None:
            raise RuntimeError("There is no False Orders choice pending.")
        choice = game.pending_false_orders_choices[0]
        attackers = {card.id: card for card in game.combat.attackers}
        return tuple(
            attackers[attacker_id]
            for attacker_id in self._blocker_draft.get(choice.blocker_id, ())
            if attacker_id in attackers
        )

    def card_status(self, game: GameState, card: Card) -> tuple[str, str, str]:
        combat = game.combat
        if combat is None:
            return "", "", ""
        bands = (
            self.attacking_bands(game)
            if combat.step is CombatStep.DECLARE_ATTACKERS
            else combat.attacking_bands
        )
        band_index = next(
            (
                index
                for index, band in enumerate(bands, start=1)
                if card in band
            ),
            None,
        )
        if combat.step is CombatStep.DECLARE_ATTACKERS and band_index is not None:
            band = bands[band_index - 1]
            return (
                "attacker",
                f"Band B{band_index}",
                f"B{band_index}: " + ", ".join(member.name for member in band),
            )
        draft_blockers = None
        if (
            (
                combat.step is CombatStep.DECLARE_BLOCKERS
                or bool(game.pending_false_orders_choices)
            )
            and self._draft_combat_id == id(combat)
        ):
            defender = game.player(combat.defending_player_id)
            band_by_member = {
                member.id: {card.id for card in band}
                for band in combat.attacking_bands
                for member in band
            }
            false_orders_choice = (
                game.pending_false_orders_choices[0]
                if game.pending_false_orders_choices else None
            )
            if false_orders_choice is None:
                draft_blockers = {
                    attacker.id: [
                        blocker
                        for blocker in defender.battlefield
                        if band_by_member.get(attacker.id, {attacker.id})
                        & set(self._blocker_draft.get(blocker.id, ()))
                    ]
                    for attacker in combat.attackers
                }
            else:
                affected = next(
                    (
                        blocker
                        for blocker in defender.battlefield
                        if blocker.id == false_orders_choice.blocker_id
                    ),
                    None,
                )
                draft_blockers = {
                    attacker.id: [
                        blocker
                        for blocker in combat.blockers.get(attacker.id, ())
                        if blocker.id != false_orders_choice.blocker_id
                    ]
                    for attacker in combat.attackers
                }
                if affected is not None:
                    drafted_ids = set(
                        self._blocker_draft.get(affected.id, ())
                    )
                    for attacker in combat.attackers:
                        if (
                            band_by_member.get(attacker.id, {attacker.id})
                            & drafted_ids
                        ):
                            draft_blockers[attacker.id].append(affected)
        attacker_index = next((index for index, candidate
                               in enumerate(combat.attackers, start=1)
                               if candidate.id == card.id), None)
        if attacker_index is not None:
            attacker = combat.attackers[attacker_index - 1]
            blockers = (draft_blockers.get(attacker.id, [])
                        if draft_blockers is not None
                        else combat.blockers.get(attacker.id, []))
            if blockers:
                prefix = f"B{band_index} · " if band_index is not None else ""
                return ("attacker", prefix + f"A{attacker_index} · blocked ×{len(blockers)}",
                        f"A{attacker_index}: {attacker.name} — blocked by "
                        + ", ".join(blocker.name for blocker in blockers))
            prefix = f"B{band_index} · " if band_index is not None else ""
            return ("attacker", prefix + f"A{attacker_index} · unblocked",
                    f"A{attacker_index}: {attacker.name} — unblocked")
        blocked = [(index, attacker) for index, attacker
                   in enumerate(combat.attackers, start=1)
                   if any(blocker.id == card.id for blocker in (
                       draft_blockers.get(attacker.id, [])
                       if draft_blockers is not None
                       else combat.blockers.get(attacker.id, [])))]
        if blocked:
            blocked_ids = {attacker.id for _, attacker in blocked}
            band_by_member = {
                member.id: (index, band)
                for index, band in enumerate(combat.attacking_bands, start=1)
                for member in band
            }
            marker_parts: list[str] = []
            detail_parts: list[str] = []
            reported_bands: set[int] = set()
            for attacker_index, attacker in blocked:
                band_info = band_by_member.get(attacker.id)
                if band_info is not None:
                    band_index, band = band_info
                    if all(member.id in blocked_ids for member in band):
                        if band_index not in reported_bands:
                            reported_bands.add(band_index)
                            marker_parts.append(f"B{band_index}")
                            detail_parts.append(
                                f"B{band_index}: "
                                + " + ".join(member.name for member in band)
                            )
                        continue
                marker_parts.append(f"A{attacker_index}")
                detail_parts.append(f"A{attacker_index}: {attacker.name}")
            markers = " + ".join(marker_parts)
            detail = ", ".join(detail_parts)
            return "blocker", f"Blocks {markers}", f"{card.name} blocks {detail}"
        return "", "", ""

    def default_damage_assignments(self, game: GameState
                                   ) -> dict[Card, dict[Card, int]]:
        combat = game.combat
        if combat is None:
            return {}
        result: dict[Card, dict[Card, int]] = {}
        defender = game.player(combat.defending_player_id)
        for attacker in combat.attackers:
            blockers = [blocker for blocker in combat.blockers[attacker.id]
                        if blocker in defender.battlefield]
            if len(blockers) > 1:
                result[attacker] = self._all_on_first(game, attacker, blockers)
        for blocker in defender.battlefield:
            attackers = [attacker for attacker in combat.attackers
                         if blocker in combat.blockers[attacker.id]]
            if len(attackers) > 1:
                result[blocker] = self._all_on_first(game, blocker, attackers)
        return result

    def _damage_recipients(self, game: GameState) -> list[tuple[Card, list[Card]]]:
        combat = game.combat
        if combat is None:
            return []
        defender = game.player(combat.defending_player_id)
        choices: list[tuple[Card, list[Card]]] = []
        for attacker in combat.attackers:
            if attacker.zone is not Zone.BATTLEFIELD:
                continue
            blockers = [blocker for blocker in combat.blockers[attacker.id]
                        if blocker in defender.battlefield]
            if len(blockers) > 1:
                choices.append((attacker, blockers))
        for blocker in defender.battlefield:
            attackers = [attacker for attacker in combat.attackers
                         if blocker in combat.blockers[attacker.id]
                         and attacker.zone is Zone.BATTLEFIELD]
            if len(attackers) > 1:
                choices.append((blocker, attackers))
        return choices

    def _initialize_damage_assignments(self, game: GameState) -> None:
        for source, recipients in self._damage_recipients(game):
            power = max(0, game.creature_power(source))
            self._damage_assignments[source.id] = {
                recipient.id: power if index == 0 else 0
                for index, recipient in enumerate(recipients)
            }

    def choosing_damage_assignment(self, game: GameState) -> bool:
        self.sync(game)
        return bool(self._damage_assignments and not self._damage_submitted)

    def _damage_assignment_player(
        self, game: GameState, source: Card, recipients: list[Card]
    ) -> str:
        combat = game.combat
        assert combat is not None
        if source in combat.attackers:
            if any(
                KeywordAbility.BANDING in game.creature_abilities(blocker)
                for blocker in recipients
            ):
                return combat.defending_player_id
            return combat.attacking_player_id
        if any(
            set(recipients).issubset(set(band))
            for band in combat.attacking_bands
        ):
            return combat.attacking_player_id
        return combat.defending_player_id

    def pending_damage_assignment_player_ids(self, game: GameState) -> list[str]:
        players: list[str] = []
        for source, recipients in self._damage_recipients(game):
            player_id = self._damage_assignment_player(game, source, recipients)
            if (
                player_id not in self._damage_confirmed_player_ids
                and player_id not in players
            ):
                players.append(player_id)
        return players

    def damage_assignment_state(
        self, game: GameState, player_id: str | None = None
    ) -> list[dict[str, object]]:
        self.sync(game)
        rows: list[dict[str, object]] = []
        for source, recipients in self._damage_recipients(game):
            assigning_player_id = self._damage_assignment_player(
                game, source, recipients
            )
            if player_id is not None and assigning_player_id != player_id:
                continue
            allocation = self._damage_assignments.get(source.id, {})
            power = max(0, game.creature_power(source))
            assigned = sum(allocation.values())
            rows.append({
                "sourceId": str(source.id),
                "sourceName": source.name,
                "power": power,
                "assigned": assigned,
                "remaining": power - assigned,
                "valid": assigned == power,
                "playerId": assigning_player_id,
                "playerName": game.player(assigning_player_id).name,
                "recipients": [
                    {
                        "id": str(recipient.id),
                        "name": recipient.name,
                        "amount": allocation.get(recipient.id, 0),
                    }
                    for recipient in recipients
                ],
            })
        return rows

    def adjust_damage_assignment(
        self,
        game: GameState,
        player_id: str,
        source_id: UUID,
        recipient_id: UUID,
        delta: int,
    ) -> None:
        self.sync(game)
        allocation = self._damage_assignments.get(source_id)
        if allocation is None or recipient_id not in allocation:
            raise ValueError("That combat damage assignment is no longer available.")
        source = next((source for source, _ in self._damage_recipients(game)
                       if source.id == source_id), None)
        if source is None:
            raise ValueError("That combat creature is no longer in combat.")
        recipients = next(
            recipients
            for candidate, recipients in self._damage_recipients(game)
            if candidate.id == source_id
        )
        if self._damage_assignment_player(game, source, recipients) != player_id:
            raise ValueError("The other player assigns that combat damage.")
        power = max(0, game.creature_power(source))
        current = allocation[recipient_id]
        total_without = sum(allocation.values()) - current
        allocation[recipient_id] = max(0, min(power - total_without, current + delta))

    def confirm_damage_assignments(self, game: GameState, player_id: str) -> bool:
        rows = self.damage_assignment_state(game, player_id)
        if not rows:
            raise ValueError("You have no combat damage assignments to make.")
        invalid = next((row for row in rows if not row["valid"]), None)
        if invalid is not None:
            raise ValueError(
                f"{invalid['sourceName']} must assign all {invalid['power']} damage."
            )
        self._damage_confirmed_player_ids.add(player_id)
        return not self.pending_damage_assignment_player_ids(game)

    def damage_assignments(self, game: GameState) -> dict[Card, dict[Card, int]]:
        self.sync(game)
        choices = self._damage_recipients(game)
        cards = {card.id: card for source, recipients in choices
                 for card in (source, *recipients)}
        result: dict[Card, dict[Card, int]] = {}
        for source, _ in choices:
            allocation = self._damage_assignments.get(source.id, {})
            power = max(0, game.creature_power(source))
            if sum(allocation.values()) != power:
                raise ValueError(f"{source.name} must assign all {power} damage.")
            result[source] = {cards[recipient_id]: amount
                              for recipient_id, amount in allocation.items()
                              if recipient_id in cards}
        return result

    def mark_damage_submitted(self, submitted: bool = True) -> None:
        self._damage_submitted = submitted

    @staticmethod
    def _all_on_first(game: GameState, source: Card,
                      recipients: Iterable[Card]) -> dict[Card, int]:
        return {recipient: max(0, game.creature_power(source)) if index == 0 else 0
                for index, recipient in enumerate(recipients)}
