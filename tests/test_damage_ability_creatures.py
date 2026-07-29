import unittest

from beta_magic import (
    Card,
    GameState,
    ORCISH_ARTILLERY,
    PRODIGAL_SORCERER,
    PlayerState,
    Zone,
)
from beta_magic.vanilla_creatures import GRIZZLY_BEARS


class DamageAbilityCreatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = GameState(
            [
                PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 10),
                PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 10),
            ]
        )
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.advance_phase()
        self.alice, self.bob = self.game.players

    def put_in_play(self, player, definition):
        card = Card(
            definition=definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def resolve_batch(self) -> None:
        for player in (self.bob, self.alice):
            self.game.pass_priority(player.id)

    def test_prodigal_sorcerer_targets_creatures_or_players(self) -> None:
        sorcerer = self.put_in_play(self.alice, PRODIGAL_SORCERER)
        target = self.put_in_play(self.bob, GRIZZLY_BEARS)

        pending = self.game.activate_ability(self.alice.id, sorcerer, 0)
        self.assertIsNotNone(pending)
        self.assertFalse(sorcerer.tapped)
        self.assertIn(target, self.game.legal_targets_for())
        self.assertEqual(self.game.legal_player_targets_for(), self.game.players)
        self.game.complete_pending_activation((target,))
        self.assertTrue(sorcerer.tapped)
        self.assertEqual(self.game.priority_player_index, 1)
        self.assertEqual(target.damage, 0)

        self.resolve_batch()
        self.assertEqual(target.damage, 1)

    def test_orcish_artillery_damages_target_and_controller(self) -> None:
        artillery = self.put_in_play(self.alice, ORCISH_ARTILLERY)

        self.game.activate_ability(self.alice.id, artillery, 0)
        self.game.complete_pending_activation((self.bob,))
        self.resolve_batch()

        self.assertEqual(self.bob.life, 18)
        self.assertEqual(self.alice.life, 17)

    def test_tap_abilities_obey_summoning_sickness(self) -> None:
        sorcerer = self.put_in_play(self.alice, PRODIGAL_SORCERER)
        sorcerer.entered_battlefield_turn = self.game.turn_number

        self.assertFalse(
            self.game.can_activate_ability(self.alice.id, sorcerer, 0)
        )
        with self.assertRaisesRegex(RuntimeError, "did not begin the turn"):
            self.game.activate_ability(self.alice.id, sorcerer, 0)

    def test_cancelling_target_selection_does_not_tap_source(self) -> None:
        sorcerer = self.put_in_play(self.alice, PRODIGAL_SORCERER)

        self.game.activate_ability(self.alice.id, sorcerer, 0)
        self.game.cancel_pending_activation()

        self.assertFalse(sorcerer.tapped)
        self.assertEqual(self.game.batch_abilities, [])

    def test_declared_ability_survives_source_leaving_play(self) -> None:
        sorcerer = self.put_in_play(self.alice, PRODIGAL_SORCERER)
        self.game.activate_ability(self.alice.id, sorcerer, 0)
        self.game.complete_pending_activation((self.bob,))
        self.game._move_card(sorcerer, Zone.GRAVEYARD)

        self.resolve_batch()

        self.assertEqual(self.bob.life, 19)


if __name__ == "__main__":
    unittest.main()
