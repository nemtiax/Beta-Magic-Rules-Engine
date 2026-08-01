import unittest

from beta_magic import (
    ANIMATE_WALL,
    COCKATRICE,
    THICKET_BASILISK,
    Card,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import (
    GIANT_SPIDER,
    GRIZZLY_BEARS,
    HILL_GIANT,
    WALL_OF_ICE,
    WALL_OF_WOOD,
)


class BasiliskCombatDestructionTests(unittest.TestCase):
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

    def fight(self, attacker, blocker):
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        self.game.declare_blockers({blocker: attacker})
        self.game.advance_combat()
        self.game.deal_combat_damage()

    def test_basilisk_and_cockatrice_destroy_nonwall_blockers(self):
        cases = (
            (THICKET_BASILISK, HILL_GIANT),
            (COCKATRICE, GIANT_SPIDER),
        )
        for attacker_definition, blocker_definition in cases:
            with self.subTest(card=attacker_definition.name):
                game = GameState(
                    [
                        PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 8),
                        PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 8),
                    ]
                )
                game.start(opening_hand_size=0, shuffle=False)
                while game.current_phase is not TurnPhase.MAIN:
                    game.advance_phase()
                attacker = self.permanent(game.players[0], attacker_definition)
                blocker = self.permanent(game.players[1], blocker_definition)
                game.begin_combat()
                game.declare_attackers([attacker])
                game.declare_blockers({blocker: attacker})
                game.advance_combat()
                game.deal_combat_damage()
                self.assertIn(blocker, game.players[1].graveyard)
                self.assertTrue(
                    game.resolved_destruction_incidents[-1]
                    .targets[0]
                    .regeneration_allowed
                )

        self.assertIn(KeywordAbility.FLYING, COCKATRICE.abilities)

    def test_blocking_wall_is_exempt(self):
        basilisk = self.permanent(self.alice, THICKET_BASILISK)
        wall = self.permanent(self.bob, WALL_OF_ICE)

        self.fight(basilisk, wall)

        self.assertIn(wall, self.bob.battlefield)

    def test_attacking_animated_wall_is_not_exempt(self):
        wall = self.permanent(self.alice, WALL_OF_WOOD)
        aura = self.permanent(self.alice, ANIMATE_WALL)
        aura.enchanted_card_id = wall.id
        basilisk = self.permanent(self.bob, THICKET_BASILISK)

        self.fight(wall, basilisk)

        self.assertIn(wall, self.alice.graveyard)

    def test_effect_survives_source_leaving_after_blockers(self):
        basilisk = self.permanent(self.alice, THICKET_BASILISK)
        blocker = self.permanent(self.bob, HILL_GIANT)
        self.game.begin_combat()
        self.game.declare_attackers([basilisk])
        self.game.declare_blockers({blocker: basilisk})
        self.game._move_card(basilisk, Zone.GRAVEYARD)

        self.game.advance_combat()
        self.game.deal_combat_damage()

        self.assertIn(blocker, self.bob.graveyard)


if __name__ == "__main__":
    unittest.main()
