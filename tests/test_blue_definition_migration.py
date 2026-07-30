import unittest

from beta_magic import CARDS_BY_NAME
from beta_magic.card_defs.blue import BLUE_CARDS
from beta_magic.types import Color


EXPECTED_NAMES = {
    "Air Elemental",
    "Ancestral Recall",
    "Braingeyser",
    "Feedback",
    "Flight",
    "Jump",
    "Lord of Atlantis",
    "Mahamoti Djinn",
    "Merfolk of the Pearl Trident",
    "Phantasmal Forces",
    "Phantom Monster",
    "Prodigal Sorcerer",
    "Psionic Blast",
    "Unsummon",
    "Wall of Air",
    "Water Elemental",
}


class BlueDefinitionMigrationTests(unittest.TestCase):
    def test_all_supported_blue_cards_are_migrated(self) -> None:
        self.assertEqual(len(BLUE_CARDS), 16)
        self.assertEqual(
            {card.name for card in BLUE_CARDS}, EXPECTED_NAMES
        )
        self.assertTrue(all(Color.BLUE in card.colors for card in BLUE_CARDS))

    def test_catalog_uses_canonical_blue_definitions(self) -> None:
        for card in BLUE_CARDS:
            self.assertIs(CARDS_BY_NAME[card.name], card)


if __name__ == "__main__":
    unittest.main()
