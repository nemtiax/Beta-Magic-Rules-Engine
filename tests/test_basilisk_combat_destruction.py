import unittest

from tests.support import declare_attackers, declare_blockers

from beta_magic.card_defs.white import ANIMATE_WALL
from beta_magic.card_defs.green import (
    COCKATRICE,
    THICKET_BASILISK,
)
from beta_magic import (
    Card,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs.green import (
    GIANT_SPIDER,
    GRIZZLY_BEARS,
    WALL_OF_ICE,
    WALL_OF_WOOD,
)
from beta_magic.card_defs.red import HILL_GIANT


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
        declare_attackers(self.game, [attacker])
        declare_blockers(self.game, {blocker: attacker})
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
                declare_attackers(game, [attacker])
                declare_blockers(game, {blocker: attacker})
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
        declare_attackers(self.game, [basilisk])
        declare_blockers(self.game, {blocker: basilisk})
        self.game._move_card(basilisk, Zone.GRAVEYARD)

        self.game.advance_combat()
        self.game.deal_combat_damage()

        self.assertIn(blocker, self.bob.graveyard)


if __name__ == "__main__":
    unittest.main()
