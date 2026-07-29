import unittest

from beta_magic import (
    FOREST,
    ISLAND,
    MOUNTAIN,
    VANILLA_CREATURES,
    Card,
    CardType,
    Color,
    GameState,
    ManaCost,
    ManaPool,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.vanilla_creatures import GRIZZLY_BEARS, HURLOON_MINOTAUR


class ManaPaymentTests(unittest.TestCase):
    def test_colored_requirements_and_generic_mana(self) -> None:
        pool = ManaPool(red=2, green=1)
        cost = ManaCost.parse("{1}{R}{R}")
        self.assertTrue(pool.can_pay(cost))
        pool.pay(cost)
        self.assertEqual(pool.total, 0)

    def test_wrong_colors_cannot_pay_colored_cost(self) -> None:
        pool = ManaPool(green=3)
        cost = ManaCost.parse("{1}{R}{R}")
        self.assertFalse(pool.can_pay(cost))
        with self.assertRaises(ValueError):
            pool.pay(cost)
        self.assertEqual(pool.green, 3)


class VanillaCreatureTests(unittest.TestCase):
    def test_reference_contains_exactly_fifteen_supported_creatures(self) -> None:
        self.assertEqual(len(VANILLA_CREATURES), 15)
        self.assertEqual(len({card.name for card in VANILLA_CREATURES}), 15)
        self.assertTrue(
            all(CardType.CREATURE in card.card_types for card in VANILLA_CREATURES)
        )
        self.assertTrue(all(not card.rules_text for card in VANILLA_CREATURES))

    def setUp(self) -> None:
        deck = [GRIZZLY_BEARS, FOREST, FOREST, FOREST]
        self.alice = PlayerState.with_deck("alice", "Alice", deck)
        self.bob = PlayerState.with_deck("bob", "Bob", [ISLAND] * 4)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=4, shuffle=False)

    def enter_main(self) -> None:
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    def test_casting_pays_mana_and_puts_creature_in_play(self) -> None:
        self.enter_main()
        creature = next(
            card for card in self.alice.hand if card.definition is GRIZZLY_BEARS
        )
        self.alice.mana_pool.green = 1
        self.alice.mana_pool.colorless = 1

        self.game.cast_creature(creature)

        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertNotIn(creature, self.alice.hand)
        self.assertIn(creature, self.alice.battlefield)
        self.assertEqual(creature.zone, Zone.BATTLEFIELD)

    def test_creature_cannot_be_cast_outside_main_or_without_right_mana(self) -> None:
        creature = next(
            card for card in self.alice.hand if card.definition is GRIZZLY_BEARS
        )
        with self.assertRaises(RuntimeError):
            self.game.cast_creature(creature)

        self.enter_main()
        self.alice.mana_pool.red = 2
        with self.assertRaises(RuntimeError):
            self.game.cast_creature(creature)
        self.assertIn(creature, self.alice.hand)
        self.assertEqual(self.alice.mana_pool.red, 2)

    def test_creature_cannot_be_cast_during_attack_response_windows(self) -> None:
        creature = next(
            card for card in self.alice.hand if card.definition is GRIZZLY_BEARS
        )
        self.enter_main()
        self.alice.mana_pool.green = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_combat()
        with self.assertRaisesRegex(RuntimeError, "during an attack"):
            self.game.cast_creature(creature)


if __name__ == "__main__":
    unittest.main()
