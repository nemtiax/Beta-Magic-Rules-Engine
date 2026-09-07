import unittest

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.green import GRIZZLY_BEARS, LIVING_LANDS, WILD_GROWTH
from beta_magic.card_defs.lands import FOREST
from beta_magic.card_defs.red import STONE_RAIN
from beta_magic.card_defs.white import CONSECRATE_LAND, WRATH_OF_GOD


class ConsecrateLandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    @staticmethod
    def add(player, definition, zone):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=zone,
        )
        player.cards_in(zone).append(card)
        return card

    def resolve(self):
        while self.game.priority_player_index is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def consecrate(self, land):
        aura = self.add(self.alice, CONSECRATE_LAND, Zone.HAND)
        self.alice.mana_pool.white = 1
        self.game.begin_cast(aura)
        self.game.complete_pending_cast((land,))
        self.resolve()
        return aura

    def test_entry_destroys_existing_auras_and_blocks_new_ones(self):
        forest = self.add(self.alice, FOREST, Zone.BATTLEFIELD)
        growth = self.add(self.alice, WILD_GROWTH, Zone.BATTLEFIELD)
        growth.enchanted_card_id = forest.id

        aura = self.consecrate(forest)

        self.assertEqual(growth.zone, Zone.GRAVEYARD)
        self.assertEqual(aura.enchanted_card_id, forest.id)
        second_growth = self.add(self.alice, WILD_GROWTH, Zone.HAND)
        self.alice.mana_pool.green = 1
        with self.assertRaisesRegex(RuntimeError, "no legal targets"):
            self.game.begin_cast(second_growth)

    def test_destroy_land_spell_cannot_destroy_consecrated_land(self):
        forest = self.add(self.alice, FOREST, Zone.BATTLEFIELD)
        self.consecrate(forest)
        stone_rain = self.add(self.alice, STONE_RAIN, Zone.HAND)
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = 2

        self.game.begin_cast(stone_rain)
        self.game.complete_pending_cast((forest,))
        self.resolve()

        self.assertEqual(forest.zone, Zone.BATTLEFIELD)
        self.assertEqual(stone_rain.zone, Zone.GRAVEYARD)

    def test_damage_remains_marked_and_becomes_lethal_when_aura_leaves(self):
        forest = self.add(self.alice, FOREST, Zone.BATTLEFIELD)
        living_lands = self.add(self.alice, LIVING_LANDS, Zone.BATTLEFIELD)
        aura = self.consecrate(forest)
        self.assertIn(living_lands, self.alice.battlefield)
        self.assertEqual(self.game.creature_toughness(forest), 1)

        forest.damage = 1
        self.game.check_state_based_actions()
        self.assertEqual(forest.zone, Zone.BATTLEFIELD)
        self.assertEqual(forest.damage, 1)

        self.game._destroy_permanents((aura,))
        self.game.check_state_based_actions()
        self.assertEqual(forest.zone, Zone.GRAVEYARD)

    def test_no_regeneration_destruction_still_cannot_kill_animated_land(self):
        forest = self.add(self.alice, FOREST, Zone.BATTLEFIELD)
        self.add(self.alice, LIVING_LANDS, Zone.BATTLEFIELD)
        self.consecrate(forest)
        wrath = self.add(self.alice, WRATH_OF_GOD, Zone.HAND)
        self.alice.mana_pool.white = 2
        self.alice.mana_pool.colorless = 2

        self.game.begin_cast(wrath)
        self.resolve()

        self.assertEqual(forest.zone, Zone.BATTLEFIELD)
        self.assertEqual(wrath.zone, Zone.GRAVEYARD)

    def test_place_in_graveyard_bypasses_destruction_protection(self):
        forest = self.add(self.alice, FOREST, Zone.BATTLEFIELD)
        self.consecrate(forest)

        self.game.put_permanent_in_graveyard(forest)

        self.assertEqual(forest.zone, Zone.GRAVEYARD)
        self.assertFalse(self.game.land_is_consecrated(forest))


if __name__ == "__main__":
    unittest.main()
