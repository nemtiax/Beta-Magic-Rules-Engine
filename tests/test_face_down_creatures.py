import unittest

from beta_magic.card_defs.blue import CLONE
from beta_magic.card_defs.red import (
    GOBLIN_BALLOON_BRIGADE,
    GOBLIN_KING,
)
from beta_magic.card_defs.white import (
    HOLY_STRENGTH,
    WHITE_KNIGHT,
)
from beta_magic.card_defs.black import TERROR
from beta_magic import (
    Card,
    Color,
    FaceDownReason,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs.green import GRIZZLY_BEARS
from beta_magic.card_defs.red import HILL_GIANT
from beta_magic.card_defs.black import SCATHE_ZOMBIES
from beta_magic.ui import GameViewModel


class FaceDownCreatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player, definition, zone=Zone.BATTLEFIELD):
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

    def test_face_down_is_concealment_not_a_generic_creature(self) -> None:
        king = self.card(self.alice, GOBLIN_KING)
        goblin = self.card(self.alice, GOBLIN_BALLOON_BRIGADE)

        self.game.turn_creature_face_down(
            king, FaceDownReason.ILLUSIONARY_MASK
        )

        self.assertEqual(self.game.creature_power(king), 2)
        self.assertEqual(self.game.creature_toughness(king), 2)
        self.assertEqual(self.game.creature_power(goblin), 2)
        self.assertEqual(self.game.creature_toughness(goblin), 2)

    def test_opponent_sees_only_public_state_and_attachment_count(self) -> None:
        creature = self.card(self.bob, HILL_GIANT)
        creature.counters["test"] = 2
        aura = self.card(self.bob, HOLY_STRENGTH)
        aura.enchanted_card_id = creature.id
        self.game.turn_creature_face_down(creature, FaceDownReason.CAMOUFLAGE)
        view = GameViewModel(self.game)

        hidden = next(
            item
            for item in view.state["opponent"]["battlefieldNonlands"]
            if item["id"] == str(creature.id)
        )
        self.assertEqual(hidden["name"], "Face-down creature")
        self.assertEqual((hidden["power"], hidden["toughness"]), ("?", "?"))
        self.assertEqual(hidden["counters"], [{"name": "test", "amount": 2}])
        self.assertEqual(len(hidden["attachments"]), 1)
        self.assertEqual(
            hidden["attachments"][0]["name"], "Face-down enchantment"
        )
        self.assertNotIn("Hill Giant", repr(hidden))
        self.assertNotIn("Holy Strength", repr(hidden))

        view.switchPerspective()
        visible = next(
            item
            for item in view.state["perspective"]["battlefieldNonlands"]
            if item["id"] == str(creature.id)
        )
        self.assertEqual(visible["name"], "Hill Giant")
        self.assertEqual(visible["attachments"][0]["name"], "Holy Strength")

    def test_hidden_characteristics_are_checked_only_on_resolution(self) -> None:
        zombie = self.card(self.bob, SCATHE_ZOMBIES)
        terror = self.card(self.alice, TERROR, Zone.HAND)
        self.game.turn_creature_face_down(
            zombie, FaceDownReason.ILLUSIONARY_MASK
        )
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 1

        self.assertIn(zombie, self.game.legal_targets_for(terror))
        self.game.begin_cast(terror)
        self.game.complete_pending_cast((zombie,))
        cast_event = self.game.events[-1]
        self.assertEqual(cast_event.target_names, ("face-down creature",))
        self.resolve_all()

        self.assertIn(zombie, self.bob.battlefield)
        self.assertIn(terror, self.alice.graveyard)
        self.assertTrue(zombie.is_face_down)

    def test_mask_creature_reveals_on_tap_or_unprevented_damage(self) -> None:
        tap_creature = self.card(self.alice, GRIZZLY_BEARS)
        self.game.turn_creature_face_down(
            tap_creature, FaceDownReason.ILLUSIONARY_MASK
        )
        self.game._tap_permanent(tap_creature)
        self.assertFalse(tap_creature.is_face_down)

        recipient = self.card(self.alice, GRIZZLY_BEARS)
        self.game.turn_creature_face_down(
            recipient, FaceDownReason.ILLUSIONARY_MASK
        )
        self.game._deal_damage(recipient, 1, "test")
        self.assertFalse(recipient.is_face_down)

        source = self.card(self.alice, GRIZZLY_BEARS)
        self.game.turn_creature_face_down(
            source, FaceDownReason.ILLUSIONARY_MASK
        )
        self.game._deal_damage(self.bob, 1, source.name, source_card=source)
        self.assertFalse(source.is_face_down)

    def test_fully_prevented_damage_does_not_reveal_mask_creature(self) -> None:
        knight = self.card(self.alice, WHITE_KNIGHT)
        self.game.turn_creature_face_down(
            knight, FaceDownReason.ILLUSIONARY_MASK
        )

        self.game._deal_damage(
            knight, 1, "black source", source_colors=frozenset({Color.BLACK})
        )

        self.assertTrue(knight.is_face_down)
        self.assertEqual(knight.damage, 0)

    def test_camouflage_state_waits_for_its_explicit_reveal_point(self) -> None:
        creature = self.card(self.alice, GRIZZLY_BEARS)
        self.game.turn_creature_face_down(creature, FaceDownReason.CAMOUFLAGE)

        self.game._tap_permanent(creature)
        self.game._deal_damage(creature, 1, "test")

        self.assertTrue(creature.is_face_down)
        self.game.turn_creature_face_up(creature)
        self.assertFalse(creature.is_face_down)

    def test_leaving_play_reveals_card_and_clears_concealment(self) -> None:
        creature = self.card(self.bob, HILL_GIANT)
        self.game.turn_creature_face_down(
            creature, FaceDownReason.ILLUSIONARY_MASK
        )

        self.game._move_card(creature, Zone.GRAVEYARD)

        self.assertFalse(creature.is_face_down)
        self.assertEqual(creature.face_down_known_to_player_ids, set())

    def test_new_controller_may_look_without_erasing_prior_knowledge(self) -> None:
        creature = self.card(self.alice, HILL_GIANT)
        self.game.turn_creature_face_down(
            creature, FaceDownReason.ILLUSIONARY_MASK
        )

        self.game._change_controller(creature, self.bob.id)

        self.assertFalse(
            self.game.card_characteristics_are_hidden_from(creature, self.alice.id)
        )
        self.assertFalse(
            self.game.card_characteristics_are_hidden_from(creature, self.bob.id)
        )

    def test_clone_of_opponents_face_down_creature_stays_unknown_to_copier(
        self,
    ) -> None:
        target = self.card(self.bob, HILL_GIANT)
        self.game.turn_creature_face_down(
            target, FaceDownReason.ILLUSIONARY_MASK
        )
        clone = self.card(self.alice, CLONE, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3

        self.game.begin_cast(clone)
        self.assertIn(target, self.game.legal_targets_for())
        self.game.complete_pending_cast((target,))
        self.resolve_all()

        view = GameViewModel(self.game)
        clone_data = next(
            item
            for item in view.state["perspective"]["battlefieldNonlands"]
            if item["id"] == str(clone.id)
        )
        self.assertEqual(clone_data["name"], "Clone")
        self.assertEqual((clone_data["power"], clone_data["toughness"]), ("?", "?"))
        self.game.turn_creature_face_up(target)
        revealed_data = next(
            item
            for item in view.state["perspective"]["battlefieldNonlands"]
            if item["id"] == str(clone.id)
        )
        self.assertEqual(revealed_data["name"], "Hill Giant")
        self.assertEqual(
            (revealed_data["power"], revealed_data["toughness"]), (3, 3)
        )

    def test_hidden_copy_knowledge_survives_control_change_and_source_leaving(
        self,
    ) -> None:
        target = self.card(self.bob, HILL_GIANT)
        self.game.turn_creature_face_down(
            target, FaceDownReason.ILLUSIONARY_MASK
        )
        clone = self.card(self.alice, CLONE, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 3
        self.game.begin_cast(clone)
        self.game.complete_pending_cast((target,))
        self.resolve_all()
        view = GameViewModel(self.game)

        alice_data = next(
            item
            for item in view.state["perspective"]["battlefieldNonlands"]
            if item["id"] == str(clone.id)
        )
        self.assertEqual((alice_data["name"], alice_data["power"]), ("Clone", "?"))
        view.switchPerspective()
        bob_data = next(
            item
            for item in view.state["opponent"]["battlefieldNonlands"]
            if item["id"] == str(clone.id)
        )
        self.assertEqual((bob_data["name"], bob_data["power"]), ("Hill Giant", 3))

        self.game._change_controller(target, self.alice.id)
        view.perspective_index = 0
        learned_data = next(
            item
            for item in view.state["perspective"]["battlefieldNonlands"]
            if item["id"] == str(clone.id)
        )
        self.assertEqual((learned_data["name"], learned_data["power"]), ("Hill Giant", 3))

        self.game._move_card(target, Zone.GRAVEYARD)
        retained_data = next(
            item
            for item in view.state["perspective"]["battlefieldNonlands"]
            if item["id"] == str(clone.id)
        )
        self.assertEqual((retained_data["name"], retained_data["power"]), ("Hill Giant", 3))


if __name__ == "__main__":
    unittest.main()
