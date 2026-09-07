import unittest

from beta_magic import (
    CLOCKWORK_BEAST,
    GAUNTLET_OF_MIGHT,
    COPY_ARTIFACT,
    FOREST,
    ANIMATE_ARTIFACT,
    SOL_RING,
    TIME_VAULT,
    UNSUMMON,
    Card,
    CardType,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class CopyArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("b", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player, definition, zone=Zone.BATTLEFIELD, *, tapped=False):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=zone,
            tapped=tapped,
        )
        player.cards_in(zone).append(card)
        return card

    def resolve(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def cast_copy(self, target: Card) -> Card:
        spell = self.card(self.alice, COPY_ARTIFACT, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((target,))
        self.resolve()
        return spell

    def test_definition_and_casting_choice(self) -> None:
        ring = self.card(self.bob, SOL_RING)
        forest = self.card(self.bob, FOREST)
        spell = self.card(self.alice, COPY_ARTIFACT, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 1

        self.game.begin_cast(spell)

        self.assertIn(ring, self.game.legal_targets_for())
        self.assertNotIn(forest, self.game.legal_targets_for())

    def test_copies_characteristics_but_remains_blue_artifact_enchantment(self) -> None:
        ring = self.card(self.bob, SOL_RING, tapped=True)

        copy = self.cast_copy(ring)

        self.assertEqual(copy.name, "Sol Ring")
        self.assertEqual(copy.definition.mana_cost, SOL_RING.mana_cost)
        self.assertEqual(
            copy.definition.card_types,
            frozenset({CardType.ARTIFACT, CardType.ENCHANTMENT}),
        )
        self.assertEqual(self.game.card_colors(copy), frozenset({Color.BLUE}))
        self.assertEqual(copy.definition.activated_abilities, SOL_RING.activated_abilities)
        self.assertFalse(copy.tapped)
        self.assertFalse(copy.is_token)

    def test_copy_gets_fresh_initial_counters_not_targets_current_counters(self) -> None:
        beast = self.card(self.bob, CLOCKWORK_BEAST, tapped=True)
        beast.counters["+1/+0"] = 2
        beast.plus_one_counters = 3
        beast.damage = 4

        copy = self.cast_copy(beast)

        self.assertEqual(copy.counters.get("+1/+0"), 7)
        self.assertEqual(copy.plus_one_counters, 0)
        self.assertEqual(copy.damage, 0)
        self.assertFalse(copy.tapped)
        self.assertIn(CardType.CREATURE, self.game.card_types(copy))

    def test_uses_the_copied_artifacts_normal_entry_orientation(self) -> None:
        vault = self.card(self.bob, TIME_VAULT)

        copy = self.cast_copy(vault)

        self.assertTrue(copy.tapped)

    def test_does_not_copy_animation_lace_or_attached_enchantments(self) -> None:
        ring = self.card(self.bob, SOL_RING)
        ring.color_override = Color.RED
        animation = self.card(self.bob, ANIMATE_ARTIFACT)
        animation.enchanted_card_id = ring.id
        self.assertIn(CardType.CREATURE, self.game.card_types(ring))

        copy = self.cast_copy(ring)

        self.assertNotIn(CardType.CREATURE, self.game.card_types(copy))
        self.assertEqual(self.game.card_colors(copy), frozenset({Color.BLUE}))
        self.assertIsNone(copy.enchanted_card_id)

    def test_copy_survives_original_and_reverts_after_leaving_play(self) -> None:
        beast = self.card(self.bob, CLOCKWORK_BEAST)
        copy = self.cast_copy(beast)
        self.game._destroy_permanents((beast,))

        self.assertIn(copy, self.alice.battlefield)
        self.assertEqual(copy.name, "Clockwork Beast")

        unsummon = self.card(self.alice, UNSUMMON, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.game.begin_cast(unsummon)
        self.game.complete_pending_cast((copy,))
        self.resolve()

        self.assertIn(copy, self.alice.hand)
        self.assertIs(copy.definition, COPY_ARTIFACT)
        self.assertIsNone(copy.printed_definition)

    def test_target_destroyed_before_resolution_counters_the_copy_spell(self) -> None:
        ring = self.card(self.bob, SOL_RING)
        spell = self.card(self.alice, COPY_ARTIFACT, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((ring,))

        self.game._destroy_permanents((ring,))
        self.resolve()

        self.assertIn(spell, self.alice.graveyard)
        self.assertIs(spell.definition, COPY_ARTIFACT)

    def test_copies_word_changes_that_resolve_during_casting_window(self) -> None:
        gauntlet = self.card(self.bob, GAUNTLET_OF_MIGHT)
        spell = self.card(self.alice, COPY_ARTIFACT, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((gauntlet,))

        gauntlet.change_color_word(Color.RED, Color.GREEN)
        gauntlet.change_land_word("Mountain", "Forest")
        self.resolve()

        self.assertEqual(spell.color_word_changes, {Color.RED: Color.GREEN})
        self.assertEqual(spell.land_word_changes, {"Mountain": "Forest"})
        gauntlet.change_land_word("Forest", "Island")
        self.assertEqual(spell.land_word_changes, {"Mountain": "Forest"})


if __name__ == "__main__":
    unittest.main()
