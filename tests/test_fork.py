import unittest

from beta_magic import Card, Color, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.green import GRIZZLY_BEARS
from beta_magic.card_defs.black import TERROR
from beta_magic.card_defs.red import HILL_GIANT
from beta_magic.card_defs.blue import COUNTERSPELL
from beta_magic.card_defs.red import FIREBALL, FORK, LIGHTNING_BOLT
from beta_magic.ui import GameViewModel


class ForkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    @staticmethod
    def add(player, definition, zone):
        card = Card(definition, player.id, zone=zone)
        player.cards_in(zone).append(card)
        return card

    def pass_twice(self):
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def cast_bolt(self):
        bolt = self.add(self.alice, LIGHTNING_BOLT, Zone.HAND)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.bob,))
        return bolt

    def cast_fork(self, original, targets, x_value=None):
        fork = self.add(self.bob, FORK, Zone.HAND)
        self.bob.mana_pool.red = 2
        self.game.begin_cast(fork)
        self.game.choose_pending_fork_copy(
            original, targets, x_value=x_value
        )
        self.game.complete_pending_cast((original,))
        return fork

    def test_copy_is_red_controlled_by_fork_caster_and_can_change_target(self):
        bolt = self.cast_bolt()
        fork = self.cast_fork(bolt, (self.alice,))

        self.pass_twice()

        self.assertEqual(fork.zone, Zone.GRAVEYARD)
        self.assertEqual(len(self.game.stack), 2)
        copy = next(card for card in self.game.stack if card.is_spell_copy)
        self.assertEqual(self.game.card_colors(copy), frozenset({Color.RED}))
        self.assertEqual(self.game.stack_spells[copy.id].caster_id, self.bob.id)
        self.assertEqual(self.game.stack_spells[copy.id].targets, (self.alice,))

        self.pass_twice()
        self.assertEqual(self.alice.life, 17)
        self.assertEqual(self.bob.life, 17)
        self.assertNotIn(copy, self.bob.graveyard)

    def test_forked_fireball_can_reallocate_generic_mana_to_targets(self):
        bear = self.add(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        fireball = self.add(self.alice, FIREBALL, Zone.HAND)
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = 5
        self.game.begin_cast(fireball, x_value=5)
        self.game.complete_pending_cast((self.bob,))

        self.cast_fork(fireball, (bear, self.alice), x_value=4)
        self.pass_twice()
        copy = next(card for card in self.game.stack if card.is_spell_copy)
        copy_state = self.game.stack_spells[copy.id]
        self.assertEqual(copy_state.x_value, 4)
        self.assertEqual(copy_state.targets, (bear, self.alice))

        self.pass_twice()
        self.assertIn(bear, self.bob.graveyard)
        self.assertEqual(self.alice.life, 18)
        self.assertEqual(self.bob.life, 15)

    def test_ui_initializes_copy_targets_and_allows_retargeting(self):
        bolt = self.cast_bolt()
        fork = self.add(self.bob, FORK, Zone.HAND)
        self.bob.mana_pool.red = 2
        view = GameViewModel(self.game)
        view.perspective_index = 1

        view.activateCard(str(fork.id))
        view.toggleCard(str(bolt.id))
        self.assertTrue(view.state["canChooseFork"])
        self.assertEqual(view.state["forkTargets"][0]["name"], "Bob")

        view.targetPlayer(self.alice.id)
        view.confirmFork()
        self.assertIsNone(self.game.pending_cast)
        self.assertEqual(
            self.game.stack_spells[fork.id].copied_spell_targets,
            (self.alice,),
        )

    def test_copy_survives_a_later_interrupt_that_counters_original(self):
        bolt = self.cast_bolt()
        counter = self.add(self.bob, COUNTERSPELL, Zone.HAND)
        self.bob.mana_pool.blue = 2
        self.game.begin_cast(counter)
        self.game.complete_pending_cast((bolt,))

        fork = self.add(self.alice, FORK, Zone.HAND)
        self.alice.mana_pool.red = 2
        self.game.begin_cast(fork)
        self.game.choose_pending_fork_copy(bolt, (self.bob,))
        self.game.complete_pending_cast((bolt,))

        self.pass_twice()
        copy = next(card for card in self.game.stack if card.is_spell_copy)
        self.assertEqual(self.game.stack[-1], counter)

        self.pass_twice()
        self.assertEqual(bolt.zone, Zone.GRAVEYARD)
        self.assertIn(copy, self.game.stack)

        self.pass_twice()
        self.assertEqual(self.bob.life, 17)

    def test_copy_inherits_current_word_changes_without_linking_original(self):
        giant = self.add(self.bob, HILL_GIANT, Zone.BATTLEFIELD)
        terror = self.add(self.alice, TERROR, Zone.HAND)
        self.alice.mana_pool.black = 2
        self.game.begin_cast(terror)
        self.game.complete_pending_cast((giant,))
        self.cast_fork(terror, (giant,))

        # Stand in for a Sleight resolving earlier in the interrupt sequence.
        terror.change_color_word(Color.BLACK, Color.GREEN)
        self.pass_twice()
        copy = next(card for card in self.game.stack if card.is_spell_copy)

        self.assertEqual(copy.color_word_changes, {Color.BLACK: Color.GREEN})
        terror.change_color_word(Color.GREEN, Color.BLUE)
        self.assertEqual(copy.color_word_changes, {Color.BLACK: Color.GREEN})


if __name__ == "__main__":
    unittest.main()
