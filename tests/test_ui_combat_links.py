import unittest

from beta_magic import (
    BENALISH_HERO,
    GRIZZLY_BEARS,
    SERRA_ANGEL,
    MESA_PEGASUS,
    Card,
    CombatState,
    CombatStep,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class UiCombatLinkTests(unittest.TestCase):
    @staticmethod
    def creature(player, definition):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def setUp(self):
        self.attacker = PlayerState("a", "Attacker")
        self.defender = PlayerState("d", "Defender")
        self.game = GameState([self.attacker, self.defender])
        self.view = GameViewModel(self.game)
        self.angel = self.creature(self.attacker, SERRA_ANGEL)
        self.bear_one = self.creature(self.defender, GRIZZLY_BEARS)
        self.bear_two = self.creature(self.defender, GRIZZLY_BEARS)
        self.game.combat = CombatState(
            self.attacker.id,
            self.defender.id,
            attackers=[self.angel],
            blockers={self.angel.id: []},
        )

    def test_unblocked_attacker_is_identified(self):
        data = self.view._card_data(self.angel)
        self.assertEqual(data["combatRole"], "attacker")
        self.assertEqual(data["combatLabel"], "A1 · unblocked")
        self.assertEqual(data["combatDetail"], "A1: Serra Angel — unblocked")

    def test_attacker_and_all_blockers_name_their_relationship(self):
        self.game.combat.blockers[self.angel.id] = [self.bear_one, self.bear_two]

        attacker_data = self.view._card_data(self.angel)
        blocker_data = self.view._card_data(self.bear_one)

        self.assertEqual(attacker_data["combatRole"], "attacker")
        self.assertEqual(attacker_data["combatLabel"], "A1 · blocked ×2")
        self.assertEqual(blocker_data["combatRole"], "blocker")
        self.assertEqual(blocker_data["combatLabel"], "Blocks A1")
        self.assertEqual(
            blocker_data["combatDetail"],
            "Grizzly Bears blocks A1: Serra Angel",
        )

    def test_one_blocker_can_reference_multiple_unique_attacker_markers(self):
        second_attacker = self.creature(self.attacker, GRIZZLY_BEARS)
        self.game.combat.attackers.append(second_attacker)
        self.game.combat.blockers = {
            self.angel.id: [self.bear_one],
            second_attacker.id: [self.bear_one],
        }

        blocker_data = self.view._card_data(self.bear_one)

        self.assertEqual(blocker_data["combatLabel"], "Blocks A1 + A2")
        self.assertIn("A1: Serra Angel", blocker_data["combatDetail"])
        self.assertIn("A2: Grizzly Bears", blocker_data["combatDetail"])

    def test_blocker_uses_band_marker_instead_of_each_attacker_marker(self):
        second_attacker = self.creature(self.attacker, GRIZZLY_BEARS)
        self.game.combat.attackers.append(second_attacker)
        self.game.combat.attacking_bands = [(self.angel, second_attacker)]
        self.game.combat.blockers = {
            self.angel.id: [self.bear_one],
            second_attacker.id: [self.bear_one],
        }

        blocker_data = self.view._card_data(self.bear_one)

        self.assertEqual(blocker_data["combatLabel"], "Blocks B1")
        self.assertIn("B1: Serra Angel + Grizzly Bears", blocker_data["combatDetail"])

    def enter_blocker_draft(self):
        self.game.combat.step = CombatStep.DECLARE_BLOCKERS
        self.view.perspective_index = 1
        self.view._combat_ui.sync(self.game)

    def test_draft_assignments_can_be_overwritten_and_cleared(self):
        self.enter_blocker_draft()
        self.view.toggleCard(str(self.angel.id))
        self.view.toggleCard(str(self.bear_one.id))
        self.view.setBlocks()

        self.assertEqual(
            self.view._combat_ui.draft_for(self.bear_one.id), (self.angel.id,)
        )
        self.assertEqual(
            self.view._card_data(self.bear_one)["combatLabel"], "Blocks A1"
        )

        self.view.toggleCard(str(self.bear_one.id))
        self.view.setBlocks()
        self.assertEqual(self.view._combat_ui.draft_for(self.bear_one.id), ())
        self.assertEqual(self.view._card_data(self.bear_one)["combatLabel"], "")

    def test_different_blockers_can_be_drafted_against_different_attackers(self):
        second_attacker = self.creature(self.attacker, GRIZZLY_BEARS)
        self.game.combat.attackers.append(second_attacker)
        self.game.combat.blockers[second_attacker.id] = []
        self.enter_blocker_draft()

        self.view.toggleCard(str(self.angel.id))
        self.view.toggleCard(str(self.bear_one.id))
        self.view.setBlocks()
        self.view.toggleCard(str(second_attacker.id))
        self.view.toggleCard(str(self.bear_two.id))
        self.view.setBlocks()

        self.assertEqual(
            self.view._card_data(self.bear_one)["combatLabel"], "Blocks A1"
        )
        self.assertEqual(
            self.view._card_data(self.bear_two)["combatLabel"], "Blocks A2"
        )

    def test_declare_blockers_submits_the_draft_atomically(self):
        flying_blocker = self.creature(self.defender, SERRA_ANGEL)
        self.enter_blocker_draft()
        self.view.toggleCard(str(self.angel.id))
        self.view.toggleCard(str(flying_blocker.id))
        self.view.setBlocks()

        self.assertEqual(self.game.combat.blockers[self.angel.id], [])
        self.view.declareBlockers()

        self.assertEqual(
            self.game.combat.blockers[self.angel.id], [flying_blocker]
        )
        self.assertEqual(self.game.combat.step, CombatStep.BLOCKER_RESPONSE)

    def test_multiple_blockers_open_damage_assignment_picker(self):
        self.game.combat.step = CombatStep.DAMAGE
        self.game.combat.blockers[self.angel.id] = [
            self.bear_one,
            self.bear_two,
        ]

        state = self.view.state

        self.assertTrue(state["choosingCombatDamage"])
        self.assertTrue(state["combatDamageValid"])
        assignment = state["combatDamageAssignments"][0]
        self.assertEqual(assignment["sourceName"], "Serra Angel")
        self.assertEqual(assignment["sourceCard"]["name"], "Serra Angel")
        self.assertEqual(assignment["power"], 4)
        self.assertEqual(
            assignment["recipients"][0]["cardData"]["name"],
            "Grizzly Bears",
        )
        self.assertEqual(
            [recipient["amount"] for recipient in assignment["recipients"]],
            [4, 0],
        )

    def test_damage_picker_requires_full_assignment_before_confirming(self):
        self.game.combat.step = CombatStep.DAMAGE
        self.game.combat.blockers[self.angel.id] = [
            self.bear_one,
            self.bear_two,
        ]
        self.view.state

        self.view.adjustCombatDamage(
            str(self.angel.id), str(self.bear_one.id), -1
        )
        state = self.view.state
        self.assertFalse(state["combatDamageValid"])
        self.assertEqual(state["combatDamageAssignments"][0]["remaining"], 1)

        self.view.adjustCombatDamage(
            str(self.angel.id), str(self.bear_two.id), 1
        )
        state = self.view.state
        self.assertTrue(state["combatDamageValid"])
        self.assertEqual(
            [
                recipient["amount"]
                for recipient in state["combatDamageAssignments"][0]["recipients"]
            ],
            [3, 1],
        )

    def test_empty_combat_response_window_does_not_report_empty_batch(self):
        self.game.active_player_index = 0
        self.game.current_phase = TurnPhase.MAIN
        self.game.combat.step = CombatStep.ATTACK_RESPONSE
        self.game.combat.attackers.clear()
        self.game.combat.blockers.clear()
        self.game.priority_player_index = 0
        self.game.consecutive_passes = 0
        self.view.perspective_index = 0

        self.view.passPriority()
        self.view.perspective_index = 1
        self.view.passPriority()

        self.assertEqual(self.game.combat.step, CombatStep.DECLARE_ATTACKERS)
        self.assertEqual(self.view.state["message"], "")

    def test_ui_can_draft_and_declare_an_attacking_band(self):
        hero = self.creature(self.attacker, BENALISH_HERO)
        pegasus = self.creature(self.attacker, MESA_PEGASUS)
        self.game.combat.step = CombatStep.DECLARE_ATTACKERS
        self.game.combat.attackers.clear()
        self.game.combat.blockers.clear()
        self.view.perspective_index = 0

        self.view.toggleCard(str(hero.id))
        self.view.toggleCard(str(pegasus.id))
        self.view.setAttackingBand()

        self.assertEqual(self.view._card_data(hero)["combatLabel"], "Band B1")
        self.view.declareAttackers()
        self.assertEqual(self.game.combat.attacking_bands, [(hero, pegasus)])
        self.assertEqual(set(self.game.combat.attackers), {hero, pegasus})


if __name__ == "__main__":
    unittest.main()
