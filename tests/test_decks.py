import unittest

from beta_magic import ALL_CARDS
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
        ):
            self.assertEqual(len(deck), 20)
            self.assertTrue(all(id(card) in canonical_ids for card in deck))

    def test_ui_keeps_factory_imports_compatible(self) -> None:
        from beta_magic import ui
        from beta_magic.decks import make_demo_game

        self.assertIs(ui.make_demo_game, make_demo_game)


if __name__ == "__main__":
    unittest.main()
