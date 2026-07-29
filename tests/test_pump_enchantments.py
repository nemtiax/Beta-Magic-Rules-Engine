import unittest

from beta_magic import (
    BLESSING,
    FIREBREATHING,
    HOLY_ARMOR,
    PUMP_ENCHANT_CREATURES,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.vanilla_creatures import GRIZZLY_BEARS


class PumpEnchantmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 30
        )
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 30)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(player, definition=GRIZZLY_BEARS):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = player.id
        player.battlefield.append(card)
        return card

    @staticmethod
    def put_in_hand(player, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        player.hand.append(card)
        return card

    def cast_aura(self, definition, creature, *, white=0, red=0):
        aura = self.put_in_hand(self.alice, definition)
        self.alice.mana_pool.white = white
        self.alice.mana_pool.red = red
        self.game.cast_enchantment(aura, creature)
        return aura

    def finish_turn(self) -> None:
        while self.game.active_player is self.alice:
            if (
                self.game.current_phase is TurnPhase.DISCARD
                and self.alice.discard_required
            ):
                self.game.discard(self.alice.hand[0])
            self.game.advance_phase()

    def test_definitions(self) -> None:
        self.assertEqual(
            PUMP_ENCHANT_CREATURES, (BLESSING, HOLY_ARMOR, FIREBREATHING)
        )
        self.assertEqual(
            tuple(card.mana_cost.compact for card in PUMP_ENCHANT_CREATURES),
            ("WW", "W", "R"),
        )
        blessing, armor, firebreathing = (
            card.activated_abilities[0] for card in PUMP_ENCHANT_CREATURES
        )
        self.assertEqual((blessing.power, blessing.toughness), (1, 1))
        self.assertEqual((armor.power, armor.toughness), (0, 1))
        self.assertEqual((firebreathing.power, firebreathing.toughness), (1, 0))
        self.assertTrue(
            all(
                ability.affects_attached_creature
                for ability in (blessing, armor, firebreathing)
            )
        )

    def test_blessing_activations_stack_and_expire_at_end_of_turn(self) -> None:
        bear = self.put_in_play(self.alice)
        aura = self.cast_aura(BLESSING, bear, white=2)
        self.alice.mana_pool.white = 2

        self.game.activate_ability(self.alice.id, aura, 0)
        self.game.activate_ability(self.alice.id, aura, 0)

        self.assertEqual(
            (self.game.creature_power(bear), self.game.creature_toughness(bear)),
            (4, 4),
        )
        self.finish_turn()
        self.assertEqual(
            (self.game.creature_power(bear), self.game.creature_toughness(bear)),
            (2, 2),
        )

    def test_holy_armor_has_static_and_repeatable_toughness_bonuses(self) -> None:
        bear = self.put_in_play(self.alice)
        aura = self.cast_aura(HOLY_ARMOR, bear, white=1)
        self.assertEqual(self.game.creature_toughness(bear), 4)
        self.alice.mana_pool.white = 2

        self.game.activate_ability(self.alice.id, aura, 0)
        self.game.activate_ability(self.alice.id, aura, 0)

        self.assertEqual(self.game.creature_toughness(bear), 6)

    def test_aura_controller_can_pump_an_opponents_enchanted_creature(self) -> None:
        bear = self.put_in_play(self.bob)
        aura = self.cast_aura(FIREBREATHING, bear, red=1)
        self.alice.mana_pool.red = 1

        self.assertFalse(self.game.can_activate_ability(self.bob.id, aura, 0))
        self.game.activate_ability(self.alice.id, aura, 0)

        self.assertEqual(self.game.creature_power(bear), 3)

    def test_resolved_pump_survives_aura_leaving_play(self) -> None:
        bear = self.put_in_play(self.alice)
        aura = self.cast_aura(FIREBREATHING, bear, red=1)
        self.alice.mana_pool.red = 1
        self.game.activate_ability(self.alice.id, aura, 0)

        self.game.put_permanent_in_graveyard(aura)

        self.assertEqual(self.game.creature_power(bear), 3)
        self.assertIn(aura, self.alice.graveyard)


if __name__ == "__main__":
    unittest.main()
