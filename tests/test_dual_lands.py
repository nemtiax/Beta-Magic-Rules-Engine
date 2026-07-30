import unittest

from beta_magic import (
    BADLANDS,
    BAYOU,
    DUAL_LANDS,
    PLATEAU,
    SAVANNAH,
    SCRUBLAND,
    TAIGA,
    TROPICAL_ISLAND,
    TUNDRA,
    UNDERGROUND_SEA,
    VOLCANIC_ISLAND,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import FOREST


class DualLandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.advance_phase()

    def put_in_play(self, definition):
        card = self.alice.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = self.alice.id
        self.alice.battlefield.append(card)
        return card

    def test_all_ten_beta_dual_lands_are_defined(self) -> None:
        self.assertEqual(
            DUAL_LANDS,
            (
                TUNDRA,
                UNDERGROUND_SEA,
                BADLANDS,
                TAIGA,
                SAVANNAH,
                SCRUBLAND,
                VOLCANIC_ISLAND,
                BAYOU,
                PLATEAU,
                TROPICAL_ISLAND,
            ),
        )
        self.assertEqual(len(DUAL_LANDS), 10)
        self.assertTrue(all(not land.is_basic_land for land in DUAL_LANDS))
        self.assertTrue(all(len(land.subtypes) == 2 for land in DUAL_LANDS))
        self.assertTrue(all(len(land.activated_abilities) == 2 for land in DUAL_LANDS))

    def test_tropical_island_has_forest_and_island_mana_abilities(self) -> None:
        self.assertEqual(TROPICAL_ISLAND.subtypes, ("Forest", "Island"))
        self.assertEqual(
            [ability.color for ability in TROPICAL_ISLAND.activated_abilities],
            [Color.GREEN, Color.BLUE],
        )

    def test_player_selects_which_dual_land_ability_to_activate(self) -> None:
        land = self.put_in_play(TUNDRA)

        self.game.activate_ability(self.alice.id, land, 1)

        self.assertTrue(land.tapped)
        self.assertEqual(self.alice.mana_pool.blue, 1)
        self.assertEqual(self.alice.mana_pool.white, 0)

    def test_tapped_dual_land_cannot_activate_its_other_ability(self) -> None:
        land = self.put_in_play(BADLANDS)
        self.game.activate_ability(self.alice.id, land, 0)

        with self.assertRaisesRegex(RuntimeError, "already tapped"):
            self.game.activate_ability(self.alice.id, land, 1)

    def test_basic_land_uses_the_same_activated_ability_system(self) -> None:
        land = self.put_in_play(FOREST)

        self.game.tap_land_for_mana(self.alice.id, land)

        self.assertEqual(self.alice.mana_pool.green, 1)
        self.assertEqual(len(FOREST.activated_abilities), 1)

    def test_mana_abilities_remain_unavailable_during_untap(self) -> None:
        game = GameState(
            [
                PlayerState.with_deck("alice", "Alice", [TUNDRA] * 20),
                PlayerState.with_deck("bob", "Bob", [FOREST] * 20),
            ]
        )
        game.start(opening_hand_size=0, shuffle=False)
        land = game.players[0].library.pop()
        land.zone = Zone.BATTLEFIELD
        land.controller_id = "alice"
        game.players[0].battlefield.append(land)

        with self.assertRaisesRegex(RuntimeError, "Untap"):
            game.activate_ability("alice", land, 0)

