import unittest

from beta_magic.card_defs.white import (
    PERSONAL_INCARNATION,
    VETERAN_BODYGUARD,
)
from beta_magic.card_defs.artifacts import JADE_MONOLITH
from beta_magic import (
    Card,
    DamageIncidentKind,
    DamageRecipientKind,
    DamageResolutionStep,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs.green import GRIZZLY_BEARS


class PersonalIncarnationBodyguardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.game.pause_for_damage_windows = True

    @staticmethod
    def permanent(player, definition, *, owner_id=None):
        card = Card(
            definition,
            owner_id=owner_id or player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def pass_window(self):
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def open_damage(self, recipient, amount=4, **nature):
        source = Card(GRIZZLY_BEARS, owner_id=self.bob.id, controller_id=self.bob.id)
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(
            recipient,
            amount,
            source.name,
            source_card=source,
            **nature,
        )
        self.game._resolve_damage_incident()
        self.pass_window()
        self.assertIs(
            self.game.pending_damage.step, DamageResolutionStep.REDIRECTION
        )
        return self.game.pending_damage.packets[0]

    def test_owner_can_redirect_part_of_incarnation_damage_to_self(self):
        incarnation = self.permanent(
            self.bob, PERSONAL_INCARNATION, owner_id=self.alice.id
        )
        packet = self.open_damage(incarnation)

        self.game.activate_ability(self.alice.id, incarnation, 0)
        self.game.redirect_damage(self.alice.id, packet.id, 2)

        redirected = self.game.pending_damage.redirected_packets[0]
        self.assertEqual(packet.remaining, 2)
        self.assertEqual(redirected.amount, 2)
        self.assertEqual(redirected.recipient_kind, DamageRecipientKind.PLAYER)
        self.assertEqual(redirected.recipient_id, self.alice.id)

    def test_owner_can_redirect_part_of_own_damage_to_incarnation(self):
        incarnation = self.permanent(self.alice, PERSONAL_INCARNATION)
        packet = self.open_damage(self.alice, amount=3)

        self.game.activate_ability(self.alice.id, incarnation, 0)
        self.game.redirect_damage(self.alice.id, packet.id, 1)

        redirected = self.game.pending_damage.redirected_packets[0]
        self.assertEqual(redirected.amount, 1)
        self.assertEqual(redirected.recipient_kind, DamageRecipientKind.CREATURE)
        self.assertEqual(redirected.recipient_id, incarnation.id)

    def test_incarnation_graveyard_penalty_is_owner_life_loss(self):
        incarnation = self.permanent(
            self.bob, PERSONAL_INCARNATION, owner_id=self.alice.id
        )
        self.alice.life = 15

        self.game._move_card(incarnation, Zone.GRAVEYARD)

        self.assertEqual(self.alice.life, 7)
        self.assertEqual(self.bob.life, 20)

    def test_exiling_incarnation_does_not_cause_life_loss(self):
        incarnation = self.permanent(self.alice, PERSONAL_INCARNATION)
        self.game._move_card(incarnation, Zone.EXILE)
        self.assertEqual(self.alice.life, 20)

    def test_each_bodyguard_receives_full_unblocked_combat_damage(self):
        first = self.permanent(self.alice, VETERAN_BODYGUARD)
        second = self.permanent(self.alice, VETERAN_BODYGUARD)
        packet = self.open_damage(
            self.alice, amount=3, combat=True, trample=False
        )

        self.assertEqual(packet.remaining, 0)
        redirected = self.game.pending_damage.redirected_packets
        self.assertEqual(
            {(item.recipient_id, item.amount) for item in redirected},
            {(first.id, 3), (second.id, 3)},
        )

    def test_bodyguard_does_not_take_blocked_trample_or_spell_damage(self):
        self.permanent(self.alice, VETERAN_BODYGUARD)
        trample = self.open_damage(
            self.alice, amount=2, combat=True, trample=True
        )
        self.assertEqual(trample.remaining, 2)
        self.assertEqual(self.game.pending_damage.redirected_packets, [])

    def test_multiple_bodyguards_copy_only_unprevented_damage_without_looping(
        self,
    ) -> None:
        first = self.permanent(self.alice, VETERAN_BODYGUARD)
        second = self.permanent(self.alice, VETERAN_BODYGUARD)
        monolith = self.permanent(self.alice, JADE_MONOLITH)
        source = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game._begin_damage_incident(DamageIncidentKind.COMBAT)
        self.game._deal_damage(
            self.alice,
            5,
            source.name,
            source_card=source,
            combat=True,
            trample=False,
        )
        self.game._resolve_damage_incident()
        original = self.game.pending_damage.packets[0]
        original.prevented = 2

        self.pass_window()
        self.assertEqual(
            {
                (packet.recipient_id, packet.amount)
                for packet in self.game.pending_damage.redirected_packets
            },
            {(first.id, 3), (second.id, 3)},
        )
        self.pass_window()
        self.pass_window()

        # Both copied portions form one fresh incident with independent
        # prevention and redirection choices.
        incident = self.game.pending_damage
        self.assertIsNotNone(incident)
        self.assertIs(incident.step, DamageResolutionStep.PREVENTION)
        self.assertEqual(len(incident.packets), 2)
        first_packet = next(
            packet for packet in incident.packets if packet.recipient_id == first.id
        )
        self.pass_window()
        self.alice.mana_pool.colorless = 1
        self.game.activate_ability(self.alice.id, monolith, 0)
        self.game.redirect_damage(self.alice.id, first_packet.id)
        self.pass_window()
        self.pass_window()

        # The Monolith's redirected portion reaches the player once; it is
        # not offered to the Bodyguards again.
        redirected = self.game.pending_damage
        self.assertIsNotNone(redirected)
        self.assertEqual(len(redirected.packets), 1)
        self.assertEqual(redirected.packets[0].recipient_id, self.alice.id)
        while self.game.pending_damage is not None:
            self.pass_window()
        self.assertEqual(self.alice.life, 17)
        self.assertEqual(first.damage, 0)
        self.assertEqual(second.damage, 3)


if __name__ == "__main__":
    unittest.main()
