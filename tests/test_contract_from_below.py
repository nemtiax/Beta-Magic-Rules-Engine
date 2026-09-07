import unittest

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.black import CONTRACT_FROM_BELOW
from beta_magic.card_defs.lands import FOREST, ISLAND, MOUNTAIN, PLAINS, SWAMP
from beta_magic.decks import make_demo_game


class ContractFromBelowTests(unittest.TestCase):
    def setUp(self) -> None:
        deck = [PLAINS, ISLAND, MOUNTAIN, FOREST, SWAMP] * 4
        self.alice = PlayerState.with_deck("a", "Alice", deck)
        self.bob = PlayerState.with_deck("b", "Bob", deck)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False, ante=True)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    def contract(self):
        card = Card(CONTRACT_FROM_BELOW, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(card)
        return card

    def resolve(self, card):
        self.alice.mana_pool.black = 1
        self.game.begin_cast(card)
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

    def test_cannot_be_cast_when_not_playing_for_ante(self) -> None:
        alice = PlayerState.with_deck("a", "Alice", [SWAMP] * 10)
        bob = PlayerState.with_deck("b", "Bob", [SWAMP] * 10)
        game = GameState([alice, bob])
        game.start(opening_hand_size=0, shuffle=False)
        game.current_phase = TurnPhase.MAIN
        game.priority_player_index = 0
        card = Card(CONTRACT_FROM_BELOW, alice.id, zone=Zone.HAND)
        alice.hand.append(card)
        alice.mana_pool.black = 1
        with self.assertRaises(RuntimeError):
            game.begin_cast(card)

    def test_discards_casters_hand_antes_first_card_and_draws_seven(self) -> None:
        contract = self.contract()
        discarded = Card(PLAINS, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(discarded)
        first_drawn = self.alice.library[-1]
        original_ante = tuple(self.alice.ante)
        self.resolve(contract)

        self.assertIn(discarded, self.alice.graveyard)
        self.assertIn(contract, self.alice.graveyard)
        self.assertEqual(tuple(self.alice.ante), original_ante + (first_drawn,))
        self.assertEqual(first_drawn.zone, Zone.ANTE)
        self.assertEqual(len(self.alice.hand), 7)

    def test_opponents_hand_and_ante_are_unchanged(self) -> None:
        contract = self.contract()
        opponent_card = Card(ISLAND, self.bob.id, zone=Zone.HAND)
        self.bob.hand.append(opponent_card)
        opponent_ante = tuple(self.bob.ante)
        self.resolve(contract)
        self.assertEqual(self.bob.hand, [opponent_card])
        self.assertEqual(tuple(self.bob.ante), opponent_ante)

    def test_contract_itself_is_not_discarded_as_part_of_hand(self) -> None:
        contract = self.contract()
        self.resolve(contract)
        self.assertEqual(contract.zone, Zone.GRAVEYARD)
        self.assertNotIn(contract, self.alice.hand)

    def test_non_ante_demo_deck_removes_contract(self) -> None:
        game = make_demo_game(ante=False)
        self.assertFalse(
            any(
                card.definition is CONTRACT_FROM_BELOW
                for player in game.players
                for card in player.library + player.hand
            )
        )

    def test_ante_demo_deck_keeps_contract(self) -> None:
        game = make_demo_game(ante=True)
        self.assertTrue(
            any(
                card.definition is CONTRACT_FROM_BELOW
                for player in game.players
                for card in player.library + player.hand + player.ante
            )
        )


if __name__ == "__main__":
    unittest.main()
