import unittest

from beta_magic import (
    BAYOU,
    BOG_WRAITH,
    LANDWALK_CREATURES,
    SHANODIN_DRYADS,
    TUNDRA,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.basic_lands import FOREST, SWAMP
from beta_magic.vanilla_creatures import GRIZZLY_BEARS


class LandwalkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 24
        )
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 24)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(player, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = player.id
        player.battlefield.append(card)
        return card

    def begin_attack(self, attacker):
        self.game.begin_combat()
        self.game.declare_attackers([attacker])

    def test_definitions(self) -> None:
        self.assertEqual(LANDWALK_CREATURES, (BOG_WRAITH, SHANODIN_DRYADS))
        self.assertEqual(
            (BOG_WRAITH.mana_cost.compact, BOG_WRAITH.power, BOG_WRAITH.toughness),
            ("3B", 3, 3),
        )
        self.assertEqual(
            (
                SHANODIN_DRYADS.mana_cost.compact,
                SHANODIN_DRYADS.power,
                SHANODIN_DRYADS.toughness,
            ),
            ("G", 1, 1),
        )
        self.assertIn(KeywordAbility.SWAMPWALK, BOG_WRAITH.abilities)
        self.assertIn(KeywordAbility.FORESTWALK, SHANODIN_DRYADS.abilities)

    def test_landwalk_creature_can_be_blocked_without_matching_land(self) -> None:
        wraith = self.put_in_play(self.alice, BOG_WRAITH)
        blocker = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.put_in_play(self.bob, FOREST)
        self.begin_attack(wraith)

        self.game.declare_blockers({blocker: wraith})

        self.assertIn(blocker, self.game.combat.blockers[wraith.id])

    def test_basic_swamp_makes_bog_wraith_unblockable(self) -> None:
        wraith = self.put_in_play(self.alice, BOG_WRAITH)
        blocker = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.put_in_play(self.bob, SWAMP)
        self.begin_attack(wraith)

        with self.assertRaisesRegex(ValueError, "swampwalk"):
            self.game.declare_blockers({blocker: wraith})

    def test_bayou_enables_both_swampwalk_and_forestwalk(self) -> None:
        for definition, message in (
            (BOG_WRAITH, "swampwalk"),
            (SHANODIN_DRYADS, "forestwalk"),
        ):
            with self.subTest(definition.name):
                game = GameState(
                    [
                        PlayerState.with_deck("a", "A", [definition] * 20),
                        PlayerState.with_deck("b", "B", [GRIZZLY_BEARS] * 20),
                    ]
                )
                game.start(opening_hand_size=0, shuffle=False)
                while game.current_phase is not TurnPhase.MAIN:
                    game.advance_phase()
                attacker = self.put_in_play(game.players[0], definition)
                blocker = self.put_in_play(game.players[1], GRIZZLY_BEARS)
                self.put_in_play(game.players[1], BAYOU)
                game.begin_combat()
                game.declare_attackers([attacker])

                with self.assertRaisesRegex(ValueError, message):
                    game.declare_blockers({blocker: attacker})

    def test_unrelated_dual_land_does_not_enable_forestwalk(self) -> None:
        dryads = self.put_in_play(self.alice, SHANODIN_DRYADS)
        blocker = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.put_in_play(self.bob, TUNDRA)
        self.begin_attack(dryads)

        self.game.declare_blockers({blocker: dryads})

        self.assertIn(blocker, self.game.combat.blockers[dryads.id])


if __name__ == "__main__":
    unittest.main()
