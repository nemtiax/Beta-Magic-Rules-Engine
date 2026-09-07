import unittest

from beta_magic import (
    CELESTIAL_PRISM,
    FOREST,
    LIGHTNING_BOLT,
    Card,
    CardType,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class CelestialPrismTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    def permanent(self) -> Card:
        prism = Card(
            CELESTIAL_PRISM,
            self.alice.id,
            controller_id=self.alice.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=self.game.turn_number,
        )
        self.alice.battlefield.append(prism)
        return prism

    def test_definition_offers_five_paid_mana_abilities(self) -> None:
        self.assertEqual(CELESTIAL_PRISM.mana_cost.compact, "3")
        self.assertEqual(
            CELESTIAL_PRISM.card_types, frozenset({CardType.ARTIFACT})
        )
        self.assertEqual(
            [ability.color for ability in CELESTIAL_PRISM.activated_abilities],
            [
                Color.WHITE,
                Color.BLUE,
                Color.BLACK,
                Color.RED,
                Color.GREEN,
            ],
        )
        self.assertEqual(
            [ability.label for ability in CELESTIAL_PRISM.activated_abilities],
            [
                "Pay 2 and tap: Add W",
                "Pay 2 and tap: Add U",
                "Pay 2 and tap: Add B",
                "Pay 2 and tap: Add R",
                "Pay 2 and tap: Add G",
            ],
        )

    def test_pays_two_taps_and_produces_the_chosen_color(self) -> None:
        prism = self.permanent()
        self.alice.mana_pool.colorless = 2

        result = self.game.activate_ability(self.alice.id, prism, 3)

        self.assertIsNone(result)
        self.assertTrue(prism.tapped)
        self.assertEqual(self.alice.mana_pool.colorless, 0)
        self.assertEqual(self.alice.mana_pool.red, 1)
        self.assertEqual(self.game.batch_abilities, [])

    def test_insufficient_mana_does_not_tap_or_produce_mana(self) -> None:
        prism = self.permanent()
        self.alice.mana_pool.colorless = 1

        self.assertFalse(
            self.game.can_activate_ability(self.alice.id, prism, 0)
        )
        with self.assertRaisesRegex(RuntimeError, "not enough mana"):
            self.game.activate_ability(self.alice.id, prism, 0)

        self.assertFalse(prism.tapped)
        self.assertEqual(self.alice.mana_pool.colorless, 1)
        self.assertEqual(self.alice.mana_pool.white, 0)

    def test_cannot_use_a_second_mode_after_tapping(self) -> None:
        prism = self.permanent()
        self.alice.mana_pool.colorless = 4
        self.game.activate_ability(self.alice.id, prism, 0)

        with self.assertRaisesRegex(RuntimeError, "already tapped"):
            self.game.activate_ability(self.alice.id, prism, 1)

    def test_interrupt_activation_preserves_spell_chain_and_resets_passes(self) -> None:
        prism = self.permanent()
        bolt = Card(LIGHTNING_BOLT, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(bolt)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.bob,))

        self.game.pass_priority(self.bob.id)
        self.assertEqual(self.game.consecutive_passes, 1)
        self.alice.mana_pool.colorless = 2
        self.game.activate_ability(self.alice.id, prism, 4)

        self.assertEqual(self.game.consecutive_passes, 0)
        self.assertEqual(self.game.priority_player_index, 0)
        self.assertEqual(self.game.interruptible_spell_id, bolt.id)
        self.assertEqual(self.game.stack, [bolt])
        self.assertEqual(self.game.batch_abilities, [])
        self.assertEqual(self.alice.mana_pool.green, 1)


if __name__ == "__main__":
    unittest.main()
