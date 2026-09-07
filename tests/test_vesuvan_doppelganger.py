import unittest

from beta_magic import (
    ANIMATE_ARTIFACT,
    BLUE_WARD,
    CLONE,
    CLOCKWORK_BEAST,
    FOREST,
    GAEAS_LIEGE,
    GRIZZLY_BEARS,
    HILL_GIANT,
    PHANTASMAL_FORCES,
    RESURRECTION,
    SOL_RING,
    VESUVAN_DOPPELGANGER,
    Card,
    CardType,
    Color,
    ContinuousEffect,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class VesuvanDoppelgangerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("b", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player, definition, zone=Zone.BATTLEFIELD, *, token=False):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=zone,
            is_token=token,
        )
        player.cards_in(zone).append(card)
        return card

    def resolve(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def cast_doppelganger(self, target: Card) -> Card:
        doppelganger = self.card(
            self.alice, VESUVAN_DOPPELGANGER, Zone.HAND
        )
        self.alice.mana_pool.blue = 2
        self.alice.mana_pool.colorless = 3
        self.game.begin_cast(doppelganger)
        self.game.complete_pending_cast((target,))
        self.resolve()
        return doppelganger

    def begin_upkeep(self) -> None:
        self.game._enter_phase(TurnPhase.UPKEEP)

    def test_initial_copy_keeps_blue_but_copies_other_characteristics(self) -> None:
        giant = self.card(self.bob, HILL_GIANT)
        giant.color_override = Color.BLACK
        giant.tapped = True
        giant.damage = 2

        doppelganger = self.cast_doppelganger(giant)

        self.assertEqual(doppelganger.name, "Hill Giant")
        self.assertEqual(doppelganger.definition.mana_cost, HILL_GIANT.mana_cost)
        self.assertEqual(doppelganger.definition.subtypes, HILL_GIANT.subtypes)
        self.assertEqual(
            self.game.card_colors(doppelganger), frozenset({Color.BLUE})
        )
        self.assertEqual(
            (self.game.creature_power(doppelganger), self.game.creature_toughness(doppelganger)),
            (3, 3),
        )
        self.assertFalse(doppelganger.tapped)
        self.assertEqual(doppelganger.damage, 0)
        self.assertTrue(doppelganger.definition.is_vesuvan_doppelganger)

    def test_initial_copy_rejects_animation_and_blue_protection(self) -> None:
        ring = self.card(self.bob, SOL_RING)
        animation = self.card(self.bob, ANIMATE_ARTIFACT)
        animation.enchanted_card_id = ring.id
        bear = self.card(self.bob, GRIZZLY_BEARS)
        ward = self.card(self.bob, BLUE_WARD)
        ward.enchanted_card_id = bear.id
        spell = self.card(self.alice, VESUVAN_DOPPELGANGER, Zone.HAND)
        self.alice.mana_pool.blue = 2
        self.alice.mana_pool.colorless = 3

        with self.assertRaisesRegex(RuntimeError, "no legal targets"):
            self.game.begin_cast(spell)

    def test_upkeep_can_keep_current_form_and_is_offered_only_once(self) -> None:
        bear = self.card(self.bob, GRIZZLY_BEARS)
        self.card(self.bob, HILL_GIANT)
        doppelganger = self.cast_doppelganger(bear)

        self.begin_upkeep()
        self.assertEqual(len(self.game.pending_doppelganger_choices), 1)
        view = GameViewModel(self.game)
        self.assertTrue(view.state["canChooseDoppelganger"])
        self.game.choose_doppelganger_creature(self.alice.id, None)

        self.assertEqual(doppelganger.name, "Grizzly Bears")
        self.assertFalse(self.game.pending_doppelganger_choices)

    def test_switch_requires_a_different_creature(self) -> None:
        bear = self.card(self.bob, GRIZZLY_BEARS)
        giant = self.card(self.bob, HILL_GIANT)
        doppelganger = self.cast_doppelganger(bear)

        self.begin_upkeep()
        choice = self.game.pending_doppelganger_choices[0]
        self.assertNotIn(bear.id, choice.candidate_ids)
        self.assertNotIn(doppelganger.id, choice.candidate_ids)
        self.assertIn(giant.id, choice.candidate_ids)

    def test_switch_resets_form_counters_but_keeps_external_state(self) -> None:
        beast = self.card(self.bob, CLOCKWORK_BEAST)
        giant = self.card(self.bob, HILL_GIANT)
        doppelganger = self.cast_doppelganger(beast)
        self.assertEqual(doppelganger.counters, {})
        doppelganger.counters["+1/+0"] = 4
        doppelganger.plus_one_counters = 2
        doppelganger.damage = 1
        doppelganger.tapped = True
        self.game.temporary_creature_effects[doppelganger.id] = [
            ContinuousEffect(power=1, toughness=1)
        ]

        self.begin_upkeep()
        self.game.choose_doppelganger_creature(self.alice.id, giant)

        self.assertEqual(doppelganger.counters, {})
        self.assertEqual(doppelganger.plus_one_counters, 0)
        self.assertEqual(doppelganger.damage, 1)
        self.assertTrue(doppelganger.tapped)
        self.assertEqual(self.game.creature_power(doppelganger), 4)
        self.assertEqual(self.game.creature_toughness(doppelganger), 4)

    def test_switching_away_avoids_old_upkeep_cost(self) -> None:
        forces = self.card(self.bob, PHANTASMAL_FORCES)
        giant = self.card(self.bob, HILL_GIANT)
        self.cast_doppelganger(forces)

        self.begin_upkeep()
        self.assertFalse(self.game.timed_events)
        self.game.choose_doppelganger_creature(self.alice.id, giant)

        self.assertFalse(self.game.timed_events)

    def test_switching_into_creature_adds_its_upkeep_cost_immediately(self) -> None:
        bear = self.card(self.bob, GRIZZLY_BEARS)
        forces = self.card(self.bob, PHANTASMAL_FORCES)
        doppelganger = self.cast_doppelganger(bear)

        self.begin_upkeep()
        self.game.choose_doppelganger_creature(self.alice.id, forces)

        self.assertEqual(len(self.game.timed_events), 1)
        self.assertEqual(self.game.timed_events[0].source_id, doppelganger.id)
        self.assertEqual(self.game.timed_events[0].effect.mana_cost.compact, "U")

    def test_switching_from_gaeas_liege_ends_its_land_changes(self) -> None:
        liege = self.card(self.bob, GAEAS_LIEGE)
        giant = self.card(self.bob, HILL_GIANT)
        self.card(self.alice, FOREST)
        forest = self.card(self.bob, FOREST)
        doppelganger = self.cast_doppelganger(liege)
        doppelganger.entered_battlefield_turn = 0
        self.game.activate_ability(self.alice.id, doppelganger, 0)
        self.game.complete_pending_activation((forest,))
        self.resolve()
        self.assertIn(doppelganger.id, forest.land_type_marks)

        self.begin_upkeep()
        self.game.choose_doppelganger_creature(self.alice.id, giant)

        self.assertNotIn(doppelganger.id, forest.land_type_marks)

    def test_copying_a_clone_copies_what_clone_is_currently_copying(self) -> None:
        bear = self.card(self.bob, GRIZZLY_BEARS)
        clone = self.card(self.bob, CLONE)
        self.game._copy_creature_definition(clone, bear)
        doppelganger = self.cast_doppelganger(clone)

        self.assertEqual(doppelganger.name, "Grizzly Bears")
        self.assertTrue(doppelganger.definition.is_vesuvan_doppelganger)
        self.assertEqual(
            self.game.card_colors(doppelganger), frozenset({Color.BLUE})
        )

    def test_clone_of_doppelganger_keeps_the_upkeep_switch_ability(self) -> None:
        bear = self.card(self.bob, GRIZZLY_BEARS)
        self.card(self.bob, HILL_GIANT)
        doppelganger = self.cast_doppelganger(bear)
        clone = self.card(self.alice, CLONE, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3
        self.game.begin_cast(clone)
        self.game.complete_pending_cast((doppelganger,))
        self.resolve()

        self.assertEqual(clone.name, "Grizzly Bears")
        self.assertTrue(clone.definition.is_vesuvan_doppelganger)
        self.assertEqual(self.game.card_colors(clone), frozenset({Color.BLUE}))
        self.begin_upkeep()
        self.assertEqual(len(self.game.pending_doppelganger_choices), 2)

    def test_artifact_creature_form_remains_an_artifact(self) -> None:
        beast = self.card(self.bob, CLOCKWORK_BEAST)

        doppelganger = self.cast_doppelganger(beast)

        self.assertIn(CardType.ARTIFACT, self.game.card_types(doppelganger))
        self.assertIn(CardType.CREATURE, self.game.card_types(doppelganger))

    def test_copying_token_still_produces_a_card(self) -> None:
        token = self.card(self.bob, GRIZZLY_BEARS, token=True)
        doppelganger = self.cast_doppelganger(token)

        self.assertFalse(doppelganger.is_token)
        self.game._move_card(doppelganger, Zone.HAND)
        self.assertIs(doppelganger.definition, VESUVAN_DOPPELGANGER)

    def test_resurrection_requires_a_fresh_initial_copy_choice(self) -> None:
        bear = self.card(self.bob, GRIZZLY_BEARS)
        doppelganger = self.card(
            self.alice, VESUVAN_DOPPELGANGER, Zone.GRAVEYARD
        )
        resurrection = self.card(self.alice, RESURRECTION, Zone.HAND)
        self.alice.mana_pool.white = 2
        self.alice.mana_pool.colorless = 2
        self.game.begin_cast(resurrection)
        self.game.complete_pending_cast((doppelganger,))
        self.resolve()

        self.assertTrue(self.game.pending_creature_copy_choices)
        self.game.choose_clone_creature(self.alice.id, bear)

        self.assertIn(doppelganger, self.alice.battlefield)
        self.assertTrue(doppelganger.definition.is_vesuvan_doppelganger)


if __name__ == "__main__":
    unittest.main()
