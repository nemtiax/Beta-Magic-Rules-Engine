import unittest

from beta_magic import (
    DRAGON_WHELP,
    FROZEN_SHADE,
    GRANITE_GARGOYLE,
    LIGHTNING_BOLT,
    PUMP_CREATURES,
    SHIVAN_DRAGON,
    WALL_OF_FIRE,
    WALL_OF_WATER,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import MOUNTAIN


class PumpCreatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [MOUNTAIN] * 30)
        self.bob = PlayerState.with_deck("bob", "Bob", [MOUNTAIN] * 30)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    def put_in_play(self, definition, *, entered_this_turn=False):
        card = self.alice.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = self.alice.id
        card.entered_battlefield_turn = (
            self.game.turn_number if entered_this_turn else None
        )
        self.alice.battlefield.append(card)
        return card

    def finish_turn(self) -> None:
        while self.game.current_phase is not TurnPhase.END:
            self.game.advance_phase()
        self.game.advance_phase()

    def activate_and_resolve(self, card, count=1) -> None:
        for _ in range(count):
            if self.game.priority_player_index is not None:
                priority = self.game.players[self.game.priority_player_index]
                self.game.pass_priority(priority.id)
            self.game.activate_ability(self.alice.id, card, 0)
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

    def test_definitions(self) -> None:
        self.assertEqual(
            PUMP_CREATURES,
            (
                SHIVAN_DRAGON,
                FROZEN_SHADE,
                GRANITE_GARGOYLE,
                DRAGON_WHELP,
                WALL_OF_WATER,
                WALL_OF_FIRE,
            ),
        )
        self.assertEqual(
            [
                (card.mana_cost.compact, card.power, card.toughness)
                for card in PUMP_CREATURES
            ],
            [
                ("4RR", 5, 5),
                ("2B", 0, 1),
                ("2R", 2, 2),
                ("2RR", 2, 3),
                ("1UU", 0, 5),
                ("1RR", 0, 5),
            ],
        )
        self.assertIn(KeywordAbility.FLYING, SHIVAN_DRAGON.abilities)
        self.assertIn(KeywordAbility.FLYING, GRANITE_GARGOYLE.abilities)
        self.assertIn(KeywordAbility.FLYING, DRAGON_WHELP.abilities)

    def test_pump_abilities_pay_mana_and_stack_until_end_of_turn(self) -> None:
        shade = self.put_in_play(FROZEN_SHADE)
        self.alice.mana_pool.black = 2

        self.game.activate_ability(self.alice.id, shade, 0)
        self.assertEqual(self.game.creature_power(shade), 0)
        self.game.pass_priority(self.bob.id)
        self.game.activate_ability(self.alice.id, shade, 0)
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

        self.assertEqual(self.alice.mana_pool.black, 0)
        self.assertEqual(
            (self.game.creature_power(shade), self.game.creature_toughness(shade)),
            (2, 3),
        )

    def test_non_tap_pump_ability_ignores_summoning_sickness(self) -> None:
        dragon = self.put_in_play(SHIVAN_DRAGON, entered_this_turn=True)
        self.alice.mana_pool.red = 1

        self.assertTrue(
            self.game.can_activate_ability(self.alice.id, dragon, 0)
        )
        self.activate_and_resolve(dragon)

        self.assertFalse(dragon.tapped)
        self.assertEqual(self.game.creature_power(dragon), 6)

    def test_pumps_expire_when_the_turn_ends(self) -> None:
        gargoyle = self.put_in_play(GRANITE_GARGOYLE)
        self.alice.mana_pool.red = 1
        self.activate_and_resolve(gargoyle)
        self.assertEqual(self.game.creature_toughness(gargoyle), 3)

        self.finish_turn()

        self.assertIn(gargoyle, self.alice.battlefield)
        self.assertEqual(self.game.creature_toughness(gargoyle), 2)

    def test_damage_and_toughness_pump_expire_together(self) -> None:
        gargoyle = self.put_in_play(GRANITE_GARGOYLE)
        gargoyle.damage = 2
        self.alice.mana_pool.red = 1
        self.activate_and_resolve(gargoyle)

        self.finish_turn()

        self.assertIn(gargoyle, self.alice.battlefield)
        self.assertEqual(gargoyle.damage, 0)
        self.assertEqual(self.game.creature_toughness(gargoyle), 2)

    def test_three_whelp_activations_are_safe(self) -> None:
        whelp = self.put_in_play(DRAGON_WHELP)
        self.alice.mana_pool.red = 3
        self.activate_and_resolve(whelp, 3)
        self.assertEqual(self.game.creature_power(whelp), 5)
        self.assertNotIn(whelp.id, self.game.destroy_at_end_of_turn)

        self.finish_turn()

        self.assertIn(whelp, self.alice.battlefield)
        self.assertEqual(self.game.creature_power(whelp), 2)

    def test_fourth_whelp_activation_schedules_end_of_turn_destruction(self) -> None:
        whelp = self.put_in_play(DRAGON_WHELP)
        self.alice.mana_pool.red = 4
        self.activate_and_resolve(whelp, 4)

        self.assertIn(whelp, self.alice.battlefield)
        self.assertEqual(self.game.creature_power(whelp), 6)
        self.assertIn(whelp.id, self.game.destroy_at_end_of_turn)

        self.finish_turn()

        self.assertIn(whelp, self.alice.graveyard)
        self.assertNotIn(whelp.id, self.game.destroy_at_end_of_turn)

    def test_pump_disappears_if_creature_leaves_play(self) -> None:
        dragon = self.put_in_play(SHIVAN_DRAGON)
        self.alice.mana_pool.red = 1
        self.activate_and_resolve(dragon)

        self.game.put_permanent_in_graveyard(dragon)

        self.assertNotIn(dragon.id, self.game.temporary_creature_effects)

    def test_unresolved_self_pump_has_no_effect_if_source_leaves_play(self) -> None:
        dragon = self.put_in_play(SHIVAN_DRAGON)
        self.alice.mana_pool.red = 1
        self.game.activate_ability(self.alice.id, dragon, 0)

        self.game._move_card(dragon, Zone.GRAVEYARD)
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

        self.assertNotIn(dragon.id, self.game.temporary_creature_effects)

    def test_pump_abilities_can_respond_to_damage_in_the_same_batch(self) -> None:
        shade = self.put_in_play(FROZEN_SHADE)
        bolt = self.bob.library.pop()
        bolt.definition = LIGHTNING_BOLT
        bolt.zone = Zone.HAND
        self.bob.hand.append(bolt)
        self.bob.mana_pool.red = 1
        self.alice.mana_pool.black = 3
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((shade,))

        for _ in range(3):
            self.game.activate_ability(self.alice.id, shade, 0)
            self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

        self.assertIn(shade, self.alice.battlefield)
        self.assertEqual(
            (self.game.creature_power(shade), self.game.creature_toughness(shade)),
            (3, 4),
        )
        self.assertEqual(shade.damage, 3)


if __name__ == "__main__":
    unittest.main()
