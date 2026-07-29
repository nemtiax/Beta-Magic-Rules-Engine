import unittest

from beta_magic import (
    BASIC_LANDS,
    FOREST,
    ISLAND,
    CardType,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


def player(player_id: str, deck=()) -> PlayerState:
    return PlayerState.with_deck(player_id, player_id.title(), deck)


class BasicLandTests(unittest.TestCase):
    def test_all_five_basic_lands_have_the_right_mana_ability(self) -> None:
        expected = [
            ("Plains", Color.WHITE),
            ("Island", Color.BLUE),
            ("Swamp", Color.BLACK),
            ("Mountain", Color.RED),
            ("Forest", Color.GREEN),
        ]
        self.assertEqual(
            [(land.name, land.produces_mana) for land in BASIC_LANDS], expected
        )
        self.assertTrue(
            all(CardType.LAND in land.card_types and land.is_basic_land for land in BASIC_LANDS)
        )

    def setUp(self) -> None:
        self.alice = player("alice", [FOREST, ISLAND, FOREST])
        self.bob = player("bob", [FOREST, FOREST, FOREST])
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=2, shuffle=False)

    def enter_main(self) -> None:
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    def test_land_can_only_be_played_in_main_and_once_per_turn(self) -> None:
        land = self.alice.hand[0]
        with self.assertRaises(RuntimeError):
            self.game.play_land(land)

        self.enter_main()
        self.game.play_land(land)
        self.assertEqual(land.zone, Zone.BATTLEFIELD)
        self.assertIn(land, self.alice.battlefield)

        with self.assertRaises(RuntimeError):
            self.game.play_land(self.alice.hand[0])

    def test_land_cannot_be_played_during_an_attack(self) -> None:
        self.enter_main()
        self.game.begin_combat()
        with self.assertRaisesRegex(RuntimeError, "during an attack"):
            self.game.play_land(self.alice.hand[0])

    def test_basic_land_taps_for_its_color(self) -> None:
        self.enter_main()
        land = self.alice.hand[0]
        color = land.definition.produces_mana
        assert color is not None
        self.game.play_land(land)
        self.game.tap_land_for_mana("alice", land)

        self.assertTrue(land.tapped)
        self.assertEqual(self.alice.mana_pool.amount(color), 1)
        with self.assertRaises(RuntimeError):
            self.game.tap_land_for_mana("alice", land)

    def test_mana_empties_and_burns_at_phase_end(self) -> None:
        self.enter_main()
        land = self.alice.hand[0]
        self.game.play_land(land)
        self.game.tap_land_for_mana("alice", land)

        self.game.advance_phase()

        self.assertEqual(self.game.current_phase, TurnPhase.DISCARD)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertEqual(self.alice.life, 19)

    def test_opponent_can_make_mana_during_active_players_turn(self) -> None:
        self.game.advance_phase()
        bob_land = self.bob.library[-1]
        self.bob.library.remove(bob_land)
        bob_land.zone = Zone.BATTLEFIELD
        self.bob.battlefield.append(bob_land)

        self.game.tap_land_for_mana("bob", bob_land)
        self.assertEqual(self.bob.mana_pool.amount(Color.GREEN), 1)
        self.game.advance_phase()
        self.assertEqual(self.bob.life, 19)
        self.assertEqual(self.bob.mana_pool.total, 0)

    def test_land_cannot_be_tapped_for_mana_during_untap(self) -> None:
        land = self.alice.library[-1]
        self.alice.library.remove(land)
        land.zone = Zone.BATTLEFIELD
        self.alice.battlefield.append(land)
        with self.assertRaisesRegex(RuntimeError, "Untap phase"):
            self.game.tap_land_for_mana("alice", land)
        self.assertFalse(land.tapped)


if __name__ == "__main__":
    unittest.main()
