"""Combat declaration and damage-assignment behavior for GameState."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable
from uuid import UUID

from .cards import Card
from .damage import DamageIncidentKind, DamageResolutionStep
from .destruction import DestructionIncident, DestructionTarget
from .types import CardType, CombatStep, GameStatus, KeywordAbility, TurnPhase, Zone

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


@dataclass(slots=True)
class AttackRequirement:
    card_id: UUID
    destroy_if_no_attack: bool = True


class CombatMixin:
    """Combat façade methods operating on state owned by ``GameState``."""

    __slots__ = ()

    def _island_sanctuary_allows(self, card: Card, defender_id: str) -> bool:
        if defender_id not in self.island_sanctuary_protected_players:
            return True
        abilities = self.creature_abilities(card)
        return KeywordAbility.FLYING in abilities or any(
            ability.landwalk_subtype == "Island" for ability in abilities
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
                card.definition.landhome.land_subtype,
            )
        )

    def _individual_blocking_error(
        self, blocker: Card, attacker: Card, defender: PlayerState
    ) -> str | None:
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
                    card.definition.landhome.land_subtype,
                )
            ):
                subtype = card.definition.landhome.land_subtype
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
            without_banding = [
                card
                for card in band
                if KeywordAbility.BANDING not in self.creature_abilities(card)
            ]
            if len(without_banding) > 1:
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
                    card.definition.landhome.land_subtype,
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
        blocking_creatures = {
            blocker
            for blockers in self.combat.blockers.values()
            for blocker in blockers
        }
        for blocker in blocking_creatures:
            blocked_attackers = [
                attacker
                for attacker in self.combat.attackers
                if blocker in self.combat.blockers[attacker.id]
                and attacker.zone is Zone.BATTLEFIELD
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
