import unittest

from beta_magic import Card, Color, GameState, KeywordAbility, PlayerState, TurnPhase, Zone
from beta_magic.card_defs import (
    BLACK_VISE,
    BLUE_ELEMENTAL_BLAST,
    BOG_WRAITH,
    CONVERSION,
    CRUSADE,
    FOREST,
    GAUNTLET_OF_MIGHT,
    GLOOM,
    GRAY_OGRE,
    GRIZZLY_BEARS,
    HEALING_SALVE,
    HILL_GIANT,
    ISLAND,
    MAGICAL_HACK,
    MOUNTAIN,
    MOX_RUBY,
    SLEIGHT_OF_MIND,
    UNDERGROUND_SEA,
    VOLCANIC_ERUPTION,
)
from beta_magic.ui import GameViewModel


class MagicalHackAndSleightTests(unittest.TestCase):
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

    def resolve_interrupt(self) -> None:
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def cast_word_change(self, player, definition, target, old, new):
        spell = self.add(player, definition, Zone.HAND)
        player.mana_pool.blue += 1
        self.game.priority_player_index = self.game.players.index(player)
        self.game.begin_cast(spell)
        self.game.complete_pending_cast(
            (target,), word_from=old, word_to=new
        )
        self.resolve_interrupt()
        return spell

    def test_definitions_and_target_eligibility(self) -> None:
        conversion = self.add(self.bob, CONVERSION)
        crusade = self.add(self.bob, CRUSADE)
        bear = self.add(self.bob, GRIZZLY_BEARS)
        vise = self.add(self.bob, BLACK_VISE)
        salve = self.add(self.bob, HEALING_SALVE, Zone.HAND)

        hack = self.add(self.alice, MAGICAL_HACK, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.game.begin_cast(hack)
        self.assertIn(conversion, self.game.legal_targets_for())
        self.assertNotIn(bear, self.game.legal_targets_for())
        self.game.cancel_pending_cast()

        sleight = self.add(self.alice, SLEIGHT_OF_MIND, Zone.HAND)
        self.game.begin_cast(sleight)
        self.assertIn(crusade, self.game.legal_targets_for())
        self.assertNotIn(vise, self.game.legal_targets_for())
        self.assertNotIn(salve, self.game.legal_targets_for())

    def test_magical_hack_changes_both_land_conversion_words_selectively(self) -> None:
        conversion = self.add(self.bob, CONVERSION)
        forest = self.add(self.bob, FOREST)
        mountain = self.add(self.bob, MOUNTAIN)

        self.cast_word_change(
            self.alice, MAGICAL_HACK, conversion, "Mountain", "Forest"
        )

        self.assertEqual(self.game.land_subtypes(forest), ("Plains",))
        self.assertEqual(self.game.land_subtypes(mountain), ("Mountain",))

    def test_sleight_changes_continuous_color_word(self) -> None:
        crusade = self.add(self.bob, CRUSADE)
        bear = self.add(self.bob, GRIZZLY_BEARS)

        self.cast_word_change(
            self.alice, SLEIGHT_OF_MIND, crusade, Color.WHITE, Color.GREEN
        )

        self.assertEqual(self.game.creature_power(bear), 3)

    def test_dual_land_land_and_mana_words_change_independently(self) -> None:
        sea = self.add(self.bob, UNDERGROUND_SEA)
        self.cast_word_change(
            self.alice, MAGICAL_HACK, sea, "Island", "Forest"
        )
        self.cast_word_change(
            self.alice, SLEIGHT_OF_MIND, sea, Color.BLUE, Color.GREEN
        )

        self.assertEqual(
            set(self.game.land_subtypes(sea)), {"Forest", "Swamp"}
        )
        self.assertEqual(
            {ability.color for ability in self.game.activated_abilities(sea)},
            {Color.GREEN, Color.BLACK},
        )

    def test_written_mana_color_is_replaceable_but_mana_symbol_is_not(self) -> None:
        mox = self.add(self.bob, MOX_RUBY)
        island = self.add(self.bob, ISLAND)

        self.assertEqual(self.game.current_color_words(mox), (Color.RED,))
        self.assertFalse(self.game.current_color_words(island))
        self.assertFalse(self.game.current_land_words(island))

    def test_repeated_hacks_operate_on_current_wording(self) -> None:
        wraith = self.add(self.bob, BOG_WRAITH)
        self.cast_word_change(
            self.alice, MAGICAL_HACK, wraith, "Swamp", "Forest"
        )
        self.cast_word_change(
            self.alice, MAGICAL_HACK, wraith, "Forest", "Island"
        )

        self.assertIn(
            KeywordAbility.ISLANDWALK,
            self.game.creature_abilities(wraith),
        )

    def test_sleight_on_spell_can_make_its_declared_target_illegal(self) -> None:
        giant = self.add(self.bob, HILL_GIANT)
        blast = self.add(self.alice, BLUE_ELEMENTAL_BLAST, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.game.begin_cast(blast, mode="Destroy permanent")
        self.game.complete_pending_cast((giant,))

        sleight = self.add(self.bob, SLEIGHT_OF_MIND, Zone.HAND)
        self.bob.mana_pool.blue = 1
        self.game.begin_cast(sleight)
        self.game.complete_pending_cast(
            (blast,), word_from=Color.RED, word_to=Color.GREEN
        )
        self.resolve_interrupt()
        self.resolve_interrupt()

        self.assertEqual(giant.zone, Zone.BATTLEFIELD)
        self.assertEqual(blast.zone, Zone.GRAVEYARD)

    def test_chosen_word_disappearing_before_resolution_fizzles(self) -> None:
        conversion = self.add(self.bob, CONVERSION)
        hack = self.add(self.alice, MAGICAL_HACK, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.game.begin_cast(hack)
        self.game.complete_pending_cast(
            (conversion,), word_from="Mountain", word_to="Forest"
        )

        conversion.change_land_word("Mountain", "Island")
        self.resolve_interrupt()

        self.assertEqual(
            conversion.land_word_changes,
            {"Mountain": "Island"},
        )

    def test_ui_chooses_target_then_word_pair(self) -> None:
        conversion = self.add(self.bob, CONVERSION)
        hack = self.add(self.alice, MAGICAL_HACK, Zone.HAND)
        self.alice.mana_pool.blue = 1
        view = GameViewModel(self.game)
        self.game.begin_cast(hack)

        view.toggleCard(str(conversion.id))

        self.assertTrue(view.state["choosingTextWords"])
        self.assertEqual(
            set(view.state["textWordFromChoices"]),
            {"Mountain", "Plains"},
        )
        view.chooseTextWords("Mountain", "Forest")
        self.assertIsNone(self.game.pending_cast)
        self.assertIn(hack, self.game.stack)

    def test_sleight_changes_every_functional_occurrence_on_gauntlet(self) -> None:
        gauntlet = self.add(self.alice, GAUNTLET_OF_MIGHT)
        red_creature = self.add(self.alice, HILL_GIANT)
        green_creature = self.add(self.alice, GRIZZLY_BEARS)
        mountain = self.add(self.alice, MOUNTAIN)

        self.cast_word_change(
            self.alice, SLEIGHT_OF_MIND, gauntlet, Color.RED, Color.GREEN
        )

        self.assertEqual(self.game.creature_power(red_creature), 3)
        self.assertEqual(self.game.creature_power(green_creature), 3)
        self.game.activate_ability(self.alice.id, mountain, 0)
        self.assertEqual(self.alice.mana_pool.red, 1)
        self.assertEqual(self.alice.mana_pool.green, 1)

    def test_chained_sleights_replace_all_current_occurrences(self) -> None:
        gauntlet = self.add(self.bob, GAUNTLET_OF_MIGHT)

        self.cast_word_change(
            self.alice, SLEIGHT_OF_MIND, gauntlet, Color.RED, Color.GREEN
        )
        self.cast_word_change(
            self.alice, SLEIGHT_OF_MIND, gauntlet, Color.GREEN, Color.BLUE
        )

        self.assertIs(gauntlet.color_word_changes[Color.RED], Color.BLUE)
        self.assertIs(gauntlet.color_word_changes[Color.GREEN], Color.BLUE)
        self.assertEqual(self.game.current_color_words(gauntlet), (Color.BLUE,))

    def test_word_change_is_forgotten_after_leaving_play_and_returning(self) -> None:
        wraith = self.add(self.bob, BOG_WRAITH)
        self.cast_word_change(
            self.alice, MAGICAL_HACK, wraith, "Swamp", "Forest"
        )

        self.game._move_card(wraith, Zone.HAND)
        self.assertFalse(wraith.land_word_changes)
        self.game._move_card(wraith, Zone.BATTLEFIELD)

        self.assertIn(
            KeywordAbility.SWAMPWALK,
            self.game.creature_abilities(wraith),
        )
        self.assertNotIn(
            KeywordAbility.FORESTWALK,
            self.game.creature_abilities(wraith),
        )

    def test_hack_cannot_retarget_already_cast_volcanic_eruption(self) -> None:
        mountain = self.add(self.bob, MOUNTAIN)
        creature = self.add(self.bob, GRAY_OGRE)
        eruption = self.add(self.alice, VOLCANIC_ERUPTION, Zone.HAND)
        self.alice.mana_pool.blue = 3
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(eruption, x_value=1)
        self.game.complete_pending_cast((mountain,))

        hack = self.add(self.bob, MAGICAL_HACK, Zone.HAND)
        self.bob.mana_pool.blue = 1
        self.game.begin_cast(hack)
        self.game.complete_pending_cast(
            (eruption,), word_from="Mountain", word_to="Island"
        )
        self.resolve_interrupt()
        self.resolve_interrupt()

        # Hack cannot exchange the declared Mountain for an Island. It makes
        # that fixed target illegal, so the spell fizzles rather than retargeting.
        self.assertEqual(mountain.zone, Zone.BATTLEFIELD)
        self.assertEqual(creature.zone, Zone.BATTLEFIELD)
        self.assertEqual(creature.damage, 0)
        self.assertEqual((self.alice.life, self.bob.life), (20, 20))

    def test_invalid_target_cannot_be_declared_in_expectation_of_sleight(self) -> None:
        bear = self.add(self.bob, GRIZZLY_BEARS)
        blast = self.add(self.alice, BLUE_ELEMENTAL_BLAST, Zone.HAND)
        self.alice.mana_pool.blue = 1

        with self.assertRaisesRegex(RuntimeError, "no legal targets"):
            self.game.begin_cast(blast, mode="Destroy permanent")

    def test_word_choices_are_fixed_and_must_be_distinct_and_applicable(self) -> None:
        conversion = self.add(self.bob, CONVERSION)
        hack = self.add(self.alice, MAGICAL_HACK, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.game.begin_cast(hack)

        with self.assertRaises(ValueError):
            self.game.complete_pending_cast(
                (conversion,), word_from="Swamp", word_to="Forest"
            )
        with self.assertRaises(ValueError):
            self.game.complete_pending_cast(
                (conversion,), word_from="Mountain", word_to="Mountain"
            )

        self.game.complete_pending_cast(
            (conversion,), word_from="Mountain", word_to="Forest"
        )
        state = self.game.stack_spells[hack.id]
        self.assertEqual((state.chosen_word_from, state.chosen_word_to), ("Mountain", "Forest"))

    def test_sleighting_gloom_does_not_reprice_an_already_cast_spell(self) -> None:
        gloom = self.add(self.bob, GLOOM)
        salve = self.add(self.alice, HEALING_SALVE, Zone.HAND)
        self.alice.life = 10
        self.alice.mana_pool.white = 1
        self.alice.mana_pool.colorless = 3
        self.game.begin_cast(salve)
        self.game.complete_pending_cast((self.alice,))
        self.assertEqual(self.alice.mana_pool.total, 0)

        sleight = self.add(self.bob, SLEIGHT_OF_MIND, Zone.HAND)
        self.bob.mana_pool.blue = 1
        self.game.begin_cast(sleight)
        self.game.complete_pending_cast(
            (gloom,), word_from=Color.WHITE, word_to=Color.GREEN
        )
        self.resolve_interrupt()
        self.resolve_interrupt()
        self.resolve_interrupt()

        self.assertEqual(self.alice.life, 13)
        self.assertEqual(salve.zone, Zone.GRAVEYARD)


if __name__ == "__main__":
    unittest.main()
