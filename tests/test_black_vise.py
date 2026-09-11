import unittest

from beta_magic import (
    BLACK_VISE,
    FOREST,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class BlackViseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 30)
        self.bob = PlayerState.with_deck("bob", "Bob", [FOREST] * 30)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def permanent(player: PlayerState, *, tapped: bool = False) -> Card:
        card = Card(
            BLACK_VISE,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            tapped=tapped,
        )
        player.battlefield.append(card)
        return card

    @staticmethod
    def draw_to(player: PlayerState, count: int) -> None:
        player.draw(count - len(player.hand))

    def enter_upkeep(self) -> None:
        self.game.advance_phase()
        self.assertIs(self.game.current_phase, TurnPhase.UPKEEP)

    def resolve_events(self) -> None:
        if self.game.pending_timed_event_order is not None:
            self.game.confirm_timed_event_order(self.alice.id)
        while self.game.timed_events:
            for _ in range(2):
                player = self.game.players[self.game.priority_player_index]
                self.game.pass_priority(player.id)

    def test_definition(self) -> None:
        self.assertEqual(BLACK_VISE.mana_cost.compact, "1")
        self.assertEqual(BLACK_VISE.card_types, frozenset({CardType.ARTIFACT}))
        self.assertEqual(BLACK_VISE.upkeep_effects[0].threshold, 4)

    def test_damages_opponent_for_each_card_beyond_four(self) -> None:
        self.permanent(self.bob)
        self.draw_to(self.alice, 7)

        self.enter_upkeep()
        self.resolve_events()

        self.assertEqual(self.alice.life, 17)
        self.assertEqual(self.bob.life, 20)

    def test_does_not_apply_during_its_controllers_upkeep(self) -> None:
        self.permanent(self.alice)
        self.draw_to(self.alice, 7)

        self.enter_upkeep()

        self.assertEqual(self.game.timed_events, [])
        self.assertEqual(self.alice.life, 20)

    def test_four_or_fewer_cards_cause_no_damage(self) -> None:
        self.permanent(self.bob)
        self.draw_to(self.alice, 4)

        self.enter_upkeep()
        self.resolve_events()

        self.assertEqual(self.alice.life, 20)

    def test_hand_size_is_checked_when_the_event_resolves(self) -> None:
        self.permanent(self.bob)
        self.draw_to(self.alice, 7)
        self.enter_upkeep()
        for card in tuple(self.alice.hand[:2]):
            self.game._move_card(card, Zone.GRAVEYARD)

        self.resolve_events()

        self.assertEqual(len(self.alice.hand), 5)
        self.assertEqual(self.alice.life, 19)

    def test_drawing_in_response_increases_the_damage(self) -> None:
        self.permanent(self.bob)
        self.draw_to(self.alice, 5)
        self.enter_upkeep()
        self.alice.draw(2)

        self.resolve_events()

        self.assertEqual(self.alice.life, 17)

    def test_tapped_vise_does_not_queue_or_resolve_its_effect(self) -> None:
        self.permanent(self.bob, tapped=True)
        self.draw_to(self.alice, 7)
        self.enter_upkeep()
        self.assertEqual(self.game.timed_events, [])

        game = GameState(
            [
                PlayerState.with_deck("a", "Alice", [FOREST] * 20),
                PlayerState.with_deck("b", "Bob", [FOREST] * 20),
            ]
        )
        game.start(opening_hand_size=0, shuffle=False)
        vise = self.permanent(game.players[1])
        game.players[0].draw(7)
        game.advance_phase()
        vise.tapped = True
        if game.pending_timed_event_order is not None:
            game.confirm_timed_event_order(game.active_player.id)
        while game.timed_events:
            for _ in range(2):
                player = game.players[game.priority_player_index]
                game.pass_priority(player.id)
        self.assertEqual(game.players[0].life, 20)

    def test_each_vise_is_a_separate_damage_source(self) -> None:
        self.permanent(self.bob)
        self.permanent(self.bob)
        self.draw_to(self.alice, 6)

        self.enter_upkeep()
        self.resolve_events()

        self.assertEqual(self.alice.life, 16)
        self.assertEqual(len(self.game.resolved_damage_incidents), 2)


if __name__ == "__main__":
    unittest.main()
