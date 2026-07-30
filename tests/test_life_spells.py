import unittest

from beta_magic import (
    STREAM_OF_LIFE,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.vanilla_creatures import GRIZZLY_BEARS


class StreamOfLifeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 20
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.spell = self.alice.library.pop()
        self.spell.definition = STREAM_OF_LIFE
        self.spell.zone = Zone.HAND
        self.alice.hand.append(self.spell)

    def test_affordable_maximum_reserves_colored_base_cost(self) -> None:
        self.alice.mana_pool.green = 2
        self.alice.mana_pool.colorless = 3
        self.assertEqual(self.game.maximum_affordable_x(self.spell), 4)

    def test_selected_x_is_paid_stored_and_used_on_resolution(self) -> None:
        self.alice.mana_pool.green = 1
        self.alice.mana_pool.colorless = 5

        pending = self.game.begin_cast(self.spell, x_value=3)
        self.assertEqual(pending.x_value, 3)
        self.game.complete_pending_cast((self.bob,))
        self.assertEqual(self.game.stack_spells[self.spell.id].x_value, 3)
        self.assertEqual(self.alice.mana_pool.total, 2)

        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

        self.assertEqual(self.bob.life, 23)
        self.assertIn(self.spell, self.alice.graveyard)

    def test_cannot_choose_an_unaffordable_x(self) -> None:
        self.alice.mana_pool.green = 1
        with self.assertRaisesRegex(RuntimeError, "not enough mana"):
            self.game.begin_cast(self.spell, x_value=1)

    def test_x_zero_is_legal(self) -> None:
        self.alice.mana_pool.green = 1
        pending = self.game.begin_cast(self.spell, x_value=0)
        self.assertEqual(pending.x_value, 0)


if __name__ == "__main__":
    unittest.main()
