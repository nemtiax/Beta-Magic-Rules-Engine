import unittest

from beta_magic import (
    HOWLING_MINE,
    ISLAND,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class HowlingMineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [ISLAND] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [ISLAND] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def mine(player: PlayerState, *, tapped: bool = False) -> Card:
        card = Card(
            HOWLING_MINE,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            tapped=tapped,
        )
        player.battlefield.append(card)
        return card

    def enter_draw(self) -> None:
        while self.game.current_phase is not TurnPhase.DRAW:
            self.game.advance_phase()

    def test_definition(self) -> None:
        self.assertEqual(HOWLING_MINE.mana_cost.compact, "2")
        self.assertEqual(HOWLING_MINE.draw_phase_effects[0].amount, 1)

    def test_untapped_mine_gives_the_active_player_an_extra_draw(self) -> None:
        self.mine(self.bob)
        starting_library = len(self.alice.library)

        self.enter_draw()

        self.assertEqual(len(self.alice.hand), 2)
        self.assertEqual(len(self.alice.library), starting_library - 2)

    def test_tapped_mine_has_no_continuous_effect(self) -> None:
        self.mine(self.bob, tapped=True)

        self.enter_draw()

        self.assertEqual(len(self.alice.hand), 1)

    def test_each_untapped_mine_adds_a_draw(self) -> None:
        self.mine(self.alice)
        self.mine(self.bob)

        self.enter_draw()

        self.assertEqual(len(self.alice.hand), 3)

    def test_mine_applies_on_each_players_turn_regardless_of_controller(self) -> None:
        self.mine(self.alice)
        while self.game.current_phase is not TurnPhase.END:
            self.game.advance_phase()
        self.game.advance_phase()

        self.enter_draw()

        self.assertEqual(len(self.bob.hand), 2)


if __name__ == "__main__":
    unittest.main()
