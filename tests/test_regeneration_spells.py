import unittest

from beta_magic.card_defs.white import DEATH_WARD, DISENCHANT
from beta_magic.card_defs.red import LIGHTNING_BOLT
from beta_magic.card_defs.artifacts import LIVING_WALL
from beta_magic import (
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs.green import GRIZZLY_BEARS
from beta_magic.damage import DamageIncidentKind, DamageResolutionStep
from beta_magic.destruction import DestructionResolutionStep


class RegenerationSpellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 20
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(player: PlayerState, definition) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    @staticmethod
    def put_in_hand(player: PlayerState, definition) -> Card:
        card = Card(definition, player.id, zone=Zone.HAND)
        player.hand.append(card)
        return card

    def test_death_ward_can_answer_lethal_damage_in_same_batch(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        ward = self.put_in_hand(self.bob, DEATH_WARD)
        self.alice.mana_pool.red = 1
        self.bob.mana_pool.white = 1

        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((bear,))
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        self.game.begin_cast(ward)
        self.game.complete_pending_cast((bear,))
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.assertIn(bear, self.bob.battlefield)
        self.assertTrue(bear.tapped)
        self.assertEqual(bear.damage, 0)
        self.assertIn(bolt, self.alice.graveyard)
        self.assertIn(ward, self.bob.graveyard)

    def test_death_ward_does_not_override_tunnels_regeneration_ban(self) -> None:
        from beta_magic.card_defs.red import TUNNEL
        from beta_magic.card_defs.green import WALL_OF_BRAMBLES

        wall = self.put_in_play(self.bob, WALL_OF_BRAMBLES)
        tunnel = self.put_in_hand(self.alice, TUNNEL)
        ward = self.put_in_hand(self.bob, DEATH_WARD)
        self.alice.mana_pool.red = 1
        self.bob.mana_pool.white = 1

        self.game.begin_cast(tunnel)
        self.game.complete_pending_cast((wall,))
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        self.game.begin_cast(ward)
        self.game.complete_pending_cast((wall,))
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.assertIn(wall, self.bob.graveyard)

    def test_death_ward_can_be_cast_in_damage_regeneration_window(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        healthy_bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        ward = self.put_in_hand(self.bob, DEATH_WARD)
        self.bob.mana_pool.white = 1
        self.game.pause_for_damage_windows = True
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(bear, 2, "Test damage")
        self.game._resolve_damage_incident()

        for _ in range(4):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        self.assertIs(
            self.game.pending_damage.step,
            DamageResolutionStep.REGENERATION,
        )

        self.game.pass_priority(self.alice.id)
        self.game.begin_cast(ward)
        self.assertEqual(self.game.legal_targets_for(), [bear])
        self.assertNotIn(healthy_bear, self.game.legal_targets_for())
        self.game.complete_pending_cast((bear,))

        self.assertIs(ward.zone, Zone.STACK)
        self.assertEqual(self.game.interruptible_spell_id, ward.id)
        self.assertIs(
            self.game.players[self.game.priority_player_index], self.alice
        )
        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)

        self.assertIs(ward.zone, Zone.GRAVEYARD)
        self.assertEqual(bear.damage, 0)
        self.assertTrue(bear.tapped)
        self.assertIn(bear.id, self.game.pending_damage.regenerated_card_ids)

    def test_death_ward_can_be_cast_in_destroy_regeneration_window(self) -> None:
        bear = self.put_in_play(self.bob, LIVING_WALL)
        disenchant = self.put_in_hand(self.alice, DISENCHANT)
        ward = self.put_in_hand(self.bob, DEATH_WARD)
        self.alice.mana_pool.white = 2
        self.bob.mana_pool.white = 1
        self.game.pause_for_damage_windows = True

        self.game.begin_cast(disenchant)
        self.game.complete_pending_cast((bear,))
        for _ in range(4):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        self.assertIs(
            self.game.pending_destruction.step,
            DestructionResolutionStep.REGENERATION,
        )

        self.game.pass_priority(self.alice.id)
        self.game.begin_cast(ward)
        self.game.complete_pending_cast((bear,))
        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)

        self.assertIs(ward.zone, Zone.GRAVEYARD)
        self.assertTrue(bear.tapped)
        self.assertIn(
            bear.id, self.game.pending_destruction.regenerated_card_ids
        )


if __name__ == "__main__":
    unittest.main()
