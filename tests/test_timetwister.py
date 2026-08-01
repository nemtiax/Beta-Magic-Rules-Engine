import unittest

from beta_magic import (
    GRIZZLY_BEARS,
    TIMETWISTER,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class TimetwisterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.random.seed(11)
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def add_card(player, definition, zone):
        card = Card(definition, player.id, controller_id=player.id, zone=zone)
        player.cards_in(zone).append(card)
        return card

    def resolve_batch(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_recycles_both_hands_and_graveyards_then_draws_seven(self) -> None:
        timetwister = self.add_card(self.alice, TIMETWISTER, Zone.HAND)
        recycled = []
        for player in self.game.players:
            recycled.append(self.add_card(player, GRIZZLY_BEARS, Zone.HAND))
            recycled.append(self.add_card(player, GRIZZLY_BEARS, Zone.GRAVEYARD))
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 2

        self.game.begin_cast(timetwister)
        self.resolve_batch()

        self.assertEqual(len(self.alice.hand), 7)
        self.assertEqual(len(self.bob.hand), 7)
        self.assertEqual(self.alice.graveyard, [timetwister])
        self.assertEqual(self.bob.graveyard, [])
        self.assertNotIn(timetwister, self.alice.hand)
        self.assertNotIn(timetwister, self.alice.library)
        for card in recycled:
            owner = self.game.player(card.owner_id)
            self.assertIn(card, owner.hand + owner.library)

    def test_timetwister_is_not_available_to_its_own_new_hand(self) -> None:
        timetwister = self.add_card(self.alice, TIMETWISTER, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 2

        self.game.begin_cast(timetwister)
        self.assertIs(timetwister.zone, Zone.STACK)
        self.resolve_batch()

        self.assertIs(timetwister.zone, Zone.GRAVEYARD)
        self.assertEqual(self.alice.graveyard, [timetwister])


if __name__ == "__main__":
    unittest.main()
