import unittest

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.black import DEMONIC_TUTOR
from beta_magic.card_defs.lands import FOREST, ISLAND, MOUNTAIN, PLAINS, SWAMP
from beta_magic.ui import GameViewModel


class DemonicTutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "a", "Alice", [PLAINS, ISLAND, SWAMP, MOUNTAIN, FOREST]
        )
        self.bob = PlayerState.with_deck("b", "Bob", [FOREST] * 5)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    def resolve_tutor(self) -> Card:
        tutor = Card(DEMONIC_TUTOR, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(tutor)
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(tutor)
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        return tutor

    def test_resolves_to_private_mandatory_library_search(self) -> None:
        tutor = self.resolve_tutor()
        choice = self.game.pending_library_search_choices[0]
        self.assertEqual(choice.chooser_id, self.alice.id)
        self.assertEqual(choice.library_player_id, self.alice.id)
        self.assertIn(tutor, self.alice.graveyard)
        self.assertEqual(
            set(self.game.legal_library_search_cards()), set(self.alice.library)
        )

    def test_selected_card_moves_to_hand_and_remaining_library_shuffles(self) -> None:
        self.resolve_tutor()
        chosen = self.alice.library[1]
        remaining_ids = {card.id for card in self.alice.library if card is not chosen}
        self.game.random.seed(4)
        self.game.choose_library_search_card(self.alice.id, chosen)
        self.assertIn(chosen, self.alice.hand)
        self.assertEqual(chosen.zone, Zone.HAND)
        self.assertEqual({card.id for card in self.alice.library}, remaining_ids)
        self.assertFalse(self.game.pending_library_search_choices)

    def test_opponent_cannot_choose_or_see_results(self) -> None:
        self.resolve_tutor()
        chosen = self.alice.library[0]
        with self.assertRaisesRegex(ValueError, "only the searching player"):
            self.game.choose_library_search_card(self.bob.id, chosen)
        view = GameViewModel(self.game)
        view.perspective_index = 1
        state = view.state
        self.assertTrue(state["librarySearchPending"])
        self.assertFalse(state["canSearchLibrary"])
        self.assertEqual(state["librarySearchCards"], [])

    def test_ui_filters_case_insensitively_sorts_and_confirms(self) -> None:
        self.resolve_tutor()
        view = GameViewModel(self.game)
        view.setLibrarySearchFilter("a")
        state = view.state
        names = [card["name"] for card in state["librarySearchCards"]]
        self.assertEqual(names, sorted(names, key=str.casefold))
        self.assertTrue(all("a" in name.casefold() for name in names))
        chosen_id = state["librarySearchCards"][0]["id"]
        view.selectLibrarySearchCard(chosen_id)
        view.confirmLibrarySearch()
        self.assertFalse(self.game.pending_library_search_choices)
        self.assertTrue(any(str(card.id) == chosen_id for card in self.alice.hand))


if __name__ == "__main__":
    unittest.main()
