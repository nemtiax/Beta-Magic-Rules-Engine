import unittest

from beta_magic import (
    BERSERK,
    DRUDGE_SKELETONS,
    GIANT_GROWTH,
    GRIZZLY_BEARS,
    PLAGUE_RATS,
    SWAMP,
    Card,
    CardType,
    DestructionResolutionStep,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)


class BerserkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 30
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 30
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player: PlayerState, definition) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        player.battlefield.append(card)
        return card

    def cast(self, definition, target: Card) -> Card:
        spell = Card(definition, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(spell)
        self.alice.mana_pool.green += 1
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((target,))
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        return spell

    def test_definition(self) -> None:
        self.assertEqual(BERSERK.mana_cost.compact, "G")
        self.assertEqual(BERSERK.card_types, frozenset({CardType.INSTANT}))
        effect = BERSERK.spell_effects[0]
        self.assertEqual(effect.power_multiplier, 2)
        self.assertTrue(effect.destroy_at_end_of_turn_if_attacked)

    def test_doubles_current_power_and_grants_trample(self) -> None:
        bear = self.permanent(self.alice, GRIZZLY_BEARS)

        self.cast(BERSERK, bear)

        self.assertEqual(self.game.creature_power(bear), 4)
        self.assertIn(KeywordAbility.TRAMPLE, self.game.creature_abilities(bear))

    def test_power_modifiers_are_applied_in_casting_order(self) -> None:
        first = self.permanent(self.alice, GRIZZLY_BEARS)
        self.cast(GIANT_GROWTH, first)
        self.cast(BERSERK, first)
        self.assertEqual(self.game.creature_power(first), 10)

        second = self.permanent(self.alice, GRIZZLY_BEARS)
        self.cast(BERSERK, second)
        self.cast(GIANT_GROWTH, second)
        self.assertEqual(self.game.creature_power(second), 7)

    def test_multiplier_recalculates_when_variable_base_power_changes(self) -> None:
        first = self.permanent(self.alice, PLAGUE_RATS)
        second = self.permanent(self.alice, PLAGUE_RATS)
        third = self.permanent(self.alice, PLAGUE_RATS)
        self.cast(GIANT_GROWTH, first)
        self.cast(BERSERK, first)
        self.assertEqual(self.game.creature_power(first), 12)

        self.game._move_card(third, Zone.GRAVEYARD)

        self.assertEqual(self.game.creature_power(first), 10)
        self.assertIn(second, self.alice.battlefield)

    def test_attacker_is_destroyed_at_end_of_turn(self) -> None:
        bear = self.permanent(self.alice, GRIZZLY_BEARS)
        self.cast(BERSERK, bear)
        self.game.attacked_this_turn.add(bear.id)
        self.game.current_phase = TurnPhase.END

        self.game.next_turn()

        self.assertIn(bear, self.alice.graveyard)

    def test_nonattacking_creature_survives_including_a_blocker(self) -> None:
        bear = self.permanent(self.alice, GRIZZLY_BEARS)
        self.cast(BERSERK, bear)
        self.game.current_phase = TurnPhase.END

        self.game.next_turn()

        self.assertIn(bear, self.alice.battlefield)
        self.assertEqual(self.game.creature_power(bear), 2)

    def test_end_of_turn_destruction_allows_regeneration(self) -> None:
        skeleton = self.permanent(self.bob, DRUDGE_SKELETONS)
        swamp = self.permanent(self.bob, SWAMP)
        self.cast(BERSERK, skeleton)
        self.game.attacked_this_turn.add(skeleton.id)
        self.game.current_phase = TurnPhase.END

        self.game.next_turn()

        self.assertEqual(
            self.game.pending_destruction.step,
            DestructionResolutionStep.REGENERATION,
        )
        self.game.pass_priority(self.alice.id)
        self.game.activate_ability(self.bob.id, swamp, 0)
        self.game.activate_ability(self.bob.id, skeleton, 0)
        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)

        self.assertIn(skeleton, self.bob.battlefield)
        self.assertTrue(skeleton.tapped)

    def test_cannot_be_cast_after_the_turns_attack_is_complete(self) -> None:
        bear = self.permanent(self.alice, GRIZZLY_BEARS)
        spell = Card(BERSERK, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(spell)
        self.alice.mana_pool.green = 1
        self.game.attacks_this_turn = 1

        with self.assertRaisesRegex(RuntimeError, "after the current turn's attack"):
            self.game.begin_cast(spell)


if __name__ == "__main__":
    unittest.main()
