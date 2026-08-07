import unittest

from beta_magic import (
    DEMONIC_HORDES,
    FOREST,
    GRIZZLY_BEARS,
    ISLAND,
    PLAINS,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    UpkeepFailure,
    Zone,
)
from beta_magic.ui import GameViewModel


class DemonicHordesTests(unittest.TestCase):
    def setUp(self):
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 20
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def enter_upkeep(self):
        self.game.advance_phase()
        self.assertIs(self.game.current_phase, TurnPhase.UPKEEP)

    def finish_event(self):
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def advance_to_main(self):
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    def resolve_batch(self):
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self):
        self.assertEqual(DEMONIC_HORDES.mana_cost.compact, "3BBB")
        self.assertEqual(
            (DEMONIC_HORDES.power, DEMONIC_HORDES.toughness), (5, 5)
        )
        upkeep = DEMONIC_HORDES.upkeep_effects[0]
        self.assertEqual(upkeep.mana_cost.compact, "BBB")
        self.assertIs(
            upkeep.failure,
            UpkeepFailure.TAP_SOURCE_AND_OPPONENT_CHOOSES_LAND,
        )
        self.assertTrue(DEMONIC_HORDES.tap_abilities_require_paid_upkeep)

    def test_paying_upkeep_unlocks_land_destruction_ability(self):
        hordes = self.permanent(self.alice, DEMONIC_HORDES)
        target = self.permanent(self.bob, ISLAND)
        self.enter_upkeep()
        self.alice.mana_pool.black = 3

        with self.assertRaisesRegex(RuntimeError, "upkeep must be paid"):
            self.game.activate_ability(self.alice.id, hordes, 0)
        self.game.choose_upkeep_payment(self.alice.id, pay=True)
        self.finish_event()
        self.advance_to_main()
        self.game.activate_ability(self.alice.id, hordes, 0)
        self.game.complete_pending_activation((target,))
        self.resolve_batch()

        self.assertTrue(hordes.tapped)
        self.assertIn(target, self.bob.graveyard)

    def test_declining_taps_hordes_and_opponent_chooses_land(self):
        hordes = self.permanent(self.alice, DEMONIC_HORDES)
        plains = self.permanent(self.alice, PLAINS)
        forest = self.permanent(self.alice, FOREST)
        opponents_land = self.permanent(self.bob, ISLAND)
        self.enter_upkeep()

        self.game.choose_upkeep_payment(self.alice.id, pay=False)
        self.finish_event()

        self.assertTrue(hordes.tapped)
        choice = self.game.pending_upkeep_land_loss
        self.assertIsNotNone(choice)
        self.assertEqual(choice.chooser_id, self.bob.id)
        self.assertEqual(choice.candidate_ids, {plains.id, forest.id})
        with self.assertRaises(ValueError):
            self.game.choose_upkeep_land_loss(self.bob.id, opponents_land)
        self.game.choose_upkeep_land_loss(self.bob.id, forest)
        self.assertIn(forest, self.alice.graveyard)
        self.assertIn(plains, self.alice.battlefield)

    def test_declining_with_no_lands_still_taps_hordes(self):
        hordes = self.permanent(self.alice, DEMONIC_HORDES)
        self.enter_upkeep()

        self.game.choose_upkeep_payment(self.alice.id, pay=False)
        self.finish_event()

        self.assertTrue(hordes.tapped)
        self.assertIsNone(self.game.pending_upkeep_land_loss)

    def test_untapping_after_declining_does_not_unlock_tap_ability(self):
        hordes = self.permanent(self.alice, DEMONIC_HORDES)
        target = self.permanent(self.bob, ISLAND)
        self.enter_upkeep()
        self.game.choose_upkeep_payment(self.alice.id, pay=False)
        self.finish_event()
        hordes.tapped = False
        self.advance_to_main()

        with self.assertRaisesRegex(RuntimeError, "upkeep must be paid"):
            self.game.activate_ability(self.alice.id, hordes, 0)
        self.assertIn(target, self.bob.battlefield)

    def test_ui_allows_opponent_to_select_the_lost_land(self):
        self.permanent(self.alice, DEMONIC_HORDES)
        land = self.permanent(self.alice, PLAINS)
        self.enter_upkeep()
        self.game.choose_upkeep_payment(self.alice.id, pay=False)
        self.finish_event()
        view = GameViewModel(self.game)
        view.switchPerspective()

        self.assertTrue(view.state["canChooseUpkeepLand"])
        view.toggleCard(str(land.id))
        view.chooseUpkeepLand()

        self.assertIsNone(self.game.pending_upkeep_land_loss)
        self.assertIn(land, self.alice.graveyard)


if __name__ == "__main__":
    unittest.main()
