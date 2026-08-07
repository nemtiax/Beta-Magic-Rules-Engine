import unittest

from beta_magic import (
    BENALISH_HERO,
    BLAZE_OF_GLORY,
    GRIZZLY_BEARS,
    MESA_PEGASUS,
    PHANTOM_MONSTER,
    Card,
    CombatStep,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui_combat import CombatUiController


class BlazeOfGloryTests(unittest.TestCase):
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
    def card(player, definition, zone=Zone.BATTLEFIELD):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=zone,
        )
        player.cards_in(zone).append(card)
        return card

    def cast_blaze(self, target):
        blaze = self.card(self.alice, BLAZE_OF_GLORY, Zone.HAND)
        self.alice.mana_pool.white = 1
        self.game.begin_cast(blaze)
        self.game.complete_pending_cast((target,))
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        return blaze

    def test_definition_and_casting_window(self):
        self.assertEqual(BLAZE_OF_GLORY.mana_cost.compact, "W")
        blocker = self.card(self.bob, GRIZZLY_BEARS)
        blaze = self.card(self.alice, BLAZE_OF_GLORY, Zone.HAND)
        self.alice.mana_pool.white = 1

        with self.assertRaisesRegex(RuntimeError, "after attackers"):
            self.game.begin_cast(blaze)

        attacker = self.card(self.alice, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        self.game.declare_blockers({blocker: attacker})
        self.alice.mana_pool.white = 1
        with self.assertRaisesRegex(RuntimeError, "before blockers"):
            self.game.begin_cast(blaze)

    def test_only_untapped_defending_creatures_are_legal_targets(self):
        attacker = self.card(self.alice, GRIZZLY_BEARS)
        own_creature = self.card(self.alice, GRIZZLY_BEARS)
        legal_blocker = self.card(self.bob, GRIZZLY_BEARS)
        tapped_blocker = self.card(self.bob, GRIZZLY_BEARS)
        tapped_blocker.tapped = True
        blaze = self.card(self.alice, BLAZE_OF_GLORY, Zone.HAND)
        self.game.begin_combat()
        self.game.declare_attackers([attacker])

        self.assertEqual(self.game.legal_targets_for(blaze), [legal_blocker])
        self.assertNotIn(own_creature, self.game.legal_targets_for(blaze))

    def test_must_block_every_legal_attacker_but_not_flyers(self):
        first = self.card(self.alice, GRIZZLY_BEARS)
        second = self.card(self.alice, GRIZZLY_BEARS)
        flyer = self.card(self.alice, PHANTOM_MONSTER)
        blocker = self.card(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers([first, second, flyer])
        self.cast_blaze(blocker)

        with self.assertRaisesRegex(ValueError, "every attacker"):
            self.game.declare_blockers({blocker: first})
        self.game.declare_blockers({blocker: (first, second)})

        self.assertIn(blocker, self.game.combat.blockers[first.id])
        self.assertIn(blocker, self.game.combat.blockers[second.id])
        self.assertNotIn(blocker, self.game.combat.blockers[flyer.id])

    def test_tapped_target_is_not_forced_or_allowed_to_block(self):
        attacker = self.card(self.alice, GRIZZLY_BEARS)
        blocker = self.card(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        self.cast_blaze(blocker)
        blocker.tapped = True

        self.game.declare_blockers({})
        self.assertEqual(self.game.combat.blockers[attacker.id], [])

    def test_attacking_band_counts_as_one_group(self):
        hero = self.card(self.alice, BENALISH_HERO)
        pegasus = self.card(self.alice, MESA_PEGASUS)
        other = self.card(self.alice, GRIZZLY_BEARS)
        blocker = self.card(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers(
            [hero, pegasus, other], bands=[(hero, pegasus)]
        )
        self.cast_blaze(blocker)

        self.game.declare_blockers({blocker: (hero, other)})

        self.assertIn(blocker, self.game.combat.blockers[hero.id])
        self.assertIn(blocker, self.game.combat.blockers[pegasus.id])
        self.assertIn(blocker, self.game.combat.blockers[other.id])

    def test_ui_preloads_all_required_blocker_assignments(self):
        first = self.card(self.alice, GRIZZLY_BEARS)
        second = self.card(self.alice, GRIZZLY_BEARS)
        blocker = self.card(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers([first, second])
        self.cast_blaze(blocker)
        self.game.combat.step = CombatStep.DECLARE_BLOCKERS
        controller = CombatUiController()

        controller.sync(self.game)

        self.assertEqual(
            controller.blocker_assignments(self.game),
            {blocker: (first, second)},
        )


if __name__ == "__main__":
    unittest.main()
