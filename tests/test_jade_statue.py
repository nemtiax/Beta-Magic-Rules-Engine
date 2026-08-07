import unittest

from beta_magic import (
    ANIMATE_ARTIFACT,
    HOLY_STRENGTH,
    JADE_STATUE,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS


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
        self.game.declare_attackers([])
        self.game.declare_blockers({})
        self.game.advance_combat()
        self.game.deal_combat_damage()
        self.assertNotIn(CardType.CREATURE, self.game.card_types(statue))

    def test_new_statue_cannot_attack_but_can_animate_for_defense(self):
        statue = self.permanent(
            self.alice, JADE_STATUE, entered_turn=self.game.turn_number
        )
        self.game.begin_combat()
        self.animate(statue)
        with self.assertRaisesRegex(ValueError, "did not begin the turn"):
            self.game.declare_attackers([statue])

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
        game.declare_attackers([attacker])
        game.players[1].mana_pool.colorless = 2
        game.pass_priority(game.players[0].id)
        game.activate_ability(game.players[1].id, defending_statue, 0)
        game.pass_priority(game.players[0].id)
        game.pass_priority(game.players[1].id)
        game.declare_blockers({defending_statue: attacker})
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
        self.game.declare_attackers([])
        self.game.declare_blockers({})
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


if __name__ == "__main__":
    unittest.main()
