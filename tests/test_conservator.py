import unittest

from beta_magic import (
    CONSERVATOR,
    FOREST,
    GRIZZLY_BEARS,
    Card,
    CardType,
    GameState,
    ManaBurnEvent,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.damage import DamageIncidentKind, DamageRecipientKind
from beta_magic.events import DamageEvent


class ConservatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.game.pause_for_damage_windows = True

    def permanent(self, owner: PlayerState, definition) -> Card:
        card = Card(
            definition,
            owner.id,
            controller_id=owner.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        owner.battlefield.append(card)
        return card

    def finish_damage(self) -> None:
        while self.game.pending_damage is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self) -> None:
        self.assertEqual(CONSERVATOR.mana_cost.compact, "4")
        self.assertEqual(CONSERVATOR.card_types, frozenset({CardType.ARTIFACT}))
        ability = CONSERVATOR.activated_abilities[0]
        self.assertEqual(ability.mana_cost.compact, "3")
        self.assertEqual(ability.amount, 2)
        self.assertTrue(ability.tap_cost)
        self.assertTrue(ability.controller_only)
        self.assertTrue(ability.prevents_life_loss)

    def test_prevents_life_loss_from_damage_without_preventing_damage(self) -> None:
        conservator = self.permanent(self.alice, CONSERVATOR)
        self.alice.mana_pool.colorless = 3
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(self.alice, 3, "Test source")
        self.game._resolve_damage_incident()

        self.game.activate_ability(self.alice.id, conservator, 0)
        packet = self.game.legal_prevention_packets()[0]
        self.assertEqual(self.game.prevent_damage(self.alice.id, packet.id), 2)
        self.finish_damage()

        self.assertTrue(conservator.tapped)
        self.assertEqual(self.alice.life, 19)
        self.assertEqual(packet.remaining, 3)
        self.assertEqual(packet.life_loss_prevented, 2)
        self.assertEqual(self.game.player_damage_history[-1].amount, 3)
        damage_events = [
            event for event in self.game.events if isinstance(event, DamageEvent)
        ]
        self.assertEqual(damage_events[-1].amount, 3)

    def test_cannot_apply_life_loss_prevention_to_a_creature(self) -> None:
        conservator = self.permanent(self.alice, CONSERVATOR)
        creature = self.permanent(self.alice, GRIZZLY_BEARS)
        self.alice.mana_pool.colorless = 3
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(creature, 1, "Creature source")
        self.game._deal_damage(self.alice, 1, "Player source")
        self.game._resolve_damage_incident()

        self.game.activate_ability(self.alice.id, conservator, 0)
        choices = self.game.legal_prevention_packets()

        self.assertEqual(len(choices), 1)
        self.assertIs(choices[0].recipient_kind, DamageRecipientKind.PLAYER)

    def test_can_pay_and_prevent_zero_pending_life_loss(self) -> None:
        conservator = self.permanent(self.alice, CONSERVATOR)
        self.alice.mana_pool.colorless = 3
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(self.alice, 2, "Test source")
        self.game._resolve_damage_incident()

        self.game.activate_ability(self.alice.id, conservator, 0)
        self.game.finish_prevention(self.alice.id)
        self.finish_damage()

        self.assertTrue(conservator.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertEqual(self.alice.life, 18)

    def test_can_prevent_mana_burn_at_a_phase_boundary(self) -> None:
        conservator = self.permanent(self.alice, CONSERVATOR)
        self.alice.mana_pool.colorless = 5

        self.game.activate_ability(self.alice.id, conservator, 0)
        self.game._empty_mana_pools()

        self.assertTrue(conservator.tapped)
        self.assertEqual(self.alice.life, 20)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertFalse(
            any(isinstance(event, ManaBurnEvent) for event in self.game.events)
        )

    def test_can_spend_three_and_prevent_zero_as_a_mana_sink(self) -> None:
        conservator = self.permanent(self.alice, CONSERVATOR)
        self.alice.mana_pool.colorless = 3

        self.game.activate_ability(self.alice.id, conservator, 0)
        self.game._empty_mana_pools()

        self.assertTrue(conservator.tapped)
        self.assertEqual(self.alice.life, 20)
        self.assertEqual(self.game.life_loss_prevention, {})

    def test_mana_burn_beyond_two_still_causes_life_loss(self) -> None:
        conservator = self.permanent(self.alice, CONSERVATOR)
        self.alice.mana_pool.colorless = 8

        self.game.activate_ability(self.alice.id, conservator, 0)
        self.game._empty_mana_pools()

        self.assertEqual(self.alice.life, 17)
        burns = [
            event for event in self.game.events if isinstance(event, ManaBurnEvent)
        ]
        self.assertEqual(burns[-1].amount, 3)


if __name__ == "__main__":
    unittest.main()
