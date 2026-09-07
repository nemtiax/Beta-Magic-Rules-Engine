import unittest
from uuid import uuid4

from beta_magic import (
    BAYOU,
    CYCLOPEAN_TOMB,
    PLAINS,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class CyclopeanTombTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [PLAINS] * 15)
        self.bob = PlayerState.with_deck("bob", "Bob", [PLAINS] * 15)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.advance_phase()
        self.assertIs(self.game.current_phase, TurnPhase.UPKEEP)

    @staticmethod
    def add(player, definition, zone):
        card = Card(definition, player.id, controller_id=player.id, zone=zone)
        player.cards_in(zone).append(card)
        return card

    def resolve_batch(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def activate_tomb(self, tomb, land) -> None:
        tomb.tapped = False
        self.alice.mana_pool.colorless = 2
        self.game.activate_ability(self.alice.id, tomb, 0)
        self.game.complete_pending_activation((land,))
        self.resolve_batch()

    def test_changes_any_non_swamp_land_and_updates_mana_abilities(self) -> None:
        tomb = self.add(self.alice, CYCLOPEAN_TOMB, Zone.BATTLEFIELD)
        plains = self.add(self.alice, PLAINS, Zone.BATTLEFIELD)
        bayou = self.add(self.bob, BAYOU, Zone.BATTLEFIELD)
        self.alice.mana_pool.colorless = 2

        self.game.activate_ability(self.alice.id, tomb, 0)
        self.assertIn(plains, self.game.legal_targets_for())
        self.assertNotIn(bayou, self.game.legal_targets_for())
        self.game.complete_pending_activation((plains,))
        self.resolve_batch()

        self.assertEqual(self.game.land_subtypes(plains), ("Swamp",))
        self.assertEqual(plains.counters["mire"], 1)
        self.assertEqual(
            [ability.color.value for ability in self.game.activated_abilities(plains)],
            ["B"],
        )

    def test_can_only_be_activated_during_its_controllers_upkeep(self) -> None:
        tomb = self.add(self.alice, CYCLOPEAN_TOMB, Zone.BATTLEFIELD)
        self.add(self.alice, PLAINS, Zone.BATTLEFIELD)
        self.alice.mana_pool.colorless = 2
        self.game.current_phase = TurnPhase.MAIN

        with self.assertRaisesRegex(RuntimeError, "controller's upkeep"):
            self.game.activate_ability(self.alice.id, tomb, 0)

    def test_leaving_play_preserves_marks_and_queues_one_removal_per_upkeep(self) -> None:
        tomb = self.add(self.alice, CYCLOPEAN_TOMB, Zone.BATTLEFIELD)
        land = self.add(self.alice, PLAINS, Zone.BATTLEFIELD)
        self.activate_tomb(tomb, land)
        mark = self.game.cyclopean_tomb_marks[0]

        self.game._move_card(tomb, Zone.HAND)
        self.assertEqual(self.game.land_subtypes(land), ("Swamp",))
        self.assertIn(mark.effect_id, self.game.cyclopean_tomb_cleanup_controllers)

        self.game._begin_scheduled_turn(self.bob.id)
        self.game.advance_phase()
        self.assertFalse(self.game.pending_tomb_cleanup_choices)
        self.game._begin_scheduled_turn(self.alice.id)
        self.game.advance_phase()
        self.assertEqual(
            self.game.pending_tomb_cleanup_choices[0].mark_ids, (mark.id,)
        )
        self.game.choose_cyclopean_tomb_cleanup(self.alice.id, mark.id)

        self.assertEqual(self.game.land_subtypes(land), ("Plains",))
        self.assertNotIn("mire", land.counters)

    def test_ability_still_resolves_if_tomb_leaves_after_activation(self) -> None:
        tomb = self.add(self.alice, CYCLOPEAN_TOMB, Zone.BATTLEFIELD)
        land = self.add(self.alice, PLAINS, Zone.BATTLEFIELD)
        self.alice.mana_pool.colorless = 2
        self.game.activate_ability(self.alice.id, tomb, 0)
        self.game.complete_pending_activation((land,))

        self.game._move_card(tomb, Zone.GRAVEYARD)
        self.resolve_batch()

        self.assertEqual(self.game.land_subtypes(land), ("Swamp",))
        effect_id = self.game.cyclopean_tomb_marks[0].effect_id
        self.assertEqual(
            self.game.cyclopean_tomb_cleanup_controllers[effect_id],
            self.alice.id,
        )

    def test_multiple_marks_from_one_tomb_are_independent_layers(self) -> None:
        tomb = self.add(self.alice, CYCLOPEAN_TOMB, Zone.BATTLEFIELD)
        land = self.add(self.alice, PLAINS, Zone.BATTLEFIELD)
        self.activate_tomb(tomb, land)
        first = self.game.cyclopean_tomb_marks[0]

        self.game.battlefield_entry_sequence += 1
        land.land_type_marks[uuid4()] = (
            "Island", self.game.battlefield_entry_sequence
        )
        self.assertEqual(self.game.land_subtypes(land), ("Island",))
        self.activate_tomb(tomb, land)
        second = self.game.cyclopean_tomb_marks[1]
        self.assertEqual(land.counters["mire"], 2)

        self.game._move_card(tomb, Zone.GRAVEYARD)
        self.game._begin_scheduled_turn(self.bob.id)
        self.game._begin_scheduled_turn(self.alice.id)
        self.game.advance_phase()
        self.game.choose_cyclopean_tomb_cleanup(self.alice.id, second.id)

        self.assertEqual(self.game.land_subtypes(land), ("Island",))
        self.assertIn(first, self.game.cyclopean_tomb_marks)
        self.assertEqual(land.counters["mire"], 1)

    def test_ui_identifies_older_and_newer_marks_on_the_same_land(self) -> None:
        tomb = self.add(self.alice, CYCLOPEAN_TOMB, Zone.BATTLEFIELD)
        land = self.add(self.alice, PLAINS, Zone.BATTLEFIELD)
        self.activate_tomb(tomb, land)
        self.game.battlefield_entry_sequence += 1
        land.land_type_marks[uuid4()] = (
            "Island", self.game.battlefield_entry_sequence
        )
        self.activate_tomb(tomb, land)
        self.game._move_card(tomb, Zone.GRAVEYARD)
        self.game._queue_cyclopean_tomb_cleanup_choices()
        view = GameViewModel(self.game)

        labels = [item["label"] for item in view.state["tombCleanupMarks"]]
        self.assertTrue(any("oldest" in label for label in labels))
        self.assertTrue(any("newest" in label for label in labels))


if __name__ == "__main__":
    unittest.main()
