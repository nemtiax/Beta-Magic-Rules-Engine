import unittest

from beta_magic import (
    ARMAGEDDON,
    FLASHFIRES,
    ICE_STORM,
    LAND_DESTRUCTION_SPELLS,
    SINKHOLE,
    STONE_RAIN,
    TSUNAMI,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.basic_lands import FOREST, ISLAND, MOUNTAIN, PLAINS, SWAMP
from beta_magic.dual_lands import BADLANDS, SAVANNAH, TROPICAL_ISLAND, TUNDRA
from beta_magic.vanilla_creatures import GRIZZLY_BEARS


class LandDestructionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 30
        )
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 30)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(player, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = player.id
        player.battlefield.append(card)
        return card

    @staticmethod
    def put_in_hand(player, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        player.hand.append(card)
        return card

    def cast(self, definition, target=None):
        spell = self.put_in_hand(self.alice, definition)
        for color in ("white", "blue", "black", "red", "green"):
            setattr(self.alice.mana_pool, color, 10)
        self.game.begin_cast(spell)
        if target is not None:
            self.game.complete_pending_cast((target,))
        while self.game.stack:
            priority = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(priority.id)
        return spell

    def test_definitions(self) -> None:
        self.assertEqual(
            LAND_DESTRUCTION_SPELLS,
            (
                STONE_RAIN,
                SINKHOLE,
                ICE_STORM,
                ARMAGEDDON,
                FLASHFIRES,
                TSUNAMI,
            ),
        )
        self.assertEqual(
            tuple(card.mana_cost.compact for card in LAND_DESTRUCTION_SPELLS),
            ("2R", "BB", "2G", "3W", "3R", "3G"),
        )
        self.assertTrue(
            all(CardType.SORCERY in card.card_types for card in LAND_DESTRUCTION_SPELLS)
        )

    def test_targeted_spells_can_destroy_any_players_basic_or_dual_land(self) -> None:
        for definition, land_definition in (
            (STONE_RAIN, PLAINS),
            (SINKHOLE, BADLANDS),
            (ICE_STORM, FOREST),
        ):
            with self.subTest(definition.name):
                land = self.put_in_play(self.bob, land_definition)
                spell = self.put_in_hand(self.alice, definition)
                self.assertIn(land, self.game.legal_targets_for(spell))
                self.cast(definition, land)
                self.assertIn(land, self.bob.graveyard)
                self.alice.hand.remove(spell)
                self.alice.library.append(spell)
                spell.zone = Zone.LIBRARY

    def test_targeted_land_destruction_rejects_nonlands(self) -> None:
        creature = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.put_in_play(self.bob, PLAINS)
        spell = self.put_in_hand(self.alice, STONE_RAIN)

        self.assertNotIn(creature, self.game.legal_targets_for(spell))
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = 2
        with self.assertRaisesRegex(ValueError, "illegal target"):
            self.game.begin_cast(spell)
            self.game.complete_pending_cast((creature,))

    def test_armageddon_destroys_all_lands_but_not_other_permanents(self) -> None:
        lands = (
            self.put_in_play(self.alice, PLAINS),
            self.put_in_play(self.alice, SAVANNAH),
            self.put_in_play(self.bob, SWAMP),
            self.put_in_play(self.bob, TUNDRA),
        )
        creature = self.put_in_play(self.bob, GRIZZLY_BEARS)

        self.cast(ARMAGEDDON)

        self.assertTrue(all(land.zone is Zone.GRAVEYARD for land in lands))
        self.assertIn(creature, self.bob.battlefield)

    def test_flashfires_uses_plains_subtype_including_dual_lands(self) -> None:
        plains = self.put_in_play(self.bob, PLAINS)
        tundra = self.put_in_play(self.bob, TUNDRA)
        mountain = self.put_in_play(self.bob, MOUNTAIN)

        self.cast(FLASHFIRES)

        self.assertIn(plains, self.bob.graveyard)
        self.assertIn(tundra, self.bob.graveyard)
        self.assertIn(mountain, self.bob.battlefield)

    def test_tsunami_uses_island_subtype_including_dual_lands(self) -> None:
        island = self.put_in_play(self.bob, ISLAND)
        tropical = self.put_in_play(self.bob, TROPICAL_ISLAND)
        swamp = self.put_in_play(self.bob, SWAMP)

        self.cast(TSUNAMI)

        self.assertIn(island, self.bob.graveyard)
        self.assertIn(tropical, self.bob.graveyard)
        self.assertIn(swamp, self.bob.battlefield)

    def test_global_land_destruction_needs_no_land_in_play(self) -> None:
        spell = self.cast(FLASHFIRES)

        self.assertIn(spell, self.alice.graveyard)


if __name__ == "__main__":
    unittest.main()
