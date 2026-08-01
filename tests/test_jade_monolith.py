import unittest

from beta_magic import (
    JADE_MONOLITH,
    LIGHTNING_BOLT,
    Card,
    Color,
    DamageIncidentKind,
    DamageRecipientKind,
    DamageResolutionStep,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS


class JadeMonolithTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.game.pause_for_damage_windows = True

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            owner_id=player.id,
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

    def open_damage(self, recipient):
        bolt = Card(LIGHTNING_BOLT, owner_id=self.bob.id, controller_id=self.bob.id)
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(
            recipient,
            3,
            bolt.name,
            source_card=bolt,
            source_controller_id=self.bob.id,
        )
        self.game._resolve_damage_incident()
        return bolt

    def test_redirects_remaining_creature_damage_to_controller(self):
        monolith = self.permanent(self.alice, JADE_MONOLITH)
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        bolt = self.open_damage(bear)
        packet = self.game.pending_damage.packets[0]
        packet.prevented = 1
        self.pass_window()
        self.assertIs(
            self.game.pending_damage.step, DamageResolutionStep.REDIRECTION
        )
        self.alice.mana_pool.colorless = 1

        self.game.activate_ability(self.alice.id, monolith, 0)
        self.assertFalse(monolith.tapped)
        self.assertEqual(self.game.redirect_damage(self.alice.id, packet.id), 2)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.pass_window()
        self.pass_window()

        redirected = self.game.pending_damage.packets[0]
        self.assertEqual(redirected.amount, 2)
        self.assertEqual(redirected.recipient_kind, DamageRecipientKind.PLAYER)
        self.assertEqual(redirected.recipient_id, self.alice.id)
        self.assertEqual(redirected.source_id, bolt.id)
        self.assertEqual(redirected.colors, frozenset({Color.RED}))
        self.assertIs(
            self.game.pending_damage.step, DamageResolutionStep.PREVENTION
        )
        self.assertEqual(bear.damage, 0)

        self.pass_window()
        self.pass_window()
        self.assertEqual(self.alice.life, 18)
        self.pass_window()

    def test_player_damage_is_not_a_legal_monolith_choice(self):
        monolith = self.permanent(self.alice, JADE_MONOLITH)
        self.open_damage(self.bob)
        self.pass_window()
        self.alice.mana_pool.colorless = 1

        with self.assertRaisesRegex(RuntimeError, "no eligible damage"):
            self.game.activate_ability(self.alice.id, monolith, 0)


if __name__ == "__main__":
    unittest.main()
