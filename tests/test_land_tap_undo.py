import unittest

from beta_magic import (
    FOREST,
    ISLAND,
    MANA_FLARE,
    MOX_PEARL,
    PSYCHIC_VENOM,
    WILD_GROWTH,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class LandTapUndoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [ISLAND] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player, definition, *, attached_to=None, zone=Zone.BATTLEFIELD):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=zone,
            entered_battlefield_turn=0 if zone is Zone.BATTLEFIELD else None,
            enchanted_card_id=attached_to.id if attached_to else None,
        )
        player.cards_in(zone).append(card)
        return card

    def test_consecutive_land_taps_can_be_undone_last_first(self) -> None:
        forest = self.card(self.alice, FOREST)
        island = self.card(self.alice, ISLAND)

        self.game.activate_ability(self.alice.id, forest, 0)
        self.game.activate_ability(self.alice.id, island, 0)

        self.assertIs(self.game.undoable_land_tap(self.alice.id), island)
        self.assertIs(self.game.undo_last_land_tap(self.alice.id), island)
        self.assertFalse(island.tapped)
        self.assertEqual(self.alice.mana_pool.blue, 0)
        self.assertEqual(self.alice.mana_pool.green, 1)

        self.assertIs(self.game.undo_last_land_tap(self.alice.id), forest)
        self.assertFalse(forest.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)

    def test_an_accidental_draw_step_tap_can_be_undone(self) -> None:
        alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        bob = PlayerState.with_deck("bob", "Bob", [ISLAND] * 20)
        game = GameState([alice, bob])
        game.start(opening_hand_size=0, shuffle=False)
        while game.current_phase is not TurnPhase.DRAW:
            game.advance_phase()
        island = self.card(alice, ISLAND)

        game.activate_ability(alice.id, island, 0)
        game.undo_last_land_tap(alice.id)

        self.assertFalse(island.tapped)
        self.assertEqual(alice.mana_pool.total, 0)

    def test_undo_restores_all_bonus_mana_from_that_tap(self) -> None:
        forest = self.card(self.alice, FOREST)
        self.card(self.alice, WILD_GROWTH, attached_to=forest)
        self.card(self.bob, MANA_FLARE)

        self.game.activate_ability(self.alice.id, forest, 0)

        self.assertEqual(self.alice.mana_pool.green, 3)
        self.game.undo_last_land_tap(self.alice.id)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertFalse(forest.tapped)

    def test_a_tap_trigger_closes_the_undo_window(self) -> None:
        island = self.card(self.alice, ISLAND)
        self.card(self.bob, PSYCHIC_VENOM, attached_to=island)

        self.game.activate_ability(self.alice.id, island, 0)

        self.assertTrue(self.game.event_opportunities)
        self.assertIsNone(self.game.undoable_land_tap(self.alice.id))
        with self.assertRaisesRegex(RuntimeError, "no land mana tap"):
            self.game.undo_last_land_tap(self.alice.id)

    def test_casting_even_a_zero_cost_spell_closes_the_window(self) -> None:
        forest = self.card(self.alice, FOREST)
        mox = self.card(self.alice, MOX_PEARL, zone=Zone.HAND)
        self.game.activate_ability(self.alice.id, forest, 0)
        self.assertIsNotNone(self.game.undoable_land_tap(self.alice.id))

        self.game.begin_cast(mox)

        self.assertTrue(self.game.stack)
        self.assertIsNone(self.game.undoable_land_tap(self.alice.id))

    def test_passing_priority_closes_the_window(self) -> None:
        island = self.card(self.bob, ISLAND)
        self.game.begin_combat()
        self.game.activate_ability(self.bob.id, island, 0)
        self.assertIsNotNone(self.game.undoable_land_tap(self.bob.id))

        self.game.pass_priority(self.bob.id)

        self.assertIsNone(self.game.undoable_land_tap(self.bob.id))

    def test_ui_exposes_and_executes_the_latest_undo(self) -> None:
        forest = self.card(self.alice, FOREST)
        self.game.activate_ability(self.alice.id, forest, 0)
        view = GameViewModel(self.game)

        self.assertTrue(view.state["canUndoLandTap"])
        self.assertEqual(view.state["undoLandTapLabel"], "Undo Forest tap")

        view.undoLandTap()

        self.assertFalse(forest.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertFalse(view.state["canUndoLandTap"])


if __name__ == "__main__":
    unittest.main()
