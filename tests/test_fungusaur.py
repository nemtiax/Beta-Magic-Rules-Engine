import unittest

from beta_magic import (
    FUNGUSAUR,
    GRIZZLY_BEARS,
    Card,
    DamageIncidentKind,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class FungusaurTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.fungusaur = Card(
            FUNGUSAUR, self.alice.id, controller_id=self.alice.id,
            zone=Zone.BATTLEFIELD,
        )
        self.alice.battlefield.append(self.fungusaur)

    def damage(self, amount: int, *, prevented: int = 0, regenerate: bool = False):
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(self.fungusaur, amount, "test")
        packet = self.game.pending_damage.packets[0]
        packet.prevented = prevented
        if regenerate:
            self.game.pending_damage.regenerated_card_ids.add(self.fungusaur.id)
        self.game._resolve_damage_incident()

    def test_surviving_damage_adds_a_counter_immediately(self) -> None:
        self.damage(1)
        self.assertEqual(self.fungusaur.plus_one_counters, 1)
        self.assertEqual(self.game.creature_power(self.fungusaur), 3)
        self.assertEqual(self.game.creature_toughness(self.fungusaur), 3)
        self.assertEqual(self.fungusaur.damage, 1)

    def test_can_grow_more_than_once_in_one_turn(self) -> None:
        self.damage(1)
        self.damage(1)
        self.assertEqual(self.fungusaur.plus_one_counters, 2)
        self.assertEqual(self.game.creature_toughness(self.fungusaur), 4)

    def test_counter_does_not_rescue_it_from_lethal_damage(self) -> None:
        self.damage(2)
        self.assertIn(self.fungusaur, self.alice.graveyard)
        self.assertEqual(self.fungusaur.plus_one_counters, 0)

    def test_regenerated_fungusaur_survives_and_gets_its_counter(self) -> None:
        self.damage(2, regenerate=True)
        self.assertIn(self.fungusaur, self.alice.battlefield)
        self.assertTrue(self.fungusaur.tapped)
        self.assertEqual(self.fungusaur.damage, 0)
        self.assertEqual(self.fungusaur.plus_one_counters, 1)

    def test_fully_prevented_damage_does_not_add_a_counter(self) -> None:
        self.damage(1, prevented=1)
        self.assertEqual(self.fungusaur.plus_one_counters, 0)

    def test_counters_are_lost_when_fungusaur_leaves_play(self) -> None:
        self.damage(1)
        self.game._move_card(self.fungusaur, Zone.HAND)
        self.assertEqual(self.fungusaur.plus_one_counters, 0)


if __name__ == "__main__":
    unittest.main()
