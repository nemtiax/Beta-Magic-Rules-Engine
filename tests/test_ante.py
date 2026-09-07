import unittest

from beta_magic import AnteAward, Card, GameState, PlayerState, Zone
from beta_magic.card_defs.lands import FOREST, ISLAND, MOUNTAIN, PLAINS
from beta_magic.types import GameStatus
from beta_magic.ui import GameViewModel, parse_args


class AnteTests(unittest.TestCase):
    def game(self):
        alice = PlayerState.with_deck(
            "a", "Alice", [PLAINS, ISLAND, MOUNTAIN, FOREST] * 3
        )
        bob = PlayerState.with_deck(
            "b", "Bob", [FOREST, MOUNTAIN, ISLAND, PLAINS] * 3
        )
        return GameState([alice, bob]), alice, bob

    def test_ante_is_revealed_before_opening_hands(self) -> None:
        game, alice, bob = self.game()
        alice_top = alice.library[-1]
        bob_top = bob.library[-1]
        game.start(opening_hand_size=2, shuffle=False, ante=True)
        self.assertEqual(alice.ante, [alice_top])
        self.assertEqual(bob.ante, [bob_top])
        self.assertEqual((len(alice.hand), len(bob.hand)), (2, 2))
        self.assertEqual((len(alice.library), len(bob.library)), (9, 9))
        self.assertTrue(all(card.zone is Zone.ANTE for card in alice.ante + bob.ante))

    def test_ante_is_optional_for_existing_games(self) -> None:
        game, alice, bob = self.game()
        game.start(opening_hand_size=2, shuffle=False)
        self.assertFalse(game.ante_enabled)
        self.assertEqual((alice.ante, bob.ante), ([], []))

    def test_winner_receives_award_record_for_all_ante_cards(self) -> None:
        game, alice, bob = self.game()
        awards = []
        game.ante_award_hook = awards.append
        game.start(opening_hand_size=0, shuffle=False, ante=True)
        ante_cards = tuple(alice.ante + bob.ante)
        game.concede(bob.id)
        self.assertEqual(game.status, GameStatus.FINISHED)
        self.assertEqual(game.ante_award.winner_id, alice.id)
        self.assertEqual(set(game.ante_award.card_ids), {card.id for card in ante_cards})
        self.assertEqual(awards, [game.ante_award])
        self.assertTrue(all(card.owner_id in {alice.id, bob.id} for card in ante_cards))

    def test_draw_returns_ante_to_original_owners_in_award_record(self) -> None:
        game, alice, bob = self.game()
        game.start(opening_hand_size=0, shuffle=False, ante=True)
        alice.has_lost = True
        bob.has_lost = True
        game.check_state_based_actions()
        award = game.ante_award
        self.assertIsInstance(award, AnteAward)
        self.assertTrue(award.is_draw)
        self.assertEqual(award.original_owner_ids, (alice.id, bob.id))

    def test_ante_zone_participates_in_validation_and_ui(self) -> None:
        game, alice, _ = self.game()
        game.start(opening_hand_size=0, shuffle=False, ante=True)
        game.validate()
        state = GameViewModel(game).state
        self.assertEqual(state["perspective"]["anteCount"], 1)
        self.assertEqual(state["perspective"]["ante"][0]["name"], alice.ante[0].name)

    def test_cli_supports_ante_with_test_decks(self) -> None:
        args = parse_args(["--test-decks", "--ante"])
        self.assertTrue(args.test_decks)
        self.assertTrue(args.ante)


if __name__ == "__main__":
    unittest.main()
