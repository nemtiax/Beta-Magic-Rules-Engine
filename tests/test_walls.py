import unittest

from beta_magic import (
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    VANILLA_WALLS,
    WALL_OF_ICE,
    WALL_OF_STONE,
    WALL_OF_WOOD,
    Zone,
)
from beta_magic.vanilla_creatures import GRIZZLY_BEARS


def player(player_id: str) -> PlayerState:
    return PlayerState.with_deck(player_id, player_id.title(), [GRIZZLY_BEARS] * 8)


class VanillaWallTests(unittest.TestCase):
    def test_all_three_beta_vanilla_walls_are_defined(self) -> None:
        self.assertEqual(
            [wall.name for wall in VANILLA_WALLS],
            ["Wall of Ice", "Wall of Stone", "Wall of Wood"],
        )
        self.assertEqual(
            [(wall.mana_cost.mana_value, wall.power, wall.toughness) for wall in VANILLA_WALLS],
            [(3, 0, 7), (3, 0, 8), (1, 0, 3)],
        )
        self.assertTrue(
            all(
                CardType.CREATURE in wall.card_types
                and wall.subtypes == ("Wall",)
                and not wall.rules_text
                for wall in VANILLA_WALLS
            )
        )

    def setUp(self) -> None:
        self.alice = player("alice")
        self.bob = player("bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(owner: PlayerState, definition):
        card = owner.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        owner.battlefield.append(card)
        return card

    def test_wall_creature_type_prevents_attacking(self) -> None:
        wall = self.put_in_play(self.alice, WALL_OF_WOOD)
        self.game.begin_combat()
        with self.assertRaisesRegex(ValueError, "Wall and cannot attack"):
            self.game.declare_attackers([wall])
        self.assertFalse(wall.tapped)

    def test_wall_can_block_normally(self) -> None:
        bear = self.put_in_play(self.alice, GRIZZLY_BEARS)
        wall = self.put_in_play(self.bob, WALL_OF_WOOD)
        self.game.begin_combat()
        self.game.declare_attackers([bear])
        self.game.declare_blockers({wall: bear})
        self.game.advance_combat()
        self.game.deal_combat_damage()
        self.assertIn(wall, self.bob.battlefield)
        self.assertEqual(wall.damage, 2)
        self.assertIn(bear, self.alice.battlefield)
        self.assertEqual(bear.damage, 0)

    def test_wall_casts_like_an_ordinary_creature(self) -> None:
        wall = self.alice.library.pop()
        wall.definition = WALL_OF_WOOD
        wall.zone = Zone.HAND
        self.alice.hand.append(wall)
        self.alice.mana_pool.green = 1
        self.game.cast_creature(wall)
        self.assertIn(wall, self.alice.battlefield)
        self.assertEqual(self.alice.mana_pool.total, 0)


if __name__ == "__main__":
    unittest.main()
