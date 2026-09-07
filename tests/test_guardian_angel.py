import unittest

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.green import GRIZZLY_BEARS
from beta_magic.card_defs.white import GUARDIAN_ANGEL
from beta_magic.damage import DamageIncidentKind, DamageResolutionStep
from beta_magic.ui import GameViewModel


class GuardianAngelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0
        self.game.pause_for_damage_windows = True

    @staticmethod
    def add(player, definition, zone):
        card = Card(definition, player.id, zone=zone)
        player.cards_in(zone).append(card)
        return card

    def open_damage(self, recipient, amount):
        self.game._begin_damage_incident(DamageIncidentKind.FAST_EFFECT_BATCH)
        self.game._deal_damage(recipient, amount, "Test damage")
        self.game._resolve_damage_incident()
        self.assertIs(
            self.game.pending_damage.step,
            DamageResolutionStep.PREVENTION,
        )

    def finish_damage(self):
        while self.game.pending_damage is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def cast_angel(self, recipient, x):
        angel = self.add(self.alice, GUARDIAN_ANGEL, Zone.HAND)
        self.alice.mana_pool.white = 1
        self.alice.mana_pool.colorless = x
        self.game.begin_guardian_angel(angel, x)
        packet = next(
            packet for packet in self.game.pending_damage.packets
            if packet.recipient_id == recipient.id
        )
        self.game.prevent_damage(self.alice.id, packet.id)
        return angel

    def test_initial_x_and_later_mana_payments_protect_same_target(self):
        self.open_damage(self.alice, 3)
        angel = self.cast_angel(self.alice, 2)
        self.assertEqual(angel.zone, Zone.GRAVEYARD)
        self.assertIn((self.alice.id, self.alice.id), self.game.guardian_angel_targets)
        self.finish_damage()
        self.assertEqual(self.alice.life, 19)

        self.open_damage(self.alice, 4)
        self.alice.mana_pool.colorless = 3
        packet, maximum = self.game.guardian_angel_payment_options(self.alice.id)[0]
        self.assertEqual(maximum, 3)
        self.game.pay_guardian_angel_prevention(self.alice.id, packet.id, 3)
        self.finish_damage()
        self.assertEqual(self.alice.life, 18)

    def test_later_payment_cannot_protect_a_different_target(self):
        bear = self.add(self.alice, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.open_damage(self.alice, 1)
        self.cast_angel(self.alice, 1)
        self.finish_damage()

        self.open_damage(bear, 1)
        self.alice.mana_pool.colorless = 1
        self.assertEqual(
            self.game.guardian_angel_payment_options(self.alice.id), []
        )

    def test_permission_expires_at_the_next_turn(self):
        self.open_damage(self.alice, 1)
        self.cast_angel(self.alice, 1)
        self.finish_damage()

        self.game._begin_scheduled_turn(self.bob.id)
        self.assertEqual(self.game.guardian_angel_targets, set())

    def test_ui_uses_x_picker_then_offers_paid_prevention(self):
        angel = self.add(self.alice, GUARDIAN_ANGEL, Zone.HAND)
        self.alice.mana_pool.white = 1
        self.alice.mana_pool.colorless = 2
        self.open_damage(self.alice, 3)
        view = GameViewModel(self.game)

        view.activateCard(str(angel.id))
        self.assertEqual(view.state["xValue"], 2)
        view.confirmXCast()
        self.assertTrue(view.state["choosingPrevention"])
        view.chooseDamagePacket(view.state["damagePacketChoices"][0]["id"])
        self.finish_damage()

        self.open_damage(self.alice, 2)
        self.alice.mana_pool.colorless = 2
        option = view.state["guardianAngelOptions"][0]
        view.chooseGuardianAngelPacket(option["id"])
        self.assertTrue(view.state["choosingGuardianAngelPayment"])
        view.adjustGuardianAngelAmount(-1)
        view.confirmGuardianAngelPayment()
        self.assertEqual(self.game.pending_damage.total_remaining, 1)

    def test_ui_closes_paid_prevention_picker_after_preventing_final_point(self):
        self.open_damage(self.alice, 1)
        self.cast_angel(self.alice, 1)
        self.finish_damage()

        self.open_damage(self.alice, 2)
        self.alice.mana_pool.colorless = 2
        view = GameViewModel(self.game)
        option = view.state["guardianAngelOptions"][0]
        view.chooseGuardianAngelPacket(option["id"])
        self.assertEqual(view.state["guardianAngelAmount"], 2)

        notified_choice_states = []
        view.stateChanged.connect(
            lambda: notified_choice_states.append(
                view.state["choosingGuardianAngelPayment"]
            )
        )
        view.confirmGuardianAngelPayment()

        self.assertEqual(self.game.pending_damage.total_remaining, 0)
        self.assertFalse(view.state["choosingGuardianAngelPayment"])
        self.assertFalse(notified_choice_states[-1])


if __name__ == "__main__":
    unittest.main()
