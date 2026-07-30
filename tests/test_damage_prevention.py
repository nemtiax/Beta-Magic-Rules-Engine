import unittest

from beta_magic import (
    HEALING_SALVE,
    PREVENTION_CARDS,
    SAMITE_HEALER,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.damage import DamageIncidentKind, DamageResolutionStep
from beta_magic.vanilla_creatures import GRIZZLY_BEARS


def player(player_id: str) -> PlayerState:
    return PlayerState.with_deck(
        player_id, player_id.title(), [GRIZZLY_BEARS] * 12
    )


class DamagePreventionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = player("alice")
        self.bob = player("bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.game.pause_for_damage_windows = True

    @staticmethod
    def put_in_play(owner: PlayerState, definition):
        card = owner.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.entered_battlefield_turn = 0
        owner.battlefield.append(card)
        return card

    @staticmethod
    def put_in_hand(owner: PlayerState, definition):
        card = owner.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        owner.hand.append(card)
        return card

    def open_damage(self, *amounts: int) -> None:
        self.game._begin_damage_incident(DamageIncidentKind.FAST_EFFECT_BATCH)
        for index, amount in enumerate(amounts):
            self.game._deal_damage(self.alice, amount, f"Source {index + 1}")
        self.game._resolve_damage_incident()
        self.assertEqual(
            self.game.pending_damage.step, DamageResolutionStep.PREVENTION
        )

    def finish_incident(self) -> None:
        while self.game.pending_damage is not None:
            priority = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(priority.id)

    def test_card_definitions(self) -> None:
        self.assertEqual(PREVENTION_CARDS, (HEALING_SALVE, SAMITE_HEALER))
        self.assertEqual(HEALING_SALVE.mana_cost.compact, "W")
        self.assertEqual(HEALING_SALVE.prevention_amount, 3)
        self.assertEqual(SAMITE_HEALER.mana_cost.compact, "1W")
        self.assertEqual((SAMITE_HEALER.power, SAMITE_HEALER.toughness), (1, 1))

    def test_healing_salve_can_gain_three_life_outside_damage(self) -> None:
        salve = self.put_in_hand(self.alice, HEALING_SALVE)
        self.alice.life = 15
        self.alice.mana_pool.white = 1
        self.game.begin_cast(salve)
        self.game.complete_pending_cast((self.alice,))
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        self.assertEqual(self.alice.life, 18)
        self.assertIn(salve, self.alice.graveyard)

    def test_healing_salve_prevents_up_to_three_from_one_recipient(self) -> None:
        salve = self.put_in_hand(self.alice, HEALING_SALVE)
        self.alice.mana_pool.white = 1
        self.open_damage(2, 3)
        self.game.begin_prevention_spell(salve)
        packets = self.game.pending_damage.packets

        self.assertEqual(self.game.prevent_damage(self.alice.id, packets[0].id), 2)
        self.assertEqual(self.game.prevent_damage(self.alice.id, packets[1].id), 1)
        self.assertIsNone(self.game.pending_prevention)
        self.finish_incident()

        self.assertEqual(self.alice.life, 18)
        self.assertIn(salve, self.alice.graveyard)

    def test_samite_healer_prevents_one_and_taps(self) -> None:
        healer = self.put_in_play(self.alice, SAMITE_HEALER)
        self.open_damage(2)
        self.game.activate_ability(self.alice.id, healer, 0)
        packet = self.game.pending_damage.packets[0]
        self.game.prevent_damage(self.alice.id, packet.id)
        self.finish_incident()

        self.assertTrue(healer.tapped)
        self.assertEqual(self.alice.life, 19)

    def test_prevention_effect_is_limited_to_one_target(self) -> None:
        salve = self.put_in_hand(self.alice, HEALING_SALVE)
        self.alice.mana_pool.white = 1
        self.game._begin_damage_incident(DamageIncidentKind.FAST_EFFECT_BATCH)
        self.game._deal_damage(self.alice, 1, "First")
        self.game._deal_damage(self.bob, 2, "Second")
        self.game._resolve_damage_incident()
        self.game.begin_prevention_spell(salve)
        first, second = self.game.pending_damage.packets
        self.game.prevent_damage(self.alice.id, first.id)

        with self.assertRaisesRegex(ValueError, "single target"):
            self.game.prevent_damage(self.alice.id, second.id)


if __name__ == "__main__":
    unittest.main()
