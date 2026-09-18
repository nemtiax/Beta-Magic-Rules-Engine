import unittest

from beta_magic.card_defs.lands import FOREST
from beta_magic.card_defs.black import LORD_OF_THE_PIT
from beta_magic.card_defs.blue import PHANTASMAL_FORCES
from beta_magic import (
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class UpkeepOrderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("b", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def permanent(player: PlayerState, definition) -> Card:
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def enter_upkeep_with_forces_then_lord(self) -> tuple[Card, Card]:
        forces = self.permanent(self.alice, PHANTASMAL_FORCES)
        lord = self.permanent(self.alice, LORD_OF_THE_PIT)
        self.game.advance_phase()
        self.assertIs(self.game.current_phase, TurnPhase.UPKEEP)
        return forces, lord

    def pass_both(self) -> None:
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_active_player_can_resolve_lord_before_phantasmal_forces(self) -> None:
        forces, _ = self.enter_upkeep_with_forces_then_lord()
        choice = self.game.pending_timed_event_order
        self.assertIsNotNone(choice)
        self.assertIsNone(self.game.priority_player_index)
        self.assertEqual(
            [event.source_name for event in self.game.timed_events],
            ["Phantasmal Forces", "Lord of the Pit"],
        )

        lord_event = next(
            event
            for event in self.game.timed_events
            if event.source_name == "Lord of the Pit"
        )
        self.game.move_timed_event_order(self.alice.id, lord_event.id, -1)
        self.game.confirm_timed_event_order(self.alice.id)

        self.assertEqual(
            [event.source_name for event in self.game.timed_events],
            ["Lord of the Pit", "Phantasmal Forces"],
        )
        self.game.choose_upkeep_sacrifice(self.alice.id, forces)
        self.pass_both()
        self.pass_both()

        self.assertIs(forces.zone, Zone.GRAVEYARD)
        self.assertEqual(self.alice.life, 20)
        self.assertEqual(self.game.timed_events, [])

    def test_order_must_be_confirmed_before_upkeep_actions_continue(self) -> None:
        self.enter_upkeep_with_forces_then_lord()

        with self.assertRaisesRegex(RuntimeError, "order their upkeep"):
            self.game.advance_phase()
        self.game.validate()

    def test_ui_exposes_a_first_to_last_order(self) -> None:
        self.enter_upkeep_with_forces_then_lord()
        view = GameViewModel(self.game)

        self.assertTrue(view.state["timedEventOrderChoice"])
        self.assertEqual(view.state["timedEventOrderPlayer"], self.alice.id)
        self.assertEqual(
            [
                item["label"].split(":", 1)[0]
                for item in view.state["timedEventOrderItems"]
            ],
            ["Phantasmal Forces", "Lord of the Pit"],
        )

        lord_event = self.game.timed_events[1]
        view.moveTimedEventOrder(str(lord_event.id), -1)
        self.assertEqual(
            view.state["timedEventOrderItems"][0]["label"].split(":", 1)[0],
            "Lord of the Pit",
        )
        view.confirmTimedEventOrder()
        self.assertFalse(view.state["timedEventOrderChoice"])
        self.assertIs(
            self.game.players[self.game.priority_player_index], self.alice
        )


if __name__ == "__main__":
    unittest.main()
