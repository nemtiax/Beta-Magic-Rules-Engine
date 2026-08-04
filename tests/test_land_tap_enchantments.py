import unittest

from beta_magic import (
    BAYOU,
    EVIL_PRESENCE,
    FOREST,
    ICY_MANIPULATOR,
    LIFETAP,
    LIVING_LANDS,
    MANABARBS,
    MOUNTAIN,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class LandTapEnchantmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [MOUNTAIN] * 20)
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
            entered_battlefield_turn=0,
            enchanted_card_id=attached_to.id if attached_to else None,
        )
        player.battlefield.append(card)
        return card

    def pass_event_window(self) -> None:
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def resolve_batch(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_beta_definitions(self) -> None:
        self.assertEqual(LIFETAP.mana_cost.compact, "UU")
        self.assertEqual(MANABARBS.mana_cost.compact, "3R")
        lifetap = LIFETAP.permanent_tapped_effects[0]
        self.assertEqual(lifetap.land_subtype, "Forest")
        self.assertTrue(lifetap.opponent_controlled_only)
        self.assertEqual(lifetap.life_gain, 1)
        self.assertEqual(MANABARBS.permanent_tapped_effects[0].damage, 1)

    def test_lifetap_gains_life_for_each_opponents_forest_tapped(self) -> None:
        self.permanent(self.alice, LIFETAP)
        forest = self.permanent(self.bob, FOREST)

        self.game.activate_ability(self.bob.id, forest, 0)
        self.assertEqual(self.alice.life, 20)
        self.pass_event_window()

        self.assertEqual(self.alice.life, 21)

    def test_lifetap_ignores_its_controllers_forests(self) -> None:
        self.permanent(self.alice, LIFETAP)
        forest = self.permanent(self.alice, FOREST)

        self.game.activate_ability(self.alice.id, forest, 0)

        self.assertEqual(self.game.event_opportunities, [])
        self.assertEqual(self.alice.life, 20)

    def test_lifetap_uses_current_land_types_and_recognizes_dual_lands(self) -> None:
        self.permanent(self.alice, LIFETAP)
        bayou = self.permanent(self.bob, BAYOU)
        converted_forest = self.permanent(self.bob, FOREST)
        self.permanent(self.alice, EVIL_PRESENCE, attached_to=converted_forest)

        self.game.activate_ability(self.bob.id, bayou, 0)
        self.pass_event_window()
        self.assertEqual(self.alice.life, 21)

        self.game.priority_player_index = None
        self.game.activate_ability(self.bob.id, converted_forest, 0)
        self.assertEqual(self.game.event_opportunities, [])
        self.assertEqual(self.alice.life, 21)

    def test_manabarbs_damages_land_controller_for_mana_or_forced_tapping(self) -> None:
        self.permanent(self.alice, MANABARBS)
        forest = self.permanent(self.bob, FOREST)

        self.game.activate_ability(self.bob.id, forest, 0)
        self.pass_event_window()
        self.assertEqual(self.bob.life, 19)

        forest.tapped = False
        icy = self.permanent(self.alice, ICY_MANIPULATOR)
        self.alice.mana_pool.colorless = 1
        self.game.activate_ability(self.alice.id, icy, 0)
        self.game.complete_pending_activation((forest,))
        self.resolve_batch()
        self.assertTrue(forest.tapped)
        self.pass_event_window()
        self.assertEqual(self.bob.life, 18)

    def test_tapping_animated_forest_to_attack_triggers_both_cards(self) -> None:
        self.permanent(self.alice, LIFETAP)
        self.permanent(self.alice, MANABARBS)
        self.permanent(self.alice, LIVING_LANDS)
        forest = self.permanent(self.bob, FOREST)
        forest.entered_battlefield_turn = 0

        while self.game.current_phase is not TurnPhase.END:
            self.game.advance_phase()
        self.game.advance_phase()
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.game.begin_combat()
        self.game.declare_attackers([forest])
        self.pass_event_window()

        self.assertEqual(self.alice.life, 21)
        self.assertEqual(self.bob.life, 19)

    def test_multiple_copies_each_create_their_own_effect(self) -> None:
        self.permanent(self.alice, LIFETAP)
        self.permanent(self.alice, LIFETAP)
        forest = self.permanent(self.bob, FOREST)

        self.game.activate_ability(self.bob.id, forest, 0)
        self.assertEqual(len(self.game.event_opportunities), 2)
        self.pass_event_window()
        self.assertEqual(self.alice.life, 22)


if __name__ == "__main__":
    unittest.main()
