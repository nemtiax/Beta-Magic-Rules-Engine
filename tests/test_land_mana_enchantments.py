import unittest

from beta_magic import (
    BAYOU,
    FOREST,
    ICY_MANIPULATOR,
    ISLAND,
    LIVING_LANDS,
    MANA_FLARE,
    WILD_GROWTH,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class LandManaEnchantmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [ISLAND] * 20)
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

    def resolve_batch(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_beta_definitions(self) -> None:
        self.assertEqual(WILD_GROWTH.mana_cost.compact, "G")
        self.assertEqual(MANA_FLARE.mana_cost.compact, "2R")
        self.assertEqual(WILD_GROWTH.subtypes, ("Enchant Land",))
        self.assertEqual(WILD_GROWTH.attached_tap_mana_effects[0].amount, 1)
        self.assertEqual(MANA_FLARE.land_mana_bonus_effects[0].amount, 1)

    def test_wild_growth_adds_green_in_addition_to_normal_land_mana(self) -> None:
        island = self.permanent(self.bob, ISLAND)
        self.permanent(self.alice, WILD_GROWTH, attached_to=island)

        self.game.activate_ability(self.bob.id, island, 0)

        self.assertEqual(self.bob.mana_pool.blue, 1)
        self.assertEqual(self.bob.mana_pool.green, 1)
        self.assertEqual(self.alice.mana_pool.total, 0)

    def test_wild_growth_produces_mana_when_icy_taps_the_land(self) -> None:
        forest = self.permanent(self.bob, FOREST)
        self.permanent(self.alice, WILD_GROWTH, attached_to=forest)
        icy = self.permanent(self.alice, ICY_MANIPULATOR)
        self.alice.mana_pool.colorless = 1

        self.game.activate_ability(self.alice.id, icy, 0)
        self.game.complete_pending_activation((forest,))
        self.resolve_batch()

        self.assertTrue(forest.tapped)
        self.assertEqual(self.bob.mana_pool.green, 1)

    def test_wild_growth_produces_mana_when_animated_land_attacks(self) -> None:
        self.permanent(self.alice, LIVING_LANDS)
        forest = self.permanent(self.alice, FOREST)
        self.permanent(self.alice, WILD_GROWTH, attached_to=forest)

        self.game.begin_combat()
        self.game.declare_attackers([forest])

        self.assertEqual(self.alice.mana_pool.green, 1)

    def test_mana_flare_only_applies_when_land_is_tapped_for_mana(self) -> None:
        self.permanent(self.alice, MANA_FLARE)
        island = self.permanent(self.bob, ISLAND)

        self.assertTrue(self.game._tap_permanent(island))
        self.assertEqual(self.bob.mana_pool.total, 0)

        island.tapped = False
        self.game.activate_ability(self.bob.id, island, 0)
        self.assertEqual(self.bob.mana_pool.blue, 2)

    def test_mana_flare_duplicates_chosen_dual_land_color_only(self) -> None:
        self.permanent(self.alice, MANA_FLARE)
        bayou = self.permanent(self.bob, BAYOU)

        self.game.activate_ability(self.bob.id, bayou, 1)

        self.assertEqual(self.bob.mana_pool.green, 2)
        self.assertEqual(self.bob.mana_pool.black, 0)

    def test_multiple_mana_flares_and_wild_growth_stack(self) -> None:
        self.permanent(self.alice, MANA_FLARE)
        self.permanent(self.bob, MANA_FLARE)
        forest = self.permanent(self.alice, FOREST)
        self.permanent(self.alice, WILD_GROWTH, attached_to=forest)
        self.permanent(self.bob, WILD_GROWTH, attached_to=forest)

        self.game.activate_ability(self.alice.id, forest, 0)

        # One normal mana, two Mana Flares, and two Wild Growths.
        self.assertEqual(self.alice.mana_pool.green, 5)


if __name__ == "__main__":
    unittest.main()
