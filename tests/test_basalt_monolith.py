import unittest

from beta_magic import (
    BASALT_MONOLITH,
    FOREST,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class BasaltMonolithTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    def permanent(self) -> Card:
        monolith = Card(
            BASALT_MONOLITH,
            self.alice.id,
            controller_id=self.alice.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=self.game.turn_number,
        )
        self.alice.battlefield.append(monolith)
        return monolith

    def resolve_batch(self) -> None:
        while self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self) -> None:
        self.assertEqual(BASALT_MONOLITH.mana_cost.compact, "3")
        self.assertEqual(
            BASALT_MONOLITH.card_types, frozenset({CardType.ARTIFACT})
        )
        self.assertFalse(BASALT_MONOLITH.untaps_normally)
        self.assertEqual(
            [ability.label for ability in BASALT_MONOLITH.activated_abilities],
            ["Add CCC", "Pay 3: Untap"],
        )

    def test_mana_ability_resolves_immediately_at_interrupt_speed(self) -> None:
        monolith = self.permanent()

        result = self.game.activate_ability(self.alice.id, monolith, 0)

        self.assertIsNone(result)
        self.assertTrue(monolith.tapped)
        self.assertEqual(self.alice.mana_pool.colorless, 3)
        self.assertEqual(self.game.batch_abilities, [])

    def test_does_not_untap_during_untap_phase(self) -> None:
        monolith = self.permanent()
        monolith.tapped = True

        self.game._enter_phase(TurnPhase.UNTAP)

        self.assertTrue(monolith.tapped)

    def test_paid_untap_is_a_fast_effect_with_a_response_window(self) -> None:
        monolith = self.permanent()
        monolith.tapped = True
        self.alice.mana_pool.colorless = 3

        self.game.activate_ability(self.alice.id, monolith, 1)

        self.assertTrue(monolith.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertEqual(len(self.game.batch_abilities), 1)
        self.assertIs(self.game.batch_abilities[0].source, monolith)
        self.assertIs(self.game.players[self.game.priority_player_index], self.bob)

        self.resolve_batch()
        self.assertFalse(monolith.tapped)

    def test_can_use_its_mana_to_pay_for_its_own_untap(self) -> None:
        monolith = self.permanent()
        self.game.activate_ability(self.alice.id, monolith, 0)

        self.game.activate_ability(self.alice.id, monolith, 1)
        self.resolve_batch()

        self.assertFalse(monolith.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)

    def test_untap_ability_requires_a_tapped_source(self) -> None:
        monolith = self.permanent()
        self.alice.mana_pool.colorless = 3

        with self.assertRaisesRegex(RuntimeError, "already untapped"):
            self.game.activate_ability(self.alice.id, monolith, 1)


if __name__ == "__main__":
    unittest.main()
