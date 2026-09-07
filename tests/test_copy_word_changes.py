import unittest

from beta_magic import Card, Color, GameState, KeywordAbility, PlayerState, Zone
from beta_magic.card_defs import (
    BOG_WRAITH,
    GAUNTLET_OF_MIGHT,
    GRIZZLY_BEARS,
    SHANODIN_DRYADS,
    VESUVAN_DOPPELGANGER,
)
from beta_magic.card_defs.blue import CLONE, COPY_ARTIFACT


class CopyWordChangeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState("a", "Alice")
        self.bob = PlayerState("b", "Bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    def test_repeated_changes_replace_current_words(self) -> None:
        card = Card(BOG_WRAITH, self.alice.id)

        card.change_land_word("Swamp", "Forest")
        card.change_land_word("Forest", "Island")

        self.assertEqual(card.land_word_changes["Swamp"], "Island")
        self.assertEqual(card.land_word_changes["Forest"], "Island")

    def test_clone_copies_hack_and_sleight_state_independently(self) -> None:
        target = Card(BOG_WRAITH, self.bob.id, zone=Zone.BATTLEFIELD)
        target.change_land_word("Swamp", "Forest")
        target.change_color_word(Color.BLACK, Color.GREEN)
        clone = Card(CLONE, self.alice.id)

        self.game._copy_creature_definition(clone, target)

        self.assertIn(
            KeywordAbility.FORESTWALK,
            self.game.creature_abilities(clone),
        )
        self.assertEqual(clone.land_word_changes, target.land_word_changes)
        self.assertEqual(clone.color_word_changes, target.color_word_changes)
        target.change_land_word("Forest", "Island")
        target.change_color_word(Color.GREEN, Color.RED)
        self.assertEqual(clone.land_word_changes["Swamp"], "Forest")
        self.assertEqual(clone.color_word_changes[Color.BLACK], Color.GREEN)

    def test_copy_artifact_stays_blue_but_copies_changed_text(self) -> None:
        gauntlet = Card(
            GAUNTLET_OF_MIGHT, self.bob.id, zone=Zone.BATTLEFIELD
        )
        gauntlet.change_color_word(Color.RED, Color.GREEN)
        gauntlet.change_land_word("Mountain", "Forest")
        copy = Card(COPY_ARTIFACT, self.alice.id)

        self.game._copy_artifact_definition(copy, gauntlet)

        self.assertEqual(self.game.card_colors(copy), frozenset({Color.BLUE}))
        self.assertEqual(copy.color_word_changes, gauntlet.color_word_changes)
        self.assertEqual(copy.land_word_changes, gauntlet.land_word_changes)

    def test_doppelganger_switch_replaces_old_form_word_changes(self) -> None:
        first = Card(BOG_WRAITH, self.bob.id, zone=Zone.BATTLEFIELD)
        first.change_land_word("Swamp", "Forest")
        second = Card(
            SHANODIN_DRYADS, self.bob.id, zone=Zone.BATTLEFIELD
        )
        second.change_land_word("Forest", "Island")
        doppelganger = Card(VESUVAN_DOPPELGANGER, self.alice.id)

        self.game._copy_creature_definition(doppelganger, first)
        self.assertEqual(doppelganger.land_word_changes, {"Swamp": "Forest"})
        self.game._copy_creature_definition(doppelganger, second)

        self.assertEqual(doppelganger.land_word_changes, {"Forest": "Island"})
        self.assertNotIn("Swamp", doppelganger.land_word_changes)
        self.assertIn(
            KeywordAbility.ISLANDWALK,
            self.game.creature_abilities(doppelganger),
        )

    def test_copying_unmodified_form_clears_previous_form_changes(self) -> None:
        changed = Card(BOG_WRAITH, self.bob.id, zone=Zone.BATTLEFIELD)
        changed.change_land_word("Swamp", "Forest")
        ordinary = Card(GRIZZLY_BEARS, self.bob.id, zone=Zone.BATTLEFIELD)
        doppelganger = Card(VESUVAN_DOPPELGANGER, self.alice.id)

        self.game._copy_creature_definition(doppelganger, changed)
        self.game._copy_creature_definition(doppelganger, ordinary)

        self.assertFalse(doppelganger.land_word_changes)
        self.assertFalse(doppelganger.color_word_changes)


if __name__ == "__main__":
    unittest.main()
