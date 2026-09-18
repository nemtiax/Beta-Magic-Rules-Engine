import unittest

from beta_magic.card_defs.blue import (
    BLUE_ELEMENTAL_BLAST,
    CLONE,
    SPELL_BLAST,
)
from beta_magic.card_defs.red import (
    HILL_GIANT,
    ROCK_HYDRA,
)
from beta_magic.card_defs.artifacts import (
    ILLUSIONARY_MASK,
    LIVING_WALL,
)
from beta_magic.card_defs.black import SCATHE_ZOMBIES
from beta_magic import (
    Card,
    CardType,
    FaceDownReason,
    GameState,
    PlayerState,
    SpellCastEvent,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class IllusionaryMaskTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [HILL_GIANT] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [HILL_GIANT] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.mask = self.card(self.alice, ILLUSIONARY_MASK, Zone.BATTLEFIELD)

    @staticmethod
    def card(player, definition, zone):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=zone,
        )
        player.cards_in(zone).append(card)
        return card

    def resolve_all(self) -> None:
        while self.game.priority_player_index is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_pays_real_cost_plus_bluff_x_and_conceals_the_spell(self) -> None:
        giant = self.card(self.alice, HILL_GIANT, Zone.HAND)
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = 5

        self.game.cast_with_illusionary_mask(
            self.alice.id, self.mask, giant, mask_x=2
        )

        self.assertFalse(self.mask.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertIn(giant, self.game.stack)
        self.assertIs(giant.face_down_reason, FaceDownReason.ILLUSIONARY_MASK)
        self.assertFalse(
            self.game.card_characteristics_are_hidden_from(giant, self.alice.id)
        )
        self.assertTrue(
            self.game.card_characteristics_are_hidden_from(giant, self.bob.id)
        )
        cast_event = next(
            event
            for event in reversed(self.game.events)
            if isinstance(event, SpellCastEvent)
        )
        self.assertEqual(cast_event.card_name, "face-down creature")

        view = GameViewModel(self.game)
        self.assertEqual(view.state["stack"], ["Hill Giant"])
        view.switchPerspective()
        self.assertEqual(view.state["stack"], ["Face-down creature"])

    def test_resolves_as_the_real_summoned_creature_and_mask_can_leave(self) -> None:
        creature = self.card(self.alice, SCATHE_ZOMBIES, Zone.HAND)
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 2
        self.game.cast_with_illusionary_mask(self.alice.id, self.mask, creature)
        self.game._move_card(self.mask, Zone.GRAVEYARD)

        self.assertTrue(creature.is_face_down)
        self.resolve_all()

        self.assertIn(creature, self.alice.battlefield)
        self.assertTrue(creature.is_face_down)
        self.assertEqual(creature.summoned_turn, self.game.turn_number)
        self.game._tap_permanent(creature)
        self.assertFalse(creature.is_face_down)

    def test_only_nonartifact_summon_cards_are_eligible(self) -> None:
        giant = self.card(self.alice, HILL_GIANT, Zone.HAND)
        artifact_creature = self.card(self.alice, LIVING_WALL, Zone.HAND)
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = 10

        legal = self.game.legal_illusionary_mask_creatures(
            self.alice.id, self.mask
        )

        self.assertIn(giant, legal)
        self.assertNotIn(artifact_creature, legal)
        with self.assertRaisesRegex(ValueError, "only a summoned creature"):
            self.game.cast_with_illusionary_mask(
                self.alice.id, self.mask, artifact_creature
            )

    def test_real_x_and_mask_x_are_paid_and_recorded_separately(self) -> None:
        hydra = self.card(self.alice, ROCK_HYDRA, Zone.HAND)
        self.alice.mana_pool.red = 2
        self.alice.mana_pool.colorless = 5

        self.game.cast_with_illusionary_mask(
            self.alice.id,
            self.mask,
            hydra,
            creature_x=3,
            mask_x=2,
        )

        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertEqual(self.game.stack_spells[hydra.id].x_value, 3)
        self.resolve_all()
        self.assertEqual(hydra.counters.get("head"), 3)

    def test_color_interrupt_may_be_aimed_at_hidden_spell_and_checks_on_resolution(
        self,
    ) -> None:
        zombie = self.card(self.alice, SCATHE_ZOMBIES, Zone.HAND)
        blast = self.card(self.bob, BLUE_ELEMENTAL_BLAST, Zone.HAND)
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 2
        self.bob.mana_pool.blue = 1
        self.game.cast_with_illusionary_mask(self.alice.id, self.mask, zombie)

        self.assertIn(
            zombie,
            self.game.legal_targets_for(blast, mode="Counter spell"),
        )
        self.game.begin_cast(blast, mode="Counter spell")
        self.game.complete_pending_cast((zombie,))
        self.resolve_all()

        self.assertIn(zombie, self.alice.battlefield)
        self.assertIn(blast, self.bob.graveyard)

    def test_spell_blast_cost_is_not_revealed_until_resolution(self) -> None:
        giant = self.card(self.alice, HILL_GIANT, Zone.HAND)
        blast = self.card(self.bob, SPELL_BLAST, Zone.HAND)
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = 3
        self.bob.mana_pool.blue = 1
        self.bob.mana_pool.colorless = 3
        self.game.cast_with_illusionary_mask(self.alice.id, self.mask, giant)

        self.game.begin_cast(blast, x_value=3)
        self.assertIn(giant, self.game.legal_targets_for())
        self.game.complete_pending_cast((giant,))
        self.resolve_all()

        self.assertIn(giant, self.alice.battlefield)

    def test_ui_selects_a_hand_creature_then_chooses_mask_x(self) -> None:
        giant = self.card(self.alice, HILL_GIANT, Zone.HAND)
        wall = self.card(self.alice, LIVING_WALL, Zone.HAND)
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = 5
        view = GameViewModel(self.game)

        view.activateAbility(str(self.mask.id), 0)

        self.assertTrue(view.state["maskCreatureChoiceRequired"])
        hand = {item["id"]: item for item in view.state["perspective"]["hand"]}
        self.assertTrue(hand[str(giant.id)]["maskChoiceEligible"])
        self.assertFalse(hand[str(wall.id)]["maskChoiceEligible"])

        view.toggleCard(str(giant.id))
        self.assertTrue(view.state["choosingMaskX"])
        self.assertEqual(view.state["maskX"], 2)
        view.adjustMaskX(-1)
        self.assertEqual(view.state["maskX"], 1)
        view.confirmMaskCast()

        self.assertFalse(view.state["choosingMaskX"])
        self.assertIn(giant, self.game.stack)
        self.assertTrue(giant.is_face_down)

    def test_copy_creature_keeps_its_normal_cast_choice(self) -> None:
        clone = self.card(self.alice, CLONE, Zone.HAND)
        giant = self.card(self.bob, HILL_GIANT, Zone.BATTLEFIELD)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3

        self.game.cast_with_illusionary_mask(
            self.alice.id, self.mask, clone, targets=(giant,)
        )
        self.resolve_all()

        self.assertIn(clone, self.alice.battlefield)
        self.assertTrue(clone.is_face_down)
        self.assertEqual(
            (
                self.game.creature_power(clone),
                self.game.creature_toughness(clone),
            ),
            (3, 3),
        )

    def test_ui_collects_a_copy_choice_after_mask_payment(self) -> None:
        clone = self.card(self.alice, CLONE, Zone.HAND)
        giant = self.card(self.bob, HILL_GIANT, Zone.BATTLEFIELD)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3
        view = GameViewModel(self.game)

        view.activateAbility(str(self.mask.id), 0)
        view.toggleCard(str(clone.id))
        view.confirmMaskCast()

        self.assertFalse(view.state["choosingMaskX"])
        self.assertTrue(view.state["targeting"])
        target_data = next(
            item
            for item in view.state["opponent"]["battlefieldNonlands"]
            if item["id"] == str(giant.id)
        )
        self.assertTrue(target_data["legalTarget"])
        view.toggleCard(str(giant.id))
        self.assertIn(clone, self.game.stack)
        self.assertTrue(clone.is_face_down)


if __name__ == "__main__":
    unittest.main()
