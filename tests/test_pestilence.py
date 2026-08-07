import unittest

from beta_magic import (
    GRIZZLY_BEARS,
    HILL_GIANT,
    PESTILENCE,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class PestilenceTests(unittest.TestCase):
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
    def permanent(player, definition):
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

    def test_definition(self):
        self.assertEqual(PESTILENCE.mana_cost.compact, "2BB")
        self.assertTrue(PESTILENCE.destroy_at_end_of_turn_if_no_creatures)
        ability = PESTILENCE.activated_abilities[0]
        self.assertEqual(ability.mana_cost_per_damage.compact, "B")

    def test_multiple_payments_can_be_one_damage_effect(self):
        pestilence = self.permanent(self.alice, PESTILENCE)
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.alice.mana_pool.black = 2

        self.game.activate_ability(
            self.alice.id, pestilence, 0, amount=2
        )
        self.resolve_batch()

        self.assertEqual((self.alice.life, self.bob.life), (18, 18))
        self.assertIn(bear, self.bob.graveyard)
        incident = self.game.resolved_damage_incidents[-1]
        player_packets = [
            packet for packet in incident.packets
            if packet.recipient_id in {self.alice.id, self.bob.id}
        ]
        self.assertEqual([packet.amount for packet in player_packets], [2, 2])

    def test_separate_activations_remain_separate_damage_effects(self):
        pestilence = self.permanent(self.alice, PESTILENCE)
        giant = self.permanent(self.bob, HILL_GIANT)
        self.alice.mana_pool.black = 2

        self.game.activate_ability(self.alice.id, pestilence, 0, amount=1)
        self.game.pass_priority(self.bob.id)
        self.game.activate_ability(self.alice.id, pestilence, 0, amount=1)
        self.resolve_batch()

        incident = self.game.resolved_damage_incidents[-1]
        alice_packets = [
            packet for packet in incident.packets
            if packet.recipient_id == self.alice.id
        ]
        self.assertEqual([packet.amount for packet in alice_packets], [1, 1])
        self.assertEqual(giant.damage, 2)

    def test_destroyed_at_end_of_turn_only_when_no_creatures_remain(self):
        pestilence = self.permanent(self.alice, PESTILENCE)
        self.game._finish_turn_effects()
        self.assertIn(pestilence, self.alice.graveyard)

        other = self.permanent(self.alice, PESTILENCE)
        self.permanent(self.alice, GRIZZLY_BEARS)
        self.game._finish_turn_effects()
        self.assertIn(other, self.alice.battlefield)

    def test_checks_after_other_scheduled_end_of_turn_destruction(self):
        pestilence = self.permanent(self.alice, PESTILENCE)
        doomed_creature = self.permanent(self.alice, GRIZZLY_BEARS)
        self.game.destroy_at_end_of_turn.add(doomed_creature.id)

        self.game._finish_turn_effects()

        self.assertIn(doomed_creature, self.alice.graveyard)
        self.assertIn(pestilence, self.alice.graveyard)

    def test_ui_chooses_highest_affordable_damage_by_default(self):
        pestilence = self.permanent(self.alice, PESTILENCE)
        self.alice.mana_pool.black = 3
        view = GameViewModel(self.game)

        view.activateAbility(str(pestilence.id), 0)

        self.assertTrue(view.state["choosingX"])
        self.assertEqual(view.state["xMinimum"], 1)
        self.assertEqual(view.state["xMaximum"], 3)
        self.assertEqual(view.state["xValue"], 3)
        self.assertTrue(view.state["xIsAbility"])
        view.adjustX(-1)
        view.confirmXCast()
        self.assertFalse(view.state["choosingX"])
        self.assertEqual(self.alice.mana_pool.black, 1)
        self.assertEqual(self.game.batch_abilities[0].amount, 2)


if __name__ == "__main__":
    unittest.main()
