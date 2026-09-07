import unittest

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.black import DARKPACT
from beta_magic.card_defs.lands import FOREST, ISLAND, PLAINS, SWAMP
from beta_magic.ui import GameViewModel


class DarkpactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "a", "Alice", [PLAINS, ISLAND, FOREST, SWAMP] * 3
        )
        self.bob = PlayerState.with_deck(
            "b", "Bob", [SWAMP, FOREST, ISLAND, PLAINS] * 3
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False, ante=True)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    def darkpact(self) -> Card:
        card = Card(DARKPACT, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(card)
        self.alice.mana_pool.black = 3
        return card

    def resolve(self, card: Card, target: Card) -> None:
        self.game.begin_cast(card)
        self.game.complete_pending_cast((target,))
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

    def test_requires_ante_and_a_nonempty_library(self) -> None:
        card = self.darkpact()
        self.alice.library.clear()
        with self.assertRaisesRegex(RuntimeError, "requires a card in your library"):
            self.game.begin_cast(card)

        alice = PlayerState.with_deck("a", "Alice", [SWAMP] * 4)
        bob = PlayerState.with_deck("b", "Bob", [SWAMP] * 4)
        game = GameState([alice, bob])
        game.start(opening_hand_size=0, shuffle=False)
        game.current_phase = TurnPhase.MAIN
        game.priority_player_index = 0
        card = Card(DARKPACT, alice.id, zone=Zone.HAND)
        alice.hand.append(card)
        alice.mana_pool.black = 3
        with self.assertRaisesRegex(RuntimeError, "not playing for ante"):
            game.begin_cast(card)

    def test_either_ante_card_is_a_legal_target(self) -> None:
        card = self.darkpact()
        self.game.begin_cast(card)
        self.assertEqual(
            set(self.game.legal_targets_for()),
            {self.alice.ante[0], self.bob.ante[0]},
        )

    def test_permanently_swaps_library_top_with_opponents_ante(self) -> None:
        card = self.darkpact()
        chosen_ante = self.bob.ante[0]
        library_top = self.alice.library[-1]

        self.resolve(card, chosen_ante)

        self.assertIs(self.alice.library[-1], chosen_ante)
        self.assertEqual(chosen_ante.zone, Zone.LIBRARY)
        self.assertEqual(chosen_ante.owner_id, self.alice.id)
        self.assertEqual(self.bob.ante, [library_top])
        self.assertEqual(library_top.zone, Zone.ANTE)
        self.assertEqual(library_top.owner_id, self.bob.id)
        self.assertIn(card, self.alice.graveyard)
        self.game.validate()

    def test_can_swap_with_own_ante(self) -> None:
        card = self.darkpact()
        chosen_ante = self.alice.ante[0]
        library_top = self.alice.library[-1]
        self.resolve(card, chosen_ante)
        self.assertIs(self.alice.library[-1], chosen_ante)
        self.assertEqual(self.alice.ante, [library_top])
        self.assertEqual(chosen_ante.owner_id, self.alice.id)
        self.assertEqual(library_top.owner_id, self.alice.id)

    def test_ui_can_select_a_displayed_ante_target(self) -> None:
        card = self.darkpact()
        view_model = GameViewModel(self.game)
        self.game.begin_cast(card)
        target = self.bob.ante[0]
        view_model.toggleCard(str(target.id))
        self.assertIsNone(self.game.pending_cast)
        self.assertEqual(self.game.stack_spells[card.id].targets, (target,))


if __name__ == "__main__":
    unittest.main()
