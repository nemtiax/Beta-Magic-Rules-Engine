import unittest

from beta_magic import (
    CONSERVATOR,
    FORCEFIELD,
    GRIZZLY_BEARS,
    WAR_MAMMOTH,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.damage import DamageIncidentKind, DamageResolutionStep


class ForcefieldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.game.pause_for_damage_windows = True

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        player.battlefield.append(card)
        return card

    def open_damage(self, source, *, combat=True, trample=False, amount=4):
        self.game._begin_damage_incident(DamageIncidentKind.COMBAT)
        self.game._deal_damage(
            self.alice,
            amount,
            source.name,
            source_card=source,
            combat=combat,
            trample=trample,
        )
        self.game._resolve_damage_incident()
        self.assertIs(
            self.game.pending_damage.step, DamageResolutionStep.PREVENTION
        )

    def finish_damage(self):
        while self.game.pending_damage is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self):
        self.assertEqual(FORCEFIELD.mana_cost.compact, "3")
        self.assertEqual(FORCEFIELD.card_types, frozenset({CardType.ARTIFACT}))
        ability = FORCEFIELD.activated_abilities[0]
        self.assertEqual(ability.mana_cost.compact, "1")
        self.assertFalse(ability.tap_cost)
        self.assertTrue(ability.unblocked_combat_only)
        self.assertTrue(ability.leaves_one_life_loss)

    def test_unblocked_creature_damage_becomes_one_life_loss(self):
        forcefield = self.permanent(self.alice, FORCEFIELD)
        attacker = self.permanent(self.bob, WAR_MAMMOTH)
        self.alice.mana_pool.colorless = 1
        self.open_damage(attacker)

        self.game.activate_ability(self.alice.id, forcefield, 0)
        packet = self.game.legal_prevention_packets()[0]
        self.assertEqual(self.game.prevent_damage(self.alice.id, packet.id), 4)
        self.assertEqual(packet.remaining, 0)
        self.assertEqual(packet.resulting_life_loss, 1)
        self.assertFalse(forcefield.tapped)
        self.finish_damage()

        self.assertEqual(self.alice.life, 19)
        self.assertEqual(self.game.player_damage_history, [])

    def test_cannot_apply_to_blocked_trample_or_noncombat_damage(self):
        forcefield = self.permanent(self.alice, FORCEFIELD)
        attacker = self.permanent(self.bob, WAR_MAMMOTH)
        self.alice.mana_pool.colorless = 2
        self.open_damage(attacker, trample=True)
        self.game.activate_ability(self.alice.id, forcefield, 0)
        self.assertEqual(self.game.legal_prevention_packets(), [])
        self.game.cancel_prevention(self.alice.id)
        self.finish_damage()

        forcefield.tapped = False
        self.open_damage(attacker, combat=False)
        self.game.activate_ability(self.alice.id, forcefield, 0)
        self.assertEqual(self.game.legal_prevention_packets(), [])

    def test_conservator_can_prevent_forcefields_life_loss(self):
        forcefield = self.permanent(self.alice, FORCEFIELD)
        conservator = self.permanent(self.alice, CONSERVATOR)
        attacker = self.permanent(self.bob, GRIZZLY_BEARS)
        self.alice.mana_pool.colorless = 4
        self.open_damage(attacker, amount=2)

        self.game.activate_ability(self.alice.id, forcefield, 0)
        packet = self.game.legal_prevention_packets()[0]
        self.game.prevent_damage(self.alice.id, packet.id)
        # Forcefield passes priority; Bob declines before Alice uses Conservator.
        self.game.pass_priority(self.bob.id)
        self.game.activate_ability(self.alice.id, conservator, 0)
        self.assertEqual(self.game.legal_prevention_packets(), [packet])
        self.game.prevent_damage(self.alice.id, packet.id)
        self.game.finish_prevention(self.alice.id)
        self.finish_damage()

        self.assertEqual(self.alice.life, 20)


if __name__ == "__main__":
    unittest.main()
