import unittest

from beta_magic import (
    FOREST,
    ISLAND,
    LIGHTNING_BOLT,
    POWER_SINK,
    SOL_RING,
    TUNDRA,
    Card,
    CardType,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS
from beta_magic.ui import GameViewModel


class PowerSinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player, definition, zone=Zone.BATTLEFIELD):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id if zone is Zone.BATTLEFIELD else None,
            base_controller_id=player.id if zone is Zone.BATTLEFIELD else None,
            zone=zone,
            entered_battlefield_turn=0 if zone is Zone.BATTLEFIELD else None,
        )
        player.cards_in(zone).append(card)
        return card

    def cast_power_sink(self, x_value):
        bolt = self.card(self.alice, LIGHTNING_BOLT, Zone.HAND)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.bob,))
        sink = self.card(self.bob, POWER_SINK, Zone.HAND)
        self.bob.mana_pool.blue = 1
        self.bob.mana_pool.colorless = x_value
        self.game.begin_cast(sink, x_value=x_value)
        self.game.complete_pending_cast((bolt,))
        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)
        return bolt, sink

    def finish_spell(self):
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self):
        self.assertEqual(POWER_SINK.mana_cost.compact, "XU")
        self.assertEqual(POWER_SINK.card_types, frozenset({CardType.INTERRUPT}))
        self.assertTrue(POWER_SINK.spell_effects[0].power_sink)

    def test_available_pool_is_mandatorily_spent_and_spell_survives(self):
        self.alice.mana_pool.colorless = 2
        bolt, sink = self.cast_power_sink(2)

        self.assertIsNone(self.game.pending_power_sink_payment)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertEqual(bolt.zone, Zone.STACK)
        self.assertEqual(sink.zone, Zone.GRAVEYARD)
        self.finish_spell()
        self.assertEqual(self.bob.life, 17)

    def test_caster_chooses_lands_until_payment_is_complete(self):
        island = self.card(self.alice, ISLAND)
        forest = self.card(self.alice, FOREST)
        bolt, _ = self.cast_power_sink(2)

        payment = self.game.pending_power_sink_payment
        self.assertIsNotNone(payment)
        self.assertEqual(payment.remaining, 2)
        self.game.choose_power_sink_mana(self.alice.id, island.id, 0)
        self.assertEqual(payment.remaining, 1)
        self.game.choose_power_sink_mana(self.alice.id, forest.id, 0)

        self.assertIsNone(self.game.pending_power_sink_payment)
        self.assertTrue(island.tapped)
        self.assertTrue(forest.tapped)
        self.assertEqual(bolt.zone, Zone.STACK)

    def test_all_lands_and_pool_are_expended_even_when_spell_is_countered(self):
        island = self.card(self.alice, ISLAND)
        self.alice.mana_pool.green = 1
        bolt, _ = self.cast_power_sink(3)

        self.assertEqual(self.game.pending_power_sink_payment.remaining, 2)
        self.game.choose_power_sink_mana(self.alice.id, island.id, 0)

        self.assertTrue(island.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertEqual(bolt.zone, Zone.GRAVEYARD)
        self.assertIsNone(self.game.pending_power_sink_payment)

    def test_nonland_mana_sources_are_not_forced(self):
        sol_ring = self.card(self.alice, SOL_RING)
        bolt, _ = self.cast_power_sink(1)

        self.assertEqual(bolt.zone, Zone.GRAVEYARD)
        self.assertFalse(sol_ring.tapped)

    def test_dual_land_modes_and_ui_belong_to_target_spell_caster(self):
        tundra = self.card(self.alice, TUNDRA)
        self.cast_power_sink(1)
        view_model = GameViewModel(self.game)

        state = view_model.state
        self.assertTrue(state["powerSinkPayment"])
        self.assertTrue(state["powerSinkCanChoose"])
        self.assertEqual(
            [choice["label"] for choice in state["powerSinkManaChoices"]],
            ["Tundra → W", "Tundra → U"],
        )
        view_model.choosePowerSinkMana(str(tundra.id), 1)
        self.assertFalse(view_model.state["powerSinkPayment"])
        self.assertEqual(self.alice.mana_pool.blue, 0)


if __name__ == "__main__":
    unittest.main()
