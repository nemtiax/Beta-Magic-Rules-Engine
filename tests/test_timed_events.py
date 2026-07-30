import unittest

from beta_magic import (
    COPPER_TABLET,
    DISENCHANT,
    TIMED_ARTIFACTS,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS


class TimedEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 30
        )
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 30)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def put_in_play(player, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = player.id
        player.battlefield.append(card)
        return card

    @staticmethod
    def put_in_hand(player, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        player.hand.append(card)
        return card

    def enter_upkeep(self) -> None:
        self.assertIs(self.game.current_phase, TurnPhase.UNTAP)
        self.game.advance_phase()
        self.assertIs(self.game.current_phase, TurnPhase.UPKEEP)

    def pass_event(self) -> None:
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_copper_tablet_definition(self) -> None:
        self.assertEqual(TIMED_ARTIFACTS, (COPPER_TABLET,))
        self.assertEqual(COPPER_TABLET.mana_cost.compact, "2")
        self.assertEqual(COPPER_TABLET.upkeep_effects[0].amount, 1)

    def test_tablet_opens_response_window_before_dealing_damage(self) -> None:
        self.put_in_play(self.bob, COPPER_TABLET)

        self.enter_upkeep()

        self.assertEqual(self.alice.life, 20)
        self.assertEqual(self.game.stack, [])
        self.assertEqual(len(self.game.timed_events), 1)
        self.assertIs(
            self.game.players[self.game.priority_player_index], self.alice
        )
        with self.assertRaisesRegex(RuntimeError, "timed event"):
            self.game.advance_phase()

        self.pass_event()

        self.assertEqual(self.alice.life, 19)
        self.assertEqual(self.game.timed_events, [])
        self.assertIsNone(self.game.priority_player_index)

    def test_fast_effect_batch_can_destroy_source_before_event_resolves(self) -> None:
        tablet = self.put_in_play(self.bob, COPPER_TABLET)
        disenchant = self.put_in_hand(self.alice, DISENCHANT)
        self.enter_upkeep()
        self.alice.mana_pool.white = 1
        self.alice.mana_pool.colorless = 1

        self.game.begin_cast(disenchant)
        self.game.complete_pending_cast((tablet,))
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.assertIn(tablet, self.bob.graveyard)
        self.assertEqual(len(self.game.timed_events), 1)
        self.assertEqual(self.alice.life, 20)

        self.pass_event()

        self.assertEqual(self.alice.life, 20)
        self.assertEqual(self.game.timed_events, [])

    def test_each_tablet_creates_its_own_ordered_event(self) -> None:
        self.put_in_play(self.alice, COPPER_TABLET)
        self.put_in_play(self.bob, COPPER_TABLET)
        self.enter_upkeep()

        self.assertEqual(len(self.game.timed_events), 2)
        self.pass_event()
        self.assertEqual(self.alice.life, 19)
        self.assertEqual(len(self.game.timed_events), 1)
        self.assertEqual(self.game.priority_player_index, self.game.active_player_index)

        self.pass_event()
        self.assertEqual(self.alice.life, 18)

    def test_tapped_opponents_artifact_has_no_upkeep_effect(self) -> None:
        tablet = self.put_in_play(self.bob, COPPER_TABLET)
        tablet.tapped = True

        self.enter_upkeep()

        self.assertEqual(self.game.timed_events, [])
        self.assertIsNone(self.game.priority_player_index)


if __name__ == "__main__":
    unittest.main()
