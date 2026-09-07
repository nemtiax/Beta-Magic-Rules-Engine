import unittest

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs import (
    ANIMATE_DEAD,
    CLOCKWORK_BEAST,
    CLONE,
    FOREST,
    GRIZZLY_BEARS,
    HILL_GIANT,
    UNSUMMON,
    VESUVAN_DOPPELGANGER,
    WHITE_KNIGHT,
)


class AnimateDeadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState("a", "Alice")
        self.bob = PlayerState("b", "Bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    @staticmethod
    def add(player, definition, zone=Zone.BATTLEFIELD):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=zone,
        )
        player.cards_in(zone).append(card)
        return card

    def cast(self, target):
        aura = self.add(self.alice, ANIMATE_DEAD, Zone.HAND)
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 1
        self.game.priority_player_index = 0
        self.game.begin_cast(aura)
        self.game.complete_pending_cast((target,))
        self.resolve()
        return aura

    def resolve(self):
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition_and_graveyard_targeting(self) -> None:
        own_creature = self.add(self.alice, GRIZZLY_BEARS, Zone.GRAVEYARD)
        opposing_knight = self.add(self.bob, WHITE_KNIGHT, Zone.GRAVEYARD)
        land = self.add(self.bob, FOREST, Zone.GRAVEYARD)
        aura = self.add(self.alice, ANIMATE_DEAD, Zone.HAND)

        self.assertEqual(ANIMATE_DEAD.mana_cost.compact, "1B")
        self.assertEqual(
            set(self.game.legal_targets_for(aura)),
            {own_creature, opposing_knight},
        )
        self.assertNotIn(land, self.game.legal_targets_for(aura))

    def test_white_knight_can_be_animated_despite_protection(self) -> None:
        knight = self.add(self.bob, WHITE_KNIGHT, Zone.GRAVEYARD)

        aura = self.cast(knight)

        self.assertEqual(knight.zone, Zone.BATTLEFIELD)
        self.assertEqual(knight.controller_id, self.alice.id)
        self.assertEqual(aura.enchanted_card_id, knight.id)
        self.assertEqual(self.game.creature_power(knight), 1)
        self.assertEqual(self.game.creature_toughness(knight), 2)
        self.assertEqual(knight.definition.mana_cost.compact, "WW")
        self.assertTrue(self.game.has_summoning_sickness(knight))

    def test_removing_animate_dead_also_destroys_its_creature(self) -> None:
        bear = self.add(self.bob, GRIZZLY_BEARS, Zone.GRAVEYARD)
        aura = self.cast(bear)

        self.game.put_permanent_in_graveyard(aura)

        self.assertEqual(aura.zone, Zone.GRAVEYARD)
        self.assertEqual(bear.zone, Zone.GRAVEYARD)
        self.assertEqual(bear.controller_id, self.bob.id)

    def test_unsummoning_creature_returns_it_to_owner_and_discards_aura(self) -> None:
        bear = self.add(self.bob, GRIZZLY_BEARS, Zone.GRAVEYARD)
        aura = self.cast(bear)
        unsummon = self.add(self.alice, UNSUMMON, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.game.priority_player_index = 0

        self.game.begin_cast(unsummon)
        self.game.complete_pending_cast((bear,))
        self.resolve()

        self.assertEqual(bear.zone, Zone.HAND)
        self.assertIn(bear, self.bob.hand)
        self.assertEqual(aura.zone, Zone.GRAVEYARD)

    def test_clockwork_beast_returns_fully_wound_with_minus_one_power(self) -> None:
        beast = self.add(self.alice, CLOCKWORK_BEAST, Zone.GRAVEYARD)

        self.cast(beast)

        self.assertEqual(beast.counters, dict(CLOCKWORK_BEAST.initial_counters))
        self.assertEqual(self.game.creature_power(beast), 6)
        self.assertEqual(self.game.creature_toughness(beast), 4)

    def test_target_leaving_graveyard_before_resolution_fizzles(self) -> None:
        bear = self.add(self.bob, GRIZZLY_BEARS, Zone.GRAVEYARD)
        aura = self.add(self.alice, ANIMATE_DEAD, Zone.HAND)
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(aura)
        self.game.complete_pending_cast((bear,))

        self.game._move_card(bear, Zone.HAND)
        self.resolve()

        self.assertEqual(aura.zone, Zone.GRAVEYARD)
        self.assertEqual(bear.zone, Zone.HAND)

    def test_animating_clone_uses_copy_choice_then_applies_minus_one(self) -> None:
        bear = self.add(self.bob, GRIZZLY_BEARS)
        clone = self.add(self.alice, CLONE, Zone.GRAVEYARD)

        aura = self.cast(clone)

        self.assertTrue(self.game.pending_creature_copy_choices)
        self.assertEqual(aura.zone, Zone.BATTLEFIELD)
        self.game.choose_clone_creature(self.alice.id, bear)
        self.assertEqual(clone.zone, Zone.BATTLEFIELD)
        self.assertEqual(aura.enchanted_card_id, clone.id)
        self.assertEqual(self.game.creature_power(clone), 1)

    def test_animating_clone_without_copy_candidate_fails_cleanly(self) -> None:
        clone = self.add(self.alice, CLONE, Zone.GRAVEYARD)

        aura = self.cast(clone)

        self.assertFalse(self.game.pending_creature_copy_choices)
        self.assertEqual(clone.zone, Zone.GRAVEYARD)
        self.assertEqual(aura.zone, Zone.GRAVEYARD)

    def test_clone_copying_an_animate_dead_creature_dies(self) -> None:
        bear = self.add(self.bob, GRIZZLY_BEARS, Zone.GRAVEYARD)
        self.cast(bear)
        clone = self.add(self.alice, CLONE, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3
        self.game.priority_player_index = 0

        self.game.begin_cast(clone)
        self.game.complete_pending_cast((bear,))
        self.resolve()

        self.assertEqual(clone.zone, Zone.GRAVEYARD)

    def test_doppelganger_switching_to_animate_dead_creature_dies(self) -> None:
        animated_bear = self.add(self.bob, GRIZZLY_BEARS, Zone.GRAVEYARD)
        self.cast(animated_bear)
        ordinary = self.add(self.bob, HILL_GIANT)
        doppelganger = self.add(self.alice, VESUVAN_DOPPELGANGER)
        self.game._copy_creature_definition(doppelganger, ordinary)
        self.game._queue_doppelganger_choices()

        self.game.choose_doppelganger_creature(
            self.alice.id, animated_bear
        )

        self.assertEqual(doppelganger.zone, Zone.GRAVEYARD)


if __name__ == "__main__":
    unittest.main()
