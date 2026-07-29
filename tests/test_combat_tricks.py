import unittest

from beta_magic import (
    GIANT_GROWTH,
    LIGHTNING_BOLT,
    RIGHTEOUSNESS,
    TARGETED_PUMP_SPELLS,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.vanilla_creatures import GRIZZLY_BEARS, HILL_GIANT


class CombatTrickTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 30
        )
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 30)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_hand(player, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        player.hand.append(card)
        return card

    @staticmethod
    def put_in_play(player, definition=GRIZZLY_BEARS):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = player.id
        player.battlefield.append(card)
        return card

    def cast(self, player, definition, target):
        spell = self.put_in_hand(player, definition)
        player.mana_pool.green += 1
        player.mana_pool.white += 1
        player.mana_pool.red += 1
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((target,))
        return spell

    def resolve_batch(self):
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definitions(self) -> None:
        self.assertEqual(TARGETED_PUMP_SPELLS, (GIANT_GROWTH, RIGHTEOUSNESS))
        self.assertEqual(GIANT_GROWTH.mana_cost.compact, "G")
        self.assertEqual(RIGHTEOUSNESS.mana_cost.compact, "W")
        self.assertTrue(
            all(CardType.INSTANT in card.card_types for card in TARGETED_PUMP_SPELLS)
        )
        self.assertFalse(GIANT_GROWTH.target_requirement.blocking_only)
        self.assertTrue(RIGHTEOUSNESS.target_requirement.blocking_only)

    def test_giant_growth_stacks_and_expires_at_end_of_turn(self) -> None:
        bear = self.put_in_play(self.alice)
        growth = self.cast(self.alice, GIANT_GROWTH, bear)

        self.resolve_batch()

        self.assertIn(growth, self.alice.graveyard)
        self.assertEqual(
            (self.game.creature_power(bear), self.game.creature_toughness(bear)),
            (5, 5),
        )
        while self.game.current_phase is not TurnPhase.END:
            self.game.advance_phase()
        self.game.advance_phase()
        self.assertEqual(
            (self.game.creature_power(bear), self.game.creature_toughness(bear)),
            (2, 2),
        )

    def test_growth_response_saves_creature_from_lightning_bolt(self) -> None:
        bear = self.put_in_play(self.bob)
        bolt = self.cast(self.alice, LIGHTNING_BOLT, bear)
        growth = self.cast(self.bob, GIANT_GROWTH, bear)

        self.resolve_batch()

        self.assertIn(bear, self.bob.battlefield)
        self.assertEqual(self.game.creature_toughness(bear), 5)
        self.assertEqual(bear.damage, 3)
        self.assertIn(bolt, self.alice.graveyard)
        self.assertIn(growth, self.bob.graveyard)

    def test_growth_saves_creature_when_bolt_is_the_response(self) -> None:
        bear = self.put_in_play(self.alice)
        growth = self.cast(self.alice, GIANT_GROWTH, bear)
        bolt = self.cast(self.bob, LIGHTNING_BOLT, bear)

        self.resolve_batch()

        self.assertIn(bear, self.alice.battlefield)
        self.assertEqual(self.game.creature_toughness(bear), 5)
        self.assertEqual(bear.damage, 3)
        self.assertIn(growth, self.alice.graveyard)
        self.assertIn(bolt, self.bob.graveyard)

    def test_righteousness_only_targets_a_current_blocker(self) -> None:
        attacker = self.put_in_play(self.alice, HILL_GIANT)
        blocker = self.put_in_play(self.bob)
        bystander = self.put_in_play(self.bob)
        righteousness = self.put_in_hand(self.bob, RIGHTEOUSNESS)

        self.assertEqual(self.game.legal_targets_for(righteousness), [])
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        self.game.declare_blockers({blocker: attacker})

        self.assertEqual(self.game.legal_targets_for(righteousness), [blocker])
        self.assertNotIn(attacker, self.game.legal_targets_for(righteousness))
        self.assertNotIn(bystander, self.game.legal_targets_for(righteousness))

    def test_righteousness_changes_combat_outcome(self) -> None:
        attacker = self.put_in_play(self.alice, HILL_GIANT)
        blocker = self.put_in_play(self.bob)
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        self.game.declare_blockers({blocker: attacker})
        righteousness = self.cast(self.bob, RIGHTEOUSNESS, blocker)

        self.resolve_batch()
        self.game.advance_combat()
        self.game.deal_combat_damage()

        self.assertIn(righteousness, self.bob.graveyard)
        self.assertIn(blocker, self.bob.battlefield)
        self.assertIn(attacker, self.alice.graveyard)


if __name__ == "__main__":
    unittest.main()
