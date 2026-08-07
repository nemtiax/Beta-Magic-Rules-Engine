import unittest

from beta_magic import (
    GRIZZLY_BEARS,
    LIGHTNING_BOLT,
    REVERSE_DAMAGE,
    SIMULACRUM,
    Card,
    DamageIncidentKind,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import BLACK_KNIGHT, HILL_GIANT, WHITE_KNIGHT


class RetroactiveDamageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 30
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 30
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(player: PlayerState, definition) -> Card:
        card = Card(
            definition, player.id, controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    @staticmethod
    def put_in_hand(player: PlayerState, definition) -> Card:
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        player.hand.append(card)
        return card

    def resolve_batch(self) -> None:
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def damage_alice(self, amount: int, source: Card) -> None:
        self.game._deal_damage(
            self.alice, amount, source.name, source_card=source
        )

    def test_reverse_damage_groups_only_the_chosen_physical_source(self) -> None:
        first = self.put_in_play(self.bob, GRIZZLY_BEARS)
        second = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.damage_alice(2, first)
        self.damage_alice(1, first)
        self.damage_alice(2, second)
        self.assertEqual(self.alice.life, 15)

        reverse = self.put_in_hand(self.alice, REVERSE_DAMAGE)
        self.alice.mana_pool.white = 2
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(reverse, damage_source_key=str(first.id))
        self.resolve_batch()

        self.assertEqual(self.alice.life, 21)
        choices = {key: amount for key, _, amount in self.game.damage_source_choices("alice")}
        self.assertEqual(choices[str(first.id)], 0)
        self.assertEqual(choices[str(second.id)], 2)

    def test_second_reverse_damage_does_not_gain_life_again(self) -> None:
        source = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.damage_alice(2, source)

        for _ in range(2):
            reverse = self.put_in_hand(self.alice, REVERSE_DAMAGE)
            self.alice.mana_pool.white = 2
            self.alice.mana_pool.colorless = 1
            self.game.begin_cast(reverse, damage_source_key=str(source.id))
            self.resolve_batch()

        self.assertEqual(self.alice.life, 22)

    def test_simulacrum_restores_life_and_transfers_all_damage(self) -> None:
        first = self.put_in_play(self.bob, GRIZZLY_BEARS)
        second = self.put_in_play(self.bob, HILL_GIANT)
        target = self.put_in_play(self.alice, HILL_GIANT)
        self.damage_alice(1, first)
        self.damage_alice(2, second)

        simulacrum = self.put_in_hand(self.alice, SIMULACRUM)
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(simulacrum)
        self.game.complete_pending_cast((target,))
        self.resolve_batch()

        self.assertEqual(self.alice.life, 20)
        self.assertIn(target, self.alice.graveyard)
        self.assertTrue(
            all(record.remaining == 0 for record in self.game.player_damage_history)
        )

    def test_simulacrum_does_not_undo_damage_triggered_effects(self) -> None:
        # The ledger changes life/damage only; already-produced consequences
        # remain, as required for Hypnotic Specter, Drain Life, and Lich.
        source = self.put_in_play(self.bob, GRIZZLY_BEARS)
        target = self.put_in_play(self.alice, HILL_GIANT)
        self.damage_alice(2, source)
        marker = object()
        self.game.events.append(marker)  # stand-in for an already-fired effect

        simulacrum = self.put_in_hand(self.alice, SIMULACRUM)
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(simulacrum)
        self.game.complete_pending_cast((target,))
        self.resolve_batch()

        self.assertIn(marker, self.game.events)

    def test_simulacrum_is_black_and_cannot_target_protection_from_black(self) -> None:
        knight = self.put_in_play(self.alice, WHITE_KNIGHT)
        simulacrum = self.put_in_hand(self.alice, SIMULACRUM)
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 1

        with self.assertRaisesRegex(RuntimeError, "no legal targets"):
            self.game.begin_cast(simulacrum)

        self.assertIn(knight, self.alice.battlefield)

    def test_transferred_damage_retains_its_color(self) -> None:
        white_source = self.put_in_play(self.bob, WHITE_KNIGHT)
        black_knight = self.put_in_play(self.alice, BLACK_KNIGHT)
        self.damage_alice(2, white_source)

        simulacrum = self.put_in_hand(self.alice, SIMULACRUM)
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(simulacrum)
        self.game.complete_pending_cast((black_knight,))
        self.resolve_batch()

        self.assertEqual(black_knight.damage, 0)
        self.assertIn(black_knight, self.alice.battlefield)

    def test_life_loss_and_mana_burn_are_not_in_the_damage_ledger(self) -> None:
        self.alice.life -= 3
        self.alice.mana_pool.colorless = 2
        self.game._empty_mana_pools()

        self.assertEqual(self.game.damage_source_choices(self.alice.id), [])

    def test_reverse_damage_can_prevent_and_gain_from_current_damage(self) -> None:
        source = self.put_in_play(self.bob, GRIZZLY_BEARS)
        reverse = self.put_in_hand(self.alice, REVERSE_DAMAGE)
        self.alice.mana_pool.white = 2
        self.alice.mana_pool.colorless = 1
        self.game.pause_for_damage_windows = True
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(
            self.alice, 2, source.name, source_card=source
        )
        self.game._resolve_damage_incident()

        self.game.begin_cast(reverse, damage_source_key=str(source.id))
        while self.game.pending_damage is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.assertEqual(self.alice.life, 22)
        self.assertIn(reverse, self.alice.graveyard)
        self.assertEqual(self.game.resolved_damage_incidents[-1].total_remaining, 0)

    def test_simulacrum_can_transfer_current_prevention_window_damage(self) -> None:
        source = self.put_in_play(self.bob, GRIZZLY_BEARS)
        target = self.put_in_play(self.alice, HILL_GIANT)
        simulacrum = self.put_in_hand(self.alice, SIMULACRUM)
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 1
        self.game.pause_for_damage_windows = True
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(
            self.alice, 2, source.name, source_card=source
        )
        self.game._resolve_damage_incident()

        self.game.begin_cast(simulacrum)
        self.game.complete_pending_cast((target,))
        while self.game.pending_damage is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.assertEqual(self.alice.life, 20)
        self.assertEqual(target.damage, 2)
        self.assertIn(simulacrum, self.alice.graveyard)


if __name__ == "__main__":
    unittest.main()
