import unittest

from beta_magic import (
    GRIZZLY_BEARS,
    LIBRARY_OF_LENG,
    MIND_TWIST,
    PLAINS,
    WHEEL_OF_FORTUNE,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class LibraryOfLengTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [PLAINS] * 15)
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 15)
        self.game = GameState([self.alice, self.bob])
        self.game.random.seed(7)
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def add(player, definition, zone):
        card = Card(definition, player.id, controller_id=player.id, zone=zone)
        player.cards_in(zone).append(card)
        return card

    def resolve_batch(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition_and_unlimited_hand_size(self) -> None:
        self.assertEqual(LIBRARY_OF_LENG.mana_cost.compact, "1")
        self.add(self.alice, LIBRARY_OF_LENG, Zone.BATTLEFIELD)
        for _ in range(9):
            self.add(self.alice, PLAINS, Zone.HAND)

        # Entering Main drew one card before the nine added for this test.
        self.assertEqual(self.alice.discard_required, 3)
        self.assertEqual(self.game.required_discards(self.alice), 0)

    def test_tapped_library_does_not_remove_the_hand_limit(self) -> None:
        library = self.add(self.alice, LIBRARY_OF_LENG, Zone.BATTLEFIELD)
        library.tapped = True
        for _ in range(8):
            self.add(self.alice, PLAINS, Zone.HAND)

        # The draw made while entering Main plus these eight cards leaves two
        # required discards when the continuous artifact is switched off.
        self.assertEqual(self.game.required_discards(self.alice), 2)

    def test_mind_twist_reveals_random_cards_then_allows_each_destination(self) -> None:
        self.add(self.bob, LIBRARY_OF_LENG, Zone.BATTLEFIELD)
        victims = [
            self.add(self.bob, definition, Zone.HAND)
            for definition in (PLAINS, GRIZZLY_BEARS, PLAINS, GRIZZLY_BEARS)
        ]
        twist = self.add(self.alice, MIND_TWIST, Zone.HAND)
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 2

        self.game.begin_cast(twist, x_value=2)
        self.game.complete_pending_cast((self.bob,))
        self.resolve_batch()

        choice = self.game.pending_library_discard_choices[0]
        self.assertEqual(choice.player_id, self.bob.id)
        self.assertEqual(len(choice.card_ids), 2)
        self.assertTrue(set(choice.card_ids) <= {card.id for card in victims})
        library_card = next(card for card in victims if card.id == choice.card_ids[0])
        graveyard_card = next(card for card in victims if card.id == choice.card_ids[1])
        self.game.toggle_library_discard_destination(self.bob.id, library_card)
        self.game.confirm_library_discard(self.bob.id)

        self.assertIs(self.bob.library[-1], library_card)
        self.assertIn(graveyard_card, self.bob.graveyard)
        self.assertEqual(len(self.bob.hand), 2)

    def test_wheel_uses_chosen_library_order_before_drawing(self) -> None:
        self.add(self.alice, LIBRARY_OF_LENG, Zone.BATTLEFIELD)
        bottom = self.add(self.alice, GRIZZLY_BEARS, Zone.HAND)
        top = self.add(self.alice, PLAINS, Zone.HAND)
        wheel = self.add(self.alice, WHEEL_OF_FORTUNE, Zone.HAND)
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = 2

        self.game.begin_cast(wheel)
        self.resolve_batch()
        self.assertTrue(self.game.pending_library_discard_choices)
        self.assertEqual(
            set(self.game.pending_library_discard_choices[0].card_ids),
            {card.id for card in self.alice.hand},
        )

        self.game.toggle_library_discard_destination(self.alice.id, bottom)
        self.game.toggle_library_discard_destination(self.alice.id, top)
        self.game.confirm_library_discard(self.alice.id)

        self.assertEqual(self.alice.hand[:2], [top, bottom])
        self.assertEqual(len(self.alice.hand), 7)

    def test_ui_exposes_destinations_and_library_order(self) -> None:
        self.add(self.bob, LIBRARY_OF_LENG, Zone.BATTLEFIELD)
        first = self.add(self.bob, PLAINS, Zone.HAND)
        second = self.add(self.bob, GRIZZLY_BEARS, Zone.HAND)
        self.game._discard_forced(
            self.bob, (first, second), source_name="Test discard"
        )
        view = GameViewModel(self.game)
        view.perspective_index = 1

        self.assertTrue(view.state["libraryDiscardChoice"])
        self.assertEqual(len(view.state["libraryDiscardCards"]), 2)
        view.toggleLibraryDiscardDestination(str(first.id))
        self.assertEqual(
            [card["name"] for card in view.state["libraryDiscardTopCards"]],
            ["Plains"],
        )


if __name__ == "__main__":
    unittest.main()
