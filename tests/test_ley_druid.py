import unittest

from beta_magic import (
    FOREST,
    LEY_DRUID,
    LIGHTNING_BOLT,
    PLAINS,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class LeyDruidTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(
        player: PlayerState, definition, *, tapped=False, entered_turn=0
    ) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            tapped=tapped,
            entered_battlefield_turn=entered_turn,
        )
        player.battlefield.append(card)
        return card

    @staticmethod
    def hand(player: PlayerState, definition) -> Card:
        card = Card(definition, player.id, zone=Zone.HAND)
        player.hand.append(card)
        return card

    def test_definition_uses_the_beta_interrupt_wording(self) -> None:
        self.assertEqual(LEY_DRUID.mana_cost.compact, "2G")
        self.assertEqual((LEY_DRUID.power, LEY_DRUID.toughness), (1, 1))
        self.assertIn("interrupt", LEY_DRUID.rules_text.lower())

    def test_ability_immediately_untaps_either_players_tapped_land(self) -> None:
        druid = self.permanent(self.alice, LEY_DRUID)
        land = self.permanent(self.bob, PLAINS, tapped=True)

        pending = self.game.activate_ability(self.alice.id, druid, 0)
        self.assertIsNotNone(pending)
        self.assertEqual(self.game.legal_targets_for(), [land])
        self.game.complete_pending_activation((land,))

        self.assertTrue(druid.tapped)
        self.assertFalse(land.tapped)
        self.assertEqual(self.game.batch_abilities, [])
        self.assertIsNone(self.game.priority_player_index)

    def test_untapped_land_is_not_a_legal_target(self) -> None:
        druid = self.permanent(self.alice, LEY_DRUID)
        tapped = self.permanent(self.alice, FOREST, tapped=True)
        untapped = self.permanent(self.alice, FOREST)

        self.game.activate_ability(self.alice.id, druid, 0)

        self.assertEqual(self.game.legal_targets_for(), [tapped])
        self.assertNotIn(untapped, self.game.legal_targets_for())

    def test_summoning_sickness_prevents_paying_the_tap_cost(self) -> None:
        druid = self.permanent(
            self.alice, LEY_DRUID, entered_turn=self.game.turn_number
        )
        self.permanent(self.alice, FOREST, tapped=True)

        with self.assertRaisesRegex(RuntimeError, "did not begin the turn"):
            self.game.activate_ability(self.alice.id, druid, 0)

    def test_interrupt_activation_preserves_spell_chain_and_resets_passes(self) -> None:
        druid = self.permanent(self.alice, LEY_DRUID)
        land = self.permanent(self.alice, FOREST, tapped=True)
        bolt = self.hand(self.alice, LIGHTNING_BOLT)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.bob,))

        self.game.pass_priority(self.bob.id)
        self.assertEqual(self.game.consecutive_passes, 1)
        self.game.activate_ability(self.alice.id, druid, 0)
        self.game.complete_pending_activation((land,))

        self.assertEqual(self.game.consecutive_passes, 0)
        self.assertEqual(self.game.priority_player_index, 0)
        self.assertEqual(self.game.interruptible_spell_id, bolt.id)
        self.assertEqual(self.game.stack, [bolt])
        self.assertEqual(self.game.batch_abilities, [])


if __name__ == "__main__":
    unittest.main()
