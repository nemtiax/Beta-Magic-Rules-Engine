import unittest

from beta_magic import (
    GRIZZLY_BEARS,
    WHEEL_OF_FORTUNE,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class WheelOfFortuneTests(unittest.TestCase):
    def setUp(self):
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 15
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 15
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def add_card(player, definition, zone):
        card = Card(definition, player.id, controller_id=player.id, zone=zone)
        player.cards_in(zone).append(card)
        return card

    def resolve_batch(self):
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self):
        self.assertEqual(WHEEL_OF_FORTUNE.mana_cost.compact, "2R")
        self.assertEqual(WHEEL_OF_FORTUNE.spell_effects[0].draw_count, 7)

    def test_each_player_discards_their_hand_then_draws_seven(self):
        wheel = self.add_card(self.alice, WHEEL_OF_FORTUNE, Zone.HAND)
        discarded = [
            self.add_card(self.alice, GRIZZLY_BEARS, Zone.HAND),
            self.add_card(self.alice, GRIZZLY_BEARS, Zone.HAND),
            self.add_card(self.bob, GRIZZLY_BEARS, Zone.HAND),
        ]
        existing_graveyard_card = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.GRAVEYARD
        )
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = 2

        self.game.begin_cast(wheel)
        self.assertIs(wheel.zone, Zone.STACK)
        self.resolve_batch()

        self.assertEqual(len(self.alice.hand), 7)
        self.assertEqual(len(self.bob.hand), 7)
        for card in discarded:
            self.assertIs(card.zone, Zone.GRAVEYARD)
            self.assertIn(card, self.game.player(card.owner_id).graveyard)
        self.assertIn(existing_graveyard_card, self.bob.graveyard)
        self.assertEqual(self.alice.graveyard[-1], wheel)
        self.assertNotIn(wheel, self.alice.hand)

    def test_player_with_an_empty_hand_still_draws_seven(self):
        wheel = self.add_card(self.alice, WHEEL_OF_FORTUNE, Zone.HAND)
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = 2

        self.game.begin_cast(wheel)
        self.resolve_batch()

        self.assertEqual(len(self.alice.hand), 7)
        self.assertEqual(len(self.bob.hand), 7)


if __name__ == "__main__":
    unittest.main()
