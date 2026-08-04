import unittest

from beta_magic import (
    ASPECT_OF_WOLF,
    BAYOU,
    FOREST,
    SAVANNAH_LIONS,
    WEAKNESS,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS


class AspectOfWolfTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player: PlayerState, definition, *, attached_to=None) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            enchanted_card_id=attached_to.id if attached_to is not None else None,
        )
        player.battlefield.append(card)
        return card

    def test_definition_uses_the_beta_floor_and_ceiling_formula(self) -> None:
        self.assertEqual(ASPECT_OF_WOLF.mana_cost.compact, "1G")
        effect = ASPECT_OF_WOLF.continuous_effects[0]
        self.assertEqual(effect.counted_controller_land_subtype, "Forest")
        self.assertEqual(effect.count_divisor, 2)
        self.assertTrue(effect.round_toughness_up)

    def test_bonus_recalculates_as_forests_enter_and_leave_play(self) -> None:
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.permanent(self.alice, ASPECT_OF_WOLF, attached_to=bear)

        expected = ((2, 2), (2, 3), (3, 3), (3, 4), (4, 4))
        forests = []
        self.assertEqual(
            (self.game.creature_power(bear), self.game.creature_toughness(bear)),
            expected[0],
        )
        for index in range(1, 5):
            forests.append(self.permanent(self.alice, FOREST))
            self.assertEqual(
                (
                    self.game.creature_power(bear),
                    self.game.creature_toughness(bear),
                ),
                expected[index],
            )

        self.game.put_permanent_in_graveyard(forests[-1])
        self.assertEqual(
            (self.game.creature_power(bear), self.game.creature_toughness(bear)),
            expected[3],
        )

    def test_uses_aspects_controller_and_counts_dual_land_types(self) -> None:
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.permanent(self.bob, FOREST)
        self.permanent(self.alice, FOREST)
        self.permanent(self.alice, BAYOU)
        self.permanent(self.alice, ASPECT_OF_WOLF, attached_to=bear)

        self.assertEqual(
            (self.game.creature_power(bear), self.game.creature_toughness(bear)),
            (3, 3),
        )

    def test_losing_a_forest_can_immediately_make_a_creature_die(self) -> None:
        lion = self.permanent(self.alice, SAVANNAH_LIONS)
        forest = self.permanent(self.alice, FOREST)
        aspect = self.permanent(self.alice, ASPECT_OF_WOLF, attached_to=lion)
        weakness = self.permanent(self.bob, WEAKNESS, attached_to=lion)
        self.assertEqual(self.game.creature_toughness(lion), 1)

        self.game.put_permanent_in_graveyard(forest)

        self.assertEqual(lion.zone, Zone.GRAVEYARD)
        self.assertEqual(aspect.zone, Zone.GRAVEYARD)
        self.assertEqual(weakness.zone, Zone.GRAVEYARD)


if __name__ == "__main__":
    unittest.main()
