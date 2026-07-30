import unittest

from beta_magic import (
    BAD_MOON,
    BAYOU,
    FOREST,
    KELDON_WARLORD,
    NIGHTMARE,
    PLAGUE_RATS,
    SWAMP,
    WALL_OF_WOOD,
    Card,
    GameState,
    PlayerState,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS


class VariableCreatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = GameState(
            [
                PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 10),
                PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 10),
            ]
        )
        self.game.start(opening_hand_size=0, shuffle=False)
        self.alice, self.bob = self.game.players

    def put_in_play(self, player, definition):
        card = Card(
            definition=definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def test_keldon_warlord_counts_only_its_controllers_non_walls(self) -> None:
        warlord = self.put_in_play(self.alice, KELDON_WARLORD)
        self.assertEqual(self.game.creature_power(warlord), 1)

        bear = self.put_in_play(self.alice, GRIZZLY_BEARS)
        self.put_in_play(self.alice, WALL_OF_WOOD)
        self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.assertEqual(
            (self.game.creature_power(warlord), self.game.creature_toughness(warlord)),
            (2, 2),
        )

        self.game.put_permanent_in_graveyard(bear)
        self.assertEqual(self.game.creature_power(warlord), 1)

    def test_nightmare_counts_swamp_subtypes_including_dual_lands(self) -> None:
        self.put_in_play(self.alice, SWAMP)
        self.put_in_play(self.alice, BAYOU)
        self.put_in_play(self.alice, FOREST)
        self.put_in_play(self.bob, SWAMP)
        nightmare = self.put_in_play(self.alice, NIGHTMARE)

        self.assertEqual(
            (self.game.creature_power(nightmare), self.game.creature_toughness(nightmare)),
            (2, 2),
        )

    def test_nightmare_dies_immediately_after_its_last_swamp_leaves(self) -> None:
        swamp = self.put_in_play(self.alice, SWAMP)
        nightmare = self.put_in_play(self.alice, NIGHTMARE)

        self.game.put_permanent_in_graveyard(swamp)

        self.assertNotIn(nightmare, self.alice.battlefield)
        self.assertIn(nightmare, self.alice.graveyard)

    def test_plague_rats_counts_rats_on_both_sides(self) -> None:
        alice_rat = self.put_in_play(self.alice, PLAGUE_RATS)
        bob_rat = self.put_in_play(self.bob, PLAGUE_RATS)
        second_alice_rat = self.put_in_play(self.alice, PLAGUE_RATS)
        self.put_in_play(self.alice, GRIZZLY_BEARS)

        for rat in (alice_rat, bob_rat, second_alice_rat):
            self.assertEqual(self.game.creature_power(rat), 3)

        self.game.put_permanent_in_graveyard(bob_rat)
        self.assertEqual(self.game.creature_toughness(alice_rat), 2)

    def test_variable_base_stats_receive_normal_continuous_bonuses(self) -> None:
        rat = self.put_in_play(self.alice, PLAGUE_RATS)
        self.put_in_play(self.alice, BAD_MOON)

        self.assertEqual(
            (self.game.creature_power(rat), self.game.creature_toughness(rat)),
            (2, 2),
        )


if __name__ == "__main__":
    unittest.main()
