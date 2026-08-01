import unittest

from beta_magic.casting import (
    PendingActivation,
    PendingCast,
    SpellOnStack,
    TargetingCastingMixin,
)
from beta_magic.characteristics import CharacteristicsMixin
from beta_magic.combat import CombatMixin, CombatState
from beta_magic.game import GameState
from beta_magic.incident_resolution import (
    DamageDestructionMixin,
    PendingPrevention,
)
from beta_magic.turn_flow import PendingTimedEvent, TurnFlowMixin


class GameComponentArchitectureTests(unittest.TestCase):
    def test_game_state_retains_casting_facade(self) -> None:
        self.assertTrue(issubclass(GameState, TargetingCastingMixin))
        self.assertIs(GameState.begin_cast, TargetingCastingMixin.begin_cast)
        self.assertIs(
            GameState.complete_pending_cast,
            TargetingCastingMixin.complete_pending_cast,
        )
        self.assertIs(
            GameState.legal_targets_for,
            TargetingCastingMixin.legal_targets_for,
        )

    def test_casting_state_types_live_with_casting_component(self) -> None:
        self.assertEqual(PendingCast.__module__, "beta_magic.casting")
        self.assertEqual(PendingActivation.__module__, "beta_magic.casting")
        self.assertEqual(SpellOnStack.__module__, "beta_magic.casting")

    def test_game_state_retains_combat_facade(self) -> None:
        self.assertTrue(issubclass(GameState, CombatMixin))
        self.assertIs(GameState.begin_combat, CombatMixin.begin_combat)
        self.assertIs(GameState.declare_attackers, CombatMixin.declare_attackers)
        self.assertIs(GameState.declare_blockers, CombatMixin.declare_blockers)
        self.assertIs(
            GameState.deal_combat_damage,
            CombatMixin.deal_combat_damage,
        )

    def test_combat_state_lives_with_combat_component(self) -> None:
        self.assertEqual(CombatState.__module__, "beta_magic.combat")

    def test_game_state_retains_damage_destruction_facade(self) -> None:
        self.assertTrue(issubclass(GameState, DamageDestructionMixin))
        self.assertIs(
            GameState._begin_damage_incident,
            DamageDestructionMixin._begin_damage_incident,
        )
        self.assertIs(
            GameState.prevent_damage,
            DamageDestructionMixin.prevent_damage,
        )
        self.assertIs(
            GameState._open_destruction_incident,
            DamageDestructionMixin._open_destruction_incident,
        )

    def test_prevention_state_lives_with_incident_coordinator(self) -> None:
        self.assertEqual(
            PendingPrevention.__module__,
            "beta_magic.incident_resolution",
        )

    def test_game_state_retains_turn_flow_facade(self) -> None:
        self.assertTrue(issubclass(GameState, TurnFlowMixin))
        self.assertIs(GameState.start, TurnFlowMixin.start)
        self.assertIs(GameState.advance_phase, TurnFlowMixin.advance_phase)
        self.assertIs(GameState.next_turn, TurnFlowMixin.next_turn)
        self.assertIs(GameState.discard, TurnFlowMixin.discard)
        self.assertIs(
            GameState.choose_upkeep_payment,
            TurnFlowMixin.choose_upkeep_payment,
        )

    def test_timed_event_state_lives_with_turn_flow_component(self) -> None:
        self.assertEqual(PendingTimedEvent.__module__, "beta_magic.turn_flow")

    def test_game_state_retains_characteristics_facade(self) -> None:
        self.assertTrue(issubclass(GameState, CharacteristicsMixin))
        self.assertIs(
            GameState.creature_power,
            CharacteristicsMixin.creature_power,
        )
        self.assertIs(
            GameState.creature_toughness,
            CharacteristicsMixin.creature_toughness,
        )
        self.assertIs(
            GameState.creature_abilities,
            CharacteristicsMixin.creature_abilities,
        )
        self.assertIs(
            GameState.activated_abilities,
            CharacteristicsMixin.activated_abilities,
        )


if __name__ == "__main__":
    unittest.main()
