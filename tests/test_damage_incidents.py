import unittest

from beta_magic import (
    COPPER_TABLET,
    ORCISH_ARTILLERY,
    LIGHTNING_BOLT,
    PSIONIC_BLAST,
    WAR_MAMMOTH,
    Card,
    Color,
    DamageIncidentKind,
    DamageRecipientKind,
    DamageResolutionStep,
    ELVISH_ARCHERS,
    GameState,
    PlayerState,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS


class DamageIncidentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = GameState(
            [
                PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 20),
                PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 20),
            ]
        )
        self.game.start(opening_hand_size=0, shuffle=False)
        self.alice, self.bob = self.game.players

    def put_in_play(self, player, definition):
        card = Card(
            definition=definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def put_in_hand(self, player, definition):
        card = Card(
            definition=definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=Zone.HAND,
        )
        player.hand.append(card)
        return card

    def pass_all(self) -> None:
        while self.game.priority_player_index is not None:
            player = self.game.players[self.game.priority_player_index]
            result = self.game.pass_priority(player.id)
            if result is not None:
                return

    def pass_damage_window(self) -> None:
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_damage_waits_for_each_resolution_window(self) -> None:
        self.game.pause_for_damage_windows = True
        self.game.advance_phase()
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((bear,))
        self.pass_all()

        incident = self.game.pending_damage
        self.assertIsNotNone(incident)
        self.assertEqual(incident.step, DamageResolutionStep.PREVENTION)
        self.assertEqual(bear.damage, 0)

        self.pass_damage_window()
        self.assertEqual(incident.step, DamageResolutionStep.REDIRECTION)
        self.assertEqual(bear.damage, 0)

        self.pass_damage_window()
        self.assertEqual(incident.step, DamageResolutionStep.REGENERATION)
        self.assertEqual(bear.damage, 3)
        self.assertIn(bear, self.bob.battlefield)

        self.pass_damage_window()
        self.assertIsNone(self.game.pending_damage)
        self.assertEqual(incident.step, DamageResolutionStep.COMPLETE)
        self.assertIn(bear, self.bob.graveyard)

    def test_first_strike_combat_resumes_after_its_damage_windows(self) -> None:
        self.game.pause_for_damage_windows = True
        while self.game.current_phase.value != "main":
            self.game.advance_phase()
        archer = self.put_in_play(self.alice, ELVISH_ARCHERS)
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers([archer])
        self.game.declare_blockers({bear: archer})
        self.game.advance_combat()

        self.game.deal_combat_damage()

        self.assertEqual(
            self.game.pending_damage.kind,
            DamageIncidentKind.FIRST_STRIKE_COMBAT,
        )
        for _ in range(3):
            self.pass_damage_window()

        self.assertIsNone(self.game.pending_damage)
        self.assertIsNone(self.game.combat)
        self.assertIn(bear, self.bob.graveyard)
        self.assertEqual(archer.damage, 0)

    def test_spell_batch_collects_all_damage_before_applying_it(self) -> None:
        self.game.advance_phase()
        blast = self.put_in_hand(self.alice, PSIONIC_BLAST)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 2

        self.game.begin_cast(blast)
        self.game.complete_pending_cast((self.bob,))
        self.pass_all()

        incident = self.game.resolved_damage_incidents[-1]
        self.assertEqual(incident.kind, DamageIncidentKind.FAST_EFFECT_BATCH)
        self.assertEqual(incident.step, DamageResolutionStep.COMPLETE)
        self.assertEqual(
            {(packet.recipient_id, packet.amount) for packet in incident.packets},
            {("alice", 2), ("bob", 4)},
        )
        self.assertTrue(
            all(packet.source_id == blast.id for packet in incident.packets)
        )
        self.assertTrue(
            all(packet.colors == frozenset({Color.BLUE}) for packet in incident.packets)
        )

    def test_activated_damage_records_source_and_controller(self) -> None:
        self.game.advance_phase()
        artillery = self.put_in_play(self.alice, ORCISH_ARTILLERY)

        self.game.activate_ability(self.alice.id, artillery, 0)
        self.game.complete_pending_activation((self.bob,))
        self.pass_all()

        incident = self.game.resolved_damage_incidents[-1]
        self.assertEqual(incident.kind, DamageIncidentKind.FAST_EFFECT_BATCH)
        self.assertEqual(incident.total_assigned, 5)
        self.assertTrue(
            all(
                packet.source_id == artillery.id
                and packet.source_controller_id == self.alice.id
                and packet.colors == frozenset({Color.RED})
                for packet in incident.packets
            )
        )

    def test_combat_packets_preserve_source_and_trample_nature(self) -> None:
        while self.game.current_phase.value != "main":
            self.game.advance_phase()
        mammoth = self.put_in_play(self.alice, WAR_MAMMOTH)
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers([mammoth])
        self.game.declare_blockers({bear: mammoth})
        self.game.advance_combat()

        self.game.deal_combat_damage()

        incident = self.game.resolved_damage_incidents[-1]
        self.assertEqual(incident.kind, DamageIncidentKind.COMBAT)
        self.assertEqual(
            {(packet.recipient_id, packet.amount) for packet in incident.packets},
            {(bear.id, 2), (self.bob.id, 1), (mammoth.id, 2)},
        )
        mammoth_packets = [
            packet
            for packet in incident.packets
            if packet.source_id == mammoth.id
        ]
        self.assertEqual(len(mammoth_packets), 2)
        self.assertTrue(
            all(packet.combat and packet.trample for packet in mammoth_packets)
        )

    def test_timed_damage_uses_a_timed_event_incident(self) -> None:
        tablet = self.put_in_play(self.alice, COPPER_TABLET)

        self.game.advance_phase()
        self.pass_all()

        incident = self.game.resolved_damage_incidents[-1]
        packet = incident.packets[0]
        self.assertEqual(incident.kind, DamageIncidentKind.TIMED_EVENT)
        self.assertEqual(packet.source_id, tablet.id)
        self.assertEqual(packet.recipient_kind, DamageRecipientKind.PLAYER)
        self.assertEqual(packet.recipient_id, self.alice.id)
        self.assertEqual(packet.amount, 1)


if __name__ == "__main__":
    unittest.main()
