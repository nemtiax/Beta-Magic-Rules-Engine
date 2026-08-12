import unittest

from beta_magic import CARDS_BY_NAME
from beta_magic.card_defs.green import GREEN_CARDS
from beta_magic.types import Color


EXPECTED_NAMES = {
    "Aspect of Wolf",
    "Berserk",
    "Birds of Paradise",
    "Cockatrice",
    "Craw Wurm",
    "Elvish Archers",
    "Fastbond",
    "Force of Nature",
    "Fog",
    "Fungusaur",
    "Gaea's Liege",
    "Giant Growth",
    "Giant Spider",
    "Grizzly Bears",
    "Hurricane",
    "Ice Storm",
    "Ironroot Treefolk",
    "Llanowar Elves",
    "Lifelace",
    "Lifeforce",
    "Living Lands",
    "Living Artifact",
    "Lure",
    "Natural Selection",
    "Ley Druid",
    "Regeneration",
    "Regrowth",
    "Scryb Sprites",
    "Shanodin Dryads",
    "Stream of Life",
    "Thicket Basilisk",
    "Timber Wolves",
    "Tranquility",
    "Tsunami",
    "Verduran Enchantress",
    "Wall of Brambles",
    "Wall of Ice",
    "Wall of Wood",
    "Wanderlust",
    "War Mammoth",
    "Web",
    "Wild Growth",
}


class GreenDefinitionMigrationTests(unittest.TestCase):
    def test_all_supported_green_cards_are_migrated(self) -> None:
        self.assertEqual(len(GREEN_CARDS), 42)
        self.assertEqual(
            {card.name for card in GREEN_CARDS}, EXPECTED_NAMES
        )
        self.assertTrue(all(Color.GREEN in card.colors for card in GREEN_CARDS))

    def test_catalog_uses_canonical_green_definitions(self) -> None:
        for card in GREEN_CARDS:
            self.assertIs(CARDS_BY_NAME[card.name], card)


if __name__ == "__main__":
    unittest.main()
