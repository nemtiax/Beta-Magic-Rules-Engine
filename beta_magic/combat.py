"""Combat declaration and damage-assignment behavior for GameState."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable
from uuid import UUID

from .cards import Card
from .damage import DamageIncidentKind, DamageResolutionStep
from .destruction import DestructionIncident, DestructionTarget
from .types import (
    CardType,
    CombatStep,
    GameStatus,
    KeywordAbility,
    RiverSide,
    TurnPhase,
    Zone,
)

if TYPE_CHECKING:
    from .game import PlayerState


@dataclass(slots=True)
class CombatState:
    """Mutable state for one attack nested inside the Main phase."""

    attacking_player_id: str
    defending_player_id: str
    step: CombatStep = CombatStep.ATTACK_RESPONSE
    attackers: list[Card] = field(default_factory=list)
    attacking_bands: list[tuple[Card, ...]] = field(default_factory=list)
    blockers: dict[UUID, list[Card]] = field(default_factory=dict)
    damage_allocations: dict[Card, dict[Card, int]] = field(default_factory=dict)
    regenerated_card_ids: set[UUID] = field(default_factory=set)
    end_of_combat_destruction_ids: set[UUID] = field(default_factory=set)
    blaze_of_glory_blocker_ids: set[UUID] = field(default_factory=set)
    river_sides: dict[UUID, RiverSide] = field(default_factory=dict)
    river_choice_card_ids: tuple[UUID, ...] = ()
    river_resume_step: CombatStep | None = None


@dataclass(slots=True)
class AttackRequirement:
    card_id: UUID
    destroy_if_no_attack: bool = True


@dataclass(frozen=True, slots=True)
class PendingFalseOrdersChoice:
    """The spell's caster replaces one defender's declared blocks."""

    chooser_id: str
    blocker_id: UUID
    source_name: str


class CombatMixin:
    """Combat façade methods operating on state owned by ``GameState``."""

    __slots__ = ()

    def raging_river_active(self) -> bool:
        """Whether the attacker currently controls at least one active River."""

        if self.combat is None:
            return False
        attacker = self.player(self.combat.attacking_player_id)
        return any(
            permanent.definition.divides_combat_by_river
            and self.continuous_permanent_is_active(permanent)
            for permanent in attacker.battlefield
        )

    def river_choice_player_id(self) -> str | None:
        """Return the player who must complete the current River placement."""

        if self.combat is None:
            return None
        if self.combat.step is CombatStep.RIVER_DEFENDER_ASSIGNMENT:
            return self.combat.defending_player_id
        if self.combat.step is CombatStep.RIVER_ATTACKER_ASSIGNMENT:
            return self.combat.attacking_player_id
        return None

    def raging_river_side(self, card: Card) -> RiverSide | None:
        """Return a creature's effective side, if a River split is active."""

        if self.combat is None or not self.raging_river_active():
            return None
        return self.combat.river_sides.get(card.id)

    def _river_defenders_needing_sides(self) -> tuple[Card, ...]:
        if self.combat is None:
            return ()
        defender = self.player(self.combat.defending_player_id)
        return tuple(
            card
            for card in defender.battlefield
            if CardType.CREATURE in self.card_types(card)
            and KeywordAbility.FLYING not in self.creature_abilities(card)
            and card.id not in self.combat.river_sides
        )

    def _begin_river_defender_assignment(self, resume: CombatStep) -> bool:
        """Pause combat for any defender placements that are now required."""

        assert self.combat is not None
        if not self.raging_river_active():
            self.combat.river_sides.clear()
            return False
        candidates = self._river_defenders_needing_sides()
        if not candidates:
            return False
        self.combat.river_choice_card_ids = tuple(card.id for card in candidates)
        self.combat.river_resume_step = resume
        self.combat.step = CombatStep.RIVER_DEFENDER_ASSIGNMENT
        self.priority_player_index = None
        self.consecutive_passes = 0
        return True

    def choose_raging_river_sides(
        self,
        player_id: str,
        assignments: dict[Card, RiverSide | str],
    ) -> CombatStep:
        """Commit the pending left/right creature placements."""

        if self.combat is None or self.combat.step not in {
            CombatStep.RIVER_DEFENDER_ASSIGNMENT,
            CombatStep.RIVER_ATTACKER_ASSIGNMENT,
        }:
            raise RuntimeError("the game is not waiting for Raging River choices")
        if self.river_choice_player_id() != player_id:
            raise RuntimeError("the other player must choose the River sides")
        expected_ids = set(self.combat.river_choice_card_ids)
        if {card.id for card in assignments} != expected_ids:
            raise ValueError("choose a side for every highlighted creature")
        battlefield = {
            card.id: card
            for player in self.players
            for card in player.battlefield
        }
        if not expected_ids <= battlefield.keys():
            raise ValueError("a creature awaiting placement has left play")
        normalized: dict[UUID, RiverSide] = {}
        for card, side in assignments.items():
            try:
                normalized[card.id] = (
                    side if isinstance(side, RiverSide) else RiverSide(side)
                )
            except ValueError as error:
                raise ValueError("a River side must be L or R") from error
        self.combat.river_sides.update(normalized)
        resume = self.combat.river_resume_step
        if resume is None:
            raise RuntimeError("the River choice has no combat step to resume")
        self.combat.river_choice_card_ids = ()
        self.combat.river_resume_step = None
        self.combat.step = resume
        self.priority_player_index = (
            self.active_player_index
            if resume in {
                CombatStep.ATTACKER_RESPONSE,
                CombatStep.BLOCKER_RESPONSE,
            }
            else None
        )
        self.consecutive_passes = 0
        return self.combat.step

    def reconcile_raging_river(self) -> None:
        """Track River removal and creatures animated during combat."""

        if self.combat is None:
            return
        if not self.raging_river_active():
            self.combat.river_sides.clear()
            return
        if self.combat.step is CombatStep.ATTACKER_RESPONSE:
            self._begin_river_defender_assignment(CombatStep.ATTACKER_RESPONSE)

    def _raging_river_blocking_error(
        self, blocker: Card, attacker: Card
    ) -> str | None:
        if self.combat is None or not self.raging_river_active():
            return None
        if KeywordAbility.FLYING in self.creature_abilities(blocker):
            return None
        blocker_side = self.combat.river_sides.get(blocker.id)
        attacker_side = self.combat.river_sides.get(attacker.id)
        if blocker_side is None or attacker_side is None:
            return f"{blocker.name} and {attacker.name} need River sides"
        if blocker_side is not attacker_side:
            return (
                f"{blocker.name} cannot block {attacker.name} from the other "
                "side of Raging River"
            )
        return None

    def _island_sanctuary_allows(self, card: Card, defender_id: str) -> bool:
        if defender_id not in self.island_sanctuary_protected_players:
            return True
        abilities = self.creature_abilities(card)
        allowed_landwalk = self.island_sanctuary_landwalk_words.get(
            defender_id, {"Island"}
        )
        return KeywordAbility.FLYING in abilities or any(
            ability.landwalk_subtype in allowed_landwalk
            for ability in abilities
        )

    def _can_attack(self, card: Card) -> bool:
        if card not in self.active_player.battlefield:
            return False
        if CardType.CREATURE not in self.card_types(card):
            return False
        if card.tapped or (
            self.has_summoning_sickness(card)
            and not self.may_attack_with_summoning_sickness(card)
        ):
            return False
        if "Wall" in card.definition.subtypes and not self.wall_can_attack(card):
            return False
        if not self._island_sanctuary_allows(
            card, self.combat.defending_player_id
        ):
            return False
        return bool(
            card.definition.landhome is None
            or self.player_controls_land_subtype(
                self.combat.defending_player_id,
                self.land_word(card, card.definition.landhome.land_subtype),
            )
        )

    def can_declare_attacker(self, card: Card) -> bool:
        """Return whether ``card`` is currently eligible to attack."""

        return bool(
            self.combat is not None
            and self.combat.step is CombatStep.DECLARE_ATTACKERS
            and self._can_attack(card)
        )

    def can_form_attacking_band(self, cards: Iterable[Card]) -> bool:
        """Whether ``cards`` can be declared together as one attacking band."""

        band = tuple(cards)
        return bool(
            len(band) >= 2
            and len({card.id for card in band}) == len(band)
            and all(self.can_declare_attacker(card) for card in band)
            and sum(
                KeywordAbility.BANDING not in self.creature_abilities(card)
                for card in band
            )
            <= 1
        )

    def _individual_blocking_error(
        self, blocker: Card, attacker: Card, defender: PlayerState
    ) -> str | None:
        river_error = self._raging_river_blocking_error(blocker, attacker)
        if river_error is not None:
            return river_error
        power_limit = blocker.definition.maximum_blocked_power
        if power_limit is not None and self.creature_power(attacker) > power_limit:
            return f"{blocker.name} cannot block a creature with power greater than {power_limit}"
        if self.creature_is_unblockable(attacker):
            return f"{attacker.name} cannot be blocked"
        if attacker.definition.cannot_be_blocked_by_subtypes & set(blocker.definition.subtypes):
            return f"{attacker.name} cannot be blocked by {blocker.name}"
        required_subtype = self.blocking_subtype_requirement(attacker)
        if required_subtype is not None and required_subtype not in blocker.definition.subtypes:
            return f"only a {required_subtype} can block {attacker.name}"
        blocking_exceptions = self.blocking_exceptions(attacker)
        if blocking_exceptions is not None:
            allowed_colors, allowed_types = blocking_exceptions
            if not (allowed_colors & self.card_colors(blocker)
                    or allowed_types & self.card_types(blocker)):
                return f"{blocker.name} cannot block {attacker.name}"
        landwalk_subtypes = {
            ability.landwalk_subtype
            for ability in self.creature_abilities(attacker)
            if ability.landwalk_subtype is not None
        }
        defending_land_subtypes = {
            subtype
            for permanent in defender.battlefield
            if CardType.LAND in permanent.definition.card_types
            for subtype in self.land_subtypes(permanent)
        }
        active_landwalk = landwalk_subtypes & defending_land_subtypes
        if active_landwalk:
            land_type = sorted(active_landwalk)[0]
            return (f"{attacker.name} has {land_type.lower()}walk and cannot "
                    f"be blocked while the defender controls a {land_type}")
        if (KeywordAbility.FLYING in self.creature_abilities(attacker)
                and KeywordAbility.FLYING not in self.creature_abilities(blocker)
                and KeywordAbility.CAN_BLOCK_FLYING not in self.creature_abilities(blocker)):
            return f"{blocker.name} cannot block a creature with Flying"
        if self._is_protected_from(attacker, self.card_colors(blocker)):
            protected_color = next(
                color.value
                for color in self.card_colors(blocker)
                if color in {
                    ability.protection_color
                    for ability in self.creature_abilities(attacker)
                }
            )
            return (f"{attacker.name} has protection from {protected_color} "
                    f"and cannot be blocked by {blocker.name}")
        return None

    def required_blaze_blocks(self, blocker: Card) -> tuple[Card, ...]:
        """Representatives of all attacking groups Blaze requires it to block."""

        if self.combat is None:
            return ()
        defender = self.player(self.combat.defending_player_id)
        if (
            blocker not in defender.battlefield
            or blocker.tapped
            or CardType.CREATURE not in self.card_types(blocker)
        ):
            return ()
        band_by_member = {
            member.id: band
            for band in self.combat.attacking_bands
            for member in band
        }
        groups: dict[tuple[UUID, ...], Card] = {}
        for attacker in self.combat.attackers:
            group = band_by_member.get(attacker.id, (attacker,))
            representative = next(
                (
                    member
                    for member in group
                    if self._individual_blocking_error(blocker, member, defender)
                    is None
                ),
                None,
            )
            if representative is not None:
                groups.setdefault(
                    tuple(member.id for member in group), representative
                )
        return tuple(groups.values())

    def lured_attackers(self) -> tuple[Card, ...]:
        """Attacking creatures currently carrying at least one Lure effect."""

        if self.combat is None:
            return ()
        lured_ids = {
            permanent.enchanted_card_id
            for player in self.players
            for permanent in player.battlefield
            if permanent.definition.lures_blockers
        }
        return tuple(
            attacker
            for attacker in self.combat.attackers
            if attacker.zone is Zone.BATTLEFIELD and attacker.id in lured_ids
        )

    def lure_block_options(self, blocker: Card) -> tuple[Card, ...]:
        """Lured attackers this particular defender can legally block."""

        if self.combat is None:
            return ()
        defender = self.player(self.combat.defending_player_id)
        if (
            blocker not in defender.battlefield
            or blocker.tapped
            or CardType.CREATURE not in self.card_types(blocker)
        ):
            return ()
        return tuple(
            attacker
            for attacker in self.lured_attackers()
            if self._individual_blocking_error(blocker, attacker, defender) is None
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

        self._clear_land_tap_undo_window()
        defender_index = (self.active_player_index + 1) % len(self.players)
        self.combat = CombatState(
            attacking_player_id=self.active_player.id,
            defending_player_id=self.players[defender_index].id,
        )
        self.priority_player_index = defender_index
        self.consecutive_passes = 0
        return self.combat.step

    def declare_attackers(
        self,
        attackers: Iterable[Card],
        bands: Iterable[Iterable[Card]] = (),
    ) -> CombatStep:
        self._require_no_pending_action()
        # Retain the direct engine API as a convenience for simulations and
        # older callers. The UI exposes this method only after priority has
        # closed the response window and entered DECLARE_ATTACKERS.
        if self.combat is not None and self.combat.step is CombatStep.ATTACK_RESPONSE:
            self._empty_mana_pools()
            if self._check_life_loss_checkpoint():
                self.combat = None
                self.combat_creature_effects.clear()
                raise RuntimeError("the game ended at the beginning of the attack")
            if self._begin_river_defender_assignment(
                CombatStep.DECLARE_ATTACKERS
            ):
                raise RuntimeError(
                    "the defender must divide creatures for Raging River first"
                )
            self.combat.step = CombatStep.DECLARE_ATTACKERS
            self.priority_player_index = None
            self.consecutive_passes = 0
        if self.combat is None or self.combat.step is not CombatStep.DECLARE_ATTACKERS:
            raise RuntimeError("the game is not waiting for attackers")
        chosen = list(attackers)
        if len({card.id for card in chosen}) != len(chosen):
            raise ValueError("an attacking creature may only be declared once")
        for card in chosen:
            if card not in self.active_player.battlefield:
                raise ValueError(f"{card.name} is not controlled by the attacker")
            if CardType.CREATURE not in self.card_types(card):
                raise ValueError(f"{card.name} is not a creature")
            if (
                "Wall" in card.definition.subtypes
                and not self.wall_can_attack(card)
            ):
                raise ValueError(f"{card.name} is a Wall and cannot attack")
            if card.tapped:
                raise ValueError(f"{card.name} is tapped")
            if (
                self.has_summoning_sickness(card)
                and not self.may_attack_with_summoning_sickness(card)
            ):
                raise ValueError(f"{card.name} did not begin the turn in play")
            if (
                card.definition.landhome is not None
                and not self.player_controls_land_subtype(
                    self.combat.defending_player_id,
                    self.land_word(card, card.definition.landhome.land_subtype),
                )
            ):
                subtype = self.land_word(
                    card, card.definition.landhome.land_subtype
                )
                raise ValueError(
                    f"{card.name} cannot attack unless the defender "
                    f"controls an {subtype}"
                )
            if not self._island_sanctuary_allows(
                card, self.combat.defending_player_id
            ):
                raise ValueError(
                    f"{card.name} cannot attack through Island Sanctuary"
                )

        declared_bands = [tuple(band) for band in bands]
        banded_ids: set[UUID] = set()
        for band in declared_bands:
            if len(band) < 2:
                raise ValueError("an attacking band must contain at least two creatures")
            if len({card.id for card in band}) != len(band):
                raise ValueError("a creature may only appear once in an attacking band")
            if any(card not in chosen for card in band):
                raise ValueError("every member of a band must be a declared attacker")
            if banded_ids & {card.id for card in band}:
                raise ValueError("an attacker may belong to only one band")
            if not self.can_form_attacking_band(band):
                raise ValueError(
                    "all but at most one creature in an attacking band must have Banding"
                )
            banded_ids.update(card.id for card in band)

        chosen_ids = {card.id for card in chosen}
        required_attackers = [
            card
            for card in self.active_player.battlefield
            if (card.definition.must_attack_if_able or card.id in self.attack_requirements)
            and card.id not in chosen_ids
            and CardType.CREATURE in self.card_types(card)
            and not card.tapped
            and (
                not self.has_summoning_sickness(card)
                or self.may_attack_with_summoning_sickness(card)
            )
            and not (
                "Wall" in card.definition.subtypes
                and not self.wall_can_attack(card)
            )
            and (
                card.definition.landhome is None
                or self.player_controls_land_subtype(
                    self.combat.defending_player_id,
                    self.land_word(card, card.definition.landhome.land_subtype),
                )
            )
            and self._island_sanctuary_allows(
                card, self.combat.defending_player_id
            )
        ]
        if required_attackers:
            raise ValueError(
                f"{required_attackers[0].name} must attack if possible"
            )

        for card in chosen:
            if (
                KeywordAbility.DOES_NOT_TAP_TO_ATTACK
                not in self.creature_abilities(card)
            ):
                self._tap_permanent(card)
            self.attacked_this_turn.add(card.id)
            counter_name = card.definition.loses_counter_when_declared_for_combat
            if counter_name is not None and card.counters.get(counter_name, 0):
                card.counters[counter_name] -= 1
        self.combat.attackers = chosen
        self.combat.attacking_bands = declared_bands
        self.combat.blockers = {card.id: [] for card in chosen}
        if self.raging_river_active() and chosen:
            self.combat.river_choice_card_ids = tuple(card.id for card in chosen)
            self.combat.river_resume_step = CombatStep.ATTACKER_RESPONSE
            self.combat.step = CombatStep.RIVER_ATTACKER_ASSIGNMENT
            self.priority_player_index = None
        else:
            self.combat.step = CombatStep.ATTACKER_RESPONSE
            self.priority_player_index = self.active_player_index
        self.consecutive_passes = 0
        self.attacks_this_turn += 1
        self.check_state_based_actions()
        return self.combat.step

    def declare_blockers(
        self, assignments: dict[Card, Card | Iterable[Card]]
    ) -> CombatStep:
        """Declare each blocker and the attacker it blocks.

        Several blockers may be assigned to one attacker. A creature that can
        block additional attackers maps to an iterable of attackers.
        """

        self._require_no_pending_action()
        # See the matching compatibility path in declare_attackers().
        if self.combat is not None and self.combat.step is CombatStep.ATTACKER_RESPONSE:
            self.combat.step = CombatStep.DECLARE_BLOCKERS
            self.priority_player_index = None
            self.consecutive_passes = 0
        if self.combat is None or self.combat.step is not CombatStep.DECLARE_BLOCKERS:
            raise RuntimeError("the game is not waiting for blockers")
        defender = self.player(self.combat.defending_player_id)
        attackers = {card.id: card for card in self.combat.attackers}
        band_by_member = {
            member.id: band
            for band in self.combat.attacking_bands
            for member in band
        }
        assigned_attackers: dict[Card, tuple[Card, ...]] = {}
        for blocker, assigned in assignments.items():
            requested = (assigned,) if isinstance(assigned, Card) else tuple(assigned)
            distinct_groups: dict[tuple[UUID, ...], Card] = {}
            for attacker in requested:
                group = band_by_member.get(attacker.id, (attacker,))
                representative = next(
                    (
                        member
                        for member in group
                        if self._individual_blocking_error(
                            blocker, member, defender
                        ) is None
                    ),
                    attacker,
                )
                distinct_groups.setdefault(
                    tuple(card.id for card in group), representative
                )
            assigned_attackers[blocker] = tuple(distinct_groups.values())
        declared_blocks = [
            (blocker, attacker)
            for blocker, assigned in assigned_attackers.items()
            for attacker in assigned
        ]
        for blocker, assigned in assigned_attackers.items():
            if len({attacker.id for attacker in assigned}) != len(assigned):
                raise ValueError(
                    f"{blocker.name} cannot block the same attacker twice"
                )
            if (
                blocker.id not in self.combat.blaze_of_glory_blocker_ids
                and len(assigned) > blocker.definition.maximum_attackers_blocked
            ):
                raise ValueError(
                    f"{blocker.name} cannot block {len(assigned)} attackers"
                )
        for blocker_id in self.combat.blaze_of_glory_blocker_ids:
            blocker = next(
                (card for card in defender.battlefield if card.id == blocker_id),
                None,
            )
            if (
                blocker is None
                or blocker.tapped
                or CardType.CREATURE not in self.card_types(blocker)
            ):
                continue
            required = {
                tuple(
                    member.id
                    for member in band_by_member.get(attacker.id, (attacker,))
                )
                for attacker in self.required_blaze_blocks(blocker)
            }
            actual = {
                tuple(
                    member.id
                    for member in band_by_member.get(attacker.id, (attacker,))
                )
                for attacker in assigned_attackers.get(blocker, ())
            }
            if actual != required:
                raise ValueError(
                    f"{blocker.name} must block every attacker it can legally block"
                )
        for blocker in defender.battlefield:
            if blocker.tapped or CardType.CREATURE not in self.card_types(blocker):
                continue
            options = self.lure_block_options(blocker)
            if not options:
                continue
            actual_member_ids = {
                member.id
                for attacker in assigned_attackers.get(blocker, ())
                for member in band_by_member.get(attacker.id, (attacker,))
            }
            if not any(attacker.id in actual_member_ids for attacker in options):
                raise ValueError(
                    f"{blocker.name} must block a Lured attacker if able"
                )
        for blocker, attacker in declared_blocks:
            if blocker not in defender.battlefield:
                raise ValueError(f"{blocker.name} is not controlled by the defender")
            if CardType.CREATURE not in self.card_types(blocker):
                raise ValueError(f"{blocker.name} is not a creature")
            if blocker.tapped:
                raise ValueError(f"{blocker.name} is tapped and cannot block")
            if attacker.id not in attackers:
                raise ValueError(f"{attacker.name} is not attacking")
            river_error = self._raging_river_blocking_error(blocker, attacker)
            if river_error is not None:
                raise ValueError(river_error)
            power_limit = blocker.definition.maximum_blocked_power
            if (
                power_limit is not None
                and self.creature_power(attacker) > power_limit
            ):
                raise ValueError(
                    f"{blocker.name} cannot block a creature with power "
                    f"greater than {power_limit}"
                )

        normalized: list[tuple[Card, Card]] = []
        for blocker, attacker in declared_blocks:
            group = band_by_member.get(attacker.id, (attacker,))
            normalized.extend((blocker, member) for member in group)
            if self.creature_is_unblockable(attacker):
                raise ValueError(f"{attacker.name} cannot be blocked")
            if (
                attacker.definition.cannot_be_blocked_by_subtypes
                & set(blocker.definition.subtypes)
            ):
                raise ValueError(
                    f"{attacker.name} cannot be blocked by {blocker.name}"
                )
            required_subtype = self.blocking_subtype_requirement(attacker)
            if (
                required_subtype is not None
                and required_subtype not in blocker.definition.subtypes
            ):
                raise ValueError(
                    f"only a {required_subtype} can block {attacker.name}"
                )
            blocking_exceptions = self.blocking_exceptions(attacker)
            if blocking_exceptions is not None:
                allowed_colors, allowed_types = blocking_exceptions
                if not (
                    allowed_colors & self.card_colors(blocker)
                    or allowed_types & self.card_types(blocker)
                ):
                    raise ValueError(
                        f"{blocker.name} cannot block {attacker.name}"
                    )
            landwalk_subtypes = {
                ability.landwalk_subtype
                for ability in self.creature_abilities(attacker)
                if ability.landwalk_subtype is not None
            }
            defending_land_subtypes = {
                subtype
                for permanent in defender.battlefield
                if CardType.LAND in permanent.definition.card_types
                for subtype in self.land_subtypes(permanent)
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
                and KeywordAbility.CAN_BLOCK_FLYING
                not in self.creature_abilities(blocker)
            ):
                raise ValueError(
                    f"{blocker.name} cannot block a creature with Flying"
                )
            if self._is_protected_from(
                attacker, self.card_colors(blocker)
            ):
                protected_color = next(
                    color.value
                    for color in self.card_colors(blocker)
                    if color
                    in {
                        ability.protection_color
                        for ability in self.creature_abilities(attacker)
                    }
                )
                raise ValueError(
                    f"{attacker.name} has protection from {protected_color} "
                    f"and cannot be blocked by {blocker.name}"
                )

        for blocker, attacker in normalized:
            self.combat.blockers[attacker.id].append(blocker)
            for effect in attacker.definition.combat_destruction_effects:
                if not (
                    effect.spare_blocking_walls
                    and "Wall" in blocker.definition.subtypes
                ):
                    self.combat.end_of_combat_destruction_ids.add(blocker.id)
            if blocker.definition.combat_destruction_effects:
                # The non-Wall rider applies only to creatures blocking the
                # Basilisk/Cockatrice, not to an attacker they block.
                self.combat.end_of_combat_destruction_ids.add(attacker.id)
        for blocker in assigned_attackers:
            counter_name = blocker.definition.loses_counter_when_declared_for_combat
            if counter_name is not None and blocker.counters.get(counter_name, 0):
                blocker.counters[counter_name] -= 1
        self.combat.step = CombatStep.BLOCKER_RESPONSE
        self.priority_player_index = self.active_player_index
        self.consecutive_passes = 0
        return self.combat.step

    def _attacking_group(self, attacker: Card) -> tuple[Card, ...]:
        """Return the declared band containing an attacker, or that attacker."""

        assert self.combat is not None
        return next(
            (
                band
                for band in self.combat.attacking_bands
                if attacker in band
            ),
            (attacker,),
        )

    def false_orders_current_assignment(self) -> tuple[Card, ...]:
        """Return one representative per group blocked by the pending creature."""

        if not self.pending_false_orders_choices or self.combat is None:
            return ()
        choice = self.pending_false_orders_choices[0]
        blocker = next(
            (
                card
                for card in self.player(self.combat.defending_player_id).battlefield
                if card.id == choice.blocker_id
            ),
            None,
        )
        if blocker is None:
            return ()
        result: list[Card] = []
        seen_groups: set[tuple[UUID, ...]] = set()
        for attacker in self.combat.attackers:
            if blocker not in self.combat.blockers.get(attacker.id, ()):
                continue
            group = self._attacking_group(attacker)
            key = tuple(member.id for member in group)
            if key not in seen_groups:
                seen_groups.add(key)
                result.append(attacker)
        return tuple(result)

    def legal_false_orders_attackers(self) -> tuple[Card, ...]:
        """Return attackers the pending False Orders creature could block."""

        if not self.pending_false_orders_choices or self.combat is None:
            return ()
        choice = self.pending_false_orders_choices[0]
        defender = self.player(self.combat.defending_player_id)
        blocker = next(
            (card for card in defender.battlefield if card.id == choice.blocker_id),
            None,
        )
        if blocker is None or CardType.CREATURE not in self.card_types(blocker):
            return ()
        legal: list[Card] = []
        for attacker in self.combat.attackers:
            group = self._attacking_group(attacker)
            if any(
                self._individual_blocking_error(blocker, member, defender) is None
                for member in group
            ):
                legal.append(attacker)
        return tuple(legal)

    def _rebuild_combat_destruction_assignments(self) -> None:
        """Recalculate Basilisk/Cockatrice delayed destruction after a change."""

        assert self.combat is not None
        self.combat.end_of_combat_destruction_ids.clear()
        for attacker in self.combat.attackers:
            for blocker in self.combat.blockers.get(attacker.id, ()):
                for effect in attacker.definition.combat_destruction_effects:
                    if not (
                        effect.spare_blocking_walls
                        and "Wall" in blocker.definition.subtypes
                    ):
                        self.combat.end_of_combat_destruction_ids.add(blocker.id)
                if blocker.definition.combat_destruction_effects:
                    self.combat.end_of_combat_destruction_ids.add(attacker.id)

    def choose_false_orders_assignment(
        self, player_id: str, attackers: Iterable[Card]
    ) -> None:
        """Commit the False Orders caster's replacement blocking decision."""

        if not self.pending_false_orders_choices:
            raise RuntimeError("there is no False Orders choice pending")
        choice = self.pending_false_orders_choices[0]
        if player_id != choice.chooser_id:
            raise ValueError("only the False Orders caster may choose the new blocks")
        if self.combat is None or self.combat.step is not CombatStep.BLOCKER_RESPONSE:
            self.pending_false_orders_choices.pop(0)
            return
        defender = self.player(self.combat.defending_player_id)
        blocker = next(
            (card for card in defender.battlefield if card.id == choice.blocker_id),
            None,
        )
        if blocker is None or CardType.CREATURE not in self.card_types(blocker):
            self.pending_false_orders_choices.pop(0)
            return

        requested = tuple(attackers)
        if len({card.id for card in requested}) != len(requested):
            raise ValueError("an attacking creature may only be chosen once")
        distinct_groups: dict[tuple[UUID, ...], Card] = {}
        for attacker in requested:
            if attacker not in self.combat.attackers:
                raise ValueError(f"{attacker.name} is not attacking")
            group = self._attacking_group(attacker)
            representative = next(
                (
                    member
                    for member in group
                    if self._individual_blocking_error(blocker, member, defender)
                    is None
                ),
                None,
            )
            if representative is None:
                raise ValueError(f"{blocker.name} cannot legally block that group")
            distinct_groups.setdefault(
                tuple(member.id for member in group), representative
            )
        assigned = tuple(distinct_groups.values())
        if (
            blocker.id not in self.combat.blaze_of_glory_blocker_ids
            and len(assigned) > blocker.definition.maximum_attackers_blocked
        ):
            raise ValueError(
                f"{blocker.name} cannot block {len(assigned)} attacking groups"
            )

        if blocker.id in self.combat.blaze_of_glory_blocker_ids:
            required = {
                tuple(member.id for member in self._attacking_group(attacker))
                for attacker in self.required_blaze_blocks(blocker)
            }
            actual = {
                tuple(member.id for member in self._attacking_group(attacker))
                for attacker in assigned
            }
            if actual != required:
                raise ValueError(
                    f"{blocker.name} must block every attacker it can legally block"
                )

        lure_options = self.lure_block_options(blocker)
        if lure_options:
            assigned_member_ids = {
                member.id
                for attacker in assigned
                for member in self._attacking_group(attacker)
            }
            if not any(card.id in assigned_member_ids for card in lure_options):
                raise ValueError(
                    f"{blocker.name} must still block a Lured attacker if able"
                )

        was_blocking = any(
            blocker in current for current in self.combat.blockers.values()
        )
        for current in self.combat.blockers.values():
            current[:] = [card for card in current if card.id != blocker.id]
        for attacker in assigned:
            for member in self._attacking_group(attacker):
                self.combat.blockers[member.id].append(blocker)

        is_blocking = bool(assigned)
        counter_name = blocker.definition.loses_counter_when_declared_for_combat
        if counter_name is not None and was_blocking != is_blocking:
            if is_blocking and blocker.counters.get(counter_name, 0):
                blocker.counters[counter_name] -= 1
            elif not is_blocking:
                blocker.counters[counter_name] = (
                    blocker.counters.get(counter_name, 0) + 1
                )
        self._rebuild_combat_destruction_assignments()
        self.pending_false_orders_choices.pop(0)
        self.check_state_based_actions()

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
        # Auto-resolved first-strike and regular-damage incidents can nest
        # their continuations; the inner continuation may already have
        # completed combat.
        if self.combat is None:
            return
        doomed_ids = set(self.combat.end_of_combat_destruction_ids)
        self._empty_mana_pools()
        self.combat = None
        self.combat_creature_effects.clear()
        self.pending_life_loss_checkpoint = True
        targets = [
            DestructionTarget(card.id, card.name, True)
            for player in self.players
            for card in player.battlefield
            if card.id in doomed_ids
        ]
        if targets:
            self.pending_destruction = DestructionIncident(targets)
            self._open_destruction_incident()
        else:
            # Ending combat can itself change characteristics, notably
            # Gaea's Liege returning to its defending Forest count.
            self.check_state_based_actions()
            self._restore_pending_context_priority()

    def _validate_damage_assignments(
        self, assignments: dict[Card, dict[Card, int]]
    ) -> dict[Card, dict[Card, int]]:
        """Validate all attacker choices before any combat damage is applied."""

        assert self.combat is not None
        allocations: dict[Card, dict[Card, int]] = {}
        for attacker in self.combat.attackers:
            if attacker.zone is not Zone.BATTLEFIELD:
                continue
            if attacker.id in self.combat.regenerated_card_ids:
                allocations[attacker] = {}
                continue
            power = max(0, self.creature_power(attacker))
            blockers = self.combat.blockers[attacker.id]
            living_blockers = [
                blocker
                for blocker in blockers
                if blocker.zone is Zone.BATTLEFIELD
                and blocker.id not in self.combat.regenerated_card_ids
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
        blocking_creatures = {
            blocker
            for blockers in self.combat.blockers.values()
            for blocker in blockers
        }
        for blocker in blocking_creatures:
            if blocker.id in self.combat.regenerated_card_ids:
                allocations[blocker] = {}
                continue
            blocked_attackers = [
                attacker
                for attacker in self.combat.attackers
                if blocker in self.combat.blockers[attacker.id]
                and attacker.zone is Zone.BATTLEFIELD
                and attacker.id not in self.combat.regenerated_card_ids
            ]
            if len(blocked_attackers) < 2:
                continue
            power = max(0, self.creature_power(blocker))
            allocation = assignments.get(blocker)
            if allocation is None:
                raise ValueError(
                    f"{blocker.name} must divide its damage among attackers"
                )
            if set(allocation) - set(blocked_attackers):
                raise ValueError("combat damage was assigned to an unblocked attacker")
            if any(amount < 0 for amount in allocation.values()):
                raise ValueError("combat damage assignments cannot be negative")
            if sum(allocation.values()) != power:
                raise ValueError(f"{blocker.name} must assign all {power} damage")
            allocations[blocker] = allocation
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
        if self.prevent_combat_damage_this_turn:
            # Fog says that no combat damage is dealt. Do not manufacture an
            # empty first-strike or regular incident: there is consequently
            # no prevention, redirection, or regeneration window to pass
            # through. The caller still performs normal end-of-combat
            # cleanup, including non-damage destruction such as Basilisk's.
            return False
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
                            if blocker.id not in self.combat.regenerated_card_ids:
                                self._deal_damage(
                                    blocker,
                                    amount,
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
                        allocations.get(blocker, {}).get(
                            attacker, max(0, self.creature_power(blocker))
                        ),
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
