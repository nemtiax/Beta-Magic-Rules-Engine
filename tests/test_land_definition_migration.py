import unittest

from beta_magic import CARDS_BY_NAME
from beta_magic.card_defs.lands import BASIC_LANDS, DUAL_LANDS, LAND_CARDS


class LandDefinitionMigrationTests(unittest.TestCase):
    def test_catalog_uses_all_land_definitions(self) -> None:
        self.assertEqual(len(LAND_CARDS), 15)
        for land in LAND_CARDS:
            self.assertIs(CARDS_BY_NAME[land.name], land)

    def test_land_groups_cover_each_definition_once(self) -> None:
        self.assertTrue(set(BASIC_LANDS).isdisjoint(DUAL_LANDS))
        self.assertEqual(set(LAND_CARDS), set(BASIC_LANDS + DUAL_LANDS))


if __name__ == "__main__":
    unittest.main()
