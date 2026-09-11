import unittest

from beta_magic import (
    BADLANDS,
    CONVERSION,
    EVIL_PRESENCE,
    FOREST,
    ISLAND,
    MOUNTAIN,
    PHANTASMAL_TERRAIN,
    Card,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS
from beta_magic.ui import GameViewModel


class LandConversionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        player.battlefield.append(card)
        return card

    def aura(self, definition, target, *, land_subtype=None):
        card = Card(definition, owner_id=self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(card)
        self.alice.mana_pool.blue = 2
        self.alice.mana_pool.black = 1
        self.game.cast_enchantment(
            card, target, land_subtype=land_subtype
        )
        return card

    def test_evil_presence_replaces_all_types_and_mana_abilities(self):
        land = self.permanent(self.bob, BADLANDS)
        aura = self.aura(EVIL_PRESENCE, land)

        self.assertEqual(self.game.land_subtypes(land), ("Swamp",))
        self.assertEqual(
            [ability.color for ability in self.game.activated_abilities(land)],
            [Color.BLACK],
        )

        self.game._move_card(aura, Zone.GRAVEYARD)
        self.assertEqual(self.game.land_subtypes(land), ("Swamp", "Mountain"))
        self.assertEqual(
            [ability.color for ability in self.game.activated_abilities(land)],
            [Color.BLACK, Color.RED],
        )

    def test_phantasmal_terrain_requires_and_remembers_basic_type(self):
        land = self.permanent(self.bob, FOREST)
        spell = Card(
            PHANTASMAL_TERRAIN, owner_id=self.alice.id, zone=Zone.HAND
        )
        self.alice.hand.append(spell)
        self.alice.mana_pool.blue = 2

        with self.assertRaisesRegex(ValueError, "basic land type"):
            self.game.begin_cast(spell, land_subtype="Desert")
        pending = self.game.begin_cast(spell, land_subtype="Island")
        self.assertEqual(pending.chosen_land_subtype, "Island")
        self.game.complete_pending_cast((land,))
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.assertEqual(spell.chosen_land_subtype, "Island")
        self.assertEqual(self.game.land_subtypes(land), ("Island",))
        self.assertEqual(
            self.game.activated_abilities(land)[0].color, Color.BLUE
        )

    def test_ui_displays_a_phantasmal_land_and_its_chosen_type(self):
        land = self.permanent(self.bob, FOREST)
        aura = self.aura(PHANTASMAL_TERRAIN, land, land_subtype="Island")
        view = GameViewModel(self.game)

        land_data = view._card_data(land)
        aura_data = view._card_data(aura)

        self.assertEqual(land_data["name"], "Island")
        self.assertIn("Current name: Island", land_data["previewStatus"])
        self.assertEqual(aura_data["attachedTo"], "Island")
        self.assertIn(
            "Chosen land type: Island",
            aura_data["previewStatus"],
        )

        self.game._move_card(aura, Zone.GRAVEYARD)
        self.assertEqual(view._card_data(land)["name"], "Forest")

    def test_conversion_changes_mountains_including_dual_lands(self):
        mountain = self.permanent(self.alice, MOUNTAIN)
        badlands = self.permanent(self.bob, BADLANDS)
        island = self.permanent(self.bob, ISLAND)
        self.permanent(self.alice, CONVERSION)

        self.assertEqual(self.game.land_subtypes(mountain), ("Plains",))
        self.assertEqual(self.game.land_subtypes(badlands), ("Plains",))
        self.assertEqual(self.game.land_subtypes(island), ("Island",))
        self.assertEqual(
            self.game.activated_abilities(mountain)[0].color, Color.WHITE
        )

    def test_attached_change_is_applied_before_conversion(self):
        land = self.permanent(self.bob, FOREST)
        self.aura(PHANTASMAL_TERRAIN, land, land_subtype="Mountain")
        self.permanent(self.alice, CONVERSION)

        self.assertEqual(self.game.land_subtypes(land), ("Plains",))


if __name__ == "__main__":
    unittest.main()
