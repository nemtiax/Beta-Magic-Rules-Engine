import unittest

from beta_magic import (
    CONTROL_ENCHANTMENTS,
    CONTROL_MAGIC,
    STEAL_ARTIFACT,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS, OBSIANUS_GOLEM, SOL_RING


class ControlEnchantmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 12
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 12
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(player: PlayerState, definition) -> Card:
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        player.battlefield.append(card)
        return card

    @staticmethod
    def put_in_hand(player: PlayerState, definition) -> Card:
        card = Card(definition, owner_id=player.id, zone=Zone.HAND)
        player.hand.append(card)
        return card

    def cast_aura(
        self, player: PlayerState, definition, target: Card
    ) -> Card:
        self.game.active_player_index = self.game.players.index(player)
        aura = self.put_in_hand(player, definition)
        player.mana_pool.blue = 2
        player.mana_pool.colorless = 2
        self.game.cast_enchantment(aura, target)
        return aura

    def test_definitions_target_creatures_and_artifacts(self) -> None:
        self.assertEqual(
            CONTROL_ENCHANTMENTS,
            (CONTROL_MAGIC, STEAL_ARTIFACT),
        )
        self.assertEqual(CONTROL_MAGIC.mana_cost.compact, "2UU")
        self.assertEqual(STEAL_ARTIFACT.mana_cost.compact, "2UU")

        creature = self.put_in_play(self.bob, GRIZZLY_BEARS)
        artifact = self.put_in_play(self.bob, SOL_RING)
        artifact_creature = self.put_in_play(self.bob, OBSIANUS_GOLEM)

        self.assertTrue(CONTROL_MAGIC.target_requirement.accepts(creature))
        self.assertFalse(CONTROL_MAGIC.target_requirement.accepts(artifact))
        self.assertTrue(STEAL_ARTIFACT.target_requirement.accepts(artifact))
        self.assertTrue(
            STEAL_ARTIFACT.target_requirement.accepts(artifact_creature)
        )
        self.assertFalse(STEAL_ARTIFACT.target_requirement.accepts(creature))

    def test_control_magic_changes_controller_but_not_owner(self) -> None:
        creature = self.put_in_play(self.bob, GRIZZLY_BEARS)

        aura = self.cast_aura(self.alice, CONTROL_MAGIC, creature)

        self.assertEqual(creature.owner_id, self.bob.id)
        self.assertEqual(creature.base_controller_id, self.bob.id)
        self.assertEqual(creature.controller_id, self.alice.id)
        self.assertIn(creature, self.alice.battlefield)
        self.assertNotIn(creature, self.bob.battlefield)
        self.assertEqual(aura.controller_id, self.alice.id)
        self.assertIn(aura, self.alice.battlefield)
        self.game.validate()

    def test_removing_aura_restores_baseline_controller(self) -> None:
        creature = self.put_in_play(self.bob, GRIZZLY_BEARS)
        aura = self.cast_aura(self.alice, CONTROL_MAGIC, creature)

        self.game.put_permanent_in_graveyard(aura)

        self.assertEqual(creature.controller_id, self.bob.id)
        self.assertIn(creature, self.bob.battlefield)
        self.assertIn(aura, self.alice.graveyard)
        self.game.validate()

    def test_newest_control_aura_wins_and_removal_reveals_previous_one(
        self,
    ) -> None:
        creature = self.put_in_play(self.bob, GRIZZLY_BEARS)
        alice_aura = self.cast_aura(self.alice, CONTROL_MAGIC, creature)
        bob_aura = self.cast_aura(self.bob, CONTROL_MAGIC, creature)

        self.assertEqual(creature.controller_id, self.bob.id)

        self.game.put_permanent_in_graveyard(bob_aura)
        self.assertEqual(creature.controller_id, self.alice.id)

        self.game.put_permanent_in_graveyard(alice_aura)
        self.assertEqual(creature.controller_id, self.bob.id)
        self.game.validate()

    def test_stolen_permanent_moves_to_owners_zone(self) -> None:
        creature = self.put_in_play(self.bob, GRIZZLY_BEARS)
        aura = self.cast_aura(self.alice, CONTROL_MAGIC, creature)

        self.game._move_card(creature, Zone.HAND)
        self.game.check_state_based_actions()

        self.assertIn(creature, self.bob.hand)
        self.assertEqual(creature.controller_id, self.bob.id)
        self.assertIn(aura, self.alice.graveyard)

    def test_control_change_obeys_summoning_sickness_and_same_turn_regain(
        self,
    ) -> None:
        creature = self.put_in_play(self.bob, GRIZZLY_BEARS)
        creature.controller_at_turn_start_id = self.bob.id
        aura = self.cast_aura(self.alice, CONTROL_MAGIC, creature)

        self.assertTrue(self.game.has_summoning_sickness(creature))

        self.game.put_permanent_in_graveyard(aura)
        self.assertFalse(self.game.has_summoning_sickness(creature))

    def test_controller_can_use_stolen_artifact(self) -> None:
        ring = self.put_in_play(self.bob, SOL_RING)
        self.cast_aura(self.alice, STEAL_ARTIFACT, ring)

        self.game.activate_ability(self.alice.id, ring, 0)

        self.assertTrue(ring.tapped)
        self.assertEqual(self.alice.mana_pool.colorless, 2)


if __name__ == "__main__":
    unittest.main()
