import unittest

from beta_magic import (
    ANIMATE_ARTIFACT,
    ANIMATE_WALL,
    CASTLE,
    MOX_SAPPHIRE,
    WRATH_OF_GOD,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import (
    GRIZZLY_BEARS,
    OBSIANUS_GOLEM,
    SOL_RING,
    WALL_OF_BONE,
    WALL_OF_WOOD,
)


class AnimationAndWrathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 20)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 20)
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

    @staticmethod
    def hand(player, definition):
        card = Card(definition, owner_id=player.id, zone=Zone.HAND)
        player.hand.append(card)
        return card

    def aura(self, definition, target):
        aura = self.hand(self.alice, definition)
        self.alice.mana_pool.white = 1
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3
        self.game.cast_enchantment(aura, target)
        return aura

    def resolve_stack(self):
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_animate_wall_allows_even_zero_power_wall_to_attack(self):
        wall = self.permanent(self.alice, WALL_OF_WOOD)
        aura = self.aura(ANIMATE_WALL, wall)

        self.game.begin_combat()
        self.game.declare_attackers([wall])

        self.assertIn(wall, self.game.combat.attackers)
        self.assertEqual((self.game.creature_power(wall), self.game.creature_toughness(wall)), (0, 3))
        self.game._move_card(aura, Zone.GRAVEYARD)
        self.game.combat = None
        self.game.attacks_this_turn = 0
        self.game.begin_combat()
        with self.assertRaisesRegex(ValueError, "Wall and cannot attack"):
            self.game.declare_attackers([wall])

    def test_animate_artifact_grants_creature_type_and_mana_value_stats(self):
        ring = self.permanent(self.alice, SOL_RING)
        aura = self.aura(ANIMATE_ARTIFACT, ring)

        self.assertEqual(
            self.game.card_types(ring),
            frozenset({CardType.ARTIFACT, CardType.CREATURE}),
        )
        self.assertEqual(
            (self.game.creature_power(ring), self.game.creature_toughness(ring)),
            (1, 1),
        )
        self.assertEqual(len(self.game.activated_abilities(ring)), 1)

        self.game._move_card(aura, Zone.GRAVEYARD)
        self.assertEqual(self.game.card_types(ring), frozenset({CardType.ARTIFACT}))

    def test_animate_artifact_rejects_printed_and_animated_creatures(self):
        golem = self.permanent(self.bob, OBSIANUS_GOLEM)
        ring = self.permanent(self.bob, SOL_RING)
        first = self.hand(self.alice, ANIMATE_ARTIFACT)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3
        self.assertNotIn(golem, self.game.legal_enchantment_targets(first))
        self.alice.hand.remove(first)

        self.aura(ANIMATE_ARTIFACT, ring)
        second = self.hand(self.alice, ANIMATE_ARTIFACT)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3
        self.assertNotIn(ring, self.game.legal_enchantment_targets(second))

    def test_zero_cost_artifact_survives_if_castle_keeps_toughness_positive(self):
        self.permanent(self.alice, CASTLE)
        mox = self.permanent(self.alice, MOX_SAPPHIRE)
        self.aura(ANIMATE_ARTIFACT, mox)

        self.assertEqual(self.game.creature_toughness(mox), 2)
        self.assertEqual(mox.zone, Zone.BATTLEFIELD)

    def test_newly_played_animated_artifact_cannot_attack_but_keeps_abilities(self):
        ring = self.permanent(
            self.alice, SOL_RING, entered_turn=self.game.turn_number
        )
        self.aura(ANIMATE_ARTIFACT, ring)

        self.assertTrue(self.game.can_activate_ability(self.alice.id, ring, 0))
        self.game.activate_ability(self.alice.id, ring, 0)
        self.assertEqual(self.alice.mana_pool.colorless, 2)
        ring.tapped = False
        self.game.begin_combat()
        with self.assertRaisesRegex(ValueError, "did not begin the turn"):
            self.game.declare_attackers([ring])

    def test_wrath_destroys_all_creatures_without_regeneration(self):
        bear = self.permanent(self.alice, GRIZZLY_BEARS)
        skeleton = self.permanent(self.bob, WALL_OF_BONE)
        ring = self.permanent(self.bob, SOL_RING)
        self.aura(ANIMATE_ARTIFACT, ring)
        spell = self.hand(self.alice, WRATH_OF_GOD)
        self.game.pause_for_damage_windows = True
        self.alice.mana_pool.white = 2
        self.alice.mana_pool.colorless = 2

        self.game.begin_cast(spell)
        self.resolve_stack()

        self.assertEqual(
            {bear.zone, skeleton.zone, ring.zone}, {Zone.GRAVEYARD}
        )
        incident = self.game.resolved_destruction_incidents[-1]
        self.assertEqual(
            {target.card_id for target in incident.targets},
            {bear.id, skeleton.id, ring.id},
        )
        self.assertTrue(
            all(
                not target.regeneration_allowed
                for target in incident.targets
            )
        )


if __name__ == "__main__":
    unittest.main()
