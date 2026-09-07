import unittest

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.black import DEMONIC_ATTORNEY
from beta_magic.card_defs.lands import FOREST, PLAINS, SWAMP
from beta_magic.types import GameStatus
from beta_magic.ui import GameViewModel


class DemonicAttorneyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [PLAINS] * 8)
        self.bob = PlayerState.with_deck("b", "Bob", [FOREST] * 8)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False, ante=True)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    def resolve_attorney(self) -> Card:
        card = Card(DEMONIC_ATTORNEY, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(card)
        self.alice.mana_pool.black = 2
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(card)
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        return card

    def test_resolution_prompts_casters_opponent(self) -> None:
        card = self.resolve_attorney()
        choice = self.game.pending_demonic_attorney_choices[0]
        self.assertEqual((choice.caster_id, choice.opponent_id), ("a", "b"))
        self.assertIn(card, self.alice.graveyard)

    def test_declining_to_concede_adds_each_library_top_to_ante(self) -> None:
        self.resolve_attorney()
        alice_top = self.alice.library[-1]
        bob_top = self.bob.library[-1]
        old_antes = (tuple(self.alice.ante), tuple(self.bob.ante))
        self.game.choose_demonic_attorney(self.bob.id, concede=False)
        self.assertEqual(tuple(self.alice.ante), old_antes[0] + (alice_top,))
        self.assertEqual(tuple(self.bob.ante), old_antes[1] + (bob_top,))
        self.assertTrue(all(card.zone is Zone.ANTE for card in (alice_top, bob_top)))
        self.assertFalse(self.game.pending_demonic_attorney_choices)

    def test_opponent_may_concede_and_award_the_ante(self) -> None:
        self.resolve_attorney()
        self.game.choose_demonic_attorney(self.bob.id, concede=True)
        self.assertEqual(self.game.status, GameStatus.FINISHED)
        self.assertEqual(self.game.ante_award.winner_id, self.alice.id)

    def test_only_opponent_can_answer(self) -> None:
        self.resolve_attorney()
        with self.assertRaisesRegex(ValueError, "only the caster's opponent"):
            self.game.choose_demonic_attorney(self.alice.id, concede=False)

    def test_cannot_be_cast_without_ante(self) -> None:
        alice = PlayerState.with_deck("a", "Alice", [SWAMP] * 5)
        bob = PlayerState.with_deck("b", "Bob", [SWAMP] * 5)
        game = GameState([alice, bob])
        game.start(opening_hand_size=0, shuffle=False)
        game.current_phase = TurnPhase.MAIN
        game.priority_player_index = 0
        card = Card(DEMONIC_ATTORNEY, alice.id, zone=Zone.HAND)
        alice.hand.append(card)
        alice.mana_pool.black = 2
        alice.mana_pool.colorless = 1
        with self.assertRaisesRegex(RuntimeError, "not playing for ante"):
            game.begin_cast(card)

    def test_ui_exposes_choice_only_to_opponent(self) -> None:
        self.resolve_attorney()
        view = GameViewModel(self.game)
        self.assertTrue(view.state["demonicAttorneyChoice"])
        self.assertFalse(view.state["canChooseDemonicAttorney"])
        view.perspective_index = 1
        self.assertTrue(view.state["canChooseDemonicAttorney"])
        view.chooseDemonicAttorney(False)
        self.assertFalse(self.game.pending_demonic_attorney_choices)


if __name__ == "__main__":
    unittest.main()
