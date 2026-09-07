import unittest

from beta_magic import (
    ANIMATE_ARTIFACT,
    BLUE_WARD,
    BOG_WRAITH,
    CHANNEL,
    CLOCKWORK_BEAST,
    CLONE,
    FOREST,
    GRIZZLY_BEARS,
    HILL_GIANT,
    KeywordAbility,
    LIVING_LANDS,
    RESURRECTION,
    SOL_RING,
    UNSUMMON,
    Card,
    CardType,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class CloneTests(unittest.TestCase):
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

    def cast_clone(self, target: Card) -> Card:
        clone = self.card(self.alice, CLONE, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3
        self.game.begin_cast(clone)
        self.game.complete_pending_cast((target,))
        self.resolve()
        return clone

    def test_copies_normal_characteristics_and_target_color(self) -> None:
        giant = self.card(self.bob, HILL_GIANT)
        giant.color_override = Color.BLACK
        giant.tapped = True
        giant.damage = 2
        giant.plus_one_counters = 3

        clone = self.cast_clone(giant)

        self.assertEqual(clone.name, "Hill Giant")
        self.assertEqual(clone.definition.mana_cost, HILL_GIANT.mana_cost)
        self.assertEqual(clone.definition.subtypes, HILL_GIANT.subtypes)
        self.assertEqual(self.game.card_colors(clone), frozenset({Color.BLACK}))
        self.assertEqual((self.game.creature_power(clone), self.game.creature_toughness(clone)), (3, 3))
        self.assertFalse(clone.tapped)
        self.assertEqual(clone.damage, 0)
        self.assertEqual(clone.plus_one_counters, 0)

    def test_copies_word_changes_that_resolve_during_casting_window(self) -> None:
        wraith = self.card(self.bob, BOG_WRAITH)
        clone = self.card(self.alice, CLONE, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3
        self.game.begin_cast(clone)
        self.game.complete_pending_cast((wraith,))

        wraith.change_land_word("Swamp", "Forest")
        self.resolve()

        self.assertIn(
            KeywordAbility.FORESTWALK,
            self.game.creature_abilities(clone),
        )
        wraith.change_land_word("Forest", "Island")
        self.assertIn(
            KeywordAbility.FORESTWALK,
            self.game.creature_abilities(clone),
        )

    def test_clone_of_artifact_creature_keeps_artifact_type(self) -> None:
        beast = self.card(self.bob, CLOCKWORK_BEAST)
        beast.counters["+1/+0"] = 4

        clone = self.cast_clone(beast)

        self.assertIn(CardType.ARTIFACT, self.game.card_types(clone))
        self.assertIn(CardType.CREATURE, self.game.card_types(clone))
        self.assertEqual(clone.counters, {})
        self.assertEqual(self.game.creature_power(clone), 0)
        self.assertEqual(self.game.creature_toughness(clone), 4)

    def test_animated_artifacts_and_lands_are_not_clone_targets(self) -> None:
        ring = self.card(self.bob, SOL_RING)
        animation = self.card(self.bob, ANIMATE_ARTIFACT)
        animation.enchanted_card_id = ring.id
        self.card(self.alice, LIVING_LANDS)
        forest = self.card(self.bob, FOREST)
        bear = self.card(self.bob, GRIZZLY_BEARS)
        clone = self.card(self.alice, CLONE, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3

        self.game.begin_cast(clone)
        legal = self.game.legal_targets_for()

        self.assertIn(bear, legal)
        self.assertNotIn(ring, legal)
        self.assertNotIn(forest, legal)

    def test_blue_ward_prevents_clone_targeting(self) -> None:
        bear = self.card(self.bob, GRIZZLY_BEARS)
        ward = self.card(self.bob, BLUE_WARD)
        ward.enchanted_card_id = bear.id
        clone = self.card(self.alice, CLONE, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3

        with self.assertRaisesRegex(RuntimeError, "no legal targets"):
            self.game.begin_cast(clone)

    def test_copy_of_token_is_still_a_card(self) -> None:
        token = self.card(self.bob, GRIZZLY_BEARS, token=True)

        clone = self.cast_clone(token)

        self.assertFalse(clone.is_token)
        self.game._move_card(clone, Zone.HAND)
        self.assertIn(clone, self.alice.hand)
        self.assertIs(clone.definition, CLONE)

    def test_target_leaving_before_resolution_counters_clone(self) -> None:
        bear = self.card(self.bob, GRIZZLY_BEARS)
        clone = self.card(self.alice, CLONE, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3
        self.game.begin_cast(clone)
        self.game.complete_pending_cast((bear,))
        self.game._destroy_permanents((bear,))

        self.resolve()

        self.assertIn(clone, self.alice.graveyard)
        self.assertIs(clone.definition, CLONE)

    def test_resurrection_waits_for_a_new_copy_choice(self) -> None:
        bear = self.card(self.bob, GRIZZLY_BEARS)
        clone = self.card(self.alice, CLONE, Zone.GRAVEYARD)
        resurrection = self.card(self.alice, RESURRECTION, Zone.HAND)
        self.alice.mana_pool.white = 2
        self.alice.mana_pool.colorless = 2
        self.game.begin_cast(resurrection)
        self.game.complete_pending_cast((clone,))
        self.resolve()

        self.assertIn(clone, self.alice.graveyard)
        self.assertTrue(self.game.pending_creature_copy_choices)
        view = GameViewModel(self.game)
        self.assertTrue(view.state["canChooseClone"])

        self.game.choose_clone_creature(self.alice.id, bear)

        self.assertIn(clone, self.alice.battlefield)
        self.assertEqual(clone.name, "Grizzly Bears")

    def test_resurrection_cannot_return_clone_without_another_creature(self) -> None:
        clone = self.card(self.alice, CLONE, Zone.GRAVEYARD)
        resurrection = self.card(self.alice, RESURRECTION, Zone.HAND)
        self.alice.mana_pool.white = 2
        self.alice.mana_pool.colorless = 2
        self.game.begin_cast(resurrection)
        self.game.complete_pending_cast((clone,))
        self.resolve()

        self.assertIn(clone, self.alice.graveyard)
        self.assertFalse(self.game.pending_creature_copy_choices)


if __name__ == "__main__":
    unittest.main()
