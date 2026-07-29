import unittest

from beta_magic import (
    BIRDS_OF_PARADISE,
    LLANOWAR_ELVES,
    MANA_CREATURES,
    Color,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.basic_lands import FOREST


class ManaCreatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    def put_in_play(self, definition, *, entered_turn=None):
        card = self.alice.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = self.alice.id
        card.entered_battlefield_turn = entered_turn
        self.alice.battlefield.append(card)
        return card

    def test_definitions(self) -> None:
        self.assertEqual(MANA_CREATURES, (LLANOWAR_ELVES, BIRDS_OF_PARADISE))
        self.assertEqual(LLANOWAR_ELVES.mana_cost.compact, "G")
        self.assertEqual((LLANOWAR_ELVES.power, LLANOWAR_ELVES.toughness), (1, 1))
        self.assertEqual(
            [ability.color for ability in LLANOWAR_ELVES.activated_abilities],
            [Color.GREEN],
        )
        self.assertEqual(BIRDS_OF_PARADISE.mana_cost.compact, "G")
        self.assertEqual(
            (BIRDS_OF_PARADISE.power, BIRDS_OF_PARADISE.toughness), (0, 1)
        )
        self.assertIn(KeywordAbility.FLYING, BIRDS_OF_PARADISE.abilities)
        self.assertEqual(
            [ability.color for ability in BIRDS_OF_PARADISE.activated_abilities],
            [
                Color.WHITE,
                Color.BLUE,
                Color.BLACK,
                Color.RED,
                Color.GREEN,
            ],
        )

    def test_llanowar_elves_taps_for_green_after_summoning_sickness(self) -> None:
        elves = self.put_in_play(LLANOWAR_ELVES)

        self.game.activate_ability(self.alice.id, elves, 0)

        self.assertTrue(elves.tapped)
        self.assertEqual(self.alice.mana_pool.green, 1)

    def test_birds_of_paradise_can_choose_any_color(self) -> None:
        birds = self.put_in_play(BIRDS_OF_PARADISE)

        self.game.activate_ability(self.alice.id, birds, 3)

        self.assertTrue(birds.tapped)
        self.assertEqual(self.alice.mana_pool.red, 1)
        self.assertEqual(self.alice.mana_pool.total, 1)

    def test_new_creature_cannot_pay_a_tap_cost(self) -> None:
        elves = self.put_in_play(
            LLANOWAR_ELVES, entered_turn=self.game.turn_number
        )

        self.assertFalse(
            self.game.can_activate_ability(self.alice.id, elves, 0)
        )
        with self.assertRaisesRegex(RuntimeError, "did not begin the turn"):
            self.game.activate_ability(self.alice.id, elves, 0)

        self.assertFalse(elves.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)

    def test_summoning_sickness_ends_on_controllers_next_turn(self) -> None:
        elves = self.put_in_play(
            LLANOWAR_ELVES, entered_turn=self.game.turn_number
        )
        while not (
            self.game.active_player is self.alice
            and self.game.turn_number > elves.entered_battlefield_turn
            and self.game.current_phase is TurnPhase.UPKEEP
        ):
            self.game.advance_phase()

        self.assertTrue(
            self.game.can_activate_ability(self.alice.id, elves, 0)
        )
        self.game.activate_ability(self.alice.id, elves, 0)
        self.assertEqual(self.alice.mana_pool.green, 1)


if __name__ == "__main__":
    unittest.main()
