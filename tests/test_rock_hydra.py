import unittest

from beta_magic import Card, GameState, PlayerState
from beta_magic.card_defs.red import ROCK_HYDRA
from beta_magic.damage import DamageIncidentKind
from beta_magic.types import TurnPhase, Zone


class RockHydraTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState("a", "Alice")
        self.bob = PlayerState("b", "Bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    def hydra(self, heads: int = 4) -> Card:
        card = Card(ROCK_HYDRA, self.alice.id, zone=Zone.BATTLEFIELD)
        card.controller_id = self.alice.id
        card.counters["head"] = heads
        self.alice.battlefield.append(card)
        return card

    def test_x_heads_are_added_when_cast(self) -> None:
        card = Card(ROCK_HYDRA, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(card)
        self.alice.mana_pool.red = 2
        self.alice.mana_pool.colorless = 4
        self.game.begin_cast(card, x_value=4)
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        self.assertEqual(card.zone, Zone.BATTLEFIELD)
        self.assertEqual(card.counters["head"], 4)
        self.assertEqual((self.game.creature_power(card), self.game.creature_toughness(card)), (4, 4))

    def test_heads_absorb_damage_and_are_lost(self) -> None:
        hydra = self.hydra()
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(hydra, 3, "test")
        self.game._resolve_damage_incident()
        self.assertEqual(hydra.counters["head"], 1)
        self.assertEqual(hydra.damage, 0)

    def test_red_mana_preserves_chosen_heads_and_prevents_damage(self) -> None:
        hydra = self.hydra()
        self.alice.mana_pool.red = 2
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(hydra, 3, "test")
        self.game._resolve_damage_incident()
        self.assertIsNotNone(self.game.pending_counter_damage_choice)
        self.game.choose_counter_damage_payment(self.alice.id, 2)
        self.assertEqual(hydra.counters["head"], 3)
        self.assertEqual(hydra.damage, 0)
        self.assertEqual(self.alice.mana_pool.red, 0)

    def test_damage_beyond_heads_is_applied_normally(self) -> None:
        hydra = self.hydra(2)
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(hydra, 3, "test")
        self.game._resolve_damage_incident()
        self.assertEqual(hydra.counters.get("head", 0), 0)
        self.assertEqual(hydra.zone, Zone.GRAVEYARD)

    def test_saved_head_can_absorb_later_points_in_same_packet(self) -> None:
        hydra = self.hydra(2)
        self.alice.mana_pool.red = 4
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(hydra, 5, "test")
        self.game._resolve_damage_incident()
        self.assertEqual(self.game.pending_counter_damage_choice.maximum_payment, 4)
        self.game.choose_counter_damage_payment(self.alice.id, 4)
        self.assertEqual(hydra.counters["head"], 1)
        self.assertEqual(hydra.damage, 0)

    def test_upkeep_can_buy_multiple_heads(self) -> None:
        hydra = self.hydra(1)
        self.game.current_phase = TurnPhase.UPKEEP
        self.alice.mana_pool.red = 6
        self.game._queue_upkeep_events()
        self.game.priority_player_index = 0
        self.assertEqual(self.game.maximum_upkeep_counter_purchase(self.alice.id), 2)
        self.game.choose_upkeep_counter_purchase(self.alice.id, 2)
        self.game._resolve_timed_event()
        self.assertEqual(hydra.counters["head"], 3)

    def test_reentry_does_not_remember_heads(self) -> None:
        hydra = self.hydra(5)
        self.game._move_card(hydra, Zone.GRAVEYARD)
        self.game._move_card(hydra, Zone.BATTLEFIELD)
        self.assertEqual(hydra.counters.get("head", 0), 0)


if __name__ == "__main__":
    unittest.main()
