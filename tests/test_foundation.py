import unittest

from beta_magic import (
    CardDefinition,
    CardType,
    Color,
    GameState,
    GameStatus,
    ManaCost,
    PlayerState,
    Zone,
)


GRIZZLY_BEARS = CardDefinition(
    name="Grizzly Bears",
    card_types=frozenset({CardType.CREATURE}),
    subtypes=("Bears",),
    mana_cost=ManaCost.parse("{1}{G}"),
    colors=frozenset({Color.GREEN}),
    power=2,
    toughness=2,
)
FOREST = CardDefinition(name="Forest", card_types=frozenset({CardType.LAND}))


class ManaCostTests(unittest.TestCase):
    def test_parses_and_formats_beta_costs(self) -> None:
        cost = ManaCost.parse("{2}{U}{U}")
        self.assertEqual(cost.generic, 2)
        self.assertEqual(cost.blue, 2)
        self.assertEqual(cost.mana_value, 4)
        self.assertEqual(str(cost), "{2}{U}{U}")
        self.assertEqual(cost.compact, "2UU")

    def test_rejects_unknown_symbols(self) -> None:
        with self.assertRaises(ValueError):
            ManaCost.parse("{X}")


class GameStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [FOREST, GRIZZLY_BEARS, FOREST]
        )
        self.bob = PlayerState.with_deck("bob", "Bob", [FOREST, FOREST, FOREST])
        self.game = GameState([self.alice, self.bob])

    def test_cards_are_individual_objects_with_shared_definitions(self) -> None:
        first, _, third = self.alice.library
        self.assertIsNot(first, third)
        self.assertIs(first.definition, third.definition)
        self.assertNotEqual(first.id, third.id)

    def test_start_draws_opening_hands_and_sets_turn(self) -> None:
        self.game.start(opening_hand_size=2, shuffle=False)
        self.assertEqual(self.game.status, GameStatus.IN_PROGRESS)
        self.assertEqual(self.game.turn_number, 1)
        self.assertEqual(len(self.alice.hand), 2)
        self.assertTrue(all(card.zone is Zone.HAND for card in self.alice.hand))

    def test_empty_library_marks_player_as_lost(self) -> None:
        self.alice.draw(3)
        self.assertEqual(self.alice.draw(), [])
        self.assertTrue(self.alice.has_lost)

    def test_move_card_keeps_zone_and_container_in_sync(self) -> None:
        card = self.alice.draw()[0]
        self.alice.move_card(card, Zone.GRAVEYARD)
        self.assertNotIn(card, self.alice.hand)
        self.assertIn(card, self.alice.graveyard)
        self.assertEqual(card.zone, Zone.GRAVEYARD)
        self.game.validate()

    def test_game_rejects_duplicate_player_ids(self) -> None:
        with self.assertRaises(ValueError):
            GameState([self.alice, PlayerState("alice", "Impostor")])


if __name__ == "__main__":
    unittest.main()
