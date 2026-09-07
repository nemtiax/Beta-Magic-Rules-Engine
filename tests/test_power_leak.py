import unittest

from beta_magic import (
    CRUSADE,
    POWER_LEAK,
    Card,
    CardType,
    GameState,
    PartialUpkeepDamageEffect,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS
from beta_magic.ui import GameViewModel


class PowerLeakTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def permanent(player, definition, *, attached=None):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        card.enchanted_card_id = attached.id if attached is not None else None
        player.battlefield.append(card)
        return card

    def install_leak(self):
        enchantment = self.permanent(self.alice, CRUSADE)
        leak = self.permanent(self.bob, POWER_LEAK, attached=enchantment)
        return enchantment, leak

    def enter_upkeep(self):
        self.game._enter_phase(TurnPhase.UPKEEP)

    def resolve_event(self):
        event = self.game.timed_events[0]
        while event in self.game.timed_events or self.game.pending_damage is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self):
        self.assertEqual(POWER_LEAK.mana_cost.compact, "1U")
        self.assertEqual(POWER_LEAK.subtypes, ("Enchant Enchantment",))
        self.assertEqual(
            POWER_LEAK.target_requirement.card_types,
            frozenset({CardType.ENCHANTMENT}),
        )
        effect = POWER_LEAK.upkeep_effects[0]
        self.assertIsInstance(effect, PartialUpkeepDamageEffect)
        self.assertEqual(effect.maximum_payment, 2)

    def test_full_partial_and_zero_payments(self):
        for payment, expected_damage in ((2, 0), (1, 1), (0, 2)):
            with self.subTest(payment=payment):
                self.setUp()
                self.install_leak()
                self.alice.mana_pool.colorless = payment
                self.enter_upkeep()

                self.game.choose_partial_upkeep_payment(self.alice.id, payment)
                self.resolve_event()

                self.assertEqual(self.alice.life, 20 - expected_damage)
                self.assertEqual(self.alice.mana_pool.total, 0)

    def test_cannot_choose_more_than_is_available(self):
        self.install_leak()
        self.alice.mana_pool.colorless = 1
        self.enter_upkeep()

        self.assertEqual(self.game.maximum_partial_upkeep_payment("a"), 1)
        with self.assertRaisesRegex(ValueError, "0 to 1"):
            self.game.choose_partial_upkeep_payment("a", 2)

    def test_each_power_leak_is_a_separate_payment_and_damage_event(self):
        enchantment, _ = self.install_leak()
        self.permanent(self.bob, POWER_LEAK, attached=enchantment)
        self.alice.mana_pool.colorless = 1
        self.enter_upkeep()

        self.game.choose_partial_upkeep_payment("a", 1)
        self.resolve_event()
        self.assertEqual(self.alice.life, 19)
        self.assertTrue(self.game.upkeep_payment_required)

        self.game.choose_partial_upkeep_payment("a", 0)
        self.resolve_event()
        self.assertEqual(self.alice.life, 17)

    def test_ui_starts_at_highest_affordable_payment(self):
        self.install_leak()
        self.alice.mana_pool.colorless = 1
        self.enter_upkeep()
        view = GameViewModel(self.game)

        self.assertTrue(view.state["partialUpkeepRequired"])
        self.assertEqual(view.state["partialUpkeepMaximum"], 2)
        self.assertEqual(view.state["partialUpkeepAffordable"], 1)
        view.choosePartialUpkeepPayment(1)
        self.assertFalse(view.state["partialUpkeepRequired"])


if __name__ == "__main__":
    unittest.main()
