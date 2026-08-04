"""Target selection and spell-casting behavior for :class:`GameState`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from .abilities import (
    ActivatedDamageAbility,
    ActivatedDestroyAbility,
    ActivatedRegenerationAbility,
    ActivatedTapAbility,
    ActivatedTemporaryAbility,
    ActivatedDiscardAbility,
    ActivatedAttackRequirementAbility,
    ActivatedLandTypeAbility,
    ActivatedUnblockableAbility,
    ActivatedInterruptUntapAbility,
    BatchActivatedAbility,
    TargetRequirement,
)
from .cards import Card
from .events import SpellCastEvent
from .effects import (
    AddManaEffect,
    AttachedLandTypeEffect,
    CounterTargetSpellEffect,
    SirensCallEffect,
)
from .types import (
    BASIC_LAND_SUBTYPES,
    CardType,
    Color,
    CombatStep,
    GameStatus,
    TurnPhase,
    Zone,
)

if TYPE_CHECKING:
    from .game import PlayerState


@dataclass(slots=True)
class PendingCast:
    """A spell whose caster still needs to supply its required targets."""

    spell: Card
    caster_id: str
    x_value: int = 0
    chosen_land_subtype: str | None = None
    chosen_mode: str | None = None


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
    ability: BatchActivatedAbility
    targets: tuple[Card | PlayerState, ...]


@dataclass(slots=True)
class SpellOnStack:
    """Casting choices retained until a spell resolves."""

    card: Card
    caster_id: str
    targets: tuple[Card | PlayerState, ...] = ()
    x_value: int = 0
    chosen_mode: str | None = None


class TargetingCastingMixin:
    """Casting façade methods operating on state owned by ``GameState``."""

    __slots__ = ()

    def cast_creature(self, card: Card) -> None:
        """Pay for and resolve a creature spell from the active player's hand."""

        self._require_no_pending_action()
        self._validate_permanent_cast(card, CardType.CREATURE)
        self._resolve_permanent_spell(card, ())

    def _validate_permanent_cast(
        self,
        card: Card,
        expected_type: CardType | None = None,
        x_value: int = 0,
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
        if not player.mana_pool.can_pay(
            card.definition.mana_cost.with_x(x_value)
        ):
            raise RuntimeError(f"not enough mana to cast {card.name}")

    def _validate_enchantment_cast(self, card: Card) -> None:
        self._validate_permanent_cast(card, CardType.ENCHANTMENT)

    def _caster_for(self, card: Card) -> PlayerState:
        for player in self.players:
            if card in player.hand:
                return player
        raise ValueError("the spell must be in a player's hand")

    def _validate_nonpermanent_cast(
        self, card: Card, x_value: int = 0
    ) -> PlayerState:
        if self.status is not GameStatus.IN_PROGRESS:
            raise RuntimeError("spells can only be cast during a game")
        caster = self._caster_for(card)
        is_instant = CardType.INSTANT in card.definition.card_types
        is_interrupt = CardType.INTERRUPT in card.definition.card_types
        is_sorcery = CardType.SORCERY in card.definition.card_types
        if not (is_instant or is_interrupt or is_sorcery):
            raise ValueError(
                f"{card.name} is not an instant, interrupt, or sorcery"
            )
        if not is_interrupt and any(
            CardType.INTERRUPT in spell.definition.card_types
            for spell in self.stack
        ):
            raise RuntimeError(
                "an interrupt sequence must finish before another spell"
            )
        if is_interrupt:
            target_requirement = card.definition.target_requirement
            can_target_in_play = (
                target_requirement is not None
                and (
                    target_requirement.zone is Zone.BATTLEFIELD
                    or Zone.BATTLEFIELD
                    in target_requirement.additional_zones
                )
            )
            has_interruptible_spell = (
                self.interruptible_spell_id is not None
                and any(
                    candidate.id == self.interruptible_spell_id
                    for candidate in self.stack
                )
            )
            can_resolve_standalone = any(
                isinstance(effect, AddManaEffect)
                for effect in card.definition.spell_effects
            )
            if (
                not has_interruptible_spell
                and not can_target_in_play
                and not can_resolve_standalone
            ):
                raise RuntimeError(
                    "interrupts can only be cast immediately on the current spell"
                )
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
        if not caster.mana_pool.can_pay(
            card.definition.mana_cost.with_x(x_value)
        ):
            raise RuntimeError(f"not enough mana to cast {card.name}")
        if any(
            isinstance(effect, SirensCallEffect)
            for effect in card.definition.spell_effects
        ) and (
            caster is self.active_player
            or self.attacks_this_turn
            or self.combat is not None
        ):
            raise RuntimeError(
                f"{card.name} can only be cast during an opponent's turn before the attack"
            )
        return caster

    def _validate_cast(self, card: Card, x_value: int = 0) -> PlayerState:
        if x_value < 0:
            raise ValueError("X cannot be negative")
        if not card.definition.mana_cost.x_symbols and x_value:
            raise ValueError(f"{card.name} has no X in its mana cost")
        caster = self._caster_for(card)
        if (
            self.priority_player_index is not None
            and caster is not self.players[self.priority_player_index]
        ):
            raise RuntimeError(
                f"{self.players[self.priority_player_index].name} has priority"
            )
        if card.definition.is_permanent:
            self._validate_permanent_cast(card, x_value=x_value)
            return caster
        return self._validate_nonpermanent_cast(card, x_value)

    def maximum_affordable_x(self, card: Card) -> int:
        """Largest X the card's current holder can pay."""

        caster = self._caster_for(card)
        cost = card.definition.mana_cost
        if not cost.x_symbols:
            raise ValueError(f"{card.name} has no X in its mana cost")
        if not caster.mana_pool.can_pay(cost.with_x(0)):
            raise RuntimeError(f"not enough mana to cast {card.name}")
        remaining = caster.mana_pool.total - cost.with_x(0).mana_value
        return remaining // cost.x_symbols

    def begin_cast(
        self,
        card: Card,
        x_value: int = 0,
        *,
        land_subtype: str | None = None,
        mode: str | None = None,
    ) -> PendingCast | None:
        """Cast an untargeted spell or wait for the spell's targets."""

        self._require_no_pending_action(allow_stack=True)
        caster = self._validate_cast(card, x_value)
        self._validate_land_type_choice(card, land_subtype)
        self._validate_casting_mode(card, mode)

        if card.definition.target_requirement is not None:
            if not self.legal_targets_for(
                card, mode=mode
            ) and not self.legal_player_targets_for(card):
                raise RuntimeError(f"there are no legal targets for {card.name}")
            self.pending_cast = PendingCast(
                card, caster.id, x_value, land_subtype, mode
            )
            return self.pending_cast
        self._cast_spell(
            card, (), caster, x_value, chosen_land_subtype=land_subtype,
            chosen_mode=mode,
        )
        return None

    def _validate_casting_mode(self, card: Card, mode: str | None) -> None:
        modes = card.definition.casting_modes
        if modes and mode not in modes:
            raise ValueError(f"{card.name} requires a casting mode choice")
        if not modes and mode is not None:
            raise ValueError(f"{card.name} does not have casting modes")

    def _validate_land_type_choice(
        self, card: Card, land_subtype: str | None
    ) -> None:
        """Validate a cast-time basic-land-type choice, when required."""

        chooses_land_type = any(
            isinstance(effect, AttachedLandTypeEffect)
            and effect.chosen_basic_subtype
            for effect in card.definition.land_type_effects
        )
        if chooses_land_type:
            if land_subtype not in BASIC_LAND_SUBTYPES:
                raise ValueError(
                    f"{card.name} requires a basic land type choice"
                )
        elif land_subtype is not None:
            raise ValueError(f"{card.name} does not choose a land type")

    def legal_targets_for(
        self, card: Card | None = None, *, mode: str | None = None
    ) -> list[Card]:
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
        if requirement.zone is None:
            return []
        caster_id = (
            self.pending_cast.caster_id
            if self.pending_cast is not None
            and self.pending_cast.spell is spell
            else pending_ability.controller_id
            if pending_ability is not None
            else spell.controller_id or spell.owner_id
        )
        target_zones = requirement.additional_zones | (
            frozenset({requirement.zone})
            if requirement.zone is not None
            else frozenset()
        )
        chosen_mode = (
            mode
            if mode is not None
            else self.pending_cast.chosen_mode
            if self.pending_cast is not None
            and self.pending_cast.spell is spell
            else None
        )
        if spell is not None and spell.definition.casting_mode_target_zones:
            try:
                mode_index = spell.definition.casting_modes.index(chosen_mode)
            except ValueError:
                return []
            target_zones &= frozenset(
                {spell.definition.casting_mode_target_zones[mode_index]}
            )
        if Zone.STACK in target_zones:
            interrupt_root_index = next(
                (
                    index
                    for index, candidate in enumerate(self.stack)
                    if candidate.id == self.interruptible_spell_id
                ),
                len(self.stack),
            )
            if CardType.INTERRUPT in spell.definition.card_types:
                stack_candidates = (
                    self.stack[interrupt_root_index:]
                    if interrupt_root_index < len(self.stack)
                    else []
                )
            else:
                stack_candidates = self.stack
        else:
            stack_candidates = []
        candidates = [
            *stack_candidates,
            *[
                candidate
                for player in self.players
                for zone in target_zones - {Zone.STACK}
                for candidate in player.cards_in(zone)
            ],
        ]
        legal = [
            candidate
            for candidate in candidates
            if self._requirement_accepts_card(
                requirement,
                candidate,
                caster_id,
                source_colors=(
                    self.card_colors(spell)
                    if spell is not None
                    else self.card_colors(pending_ability.source)
                    if pending_ability is not None
                    else frozenset()
                ),
            )
        ]
        if pending_ability is not None:
            pending_effect = self.activated_abilities(
                pending_ability.source
            )[pending_ability.ability_index]
            if isinstance(pending_effect, ActivatedAttackRequirementAbility):
                legal = [
                    candidate for candidate in legal
                    if candidate.summoned_turn != self.turn_number
                ]
            if (
                isinstance(pending_effect, ActivatedTemporaryAbility)
                and pending_effect.toughness_less_than_source_power
            ):
                source_power = self.creature_power(pending_ability.source)
                legal = [
                    candidate
                    for candidate in legal
                    if self.creature_toughness(candidate) < source_power
                ]
        counter_effect = next(
            (
                effect
                for effect in (
                    spell.definition.spell_effects
                    if spell is not None
                    else ()
                )
                if isinstance(effect, CounterTargetSpellEffect)
                and effect.x_equals_target_cost
            ),
            None,
        )
        if (
            counter_effect is not None
            and self.pending_cast is not None
            and self.pending_cast.spell is spell
        ):
            declared_x = self.pending_cast.x_value
            legal = [
                candidate
                for candidate in legal
                if candidate.id in self.stack_spells
                and candidate.definition.mana_cost.with_x(
                    self.stack_spells[candidate.id].x_value
                ).mana_value
                == declared_x
            ]
        return legal

    def _requirement_accepts_card(
        self,
        requirement: TargetRequirement,
        card: Card,
        caster_id: str | None = None,
        *,
        check_tapped: bool = True,
        source_colors: frozenset[Color] = frozenset(),
    ) -> bool:
        if not requirement.accepts_card(
            card,
            check_tapped=check_tapped,
            current_colors=self.card_colors(card),
            current_card_types=self.card_types(card),
        ):
            return False
        if self._is_protected_from(card, source_colors):
            return False
        if requirement.owner_only and card.owner_id != caster_id:
            return False
        if requirement.controller_only and card.controller_id != caster_id:
            return False
        if (
            requirement.active_player_only
            and card.controller_id != self.active_player.id
        ):
            return False
        if (
            requirement.maximum_power is not None
            and (
                CardType.CREATURE not in self.card_types(card)
                or self.creature_power(card) > requirement.maximum_power
            )
        ):
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

    def _is_protected_from(
        self, creature: Card, colors: frozenset[Color]
    ) -> bool:
        """Whether an in-play creature has FAQ protection from a source color."""

        if (
            CardType.CREATURE not in self.card_types(creature)
            or creature.zone is not Zone.BATTLEFIELD
        ):
            return False
        protected_colors = {
            ability.protection_color
            for ability in self.creature_abilities(creature)
            if ability.protection_color is not None
        }
        return bool(protected_colors & colors)

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
        players = list(self.players)
        if requirement.opponent_only:
            controller_id = (
                spell.owner_id
                if spell is not None
                else pending_ability.controller_id
            )
            players = [player for player in players if player.id != controller_id]
        return players

    def _pending_ability_requirement(
        self, pending: PendingActivation | None
    ) -> TargetRequirement | None:
        if pending is None:
            return None
        ability = self.activated_abilities(pending.source)[pending.ability_index]
        return (
            ability.target_requirement
            if isinstance(
                ability,
                (
                    ActivatedDamageAbility,
                    ActivatedDestroyAbility,
                    ActivatedTapAbility,
                    ActivatedUnblockableAbility,
                    ActivatedTemporaryAbility,
                    ActivatedDiscardAbility,
                    ActivatedAttackRequirementAbility,
                    ActivatedLandTypeAbility,
                    ActivatedInterruptUntapAbility,
                ),
            )
            else None
        )

    def complete_pending_activation(
        self, targets: Iterable[Card | PlayerState]
    ) -> None:
        """Choose targets, pay tap costs, and declare an activated fast effect."""

        if self.pending_activation is None:
            raise RuntimeError("there is no activated ability waiting for targets")
        pending = self.pending_activation
        ability = self.activated_abilities(pending.source)[pending.ability_index]
        assert isinstance(
            ability,
            (
                ActivatedDamageAbility,
                ActivatedDestroyAbility,
                ActivatedTapAbility,
                ActivatedUnblockableAbility,
                ActivatedTemporaryAbility,
                ActivatedDiscardAbility,
                ActivatedAttackRequirementAbility,
                ActivatedLandTypeAbility,
                ActivatedInterruptUntapAbility,
            ),
        )
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
            self._tap_permanent(pending.source)
        if isinstance(
            ability,
            (
                ActivatedDamageAbility,
                ActivatedDestroyAbility,
                ActivatedTapAbility,
                ActivatedUnblockableAbility,
                ActivatedTemporaryAbility,
                ActivatedDiscardAbility,
                ActivatedAttackRequirementAbility,
                ActivatedLandTypeAbility,
                ActivatedInterruptUntapAbility,
            ),
        ):
            player.mana_pool.pay(ability.mana_cost)
        if isinstance(ability, ActivatedInterruptUntapAbility):
            for target in chosen:
                if isinstance(target, Card):
                    target.tapped = False
            # Interrupt-speed permanent abilities resolve immediately. Taking
            # the action invalidates earlier passes without closing or
            # replacing the current spell's interrupt window.
            self.consecutive_passes = 0
            self.check_state_based_actions()
            return
        self.batch_abilities.append(
            AbilityOnStack(
                pending.source,
                pending.source.name,
                player.id,
                ability,
                chosen,
            )
        )
        self.interruptible_spell_id = None
        self.check_state_based_actions()
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
        legal_cards = self.legal_targets_for(
            pending.spell, mode=pending.chosen_mode
        )
        legal_players = self.legal_player_targets_for(pending.spell)
        if any(
            target not in (
                legal_cards if isinstance(target, Card) else legal_players
            )
            for target in chosen
        ):
            raise ValueError(f"illegal target for {pending.spell.name}")
        counter_effect = next(
            (
                effect
                for effect in pending.spell.definition.spell_effects
                if isinstance(effect, CounterTargetSpellEffect)
            ),
            None,
        )
        if counter_effect is not None and counter_effect.x_equals_target_cost:
            target = chosen[0]
            assert isinstance(target, Card)
            target_spell = self.stack_spells[target.id]
            target_cost = target.definition.mana_cost.with_x(
                target_spell.x_value
            ).mana_value
            if pending.x_value != target_cost:
                raise ValueError(
                    f"X must equal {target.name}'s casting cost ({target_cost})"
                )
        caster = self.player(pending.caster_id)
        validated_caster = self._validate_cast(
            pending.spell, pending.x_value
        )
        if caster is not validated_caster:
            raise RuntimeError("the pending spell's caster has changed")
        self.pending_cast = None
        self._cast_spell(
            pending.spell,
            chosen,
            caster,
            pending.x_value,
            chosen_land_subtype=pending.chosen_land_subtype,
            chosen_mode=pending.chosen_mode,
        )

    def cancel_pending_cast(self) -> None:
        if self.pending_cast is None:
            raise RuntimeError("there is no pending spell to cancel")
        self.pending_cast = None

    def _resolve_permanent_spell(
        self,
        card: Card,
        targets: tuple[Card, ...],
        *,
        chosen_land_subtype: str | None = None,
    ) -> None:
        player = self.active_player
        player.mana_pool.pay(card.definition.mana_cost)
        card.controller_id = player.id
        self._move_card(card, Zone.BATTLEFIELD)
        card.entered_battlefield_turn = self.turn_number
        card.enchanted_card_id = targets[0].id if targets else None
        if card.definition.taps_attached_on_entry and targets:
            self._tap_permanent(targets[0])
        card.chosen_land_subtype = chosen_land_subtype
        self._reconcile_control_effects()
        self.events.append(
            SpellCastEvent(
                card_id=card.id,
                card_name=card.name,
                caster_id=player.id,
                target_ids=tuple(target.id for target in targets),
                target_names=tuple(target.name for target in targets),
            )
        )
        self._record_spell_cast_opportunity(card)
        self.check_state_based_actions()

    def _cast_spell(
        self,
        card: Card,
        targets: tuple[Card | PlayerState, ...],
        caster: PlayerState,
        x_value: int = 0,
        *,
        chosen_land_subtype: str | None = None,
        chosen_mode: str | None = None,
    ) -> None:
        """Pay for a spell and add it to the current response batch."""

        caster.mana_pool.pay(card.definition.mana_cost.with_x(x_value))
        card.controller_id = caster.id
        self._move_card(card, Zone.STACK)
        card.chosen_land_subtype = chosen_land_subtype
        if (
            CardType.INTERRUPT not in card.definition.card_types
            or self.interruptible_spell_id is None
        ):
            self.interruptible_spell_id = card.id
        self.stack_spells[card.id] = SpellOnStack(
            card, caster.id, targets, x_value, chosen_mode
        )
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
                    if not isinstance(target, Card)
                ),
                target_names=tuple(target.name for target in targets),
            )
        )
        self._record_spell_cast_opportunity(card)
        self.priority_player_index = (
            self.players.index(caster) + 1
        ) % len(self.players)
        self.consecutive_passes = 0
