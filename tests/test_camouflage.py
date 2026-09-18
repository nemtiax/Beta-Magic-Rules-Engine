import unittest

from tests.support import declare_attackers, declare_blockers
from random import Random

from beta_magic.card_defs.blue import AIR_ELEMENTAL
from beta_magic.card_defs.green import (
    CAMOUFLAGE,
    GRIZZLY_BEARS,
    LIVING_LANDS,
    LURE,
)
from beta_magic.card_defs.artifacts import CLOCKWORK_BEAST
from beta_magic.card_defs.lands import FOREST
from beta_magic.card_defs.white import MESA_PEGASUS
from beta_magic import (
    Card,
    CardType,
    CombatStep,
    FaceDownReason,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.effects import CamouflageEffect
from beta_magic.ui import GameViewModel
from beta_magic.ui_combat import CombatUiController


class CamouflageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 20
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player: PlayerState, definition, zone=Zone.BATTLEFIELD) -> Card:
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=zone,
            entered_battlefield_turn=0,
        )
        player.cards_in(zone).append(card)
        return card

    def resolve_batch(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self) -> None:
        self.assertEqual(CAMOUFLAGE.mana_cost.compact, "G")
        self.assertEqual(CAMOUFLAGE.card_types, frozenset({CardType.INSTANT}))
        self.assertTrue(
            any(
                isinstance(effect, CamouflageEffect)
                for effect in CAMOUFLAGE.spell_effects
            )
        )

    def test_cast_outside_attack_is_legal_and_has_no_effect(self) -> None:
        creature = self.card(self.alice, GRIZZLY_BEARS)
        camouflage = self.card(self.alice, CAMOUFLAGE, Zone.HAND)
        self.alice.mana_pool.green = 1

        self.game.begin_cast(camouflage)
        self.resolve_batch()

        self.assertFalse(creature.is_face_down)
        self.assertIn(camouflage, self.alice.graveyard)

    def test_resolution_conceals_and_randomizes_current_attackers(self) -> None:
        attackers = [
            self.card(self.alice, GRIZZLY_BEARS),
            self.card(self.alice, AIR_ELEMENTAL),
            self.card(self.alice, MESA_PEGASUS),
        ]
        self.game.begin_combat()
        declare_attackers(self.game, attackers)
        self.game.random.seed(41)
        expected = list(attackers)
        Random(41).shuffle(expected)
        camouflage = self.card(self.alice, CAMOUFLAGE, Zone.HAND)
        self.alice.mana_pool.green = 1

        self.game.begin_cast(camouflage)
        self.resolve_batch()

        self.assertEqual(self.game.combat.attackers, expected)
        self.assertEqual(
            self.game.combat.camouflaged_attacker_ids,
            {card.id for card in attackers},
        )
        self.assertTrue(
            all(
                card.face_down_reason is FaceDownReason.CAMOUFLAGE
                for card in attackers
            )
        )

    def test_ui_keeps_shuffled_positions_but_hides_them_from_defender(self) -> None:
        attackers = [
            self.card(self.alice, GRIZZLY_BEARS),
            self.card(self.alice, AIR_ELEMENTAL),
            self.card(self.alice, MESA_PEGASUS),
        ]
        self.game.begin_combat()
        declare_attackers(self.game, attackers)
        self.game.random.seed(19)
        self.game.apply_camouflage(self.alice.id)
        shuffled_ids = [str(card.id) for card in self.game.combat.attackers]
        view = GameViewModel(self.game)

        attacker_state = view.state
        self.assertEqual(
            [card["id"] for card in attacker_state["perspective"]["battlefieldNonlands"]],
            shuffled_ids,
        )
        self.assertEqual(
            [item["label"] for item in attacker_state["attackers"]],
            [card.name for card in self.game.combat.attackers],
        )

        view.switchPerspective()
        defender_state = view.state
        self.assertEqual(
            [card["id"] for card in defender_state["opponent"]["battlefieldNonlands"]],
            shuffled_ids,
        )
        self.assertEqual(
            [item["label"] for item in defender_state["attackers"]],
            ["Face-down creature"] * len(attackers),
        )
        self.assertNotIn("Air Elemental", repr(defender_state["opponent"]))

        # Rebuilding presentation state does not shuffle the positions again.
        self.assertEqual(
            [card["id"] for card in view.state["opponent"]["battlefieldNonlands"]],
            shuffled_ids,
        )

    def test_impossible_blocks_are_removed_only_after_reveal(self) -> None:
        flyer = self.card(self.alice, AIR_ELEMENTAL)
        ground = self.card(self.alice, GRIZZLY_BEARS)
        first_blocker = self.card(self.bob, GRIZZLY_BEARS)
        second_blocker = self.card(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        declare_attackers(self.game, [flyer, ground])
        self.game.apply_camouflage(self.alice.id)
        self.game.combat.step = CombatStep.DECLARE_BLOCKERS

        declare_blockers(self.game,
            {first_blocker: flyer, second_blocker: ground}
        )

        self.assertFalse(flyer.is_face_down)
        self.assertFalse(ground.is_face_down)
        self.assertEqual(self.game.combat.blockers[flyer.id], [])
        self.assertEqual(self.game.combat.blockers[ground.id], [second_blocker])
        self.assertEqual(self.game.combat.camouflage_invalid_block_count, 1)
        self.assertEqual(self.game.combat.camouflaged_attacker_ids, set())

    def test_a_legal_flying_block_survives_the_reveal(self) -> None:
        flyer = self.card(self.alice, AIR_ELEMENTAL)
        flying_blocker = self.card(self.bob, MESA_PEGASUS)
        self.game.begin_combat()
        declare_attackers(self.game, [flyer])
        self.game.apply_camouflage(self.alice.id)
        self.game.combat.step = CombatStep.DECLARE_BLOCKERS

        declare_blockers(self.game, {flying_blocker: flyer})

        self.assertEqual(
            self.game.combat.blockers[flyer.id], [flying_blocker]
        )
        self.assertEqual(self.game.combat.camouflage_invalid_block_count, 0)

    def test_an_impossible_block_does_not_count_as_blocking(self) -> None:
        flyer = self.card(self.alice, AIR_ELEMENTAL)
        beast = self.card(self.bob, CLOCKWORK_BEAST)
        starting_counters = beast.counters["+1/+0"]
        self.game.begin_combat()
        declare_attackers(self.game, [flyer])
        self.game.apply_camouflage(self.alice.id)
        self.game.combat.step = CombatStep.DECLARE_BLOCKERS

        declare_blockers(self.game, {beast: flyer})

        self.assertEqual(self.game.combat.blockers[flyer.id], [])
        self.assertEqual(beast.counters["+1/+0"], starting_counters)

    def test_animated_land_joins_the_concealed_attacker_row(self) -> None:
        self.card(self.alice, LIVING_LANDS)
        forest = self.card(self.alice, FOREST)
        self.game.begin_combat()
        declare_attackers(self.game, [forest])
        self.game.apply_camouflage(self.alice.id)
        view = GameViewModel(self.game)
        view.switchPerspective()

        hidden = view.state["opponent"]
        self.assertIn(
            str(forest.id),
            [card["id"] for card in hidden["battlefieldNonlands"]],
        )
        self.assertNotIn(
            str(forest.id),
            [card["id"] for card in hidden["battlefieldLands"]],
        )

        self.game.combat.step = CombatStep.DECLARE_BLOCKERS
        declare_blockers(self.game, {})
        revealed = view.state["opponent"]
        self.assertIn(
            str(forest.id),
            [card["id"] for card in revealed["battlefieldLands"]],
        )

    def test_blocker_ui_does_not_preload_hidden_block_requirements(self) -> None:
        attacker = self.card(self.alice, GRIZZLY_BEARS)
        blocker = self.card(self.bob, GRIZZLY_BEARS)
        lure = self.card(self.alice, LURE)
        lure.enchanted_card_id = attacker.id
        self.game.begin_combat()
        declare_attackers(self.game, [attacker])
        self.game.apply_camouflage(self.alice.id)
        self.game.combat.blaze_of_glory_blocker_ids.add(blocker.id)
        self.game.combat.step = CombatStep.DECLARE_BLOCKERS
        controller = CombatUiController()

        controller.sync(self.game)

        self.assertEqual(controller.draft_for(blocker.id), ())


if __name__ == "__main__":
    unittest.main()
