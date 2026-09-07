import unittest

from beta_magic import (
    GLASSES_OF_URZA,
    FOREST,
    ISLAND,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class GlassesOfUrzaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [ISLAND] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.glasses = Card(
            GLASSES_OF_URZA,
            self.alice.id,
            controller_id=self.alice.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        self.alice.battlefield.append(self.glasses)
        self.bob.hand.extend(
            (
                Card(FOREST, self.bob.id, zone=Zone.HAND),
                Card(ISLAND, self.bob.id, zone=Zone.HAND),
            )
        )

    def resolve_batch(self) -> None:
        while self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self) -> None:
        self.assertEqual(GLASSES_OF_URZA.mana_cost.compact, "1")
        self.assertEqual(
            GLASSES_OF_URZA.card_types, frozenset({CardType.ARTIFACT})
        )
        ability = GLASSES_OF_URZA.activated_abilities[0]
        self.assertTrue(ability.tap_cost)
        self.assertEqual(ability.mana_cost.mana_value, 0)
        self.assertEqual(ability.label, "Tap: Look at opponent's hand")

    def test_activation_uses_fast_effect_batch_then_snapshots_hand(self) -> None:
        result = self.game.activate_ability(self.alice.id, self.glasses, 0)

        self.assertIsNone(result)
        self.assertTrue(self.glasses.tapped)
        self.assertEqual(len(self.game.batch_abilities), 1)
        self.assertEqual(self.game.pending_hand_reveals, [])
        self.assertIs(
            self.game.players[self.game.priority_player_index], self.bob
        )

        self.resolve_batch()

        reveal = self.game.pending_hand_reveals[0]
        self.assertEqual(reveal.viewer_id, self.alice.id)
        self.assertEqual(reveal.target_id, self.bob.id)
        self.assertEqual(reveal.cards, tuple(self.bob.hand))

    def test_reveal_blocks_play_until_viewer_dismisses_it(self) -> None:
        self.game.activate_ability(self.alice.id, self.glasses, 0)
        self.resolve_batch()

        with self.assertRaisesRegex(RuntimeError, "finish looking"):
            self.game.propose_phase_advance()
        with self.assertRaisesRegex(ValueError, "only the player looking"):
            self.game.finish_hand_reveal(self.bob.id)

        self.game.finish_hand_reveal(self.alice.id)

        self.assertEqual(self.game.pending_hand_reveals, [])
        self.game.propose_phase_advance()

    def test_hotseat_view_only_exposes_cards_to_ability_controller(self) -> None:
        self.game.activate_ability(self.alice.id, self.glasses, 0)
        self.resolve_batch()
        view_model = GameViewModel(self.game)

        alice_state = view_model.state
        self.assertTrue(alice_state["handRevealPending"])
        self.assertTrue(alice_state["handRevealCanView"])
        self.assertEqual(
            [card["name"] for card in alice_state["handRevealCards"]],
            ["Forest", "Island"],
        )

        view_model.switchPerspective()
        bob_state = view_model.state
        self.assertTrue(bob_state["handRevealPending"])
        self.assertFalse(bob_state["handRevealCanView"])
        self.assertEqual(bob_state["handRevealCards"], [])

        view_model.switchPerspective()
        view_model.finishHandReveal()
        self.assertFalse(view_model.state["handRevealPending"])


if __name__ == "__main__":
    unittest.main()
