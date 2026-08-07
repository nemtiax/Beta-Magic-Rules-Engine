import unittest

from beta_magic import (
    DISINTEGRATE,
    DRUDGE_SKELETONS,
    GRIZZLY_BEARS,
    Card,
    CardType,
    DamageResolutionStep,
    DestructionIncident,
    DestructionTarget,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class DisintegrateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 20
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

    def cast(self, x_value: int, target: Card | PlayerState) -> Card:
        spell = Card(DISINTEGRATE, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(spell)
        self.alice.mana_pool.red = x_value + 1
        self.game.begin_cast(spell, x_value=x_value)
        self.game.complete_pending_cast((target,))
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        return spell

    def finish_damage(self) -> None:
        while self.game.pending_damage is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition_and_player_damage(self) -> None:
        self.assertEqual(DISINTEGRATE.mana_cost.compact, "XR")
        self.assertEqual(DISINTEGRATE.card_types, frozenset({CardType.SORCERY}))

        spell = self.cast(4, self.bob)

        self.assertEqual(self.bob.life, 16)
        self.assertIn(spell, self.alice.graveyard)

    def test_lethal_damage_sets_creature_aside(self) -> None:
        bear = self.permanent(self.bob, GRIZZLY_BEARS)

        self.cast(2, bear)

        self.assertIn(bear, self.bob.exile)
        self.assertNotIn(bear, self.bob.graveyard)

    def test_zero_damage_marks_target_that_dies_later_this_turn(self) -> None:
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.cast(0, bear)

        self.assertIn(bear, self.bob.battlefield)
        self.assertIn(bear.id, self.game.disintegrated_this_turn)
        self.game._deal_damage(bear, 2, "later damage")

        self.assertIn(bear, self.bob.exile)

    def test_preventing_all_damage_does_not_remove_the_turn_mark(self) -> None:
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game.pause_for_damage_windows = True
        self.cast(2, bear)
        self.assertEqual(
            self.game.pending_damage.step, DamageResolutionStep.PREVENTION
        )
        self.game.pending_damage.packets[0].prevented = 2
        self.finish_damage()

        self.assertIn(bear, self.bob.battlefield)
        self.assertIn(bear.id, self.game.disintegrated_this_turn)
        self.game.pause_for_damage_windows = False
        self.game._deal_damage(bear, 2, "later damage")
        self.assertIn(bear, self.bob.exile)

    def test_marked_creature_cannot_use_regeneration(self) -> None:
        skeleton = self.permanent(self.bob, DRUDGE_SKELETONS)
        self.game.pause_for_damage_windows = True
        self.cast(1, skeleton)
        while self.game.pending_damage.step is not DamageResolutionStep.REGENERATION:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        self.bob.mana_pool.black = 1

        self.game.pass_priority(self.alice.id)
        with self.assertRaisesRegex(RuntimeError, "cannot regenerate this turn"):
            self.game.activate_ability(self.bob.id, skeleton, 0)
        self.finish_damage()

        self.assertIn(skeleton, self.bob.exile)

    def test_later_destroy_effect_also_forbids_regeneration(self) -> None:
        skeleton = self.permanent(self.bob, DRUDGE_SKELETONS)
        self.cast(0, skeleton)
        self.game.pending_destruction = DestructionIncident(
            [DestructionTarget(skeleton.id, skeleton.name)]
        )

        self.game._open_destruction_incident()

        self.assertFalse(
            self.game.resolved_destruction_incidents[-1]
            .targets[0]
            .regeneration_allowed
        )
        self.assertIn(skeleton, self.bob.exile)

    def test_mark_expires_at_end_of_turn(self) -> None:
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.cast(0, bear)
        self.game.current_phase = TurnPhase.END

        self.game.next_turn()
        self.game._deal_damage(bear, 2, "next-turn damage")

        self.assertIn(bear, self.bob.graveyard)
        self.assertNotIn(bear, self.bob.exile)


if __name__ == "__main__":
    unittest.main()
