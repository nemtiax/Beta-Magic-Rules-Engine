import unittest
from unittest.mock import patch

from beta_magic import ALL_CARDS
from beta_magic.card_defs.catalog import card_named
from beta_magic.deck_files import LoadedDeck
from beta_magic.decks import (
    AEGIS_WARDS_DECK,
    ARCANE_DEPTHS_DECK,
    COPPER_CONTROL_DECK,
    COPPER_PRESSURE_DECK,
    ELEMENTAL_SURGE_DECK,
    MOONLIT_HORDE_DECK,
    RADIANT_CHARGE_DECK,
    SPECTRUM_ASSAULT_DECK,
    STONEFIRE_DECK,
    VERDANT_TIDES_DECK,
    IVORY_LAYERS_DECK,
    SHADOW_COATS_DECK,
    CAMOUFLAGE_RAIDERS_DECK,
    CAMOUFLAGE_GUARDIANS_DECK,
    make_saved_deck_game,
)


class SeededDeckModuleTests(unittest.TestCase):
    def test_seeded_decks_only_use_canonical_catalog_definitions(self) -> None:
        canonical_ids = {id(card) for card in ALL_CARDS}
        for deck in (
            VERDANT_TIDES_DECK,
            STONEFIRE_DECK,
            RADIANT_CHARGE_DECK,
            MOONLIT_HORDE_DECK,
            COPPER_CONTROL_DECK,
            COPPER_PRESSURE_DECK,
            ARCANE_DEPTHS_DECK,
            ELEMENTAL_SURGE_DECK,
            AEGIS_WARDS_DECK,
            SPECTRUM_ASSAULT_DECK,
            IVORY_LAYERS_DECK,
            SHADOW_COATS_DECK,
            CAMOUFLAGE_RAIDERS_DECK,
            CAMOUFLAGE_GUARDIANS_DECK,
        ):
            self.assertEqual(len(deck), 20)
            self.assertTrue(all(id(card) in canonical_ids for card in deck))

    def test_saved_deck_game_uses_file_names_and_all_card_copies(self) -> None:
        first = LoadedDeck("Ruby Lightning", (card_named("Mountain"),) * 40)
        second = LoadedDeck("Verdant Might", (card_named("Forest"),) * 40)

        with patch(
            "beta_magic.decks.load_deck_file",
            side_effect=(first, second),
        ) as load:
            game = make_saved_deck_game("first.json", "second.json")

        self.assertEqual(load.call_args_list[0].args, ("first.json",))
        self.assertEqual(load.call_args_list[1].args, ("second.json",))
        self.assertEqual(
            [player.name for player in game.players],
            ["Ruby Lightning", "Verdant Might"],
        )
        for player in game.players:
            self.assertEqual(len(player.hand) + len(player.library), 40)

if __name__ == "__main__":
    unittest.main()
