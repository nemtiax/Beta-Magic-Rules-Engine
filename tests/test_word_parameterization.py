import unittest
from uuid import uuid4

from beta_magic import (
    Card,
    Color,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import (
    BOG_WRAITH,
    BLUE_ELEMENTAL_BLAST,
    CIRCLE_OF_PROTECTION_RED,
    CONVERSION,
    COPY_ARTIFACT,
    CRUSADE,
    FOREST,
    GLOOM,
    GRIZZLY_BEARS,
    HEALING_SALVE,
    HILL_GIANT,
    LLANOWAR_ELVES,
    MOUNTAIN,
    PLAINS,
    SOL_RING,
)


class WordParameterizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState("a", "Alice")
        self.bob = PlayerState("b", "Bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

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

    def test_continuous_color_word_is_resolved_from_source(self) -> None:
        crusade = self.add(self.alice, CRUSADE)
        bear = self.add(self.alice, GRIZZLY_BEARS)
        crusade.color_word_changes[Color.WHITE] = Color.GREEN

        self.assertEqual(self.game.creature_power(bear), 3)
        self.assertEqual(self.game.creature_toughness(bear), 3)

    def test_landwalk_word_is_resolved_on_printed_ability(self) -> None:
        wraith = self.add(self.alice, BOG_WRAITH)
        wraith.land_word_changes["Swamp"] = "Forest"

        abilities = self.game.creature_abilities(wraith)
        self.assertIn(KeywordAbility.FORESTWALK, abilities)
        self.assertNotIn(KeywordAbility.SWAMPWALK, abilities)

    def test_target_color_word_is_resolved_from_spell(self) -> None:
        blast = self.add(self.alice, BLUE_ELEMENTAL_BLAST, Zone.HAND)
        blast.color_word_changes[Color.RED] = Color.GREEN

        requirement = self.game._translated_target_requirement(
            blast, blast.definition.target_requirement
        )

        self.assertIs(requirement.color, Color.GREEN)

    def test_interrupt_word_change_can_invalidate_declared_target(self) -> None:
        giant = self.add(self.bob, HILL_GIANT)
        blast = self.add(self.alice, BLUE_ELEMENTAL_BLAST, Zone.HAND)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0
        self.alice.mana_pool.blue = 1

        self.game.begin_cast(blast, mode="Destroy permanent")
        self.game.complete_pending_cast((giant,))
        state = self.game.stack_spells[blast.id]
        self.assertIs(state.declared_target_requirement.color, Color.RED)

        blast.color_word_changes[Color.RED] = Color.GREEN
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

        self.assertEqual(blast.zone, Zone.GRAVEYARD)
        self.assertEqual(giant.zone, Zone.BATTLEFIELD)

    def test_activated_mana_color_word_is_resolved(self) -> None:
        elf = self.add(self.alice, LLANOWAR_ELVES)
        elf.color_word_changes[Color.GREEN] = Color.BLUE

        ability = self.game.activated_abilities(elf)[0]

        self.assertIs(ability.color, Color.BLUE)

    def test_prevention_source_color_word_is_resolved(self) -> None:
        circle = self.add(self.alice, CIRCLE_OF_PROTECTION_RED)
        circle.color_word_changes[Color.RED] = Color.BLACK

        ability = self.game.activated_abilities(circle)[0]

        self.assertIs(ability.source_color, Color.BLACK)

    def test_global_land_conversion_resolves_both_words(self) -> None:
        conversion = self.add(self.alice, CONVERSION)
        forest = self.add(self.alice, FOREST)
        conversion.land_word_changes.update(
            {"Mountain": "Forest", "Plains": "Island"}
        )

        self.assertEqual(self.game.land_subtypes(forest), ("Island",))

    def test_gloom_tax_uses_its_current_color_word(self) -> None:
        gloom = self.add(self.bob, GLOOM)
        spell = self.add(self.alice, HEALING_SALVE, Zone.HAND)
        gloom.color_word_changes[Color.WHITE] = Color.GREEN

        self.assertEqual(self.game.spell_mana_cost(spell).compact, "W")
        spell.color_override = Color.GREEN
        self.assertEqual(self.game.spell_mana_cost(spell).compact, "3W")

    def test_copy_effect_copies_word_changes(self) -> None:
        target = self.add(self.bob, SOL_RING)
        target.color_word_changes[Color.RED] = Color.BLUE
        target.land_word_changes["Swamp"] = "Island"
        copy = Card(COPY_ARTIFACT, self.alice.id)

        self.game._copy_artifact_definition(copy, target)

        self.assertEqual(copy.color_word_changes, target.color_word_changes)
        self.assertEqual(copy.land_word_changes, target.land_word_changes)
        self.assertIsNot(copy.color_word_changes, target.color_word_changes)

    def test_word_changes_end_when_card_leaves_play(self) -> None:
        card = self.add(self.alice, PLAINS)
        card.color_word_changes[Color.WHITE] = Color.BLUE
        card.land_word_changes["Plains"] = "Island"

        self.game._move_card(card, Zone.GRAVEYARD)

        self.assertFalse(card.color_word_changes)
        self.assertFalse(card.land_word_changes)

    def test_basic_land_mana_comes_from_current_land_type(self) -> None:
        land = self.add(self.alice, MOUNTAIN)
        land.land_type_marks[uuid4()] = ("Forest", 1)

        abilities = self.game.activated_abilities(land)

        self.assertEqual([ability.color for ability in abilities], [Color.GREEN])


if __name__ == "__main__":
    unittest.main()
