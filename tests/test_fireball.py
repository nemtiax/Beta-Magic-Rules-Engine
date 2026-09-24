import unittest

from beta_magic import (
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs.green import GRIZZLY_BEARS
from beta_magic.card_defs.lands import MOUNTAIN
from beta_magic.card_defs.red import FIREBALL
from beta_magic.card_defs.artifacts import JADE_MONOLITH
from beta_magic.card_defs.white import CIRCLE_OF_PROTECTION_RED
from beta_magic import DamageResolutionStep
from beta_magic.ui import GameViewModel


class FireballTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [MOUNTAIN] * 20)
        self.bob = PlayerState.with_deck("b", "Bob", [MOUNTAIN] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    @staticmethod
    def add(player, definition, zone):
        card = Card(definition, player.id, zone=zone)
        player.cards_in(zone).append(card)
        return card

    def give_mana(self, total):
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = total - 1

    def cast(self, x, targets):
        spell = self.add(self.alice, FIREBALL, Zone.HAND)
        self.game.begin_cast(spell, x_value=x)
        self.game.complete_pending_cast(targets)
        return spell

    def resolve(self):
        while self.game.priority_player_index is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_extra_targets_cost_one_and_damage_is_evenly_rounded_down(self):
        bear = self.add(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.give_mana(7)
        self.cast(5, (bear, self.bob))
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.resolve()
        self.assertIn(bear, self.bob.graveyard)
        self.assertEqual(self.bob.life, 18)

    def test_cast_rejects_an_unaffordable_extra_target(self):
        bear = self.add(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.give_mana(6)
        spell = self.add(self.alice, FIREBALL, Zone.HAND)
        self.game.begin_cast(spell, x_value=5)
        with self.assertRaisesRegex(RuntimeError, "2 targets"):
            self.game.complete_pending_cast((bear, self.bob))
        self.assertIs(self.game.pending_cast.spell, spell)

    def test_each_portion_has_a_distinct_damage_source(self):
        bear = self.add(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.give_mana(6)
        self.cast(4, (bear, self.bob))
        self.resolve()
        packets = self.game.resolved_damage_incidents[-1].packets
        self.assertEqual(len(packets), 2)
        self.assertEqual(len({packet.source_id for packet in packets}), 2)

    def test_one_invalid_target_only_fizzles_its_own_portion(self):
        bear = self.add(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.give_mana(6)
        self.cast(4, (bear, self.bob))
        self.game._move_card(bear, Zone.GRAVEYARD)
        self.resolve()
        self.assertEqual(self.bob.life, 18)

    def test_ui_draft_can_add_remove_targets_and_adjust_x(self):
        bear = self.add(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        spell = self.add(self.alice, FIREBALL, Zone.HAND)
        self.give_mana(7)
        view = GameViewModel(self.game)
        view.activateCard(str(spell.id))
        self.assertTrue(view.state["choosingFireball"])
        self.assertEqual(view.state["fireballX"], 6)

        view.toggleCard(str(bear.id))
        view.targetPlayer(self.bob.id)
        state = view.state
        self.assertEqual(state["fireballTargetCount"], 2)
        self.assertEqual(state["fireballX"], 5)
        self.assertEqual(state["fireballDamageEach"], 2)

        view.adjustFireballX(-1)
        view.removeFireballTarget(f"card:{bear.id}")
        self.assertEqual(view.state["fireballTargetCount"], 1)
        self.assertEqual(view.state["fireballX"], 4)
        view.confirmFireball()
        self.assertIsNone(self.game.pending_cast)
        self.assertIn(spell, self.game.stack)
        self.assertEqual(self.game.stack_spells[spell.id].targets, (self.bob,))

    def test_split_portions_remain_separate_after_redirect_and_prevention(self):
        first = self.add(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        second = self.add(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        monolith = self.add(self.bob, JADE_MONOLITH, Zone.BATTLEFIELD)
        circle = self.add(self.bob, CIRCLE_OF_PROTECTION_RED, Zone.BATTLEFIELD)
        self.game.pause_for_damage_windows = True
        self.give_mana(6)
        self.cast(4, (first, second))
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        self.assertIs(
            self.game.pending_damage.step, DamageResolutionStep.PREVENTION
        )

        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        self.bob.mana_pool.colorless = 2
        for packet in tuple(self.game.pending_damage.packets):
            if self.game.players[self.game.priority_player_index] is self.alice:
                self.game.pass_priority(self.alice.id)
            self.game.activate_ability(self.bob.id, monolith, 0)
            self.game.redirect_damage(self.bob.id, packet.id)
        while self.game.pending_damage.step is not DamageResolutionStep.REGENERATION:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        redirected = self.game.pending_damage
        self.assertIs(redirected.step, DamageResolutionStep.PREVENTION)
        self.assertEqual(len(redirected.packets), 2)
        self.assertEqual(len({packet.source_id for packet in redirected.packets}), 2)
        self.bob.mana_pool.colorless = 1
        self.game.pass_priority(self.alice.id)
        self.game.activate_ability(self.bob.id, circle, 0)
        choices = self.game.legal_prevention_packets()
        self.assertEqual(len(choices), 2)
        self.game.prevent_damage(self.bob.id, choices[0].id)
        while self.game.pending_damage is not None:
            for _ in range(2):
                player = self.game.players[self.game.priority_player_index]
                self.game.pass_priority(player.id)

        self.assertEqual(self.bob.life, 18)
        self.assertEqual((first.damage, second.damage), (0, 0))


if __name__ == "__main__":
    unittest.main()
