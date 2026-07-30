import unittest

from beta_magic import (
    LIGHTNING_BOLT,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS


class SpellStackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 24
        )
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 24)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_hand(player, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        player.hand.append(card)
        return card

    @staticmethod
    def put_in_play(player, definition=GRIZZLY_BEARS):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = player.id
        player.battlefield.append(card)
        return card

    def cast_bolt(self, player, target):
        bolt = self.put_in_hand(player, LIGHTNING_BOLT)
        player.mana_pool.red += 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((target,))
        return bolt

    def pass_current_priority(self):
        player = self.game.players[self.game.priority_player_index]
        return self.game.pass_priority(player.id)

    def test_spell_waits_until_both_players_pass(self) -> None:
        bolt = self.cast_bolt(self.alice, self.bob)

        self.assertEqual(self.game.stack, [bolt])
        self.assertEqual(self.bob.life, 20)
        self.assertEqual(
            self.game.players[self.game.priority_player_index], self.bob
        )

        self.assertIsNone(self.pass_current_priority())
        self.assertEqual(self.bob.life, 20)
        self.assertEqual(self.pass_current_priority(), (bolt,))

        self.assertEqual(self.bob.life, 17)
        self.assertIn(bolt, self.alice.graveyard)
        self.assertIsNone(self.game.priority_player_index)

    def test_response_and_original_resolve_in_one_batch(self) -> None:
        first = self.cast_bolt(self.alice, self.bob)
        response = self.cast_bolt(self.bob, self.alice)

        self.assertEqual(self.game.stack, [first, response])
        self.pass_current_priority()
        self.pass_current_priority()

        self.assertEqual(self.alice.life, 17)
        self.assertEqual(self.bob.life, 17)
        self.assertFalse(self.game.stack)

    def test_two_spells_keep_targets_legal_until_simultaneous_batch_resolves(
        self,
    ) -> None:
        bear = self.put_in_play(self.bob)
        original = self.cast_bolt(self.alice, bear)
        response = self.cast_bolt(self.bob, bear)

        self.pass_current_priority()
        self.pass_current_priority()
        self.assertIn(response, self.bob.graveyard)
        self.assertIn(bear, self.bob.graveyard)
        self.assertIn(original, self.alice.graveyard)
        self.assertFalse(self.game.stack)

    def test_turn_actions_cannot_advance_while_stack_is_nonempty(self) -> None:
        self.cast_bolt(self.alice, self.bob)

        with self.assertRaisesRegex(RuntimeError, "resolve the batch"):
            self.game.advance_phase()

    def test_permanent_spell_also_waits_on_the_stack(self) -> None:
        bear = self.put_in_hand(self.alice, GRIZZLY_BEARS)
        self.alice.mana_pool.green = 1
        self.alice.mana_pool.colorless = 1

        self.game.begin_cast(bear)

        self.assertIn(bear, self.game.stack)
        self.assertNotIn(bear, self.alice.battlefield)
        self.pass_current_priority()
        self.pass_current_priority()
        self.assertIn(bear, self.alice.battlefield)


if __name__ == "__main__":
    unittest.main()
