import unittest

from beta_magic import Card, CardType, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.artifacts import TIME_VAULT
from beta_magic.card_defs.black import PARALYZE
from beta_magic.card_defs.blue import ANIMATE_ARTIFACT
from beta_magic.card_defs.green import (
    GRIZZLY_BEARS,
    INSTILL_ENERGY,
    LLANOWAR_ELVES,
)


class InstillEnergyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 20)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition, *, tapped=False, entered_turn=None):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            tapped=tapped,
            entered_battlefield_turn=entered_turn,
            summoned_turn=entered_turn,
        )
        player.battlefield.append(card)
        return card

    def aura(self, definition, target, controller=None):
        player = controller or self.alice
        aura = self.permanent(player, definition)
        aura.enchanted_card_id = target.id
        return aura

    def resolve_batch(self):
        while self.game.priority_player_index is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self):
        self.assertEqual(INSTILL_ENERGY.mana_cost.compact, "G")
        self.assertEqual(
            INSTILL_ENERGY.card_types, frozenset({CardType.ENCHANTMENT})
        )
        ability = INSTILL_ENERGY.activated_abilities[0]
        self.assertTrue(ability.affects_attached_creature)
        self.assertTrue(ability.once_per_turn)
        self.assertTrue(ability.controller_turn_only)

    def test_new_creature_may_attack_but_cannot_use_tap_abilities(self):
        elves = self.permanent(
            self.alice,
            LLANOWAR_ELVES,
            entered_turn=self.game.turn_number,
        )
        self.aura(INSTILL_ENERGY, elves)

        self.assertFalse(self.game.can_activate_ability(self.alice.id, elves, 0))
        self.game.begin_combat()
        self.game.declare_attackers((elves,))
        self.assertIn(elves, self.game.combat.attackers)

    def test_extra_untap_is_a_fast_effect_and_only_once_each_turn(self):
        bear = self.permanent(self.alice, GRIZZLY_BEARS, tapped=True)
        instill = self.aura(INSTILL_ENERGY, bear)

        self.game.activate_ability(self.alice.id, instill, 0)
        self.assertTrue(bear.tapped)
        self.assertTrue(self.game.batch_abilities)
        self.resolve_batch()
        self.assertFalse(bear.tapped)

        bear.tapped = True
        with self.assertRaisesRegex(RuntimeError, "already been used"):
            self.game.activate_ability(self.alice.id, instill, 0)

    def test_cannot_use_extra_untap_during_an_opponents_turn(self):
        bear = self.permanent(self.alice, GRIZZLY_BEARS, tapped=True)
        instill = self.aura(INSTILL_ENERGY, bear)
        self.game.active_player_index = 1
        with self.assertRaisesRegex(RuntimeError, "during your turn"):
            self.game.activate_ability(self.alice.id, instill, 0)

    def test_extra_untap_ignores_paralyze(self):
        bear = self.permanent(self.alice, GRIZZLY_BEARS, tapped=True)
        self.aura(PARALYZE, bear, controller=self.bob)
        instill = self.aura(INSTILL_ENERGY, bear)

        self.game.activate_ability(self.alice.id, instill, 0)
        self.resolve_batch()
        self.assertFalse(bear.tapped)

    def test_can_untap_an_animated_time_vault_without_skipping_a_turn(self):
        vault = self.permanent(self.alice, TIME_VAULT, tapped=True)
        self.aura(ANIMATE_ARTIFACT, vault)
        instill = self.aura(INSTILL_ENERGY, vault)
        self.assertIn(CardType.CREATURE, self.game.card_types(vault))

        self.game.activate_ability(self.alice.id, instill, 0)
        self.resolve_batch()
        self.assertFalse(vault.tapped)
        self.assertFalse(self.game.vaults_untapping_next_turn)

    def test_tap_untap_tap_requires_separate_batches(self):
        elves = self.permanent(self.alice, LLANOWAR_ELVES, tapped=True)
        instill = self.aura(INSTILL_ENERGY, elves)
        self.game.activate_ability(self.alice.id, instill, 0)

        with self.assertRaisesRegex(RuntimeError, "Bob has priority"):
            self.game.activate_ability(self.alice.id, elves, 0)
        self.resolve_batch()
        self.game.activate_ability(self.alice.id, elves, 0)


if __name__ == "__main__":
    unittest.main()
