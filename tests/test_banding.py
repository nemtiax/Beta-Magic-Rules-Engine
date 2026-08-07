import unittest

from beta_magic import (
    BENALISH_HERO,
    GRIZZLY_BEARS,
    HELM_OF_CHATZUK,
    MESA_PEGASUS,
    TIMBER_WOLVES,
    Card,
    CombatStep,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class BandingTests(unittest.TestCase):
    def setUp(self):
        self.alice = PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 8)
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 8)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    def creature(self, player, definition):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def resolve_batch(self):
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def activate_helm(self, player, helm, target):
        while self.game.players[self.game.priority_player_index] is not player:
            current = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(current.id)
        player.mana_pool.colorless = 1
        self.game.activate_ability(player.id, helm, 0)
        self.game.complete_pending_activation((target,))
        self.resolve_batch()

    def test_all_but_one_member_of_an_attacking_band_must_have_banding(self):
        hero = self.creature(self.alice, BENALISH_HERO)
        wolves = self.creature(self.alice, TIMBER_WOLVES)
        bear = self.creature(self.alice, GRIZZLY_BEARS)
        self.game.begin_combat()

        self.game.declare_attackers(
            [hero, wolves, bear], bands=[(hero, wolves, bear)]
        )
        self.assertEqual(self.game.combat.attacking_bands, [(hero, wolves, bear)])

        game = GameState([
            PlayerState.with_deck("a", "A", [GRIZZLY_BEARS] * 8),
            PlayerState.with_deck("b", "B", [GRIZZLY_BEARS] * 8),
        ])
        game.start(opening_hand_size=0, shuffle=False)
        while game.current_phase is not TurnPhase.MAIN:
            game.advance_phase()
        bear = Card(
            GRIZZLY_BEARS, owner_id="a", controller_id="a", zone=Zone.BATTLEFIELD
        )
        other_bear = Card(
            GRIZZLY_BEARS, owner_id="a", controller_id="a", zone=Zone.BATTLEFIELD
        )
        game.players[0].battlefield.extend((bear, other_bear))
        game.begin_combat()
        with self.assertRaisesRegex(ValueError, "all but at most one"):
            game.declare_attackers(
                [bear, other_bear], bands=[(bear, other_bear)]
            )

    def test_blocking_one_member_blocks_the_entire_band(self):
        hero = self.creature(self.alice, BENALISH_HERO)
        pegasus = self.creature(self.alice, MESA_PEGASUS)
        blocker = self.creature(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers(
            [hero, pegasus], bands=[(hero, pegasus)]
        )

        # The ground creature can block the Hero, which stops the whole band,
        # including the flying Pegasus.
        self.game.declare_blockers({blocker: pegasus})

        self.assertEqual(self.game.combat.blockers[hero.id], [blocker])
        self.assertEqual(self.game.combat.blockers[pegasus.id], [blocker])

    def test_blocker_divides_damage_among_members_of_attacking_band(self):
        hero = self.creature(self.alice, BENALISH_HERO)
        pegasus = self.creature(self.alice, MESA_PEGASUS)
        blocker = self.creature(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers(
            [hero, pegasus], bands=[(hero, pegasus)]
        )
        self.game.declare_blockers({blocker: hero})
        self.game.advance_combat()
        self.assertEqual(self.game.combat.step, CombatStep.DAMAGE)

        with self.assertRaisesRegex(ValueError, "divide its damage"):
            self.game.deal_combat_damage()
        self.game.deal_combat_damage({blocker: {hero: 2, pegasus: 0}})

        self.assertIn(hero, self.alice.graveyard)
        self.assertIn(pegasus, self.alice.battlefield)
        self.assertIn(blocker, self.bob.graveyard)

    def test_defensive_banding_gives_defender_damage_assignment(self):
        attacker = self.creature(self.alice, GRIZZLY_BEARS)
        hero = self.creature(self.bob, BENALISH_HERO)
        bear = self.creature(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        self.game.declare_blockers({hero: attacker, bear: attacker})
        self.game.advance_combat()
        view = GameViewModel(self.game)

        self.assertEqual(view.state["combatDamageAssignments"], [])
        self.assertEqual(view.state["combatDamageWaitingFor"], "Bob")
        view.switchPerspective()
        rows = view.state["combatDamageAssignments"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sourceName"], "Grizzly Bears")
        self.assertEqual(rows[0]["playerName"], "Bob")

    def test_helm_can_grant_banding_before_attackers_are_declared(self):
        helm = self.creature(self.alice, HELM_OF_CHATZUK)
        first_bear = self.creature(self.alice, GRIZZLY_BEARS)
        second_bear = self.creature(self.alice, GRIZZLY_BEARS)
        self.game.begin_combat()

        self.activate_helm(self.alice, helm, first_bear)
        self.game.declare_attackers(
            [first_bear, second_bear], bands=[(first_bear, second_bear)]
        )

        self.assertTrue(helm.tapped)
        self.assertEqual(
            self.game.combat.attacking_bands,
            [(first_bear, second_bear)],
        )

    def test_helm_after_attackers_does_not_retroactively_make_a_band(self):
        helm = self.creature(self.alice, HELM_OF_CHATZUK)
        first_bear = self.creature(self.alice, GRIZZLY_BEARS)
        second_bear = self.creature(self.alice, GRIZZLY_BEARS)
        blocker = self.creature(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers([first_bear, second_bear])

        self.activate_helm(self.alice, helm, first_bear)
        self.assertEqual(self.game.combat.attacking_bands, [])
        self.game.declare_blockers({blocker: first_bear})

        self.assertEqual(self.game.combat.blockers[first_bear.id], [blocker])
        self.assertEqual(self.game.combat.blockers[second_bear.id], [])

    def test_helm_cannot_be_activated_during_attacker_declaration(self):
        helm = self.creature(self.alice, HELM_OF_CHATZUK)
        bear = self.creature(self.alice, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        self.alice.mana_pool.colorless = 1

        with self.assertRaises(RuntimeError):
            self.game.activate_ability(self.alice.id, helm, 0)

    def test_helm_can_grant_defensive_banding_before_damage(self):
        attacker = self.creature(self.alice, GRIZZLY_BEARS)
        helm = self.creature(self.bob, HELM_OF_CHATZUK)
        first_blocker = self.creature(self.bob, GRIZZLY_BEARS)
        second_blocker = self.creature(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        self.game.declare_blockers(
            {first_blocker: attacker, second_blocker: attacker}
        )

        self.activate_helm(self.bob, helm, first_blocker)
        self.game.advance_combat()
        view = GameViewModel(self.game)
        view.switchPerspective()

        rows = view.state["combatDamageAssignments"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["playerName"], "Bob")


if __name__ == "__main__":
    unittest.main()
