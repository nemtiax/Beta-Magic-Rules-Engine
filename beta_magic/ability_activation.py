"""Activated-ability declaration and validation for :class:`GameState`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .abilities import (
    ActivatedAbility,
    ActivatedAnimationAbility,
    ActivatedAttackRequirementAbility,
    ActivatedDamageAbility,
    ActivatedGlobalDamageAbility,
    ActivatedDestroyAbility,
    ActivatedDestroyAllAbility,
    ActivatedDiscardAbility,
    ActivatedDrawAbility,
    ActivatedCreateTokenAbility,
    ActivatedEventDrawAbility,
    ActivatedEventLifeGainAbility,
    ActivatedExtraTurnAbility,
    ActivatedInterruptUntapAbility,
    ActivatedCounterSpellAbility,
    ActivatedLandTypeAbility,
    ActivatedManaAbility,
    ActivatedPreventDamageAbility,
    ActivatedRevealHandAbility,
    ActivatedPumpAbility,
    ActivatedRedirectDamageAbility,
    ActivatedRegenerationAbility,
    ActivatedTapAbility,
    ActivatedTemporaryAbility,
    ActivatedUntapAbility,
    ActivatedUnblockableAbility,
)
from .cards import Card
from .casting import AbilityOnStack, PendingActivation
from .incident_resolution import PendingPrevention, PendingRedirection
from .types import CardType, CombatStep, GameStatus, TurnPhase, Zone

if TYPE_CHECKING:
    from .game import PlayerState


class AbilityActivationMixin:
    """Declare activated abilities and validate their costs and timing."""

    __slots__ = ()

    def activate_ability(
        self, player_id: str, card: Card, ability_index: int, *, amount: int = 1
    ) -> PendingActivation | None:
        """Pay a permanent ability's costs and apply its effect."""

        try:
            selected_ability = self.activated_abilities(card)[ability_index]
        except IndexError as error:
            raise ValueError(f"{card.name} has no such activated ability") from error
        if isinstance(selected_ability, ActivatedPreventDamageAbility):
            if (
                selected_ability.prevents_life_loss
                and self.pending_damage is None
            ):
                player, ability = self._validate_ability_activation(
                    player_id, card, ability_index
                )
                self.pay_mana(player, self.ability_mana_cost(card, ability.mana_cost))
                if ability.tap_cost:
                    self._tap_permanent(card)
                assert ability.amount is not None
                self.life_loss_prevention[player.id] = (
                    self.life_loss_prevention.get(player.id, 0) + ability.amount
                )
                self.consecutive_passes = 0
                return None
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
                prevents_life_loss=ability.prevents_life_loss,
            )
            return None
        if isinstance(selected_ability, ActivatedRedirectDamageAbility):
            player, _ = self._validate_redirection_activation(
                player_id, card, ability_index
            )
            self.pending_redirection = PendingRedirection(
                card, player.id, ability_index
            )
            return None
        if isinstance(selected_ability, ActivatedRegenerationAbility):
            player, ability, affected_card = self._validate_regeneration_activation(
                player_id, card, ability_index
            )
            if ability.counter_cost is not None:
                card.counters[ability.counter_cost] -= 1
            else:
                self.pay_mana(player, ability.mana_cost)
            self._tap_permanent(affected_card)
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
        if isinstance(ability, ActivatedGlobalDamageAbility):
            if amount < 1:
                raise ValueError("activation amount must be at least 1")
            cost = ability.mana_cost_per_damage.scaled(amount)
            if not self.can_pay_mana(player, cost):
                raise RuntimeError(f"not enough mana to activate {card.name}")
            self.pay_mana(player, cost)
            self.batch_abilities.append(
                AbilityOnStack(card, card.name, player.id, ability, (), amount)
            )
            self.interruptible_spell_id = None
            self.priority_player_index = (
                self.players.index(player) + 1
            ) % len(self.players)
            self.consecutive_passes = 0
            return None
        if isinstance(
            ability,
            (
                ActivatedDamageAbility,
                ActivatedGlobalDamageAbility,
                ActivatedDestroyAbility,
                ActivatedTapAbility,
                ActivatedUnblockableAbility,
                ActivatedTemporaryAbility,
                ActivatedDiscardAbility,
                ActivatedAttackRequirementAbility,
                ActivatedLandTypeAbility,
                ActivatedInterruptUntapAbility,
                ActivatedCounterSpellAbility,
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
            self.pay_mana(player, ability.mana_cost)
            if ability.tap_cost:
                self._tap_permanent(card)
            player.mana_pool.add(ability.color, ability.amount)
            if CardType.LAND in card.definition.card_types:
                for owner in self.players:
                    for source in owner.battlefield:
                        if not self.continuous_permanent_is_active(source):
                            continue
                        for effect in source.definition.land_mana_bonus_effects:
                            player.mana_pool.add(ability.color, effect.amount)
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
            self.pay_mana(player, ability.mana_cost)
            if ability.tap_cost:
                self._tap_permanent(card)
            self.batch_abilities.append(
                AbilityOnStack(card, card.name, player.id, ability, ())
            )
            self.interruptible_spell_id = None
            self.priority_player_index = (
                self.players.index(player) + 1
            ) % len(self.players)
            self.consecutive_passes = 0
            return None
        if isinstance(ability, ActivatedCreateTokenAbility):
            self.pay_mana(player, ability.mana_cost)
            if ability.tap_cost:
                self._tap_permanent(card)
            self.batch_abilities.append(
                AbilityOnStack(card, card.name, player.id, ability, ())
            )
            self.interruptible_spell_id = None
            self.priority_player_index = (
                self.players.index(player) + 1
            ) % len(self.players)
            self.consecutive_passes = 0
            return None
        if isinstance(ability, ActivatedRevealHandAbility):
            self.pay_mana(player, ability.mana_cost)
            if ability.tap_cost:
                self._tap_permanent(card)
            self.batch_abilities.append(
                AbilityOnStack(card, card.name, player.id, ability, ())
            )
            self.interruptible_spell_id = None
            self.priority_player_index = (
                self.players.index(player) + 1
            ) % len(self.players)
            self.consecutive_passes = 0
            return None
        if isinstance(ability, ActivatedDestroyAllAbility):
            self.pay_mana(player, ability.mana_cost)
            if ability.tap_cost:
                self._tap_permanent(card)
            self.batch_abilities.append(
                AbilityOnStack(card, card.name, player.id, ability, ())
            )
            self.interruptible_spell_id = None
            self.priority_player_index = (
                self.players.index(player) + 1
            ) % len(self.players)
            self.consecutive_passes = 0
            return None
        if isinstance(ability, ActivatedExtraTurnAbility):
            if ability.tap_cost:
                self._tap_permanent(card)
            self.batch_abilities.append(
                AbilityOnStack(card, card.name, player.id, ability, ())
            )
            self.interruptible_spell_id = None
            self.priority_player_index = (
                self.players.index(player) + 1
            ) % len(self.players)
            self.consecutive_passes = 0
            return None
        if isinstance(ability, ActivatedUntapAbility):
            self.pay_mana(player, ability.mana_cost)
            self.batch_abilities.append(
                AbilityOnStack(card, card.name, player.id, ability, (card,))
            )
            self.interruptible_spell_id = None
            self.priority_player_index = (
                self.players.index(player) + 1
            ) % len(self.players)
            self.consecutive_passes = 0
            return None
        if isinstance(
            ability, (ActivatedEventLifeGainAbility, ActivatedEventDrawAbility)
        ):
            opportunity = self._matching_event_opportunities(card, ability)[0]
            if isinstance(ability, ActivatedEventLifeGainAbility):
                self.pay_mana(player, ability.mana_cost)
            self.event_ability_uses.add((card.id, opportunity.id))
            self.batch_abilities.append(
                AbilityOnStack(
                    card,
                    card.name,
                    player.id,
                    ability,
                    (),
                    event_id=opportunity.id,
                )
            )
            self.interruptible_spell_id = None
            self.priority_player_index = (
                self.players.index(player) + 1
            ) % len(self.players)
            self.consecutive_passes = 0
            return None
        if isinstance(ability, ActivatedAnimationAbility):
            self.pay_mana(player, ability.mana_cost)
            self.batch_abilities.append(
                AbilityOnStack(card, card.name, player.id, ability, (card,))
            )
            self.ability_activations_this_turn[card.id] = (
                self.ability_activations_this_turn.get(card.id, 0) + 1
            )
            self.interruptible_spell_id = None
            self.priority_player_index = (
                self.players.index(player) + 1
            ) % len(self.players)
            self.consecutive_passes = 0
            return None

        self.pay_mana(player, ability.mana_cost)
        affected_card = (
            self._attached_creature(card)
            if ability.affects_attached_creature
            else card
        )
        self.batch_abilities.append(
            AbilityOnStack(card, card.name, player.id, ability, (affected_card,))
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
        if self.combat is not None and self.combat.step in {
            CombatStep.DECLARE_ATTACKERS,
            CombatStep.DECLARE_BLOCKERS,
        }:
            raise RuntimeError(
                "abilities cannot be activated during a combat declaration"
            )
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
                ActivatedAnimationAbility,
                ActivatedPumpAbility,
                ActivatedDamageAbility,
                ActivatedGlobalDamageAbility,
                ActivatedDestroyAbility,
                ActivatedDestroyAllAbility,
                ActivatedTapAbility,
                ActivatedUnblockableAbility,
                ActivatedTemporaryAbility,
                ActivatedDiscardAbility,
                ActivatedAttackRequirementAbility,
                ActivatedLandTypeAbility,
                ActivatedDrawAbility,
                ActivatedCreateTokenAbility,
                ActivatedRevealHandAbility,
                ActivatedExtraTurnAbility,
                ActivatedUntapAbility,
                ActivatedInterruptUntapAbility,
                ActivatedCounterSpellAbility,
                ActivatedEventLifeGainAbility,
                ActivatedEventDrawAbility,
                ActivatedPreventDamageAbility,
                ActivatedRedirectDamageAbility,
            ),
        ):
            raise ValueError("unsupported activated ability")
        if (
            (self.pending_damage is not None or self.pending_destruction is not None)
            and not isinstance(
                ability,
                (
                    ActivatedManaAbility,
                    ActivatedPreventDamageAbility,
                    ActivatedRedirectDamageAbility,
                ),
            )
        ):
            raise RuntimeError(
                "only mana, prevention, redirection, and regeneration abilities "
                "can be used during damage resolution"
            )
        if isinstance(ability, ActivatedAnimationAbility):
            if self.combat is None:
                raise RuntimeError(
                    f"{card.name} can only be animated during an attack"
                )
            if (
                ability.once_per_turn
                and self.ability_activations_this_turn.get(card.id, 0)
            ):
                raise RuntimeError(f"{card.name} has already been activated this turn")
        if isinstance(ability, ActivatedAttackRequirementAbility) and (
            player is self.active_player
            or self.attacks_this_turn
            or self.combat is not None
        ):
            raise RuntimeError(
                f"{card.name} can only be activated during an opponent's turn before the attack"
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
                    ActivatedManaAbility,
                    ActivatedPumpAbility,
                    ActivatedDamageAbility,
                    ActivatedDestroyAbility,
                    ActivatedDestroyAllAbility,
                    ActivatedTapAbility,
                    ActivatedUnblockableAbility,
                    ActivatedTemporaryAbility,
                    ActivatedDiscardAbility,
                    ActivatedAttackRequirementAbility,
                    ActivatedLandTypeAbility,
                    ActivatedDrawAbility,
                    ActivatedCreateTokenAbility,
                    ActivatedRevealHandAbility,
                    ActivatedExtraTurnAbility,
                    ActivatedUntapAbility,
                    ActivatedInterruptUntapAbility,
                    ActivatedCounterSpellAbility,
                    ActivatedEventLifeGainAbility,
                    ActivatedPreventDamageAbility,
                    ActivatedAnimationAbility,
                ),
            )
            and not self.can_pay_mana(
                player, self.ability_mana_cost(card, ability.mana_cost)
            )
        ):
            raise RuntimeError(
                f"not enough mana to activate {card.name}: {ability.label}"
            )
        if isinstance(
            ability, (ActivatedEventLifeGainAbility, ActivatedEventDrawAbility)
        ):
            if card.tapped and CardType.ARTIFACT in card.definition.card_types:
                raise RuntimeError(f"{card.name} is tapped and cannot be used")
            if not self._matching_event_opportunities(card, ability):
                raise RuntimeError(f"{card.name} has no matching event to catch")
        has_tap_cost = (
            isinstance(ability, ActivatedManaAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedPreventDamageAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedRevealHandAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedDamageAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedDestroyAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedDestroyAllAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedTapAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedUnblockableAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedTemporaryAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedDrawAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedCreateTokenAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedExtraTurnAbility) and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedAttackRequirementAbility)
            and ability.tap_cost
        ) or (
            isinstance(ability, ActivatedLandTypeAbility) and ability.tap_cost
        ) or (
            isinstance(
                ability,
                (ActivatedInterruptUntapAbility, ActivatedCounterSpellAbility),
            )
            and ability.tap_cost
        )
        if (
            has_tap_cost
            and card.definition.tap_abilities_require_paid_upkeep
            and card.id in self.unpaid_tap_upkeep_ids
        ):
            raise RuntimeError(
                f"{card.name}'s upkeep must be paid before it can be tapped"
            )
        if has_tap_cost and card.tapped:
            raise RuntimeError(f"{card.name} is already tapped")
        if isinstance(ability, ActivatedUntapAbility) and not card.tapped:
            raise RuntimeError(f"{card.name} is already untapped")
        if (
            has_tap_cost
            and CardType.CREATURE in card.definition.card_types
            and self.has_summoning_sickness(card)
        ):
            raise RuntimeError(
                f"{card.name} did not begin the turn under its controller's control"
            )
        return player, ability

    def maximum_affordable_ability_amount(
        self, player_id: str, card: Card, ability_index: int
    ) -> int:
        """Largest repeated payment affordable for a scalable ability."""

        player = self.player(player_id)
        try:
            ability = self.activated_abilities(card)[ability_index]
        except IndexError as error:
            raise ValueError(f"{card.name} has no such activated ability") from error
        if not isinstance(ability, ActivatedGlobalDamageAbility):
            raise ValueError("that ability does not accept a variable payment")
        amount = 0
        while self.can_pay_mana(
            player,
            ability.mana_cost_per_damage.scaled(amount + 1)
        ):
            amount += 1
        if not amount:
            raise RuntimeError(f"not enough mana to activate {card.name}")
        return amount

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
            elif isinstance(ability, ActivatedRedirectDamageAbility):
                self._validate_redirection_activation(
                    player_id, card, ability_index
                )
            else:
                self._validate_ability_activation(player_id, card, ability_index)
        except (KeyError, ValueError, RuntimeError):
            return False
        return True
