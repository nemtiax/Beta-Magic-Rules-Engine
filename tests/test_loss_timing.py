import unittest

from tests.support import declare_attackers, declare_blockers

from beta_magic import (
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs.lands import FOREST
from beta_magic.card_defs.green import GRIZZLY_BEARS
from beta_magic.types import GameStatus


class LifeLossTimingTests(unittest.TestCase):
    def make_game(self, *, ante: bool = False):
        alice = PlayerState.with_deck("a", "Alice", [FOREST] * 30)
        bob = PlayerState.with_deck("b", "Bob", [FOREST] * 30)
        game = GameState([alice, bob])
        game.start(opening_hand_size=0, shuffle=False, ante=ante)
        while game.current_phase is not TurnPhase.MAIN:
            game.advance_phase()
        return game, alice, bob

    @staticmethod
    def creature(player: PlayerState) -> Card:
        card = Card(
            GRIZZLY_BEARS,
            player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            controller_at_turn_start_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        player.battlefield.append(card)
        return card

    def test_zero_life_can_be_recovered_before_phase_ends(self) -> None:
        game, alice, _ = self.make_game(ante=True)
        alice.life = 3

        game._lose_life(alice, 3)
        game.check_state_based_actions()

        self.assertEqual(alice.life, 0)
        self.assertFalse(alice.has_lost)
        self.assertIs(game.status, GameStatus.IN_PROGRESS)

        game._gain_life(alice, 3)
        game.advance_phase()

        self.assertEqual(alice.life, 3)
        self.assertFalse(alice.has_lost)
        self.assertIs(game.status, GameStatus.IN_PROGRESS)
        self.assertIs(game.current_phase, TurnPhase.DISCARD)

    def test_zero_life_loses_when_the_phase_ends(self) -> None:
        game, alice, _ = self.make_game()
        game._lose_life(alice, alice.life)

        game.advance_phase()

        self.assertTrue(alice.has_lost)
        self.assertIs(game.status, GameStatus.FINISHED)
        self.assertIs(game.current_phase, TurnPhase.MAIN)

    def test_phase_ending_mana_burn_is_included_in_loss_check(self) -> None:
        game, alice, _ = self.make_game()
        alice.life = 1
        alice.mana_pool.green = 1

        game.advance_phase()

        self.assertEqual(alice.life, 0)
        self.assertTrue(alice.has_lost)
        self.assertIs(game.status, GameStatus.FINISHED)

    def test_life_is_checked_at_beginning_and_end_of_attack(self) -> None:
        with self.subTest(boundary="beginning"):
            game, alice, bob = self.make_game()
            alice.life = 0
            game.begin_combat()
            game.pass_priority(bob.id)
            game.pass_priority(alice.id)
            self.assertTrue(alice.has_lost)
            self.assertIs(game.status, GameStatus.FINISHED)

        with self.subTest(boundary="end"):
            game, alice, bob = self.make_game()
            attacker = self.creature(alice)
            bob.life = 1
            game.begin_combat()
            declare_attackers(game, (attacker,))
            declare_blockers(game, {})
            game.advance_combat()
            game.deal_combat_damage()
            self.assertEqual(bob.life, -1)
            self.assertTrue(bob.has_lost)
            self.assertIs(game.status, GameStatus.FINISHED)


if __name__ == "__main__":
    unittest.main()
