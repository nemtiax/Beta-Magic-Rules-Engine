import unittest

from beta_magic import CARDS_BY_NAME
from beta_magic.card_defs.green import GREEN_CARDS
from beta_magic.types import Color


EXPECTED_NAMES = {
    "Birds of Paradise",
    "Craw Wurm",
    "Elvish Archers",
    "Force of Nature",
    "Giant Growth",
    "Giant Spider",
    "Grizzly Bears",
    "Hurricane",
    "Ice Storm",
    "Ironroot Treefolk",
    "Llanowar Elves",
    "Regeneration",
    "Regrowth",
    "Scryb Sprites",
    "Shanodin Dryads",
    "Stream of Life",
    "Tranquility",
    "Tsunami",
    "Wall of Brambles",
    "Wall of Ice",
    "Wall of Wood",
    "Wanderlust",
    "War Mammoth",
    "Web",
}


class GreenDefinitionMigrationTests(unittest.TestCase):
    def test_all_supported_green_cards_are_migrated(self) -> None:
        self.assertEqual(len(GREEN_CARDS), 24)
        self.assertEqual(
            {card.name for card in GREEN_CARDS}, EXPECTED_NAMES
        )
        self.assertTrue(all(Color.GREEN in card.colors for card in GREEN_CARDS))

    def test_catalog_uses_canonical_green_definitions(self) -> None:
        for card in GREEN_CARDS:
            self.assertIs(CARDS_BY_NAME[card.name], card)


if __name__ == "__main__":
    unittest.main()
