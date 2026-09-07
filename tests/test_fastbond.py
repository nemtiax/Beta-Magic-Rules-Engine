import unittest

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.green import FASTBOND
from beta_magic.card_defs.lands import FOREST, ISLAND, PLAINS


class FastbondTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [FOREST] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [ISLAND] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def add_card(player, definition, zone) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id if zone is Zone.BATTLEFIELD else None,
            base_controller_id=player.id if zone is Zone.BATTLEFIELD else None,
            zone=zone,
        )
        player.cards_in(zone).append(card)
        return card

    def add_fastbond(self) -> Card:
        return self.add_card(self.alice, FASTBOND, Zone.BATTLEFIELD)

    def land(self, definition=FOREST) -> Card:
        return self.add_card(self.alice, definition, Zone.HAND)

    def test_first_land_is_free_and_each_later_land_deals_one_damage(self) -> None:
        self.add_fastbond()
        lands = [self.land(), self.land(ISLAND), self.land(PLAINS)]
        self.game.play_land(lands[0])
        self.assertEqual(self.alice.life, 20)
        self.game.play_land(lands[1])
        self.assertEqual(self.alice.life, 19)
        self.game.play_land(lands[2])
        self.assertEqual(self.alice.life, 18)
        self.assertEqual(self.game.lands_played_this_turn, 3)

    def test_playing_fastbond_after_normal_land_does_not_grant_a_new_free_land(self) -> None:
        first = self.land()
        second = self.land()
        self.game.play_land(first)
        self.add_fastbond()
        self.game.play_land(second)
        self.assertEqual(self.alice.life, 19)

    def test_second_fastbond_does_not_reset_the_land_counter(self) -> None:
        self.add_fastbond()
        self.game.play_land(self.land())
        self.game.play_land(self.land())
        self.assertEqual(self.alice.life, 19)
        self.add_fastbond()
        self.game.play_land(self.land())
        self.assertEqual(self.game.lands_played_this_turn, 3)
        self.assertEqual(self.alice.life, 17)

    def test_losing_all_fastbonds_restores_normal_land_limit(self) -> None:
        fastbond = self.add_fastbond()
        self.game.play_land(self.land())
        self.game.play_land(self.land())
        self.game._move_card(fastbond, Zone.GRAVEYARD)
        with self.assertRaisesRegex(RuntimeError, "already played a land"):
            self.game.play_land(self.land())

    def test_fastbond_does_not_change_when_lands_may_be_played(self) -> None:
        self.add_fastbond()
        land = self.land()
        self.game.current_phase = TurnPhase.DISCARD
        with self.assertRaisesRegex(RuntimeError, "Main phase"):
            self.game.play_land(land)

    def test_opponents_fastbond_does_not_grant_permission(self) -> None:
        self.add_card(self.bob, FASTBOND, Zone.BATTLEFIELD)
        self.game.play_land(self.land())
        with self.assertRaisesRegex(RuntimeError, "already played a land"):
            self.game.play_land(self.land())

    def test_land_entering_without_being_played_neither_counts_nor_hurts(self) -> None:
        self.add_fastbond()
        land = self.alice.library[-1]
        self.game._move_card(land, Zone.BATTLEFIELD)
        self.assertEqual(self.game.lands_played_this_turn, 0)
        self.assertEqual(self.alice.life, 20)


if __name__ == "__main__":
    unittest.main()
