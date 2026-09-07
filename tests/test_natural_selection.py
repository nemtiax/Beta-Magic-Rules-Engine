import unittest
from uuid import UUID

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.green import NATURAL_SELECTION
from beta_magic.card_defs.lands import FOREST, ISLAND, MOUNTAIN, PLAINS, SWAMP
from beta_magic.ui import GameViewModel


class NaturalSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "a", "Alice", [PLAINS, ISLAND, SWAMP, MOUNTAIN, FOREST]
        )
        self.bob = PlayerState.with_deck(
            "b", "Bob", [FOREST, MOUNTAIN, SWAMP, ISLAND, PLAINS]
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    def resolve(self, target: PlayerState) -> Card:
        card = Card(NATURAL_SELECTION, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(card)
        self.alice.mana_pool.green = 1
        self.game.begin_cast(card)
        self.game.complete_pending_cast((target,))
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        return card

    def test_can_target_either_players_library(self) -> None:
        card = Card(NATURAL_SELECTION, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(card)
        self.alice.mana_pool.green = 1
        self.game.begin_cast(card)
        self.assertEqual(
            {player.id for player in self.game.legal_player_targets_for()},
            {self.alice.id, self.bob.id},
        )

    def test_reveals_top_three_to_caster_in_top_first_order(self) -> None:
        expected = [card.id for card in reversed(self.bob.library[-3:])]
        self.resolve(self.bob)
        choice = self.game.pending_natural_selection_choices[0]
        self.assertEqual(choice.chooser_id, self.alice.id)
        self.assertEqual(choice.target_player_id, self.bob.id)
        self.assertEqual(choice.card_ids_top_first, expected)

    def test_caster_can_reorder_top_three(self) -> None:
        untouched = tuple(self.bob.library[:-3])
        self.resolve(self.bob)
        choice = self.game.pending_natural_selection_choices[0]
        original = tuple(choice.card_ids_top_first)
        self.game.move_natural_selection_card(self.alice.id, original[2], -1)
        self.game.move_natural_selection_card(self.alice.id, original[2], -1)
        self.game.choose_natural_selection(self.alice.id, shuffle=False)
        self.assertEqual(tuple(self.bob.library[:-3]), untouched)
        self.assertEqual(
            tuple(card.id for card in reversed(self.bob.library[-3:])),
            (original[2], original[0], original[1]),
        )

    def test_may_keep_original_order(self) -> None:
        original = tuple(self.alice.library)
        self.resolve(self.alice)
        self.game.choose_natural_selection(self.alice.id, shuffle=False)
        self.assertEqual(tuple(self.alice.library), original)

    def test_may_shuffle_entire_library(self) -> None:
        self.resolve(self.bob)
        before_ids = {card.id for card in self.bob.library}
        before_order = tuple(self.bob.library)
        self.game.random.seed(7)
        self.game.choose_natural_selection(self.alice.id, shuffle=True)
        self.assertEqual({card.id for card in self.bob.library}, before_ids)
        self.assertNotEqual(tuple(self.bob.library), before_order)

    def test_short_library_displays_only_available_cards(self) -> None:
        self.bob.library[:] = self.bob.library[-2:]
        self.resolve(self.bob)
        self.assertEqual(
            len(self.game.pending_natural_selection_choices[0].card_ids_top_first),
            2,
        )

    def test_ui_keeps_inspected_cards_private_and_supports_reordering(self) -> None:
        self.resolve(self.bob)
        view = GameViewModel(self.game)
        own_state = view.state
        self.assertTrue(own_state["canChooseNaturalSelection"])
        self.assertEqual(len(own_state["naturalSelectionCards"]), 3)
        first_id = own_state["naturalSelectionCards"][0]["id"]
        view.moveNaturalSelectionCard(first_id, 1)
        self.assertNotEqual(
            self.game.pending_natural_selection_choices[0].card_ids_top_first[0],
            UUID(first_id),
        )
        view.perspective_index = 1
        other_state = view.state
        self.assertFalse(other_state["canChooseNaturalSelection"])
        self.assertEqual(other_state["naturalSelectionCards"], [])
if __name__ == "__main__":
    unittest.main()
