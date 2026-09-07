import unittest

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.black import GLOOM
from beta_magic.card_defs.white import (
    CIRCLE_OF_PROTECTION_BLACK,
    HEALING_SALVE,
    HOLY_STRENGTH,
    SAMITE_HEALER,
)
from beta_magic.types import Color


class GloomTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState("a", "Alice")
        self.bob = PlayerState("b", "Bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

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

    def spell_in_hand(self, definition):
        card = Card(definition, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(card)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0
        return card

    def test_white_spell_costs_three_additional_colorless(self) -> None:
        self.permanent(self.bob, GLOOM)
        spell = self.spell_in_hand(HOLY_STRENGTH)
        self.assertEqual(self.game.spell_mana_cost(spell).compact, "3W")
        self.alice.mana_pool.white = 1
        with self.assertRaises(RuntimeError):
            self.game.begin_cast(spell)

    def test_laced_white_spell_uses_final_color(self) -> None:
        self.permanent(self.bob, GLOOM)
        spell = self.spell_in_hand(HEALING_SALVE)
        spell.color_override = Color.BLUE
        self.assertEqual(self.game.spell_mana_cost(spell).compact, "W")

    def test_multiple_glooms_stack(self) -> None:
        self.permanent(self.alice, GLOOM)
        self.permanent(self.bob, GLOOM)
        spell = self.spell_in_hand(HEALING_SALVE)
        self.assertEqual(self.game.spell_mana_cost(spell).compact, "6W")

    def test_circle_activation_costs_four_regardless_of_lace(self) -> None:
        self.permanent(self.bob, GLOOM)
        circle = self.permanent(self.alice, CIRCLE_OF_PROTECTION_BLACK)
        circle.color_override = Color.BLUE
        ability = circle.definition.activated_abilities[0]
        self.assertEqual(
            self.game.ability_mana_cost(circle, ability.mana_cost).compact, "4"
        )

    def test_other_white_in_play_abilities_are_not_taxed(self) -> None:
        self.permanent(self.bob, GLOOM)
        healer = self.permanent(self.alice, SAMITE_HEALER)
        ability = healer.definition.activated_abilities[0]
        self.assertEqual(
            self.game.ability_mana_cost(healer, ability.mana_cost).compact,
            ability.mana_cost.compact,
        )


if __name__ == "__main__":
    unittest.main()
