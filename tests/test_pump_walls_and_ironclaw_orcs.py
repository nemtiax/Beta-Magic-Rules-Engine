import unittest

from beta_magic import (
    IRONCLAW_ORCS,
    WALL_OF_FIRE,
    WALL_OF_WATER,
    Card,
    ContinuousEffect,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS, MONSS_GOBLIN_RAIDERS


class PumpWallsAndIronclawOrcsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        player.battlefield.append(card)
        return card

    def resolve_batch(self):
        while self.game.priority_player_index is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_both_walls_pump_power_until_end_of_turn(self):
        for definition, color in (
            (WALL_OF_WATER, "blue"),
            (WALL_OF_FIRE, "red"),
        ):
            with self.subTest(card=definition.name):
                wall = self.permanent(self.alice, definition)
                setattr(self.alice.mana_pool, color, 2)
                self.game.activate_ability(self.alice.id, wall, 0)
                self.game.pass_priority(self.bob.id)
                self.game.activate_ability(self.alice.id, wall, 0)
                self.resolve_batch()
                self.assertEqual(self.game.creature_power(wall), 2)
                self.assertEqual(self.game.creature_toughness(wall), 5)
                self.game.temporary_creature_effects.clear()
                self.alice.battlefield.remove(wall)

    def test_ironclaw_orcs_can_block_power_one_but_not_power_two(self):
        orcs = self.permanent(self.bob, IRONCLAW_ORCS)
        small = self.permanent(self.alice, MONSS_GOBLIN_RAIDERS)
        self.game.begin_combat()
        self.game.declare_attackers([small])
        self.game.declare_blockers({orcs: small})

        game = GameState(
            [
                PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 8),
                PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 8),
            ]
        )
        game.start(opening_hand_size=0, shuffle=False)
        while game.current_phase is not TurnPhase.MAIN:
            game.advance_phase()
        bear = self.permanent(game.players[0], GRIZZLY_BEARS)
        other_orcs = self.permanent(game.players[1], IRONCLAW_ORCS)
        game.begin_combat()
        game.declare_attackers([bear])
        with self.assertRaisesRegex(ValueError, "power greater than 1"):
            game.declare_blockers({other_orcs: bear})

    def test_ironclaw_restriction_uses_current_attacker_power(self):
        orcs = self.permanent(self.bob, IRONCLAW_ORCS)
        attacker = self.permanent(self.alice, MONSS_GOBLIN_RAIDERS)
        self.game.temporary_creature_effects[attacker.id] = [
            ContinuousEffect(power=1)
        ]

        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        with self.assertRaisesRegex(ValueError, "power greater than 1"):
            self.game.declare_blockers({orcs: attacker})


if __name__ == "__main__":
    unittest.main()
