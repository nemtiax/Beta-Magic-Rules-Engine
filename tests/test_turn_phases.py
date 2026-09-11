import unittest

from beta_magic import (
    Card,
    CardDefinition,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


FOREST = CardDefinition(name="Forest", card_types=frozenset({CardType.LAND}))
ZERO_INSTANT = CardDefinition(
    name="Test Instant",
    card_types=frozenset({CardType.INSTANT}),
)


def player(player_id: str, card_count: int = 12) -> PlayerState:
    return PlayerState.with_deck(
        player_id, player_id.title(), [FOREST] * card_count
    )


class TurnPhaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = player("alice")
        self.bob = player("bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=7, shuffle=False)

    def test_game_starts_in_untap(self) -> None:
        self.assertEqual(self.game.current_phase, TurnPhase.UNTAP)
        self.assertEqual(self.game.turn_number, 1)

    def test_untap_advances_immediately_without_a_response_window(self) -> None:
        self.assertEqual(self.game.propose_phase_advance(), TurnPhase.UPKEEP)
        self.assertIsNone(self.game.pending_phase_advance)
        self.assertIsNone(self.game.priority_player_index)

    def test_phase_only_ends_after_opponent_passes(self) -> None:
        self.game.advance_phase()
        self.alice.mana_pool.green = 2

        self.game.propose_phase_advance()

        self.assertEqual(self.game.current_phase, TurnPhase.UPKEEP)
        self.assertEqual(self.game.pending_phase_advance, TurnPhase.UPKEEP)
        self.assertEqual(self.game.priority_player_index, 1)
        self.assertEqual(self.alice.mana_pool.total, 2)

        self.game.pass_priority(self.bob.id)
        self.assertEqual(self.game.current_phase, TurnPhase.DRAW)
        self.assertIsNone(self.game.pending_phase_advance)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertEqual(self.alice.life, 18)

    def test_active_player_has_first_announcement_in_a_neutral_phase(self) -> None:
        self.game.advance_phase()
        spell = Card(ZERO_INSTANT, self.bob.id, zone=Zone.HAND)
        self.bob.hand.append(spell)

        self.assertEqual(
            self.game.action_priority_player_index,
            self.game.active_player_index,
        )
        with self.assertRaisesRegex(RuntimeError, "Alice has priority"):
            self.game.begin_cast(spell)

        self.game.propose_phase_advance()
        self.game.begin_cast(spell)
        self.assertIn(spell, self.game.stack)

    def test_batch_resolution_returns_neutral_announcement_to_active_player(
        self,
    ) -> None:
        self.game.advance_phase()
        active_spell = Card(ZERO_INSTANT, self.alice.id, zone=Zone.HAND)
        inactive_spell = Card(ZERO_INSTANT, self.bob.id, zone=Zone.HAND)
        self.alice.hand.append(active_spell)
        self.bob.hand.append(inactive_spell)

        self.game.begin_cast(active_spell)
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.assertIsNone(self.game.priority_player_index)
        self.assertTrue(self.game.player_has_action_priority(self.alice.id))
        self.assertFalse(self.game.player_has_action_priority(self.bob.id))
        with self.assertRaisesRegex(RuntimeError, "Alice has priority"):
            self.game.begin_cast(inactive_spell)

    def test_action_during_phase_close_requires_both_players_to_pass_again(self) -> None:
        self.game.advance_phase()
        spell = Card(ZERO_INSTANT, self.bob.id, zone=Zone.HAND)
        self.bob.hand.append(spell)
        self.game.propose_phase_advance()

        self.game.begin_cast(spell)
        self.assertEqual(self.game.consecutive_passes, 0)
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.assertEqual(spell.zone, Zone.GRAVEYARD)
        self.assertEqual(self.game.current_phase, TurnPhase.UPKEEP)
        self.assertEqual(self.game.priority_player_index, 0)

        self.game.pass_priority(self.alice.id)
        self.assertEqual(self.game.current_phase, TurnPhase.UPKEEP)
        self.game.pass_priority(self.bob.id)
        self.assertEqual(self.game.current_phase, TurnPhase.DRAW)

    def test_turn_follows_beta_phase_order_and_draws_on_entry(self) -> None:
        library_size = len(self.alice.library)
        self.assertEqual(self.game.advance_phase(), TurnPhase.UPKEEP)
        self.assertEqual(self.game.advance_phase(), TurnPhase.DRAW)
        self.assertEqual(len(self.alice.library), library_size - 1)
        self.assertEqual(len(self.alice.hand), 8)
        self.assertEqual(self.game.advance_phase(), TurnPhase.MAIN)
        self.assertEqual(self.game.advance_phase(), TurnPhase.DISCARD)

    def test_cannot_leave_discard_with_more_than_seven_cards(self) -> None:
        for _ in range(4):
            self.game.advance_phase()
        self.assertEqual(self.game.current_phase, TurnPhase.DISCARD)
        self.assertEqual(self.alice.discard_required, 1)
        with self.assertRaises(RuntimeError):
            self.game.advance_phase()
        self.game.discard(self.alice.hand[0])
        self.assertEqual(self.game.advance_phase(), TurnPhase.END)

    def test_turn_based_discard_is_only_legal_when_required(self) -> None:
        with self.assertRaises(RuntimeError):
            self.game.discard(self.alice.hand[0])

    def test_advancing_end_starts_opponents_turn_and_untaps(self) -> None:
        # Avoid the draw-created discard choice in this transition-focused test.
        self.alice.hand.pop()
        for _ in range(5):
            self.game.advance_phase()

        tapped_land = Card(
            FOREST,
            owner_id="bob",
            controller_id="bob",
            zone=Zone.BATTLEFIELD,
            tapped=True,
        )
        self.bob.battlefield.append(tapped_land)
        self.assertEqual(self.game.current_phase, TurnPhase.END)

        self.assertEqual(self.game.advance_phase(), TurnPhase.UNTAP)
        self.assertIs(self.game.active_player, self.bob)
        self.assertEqual(self.game.turn_number, 2)
        self.assertFalse(tapped_land.tapped)

    def test_next_property_ends_after_end_phase(self) -> None:
        self.assertEqual(TurnPhase.UNTAP.next, TurnPhase.UPKEEP)
        self.assertIsNone(TurnPhase.END.next)


if __name__ == "__main__":
    unittest.main()
