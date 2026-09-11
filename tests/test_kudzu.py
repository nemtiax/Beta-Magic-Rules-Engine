import unittest

from beta_magic import (
    Card,
    FOREST,
    GameState,
    ISLAND,
    KUDZU,
    PlayerState,
    TurnPhase,
    Zone,
)


class KudzuTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 10)
        self.bob = PlayerState.with_deck("bob", "Bob", [ISLAND] * 10)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition, *, attached_to=None):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            enchanted_card_id=attached_to.id if attached_to else None,
        )
        player.battlefield.append(card)
        return card

    def close_event_window(self) -> None:
        while self.game.priority_player_index is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self) -> None:
        self.assertEqual(KUDZU.mana_cost.compact, "1GG")
        self.assertEqual(KUDZU.subtypes, ("Enchant Land",))
        self.assertTrue(KUDZU.destroys_attached_land_when_tapped)

    def test_tapped_land_is_destroyed_and_former_controller_moves_kudzu(self) -> None:
        island = self.permanent(self.bob, ISLAND)
        forest = self.permanent(self.alice, FOREST)
        kudzu = self.permanent(self.alice, KUDZU, attached_to=island)

        self.game.priority_player_index = self.game.players.index(self.bob)
        self.game.activate_ability(self.bob.id, island, 0)
        self.close_event_window()

        self.assertIn(island, self.bob.graveyard)
        self.assertIsNone(kudzu.enchanted_card_id)
        self.assertEqual(kudzu.controller_id, self.bob.id)
        self.assertEqual(self.game.pending_kudzu_choices[0].chooser_id, self.bob.id)

        self.game.choose_kudzu_land(self.bob.id, forest)

        self.assertEqual(kudzu.enchanted_card_id, forest.id)
        self.assertFalse(self.game.pending_kudzu_choices)

    def test_kudzu_is_destroyed_when_no_other_land_remains(self) -> None:
        island = self.permanent(self.bob, ISLAND)
        kudzu = self.permanent(self.alice, KUDZU, attached_to=island)

        self.game.priority_player_index = self.game.players.index(self.bob)
        self.game.activate_ability(self.bob.id, island, 0)
        self.close_event_window()

        self.assertIn(island, self.bob.graveyard)
        self.assertIn(kudzu, self.alice.graveyard)
        self.assertFalse(self.game.pending_kudzu_choices)

    def test_destroying_enchanted_land_normally_also_destroys_kudzu(self) -> None:
        island = self.permanent(self.bob, ISLAND)
        kudzu = self.permanent(self.alice, KUDZU, attached_to=island)

        self.game._destroy_permanents((island,))

        self.assertIn(kudzu, self.alice.graveyard)
        self.assertFalse(self.game.pending_kudzu_choices)

    def test_already_tapped_land_does_not_trigger_again(self) -> None:
        island = self.permanent(self.bob, ISLAND)
        self.permanent(self.alice, KUDZU, attached_to=island)
        island.tapped = True

        self.assertFalse(self.game._tap_permanent(island))
        self.assertFalse(self.game.event_opportunities)


if __name__ == "__main__":
    unittest.main()
