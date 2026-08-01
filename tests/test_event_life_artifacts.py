import unittest

from beta_magic import (
    CRYSTAL_ROD,
    EVENT_LIFE_ARTIFACTS,
    IRON_STAR,
    IVORY_CUP,
    LUCKY_CHARMS,
    SOUL_NET,
    THRONE_OF_BONE,
    WOODEN_SPHERE,
    Card,
    Color,
    DestructionIncident,
    DestructionResolutionStep,
    DestructionTarget,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRAY_OGRE, GRIZZLY_BEARS, LIGHTNING_BOLT


class EventLifeArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState("alice", "Alice")
        self.bob = PlayerState("bob", "Bob")
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

    def cast_bolt(self, caster: PlayerState, target) -> Card:
        bolt = self.put_in_hand(caster, LIGHTNING_BOLT)
        caster.mana_pool.red += 1
        pending = self.game.begin_cast(bolt)
        self.assertIsNotNone(pending)
        self.game.complete_pending_cast((target,))
        return bolt

    def pass_current_priority(self) -> None:
        index = self.game.priority_player_index
        self.assertIsNotNone(index)
        self.game.pass_priority(self.game.players[index].id)

    def resolve_current_batch(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            self.pass_current_priority()

    def test_card_cycle_and_event_abilities(self) -> None:
        self.assertEqual(
            LUCKY_CHARMS,
            (
                THRONE_OF_BONE,
                WOODEN_SPHERE,
                IVORY_CUP,
                IRON_STAR,
                CRYSTAL_ROD,
            ),
        )
        self.assertEqual(EVENT_LIFE_ARTIFACTS, LUCKY_CHARMS + (SOUL_NET,))
        self.assertEqual(
            [
                charm.activated_abilities[0].spell_color
                for charm in LUCKY_CHARMS
            ],
            [
                Color.BLACK,
                Color.GREEN,
                Color.WHITE,
                Color.RED,
                Color.BLUE,
            ],
        )
        self.assertTrue(SOUL_NET.activated_abilities[0].creature_death)

    def test_matching_spell_opens_optional_paid_fast_effect(self) -> None:
        star = self.put_in_play(self.alice, IRON_STAR)
        self.alice.mana_pool.colorless = 1
        self.cast_bolt(self.alice, self.bob)

        self.assertEqual(len(self.game.event_opportunities), 1)
        self.game.validate()
        self.assertFalse(self.game.can_activate_ability(self.alice.id, star, 0))

        self.pass_current_priority()
        self.assertTrue(self.game.can_activate_ability(self.alice.id, star, 0))
        self.game.activate_ability(self.alice.id, star, 0)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertFalse(self.game.can_activate_ability(self.alice.id, star, 0))

        self.resolve_current_batch()

        self.assertEqual(self.alice.life, 21)
        self.assertEqual(self.bob.life, 17)
        self.assertEqual(self.game.event_opportunities, [])

    def test_wrong_color_charm_cannot_catch_spell(self) -> None:
        cup = self.put_in_play(self.alice, IVORY_CUP)
        self.alice.mana_pool.colorless = 1

        self.cast_bolt(self.alice, self.bob)

        self.assertEqual(self.game.event_opportunities, [])
        self.assertFalse(self.game.can_activate_ability(self.alice.id, cup, 0))

    def test_successfully_cast_permanent_opens_an_event_window(self) -> None:
        star = self.put_in_play(self.alice, IRON_STAR)
        ogre = self.put_in_hand(self.alice, GRAY_OGRE)
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = 3

        self.game.cast_creature(ogre)

        self.assertIn(ogre, self.alice.battlefield)
        self.assertEqual(len(self.game.event_opportunities), 1)
        self.pass_current_priority()
        self.game.activate_ability(self.alice.id, star, 0)
        self.resolve_current_batch()
        self.assertEqual(self.alice.life, 21)

    def test_multiple_artifacts_can_each_catch_one_spell(self) -> None:
        first = self.put_in_play(self.alice, IRON_STAR)
        second = self.put_in_play(self.alice, IRON_STAR)
        self.alice.mana_pool.colorless = 2
        self.cast_bolt(self.alice, self.bob)
        self.pass_current_priority()

        self.game.activate_ability(self.alice.id, first, 0)
        self.pass_current_priority()
        self.game.activate_ability(self.alice.id, second, 0)
        self.resolve_current_batch()

        self.assertEqual(self.alice.life, 22)

    def test_one_artifact_can_catch_two_distinct_spell_events(self) -> None:
        star = self.put_in_play(self.alice, IRON_STAR)
        self.alice.mana_pool.colorless = 2
        self.cast_bolt(self.alice, self.bob)
        self.pass_current_priority()
        self.game.activate_ability(self.alice.id, star, 0)

        # Bob now has priority and adds another red spell to the same batch.
        self.cast_bolt(self.bob, self.alice)
        self.assertTrue(self.game.can_activate_ability(self.alice.id, star, 0))
        self.game.activate_ability(self.alice.id, star, 0)
        self.resolve_current_batch()

        self.assertEqual(self.alice.life, 19)
        self.assertEqual(self.bob.life, 17)

    def test_soul_net_catches_a_creature_reaching_graveyard(self) -> None:
        net = self.put_in_play(self.alice, SOUL_NET)
        creature = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.alice.mana_pool.colorless = 1

        self.game.put_permanent_in_graveyard(creature)

        self.assertEqual(len(self.game.event_opportunities), 1)
        self.assertTrue(self.game.can_activate_ability(self.alice.id, net, 0))
        self.game.activate_ability(self.alice.id, net, 0)
        self.resolve_current_batch()

        self.assertEqual(self.alice.life, 21)

    def test_soul_net_does_not_catch_exile_or_regeneration(self) -> None:
        net = self.put_in_play(self.alice, SOUL_NET)
        creature = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.alice.mana_pool.colorless = 1

        self.game._move_card(creature, Zone.EXILE)

        self.assertEqual(self.game.event_opportunities, [])
        self.assertFalse(self.game.can_activate_ability(self.alice.id, net, 0))

        regenerated = self.put_in_play(self.bob, GRIZZLY_BEARS)
        incident = DestructionIncident(
            [DestructionTarget(regenerated.id, regenerated.name)]
        )
        incident.step = DestructionResolutionStep.REGENERATION
        incident.regenerated_card_ids.add(regenerated.id)
        self.game.pending_destruction = incident
        self.game._finish_destruction_incident()

        self.assertIn(regenerated, self.bob.battlefield)
        self.assertEqual(self.game.event_opportunities, [])

    def test_soul_net_event_waits_until_lethal_damage_is_resolved(self) -> None:
        net = self.put_in_play(self.alice, SOUL_NET)
        creature = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.alice.mana_pool.colorless = 1
        self.cast_bolt(self.bob, creature)

        self.resolve_current_batch()

        self.assertIn(creature, self.bob.graveyard)
        self.assertEqual(len(self.game.event_opportunities), 1)
        self.assertTrue(self.game.can_activate_ability(self.alice.id, net, 0))


if __name__ == "__main__":
    unittest.main()
