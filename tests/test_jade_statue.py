import unittest

from tests.support import declare_attackers, declare_blockers

from beta_magic.card_defs.blue import ANIMATE_ARTIFACT
from beta_magic.card_defs.white import HOLY_STRENGTH
from beta_magic.card_defs.artifacts import JADE_STATUE
from beta_magic import (
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs.green import GRIZZLY_BEARS, REGENERATION
from beta_magic.ui import GameViewModel


class JadeStatueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition, *, entered_turn=0):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=entered_turn,
        )
        player.battlefield.append(card)
        return card

    def animate(self, statue):
        self.alice.mana_pool.colorless = 2
        if (
            self.game.priority_player_index is not None
            and self.game.players[self.game.priority_player_index] is not self.alice
        ):
            self.game.pass_priority(
                self.game.players[self.game.priority_player_index].id
            )
        self.game.activate_ability(self.alice.id, statue, 0)
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

    def test_only_activates_during_combat_and_only_once_per_turn(self):
        statue = self.permanent(self.alice, JADE_STATUE)
        self.alice.mana_pool.colorless = 4
        with self.assertRaisesRegex(RuntimeError, "during an attack"):
            self.game.activate_ability(self.alice.id, statue, 0)

        self.game.begin_combat()
        self.animate(statue)
        self.assertIn(CardType.CREATURE, self.game.card_types(statue))
        with self.assertRaisesRegex(RuntimeError, "already been activated"):
            self.game.activate_ability(self.alice.id, statue, 0)

    def test_animation_is_three_six_and_ends_with_combat(self):
        statue = self.permanent(self.alice, JADE_STATUE)
        self.game.begin_combat()
        self.animate(statue)

        self.assertEqual(
            (
                self.game.creature_power(statue),
                self.game.creature_toughness(statue),
            ),
            (3, 6),
        )
        declare_attackers(self.game, [])
        declare_blockers(self.game, {})
        self.game.advance_combat()
        self.game.deal_combat_damage()
        self.assertNotIn(CardType.CREATURE, self.game.card_types(statue))

    def test_animated_stats_are_exposed_to_the_ui(self):
        statue = self.permanent(self.alice, JADE_STATUE)
        self.game.begin_combat()
        self.animate(statue)

        data = GameViewModel(self.game)._presentation._card_data(statue)

        self.assertTrue(data["isCreature"])
        self.assertEqual((data["power"], data["toughness"]), (3, 6))

    def test_new_statue_cannot_attack_but_can_animate_for_defense(self):
        statue = self.permanent(
            self.alice, JADE_STATUE, entered_turn=self.game.turn_number
        )
        self.game.begin_combat()
        self.animate(statue)
        with self.assertRaisesRegex(ValueError, "did not begin the turn"):
            declare_attackers(self.game, [statue])

        game = GameState(
            [
                PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 8),
                PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 8),
            ]
        )
        game.start(opening_hand_size=0, shuffle=False)
        while game.current_phase is not TurnPhase.MAIN:
            game.advance_phase()
        attacker = self.permanent(game.players[0], GRIZZLY_BEARS)
        defending_statue = self.permanent(
            game.players[1], JADE_STATUE, entered_turn=game.turn_number
        )
        game.begin_combat()
        declare_attackers(game, [attacker])
        game.players[1].mana_pool.colorless = 2
        game.pass_priority(game.players[0].id)
        game.activate_ability(game.players[1].id, defending_statue, 0)
        game.pass_priority(game.players[0].id)
        game.pass_priority(game.players[1].id)
        declare_blockers(game, {defending_statue: attacker})
        self.assertFalse(defending_statue.tapped)

    def test_animate_artifact_is_overridden_only_for_current_combat(self):
        statue = self.permanent(self.alice, JADE_STATUE)
        animate_artifact = self.permanent(self.alice, ANIMATE_ARTIFACT)
        animate_artifact.enchanted_card_id = statue.id
        self.assertEqual(
            (self.game.creature_power(statue), self.game.creature_toughness(statue)),
            (4, 4),
        )

        self.game.begin_combat()
        self.animate(statue)
        self.assertEqual(
            (self.game.creature_power(statue), self.game.creature_toughness(statue)),
            (3, 6),
        )
        declare_attackers(self.game, [])
        declare_blockers(self.game, {})
        self.game.advance_combat()
        self.game.deal_combat_damage()
        self.assertEqual(
            (self.game.creature_power(statue), self.game.creature_toughness(statue)),
            (4, 4),
        )

    def test_creature_aura_lies_dormant_and_returns_on_animation(self):
        statue = self.permanent(self.alice, JADE_STATUE)
        animate_artifact = self.permanent(self.alice, ANIMATE_ARTIFACT)
        animate_artifact.enchanted_card_id = statue.id
        strength = self.permanent(self.alice, HOLY_STRENGTH)
        strength.enchanted_card_id = statue.id
        self.game._move_card(animate_artifact, Zone.GRAVEYARD)

        self.assertIn(strength, self.alice.battlefield)
        self.assertNotIn(CardType.CREATURE, self.game.card_types(statue))
        self.game.begin_combat()
        self.animate(statue)
        self.assertEqual(
            (self.game.creature_power(statue), self.game.creature_toughness(statue)),
            (4, 8),
        )

    def test_opponent_keeps_authority_over_dormant_regeneration_aura(self):
        statue = self.permanent(self.alice, JADE_STATUE)
        first_animation = self.permanent(self.alice, ANIMATE_ARTIFACT)
        first_animation.enchanted_card_id = statue.id
        regeneration = self.permanent(self.bob, REGENERATION)
        regeneration.enchanted_card_id = statue.id

        self.game._move_card(first_animation, Zone.GRAVEYARD)
        self.assertNotIn(CardType.CREATURE, self.game.card_types(statue))
        self.assertIn(regeneration, self.bob.battlefield)

        second_animation = self.permanent(self.alice, ANIMATE_ARTIFACT)
        second_animation.enchanted_card_id = statue.id
        self.assertEqual(
            (self.game.creature_power(statue), self.game.creature_toughness(statue)),
            (4, 4),
        )
        self.game.pause_for_damage_windows = True
        self.game._deal_damage(statue, 4, "test")
        for _ in range(4):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.bob.mana_pool.green = 1
        with self.assertRaisesRegex(ValueError, "only activate.*control"):
            self.game.activate_ability(self.alice.id, regeneration, 0)
        self.game.pass_priority(self.alice.id)
        self.game.activate_ability(self.bob.id, regeneration, 0)
        while self.game.pending_damage is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.assertIn(statue, self.alice.battlefield)
        self.assertIn(regeneration, self.bob.battlefield)
        self.assertTrue(statue.tapped)
        self.assertEqual(statue.damage, 0)


if __name__ == "__main__":
    unittest.main()
