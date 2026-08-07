import unittest

from beta_magic import (
    BENALISH_HERO,
    GRIZZLY_BEARS,
    LURE,
    MESA_PEGASUS,
    PHANTOM_MONSTER,
    TWO_HEADED_GIANT_OF_FORIYS,
    Card,
    CombatStep,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui_combat import CombatUiController


class LureTests(unittest.TestCase):
    def setUp(self):
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 20
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition, *, attached=None):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        card.enchanted_card_id = attached.id if attached is not None else None
        player.battlefield.append(card)
        return card

    def test_definition(self):
        self.assertEqual(LURE.mana_cost.compact, "1GG")
        self.assertTrue(LURE.lures_blockers)
        self.assertEqual(LURE.subtypes, ("Enchant Creature",))

    def test_every_eligible_defender_must_block_lured_attacker(self):
        lured = self.permanent(self.alice, GRIZZLY_BEARS)
        other = self.permanent(self.alice, GRIZZLY_BEARS)
        self.permanent(self.alice, LURE, attached=lured)
        first = self.permanent(self.bob, GRIZZLY_BEARS)
        second = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers([lured, other])

        with self.assertRaisesRegex(ValueError, "Lured attacker"):
            self.game.declare_blockers({first: lured, second: other})
        self.game.declare_blockers({first: lured, second: lured})

        self.assertEqual(self.game.combat.blockers[lured.id], [first, second])
        self.assertEqual(self.game.combat.blockers[other.id], [])

    def test_creatures_unable_to_block_lured_flyer_are_not_forced(self):
        lured_flyer = self.permanent(self.alice, PHANTOM_MONSTER)
        ground = self.permanent(self.alice, GRIZZLY_BEARS)
        self.permanent(self.alice, LURE, attached=lured_flyer)
        ground_blocker = self.permanent(self.bob, GRIZZLY_BEARS)
        flying_blocker = self.permanent(self.bob, MESA_PEGASUS)
        self.game.begin_combat()
        self.game.declare_attackers([lured_flyer, ground])

        self.game.declare_blockers(
            {ground_blocker: ground, flying_blocker: lured_flyer}
        )

        self.assertNotIn(
            ground_blocker, self.game.combat.blockers[lured_flyer.id]
        )

    def test_multiple_lured_attackers_allow_each_blocker_to_choose(self):
        first_lure = self.permanent(self.alice, GRIZZLY_BEARS)
        second_lure = self.permanent(self.alice, GRIZZLY_BEARS)
        self.permanent(self.alice, LURE, attached=first_lure)
        self.permanent(self.alice, LURE, attached=second_lure)
        first_blocker = self.permanent(self.bob, GRIZZLY_BEARS)
        second_blocker = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers([first_lure, second_lure])

        self.game.declare_blockers(
            {first_blocker: first_lure, second_blocker: second_lure}
        )

        self.assertIn(first_blocker, self.game.combat.blockers[first_lure.id])
        self.assertIn(second_blocker, self.game.combat.blockers[second_lure.id])

    def test_lure_does_not_prevent_a_multi_blocker_from_blocking_another(self):
        lured = self.permanent(self.alice, GRIZZLY_BEARS)
        other = self.permanent(self.alice, GRIZZLY_BEARS)
        self.permanent(self.alice, LURE, attached=lured)
        giant = self.permanent(self.bob, TWO_HEADED_GIANT_OF_FORIYS)
        self.game.begin_combat()
        self.game.declare_attackers([lured, other])

        self.game.declare_blockers({giant: (lured, other)})

        self.assertIn(giant, self.game.combat.blockers[lured.id])
        self.assertIn(giant, self.game.combat.blockers[other.id])

    def test_lured_band_member_only_affects_creatures_that_can_block_it(self):
        hero = self.permanent(self.alice, BENALISH_HERO)
        lured_pegasus = self.permanent(self.alice, MESA_PEGASUS)
        self.permanent(self.alice, LURE, attached=lured_pegasus)
        ground_blocker = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers(
            [hero, lured_pegasus], bands=[(hero, lured_pegasus)]
        )

        self.game.declare_blockers({})

        self.assertEqual(self.game.combat.blockers[hero.id], [])
        self.assertEqual(self.game.combat.blockers[lured_pegasus.id], [])
        self.assertNotIn(ground_blocker, self.game.combat.blockers[hero.id])

    def test_ui_preloads_forced_lure_blocks(self):
        lured = self.permanent(self.alice, GRIZZLY_BEARS)
        self.permanent(self.alice, LURE, attached=lured)
        first = self.permanent(self.bob, GRIZZLY_BEARS)
        second = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers([lured])
        self.game.combat.step = CombatStep.DECLARE_BLOCKERS
        controller = CombatUiController()

        controller.sync(self.game)

        self.assertEqual(
            controller.blocker_assignments(self.game),
            {first: (lured,), second: (lured,)},
        )


if __name__ == "__main__":
    unittest.main()
