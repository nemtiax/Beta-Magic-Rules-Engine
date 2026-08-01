import unittest

from beta_magic import (
    TIME_VAULT,
    TIME_WALK,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS


class TimeWalkAndVaultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "a", "Alice", [GRIZZLY_BEARS] * 30
        )
        self.bob = PlayerState.with_deck(
            "b", "Bob", [GRIZZLY_BEARS] * 30
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player, definition, zone):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id if zone is Zone.BATTLEFIELD else None,
            base_controller_id=(
                player.id if zone is Zone.BATTLEFIELD else None
            ),
            zone=zone,
            entered_battlefield_turn=0 if zone is Zone.BATTLEFIELD else None,
        )
        player.cards_in(zone).append(card)
        return card

    def resolve(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def finish_turn(self) -> None:
        while self.game.current_phase is not TurnPhase.END:
            self.game.advance_phase()
        self.game.advance_phase()

    def cast_time_walk(self):
        walk = self.card(self.alice, TIME_WALK, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(walk)
        self.resolve()
        return walk

    def test_multiple_time_walks_queue_multiple_turns(self):
        self.cast_time_walk()
        self.cast_time_walk()
        self.assertEqual(self.game.upcoming_turns, ["a", "a"])

        self.finish_turn()
        self.assertIs(self.game.active_player, self.alice)
        self.assertEqual(self.game.upcoming_turns, ["a"])

        self.finish_turn()
        self.assertIs(self.game.active_player, self.alice)
        self.assertEqual(self.game.upcoming_turns, [])

        self.finish_turn()
        self.assertIs(self.game.active_player, self.bob)

    def test_newest_additional_turn_is_immediately_after_current(self):
        self.game.schedule_extra_turn(self.alice.id)
        self.game.schedule_extra_turn(self.bob.id)
        self.assertEqual(self.game.upcoming_turns, ["b", "a"])

    def test_time_vault_enters_tapped_and_does_not_untap_normally(self):
        vault = self.card(self.alice, TIME_VAULT, Zone.HAND)
        self.alice.mana_pool.colorless = 2
        self.game.begin_cast(vault)
        self.resolve()
        self.assertTrue(vault.tapped)

        # Taking a turn rather than skipping leaves it tapped.
        self.game.schedule_extra_turn(self.alice.id)
        self.finish_turn()
        self.assertIsNotNone(self.game.pending_turn_choice)
        self.game.choose_time_vault_skip(self.alice.id, None)
        self.assertTrue(vault.tapped)

    def test_skipped_turn_readies_only_the_chosen_vault_on_following_turn(self):
        first = self.card(self.bob, TIME_VAULT, Zone.BATTLEFIELD)
        second = self.card(self.bob, TIME_VAULT, Zone.BATTLEFIELD)
        first.tapped = second.tapped = True

        self.finish_turn()
        self.assertEqual(
            set(self.game.pending_turn_choice.vault_ids),
            {first.id, second.id},
        )
        self.game.choose_time_vault_skip(self.bob.id, first)
        self.assertIs(self.game.active_player, self.alice)
        self.assertTrue(first.tapped)
        self.assertTrue(second.tapped)

        self.finish_turn()
        self.assertIsNotNone(self.game.pending_turn_choice)
        self.game.choose_time_vault_skip(self.bob.id, None)
        self.assertIs(self.game.active_player, self.bob)
        self.assertFalse(first.tapped)
        self.assertTrue(second.tapped)

    def test_vault_activation_adds_a_turn_after_the_batch_resolves(self):
        vault = self.card(self.alice, TIME_VAULT, Zone.BATTLEFIELD)
        vault.tapped = False
        self.game.activate_ability(self.alice.id, vault, 0)
        self.assertEqual(self.game.upcoming_turns, [])
        self.resolve()
        self.assertEqual(self.game.upcoming_turns, [self.alice.id])
        self.assertTrue(vault.tapped)


if __name__ == "__main__":
    unittest.main()
