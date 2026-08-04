import unittest

from beta_magic import CARDS_BY_NAME
from beta_magic.card_defs.blue import BLUE_CARDS
from beta_magic.types import Color


EXPECTED_NAMES = {
    "Air Elemental",
    "Animate Artifact",
    "Ancestral Recall",
    "Braingeyser",
    "Blue Elemental Blast",
    "Control Magic",
    "Counterspell",
    "Creature Bond",
    "Feedback",
    "Flight",
    "Jump",
    "Lifetap",
    "Invisibility",
    "Lord of Atlantis",
    "Mahamoti Djinn",
    "Merfolk of the Pearl Trident",
    "Phantasmal Forces",
    "Phantasmal Terrain",
    "Phantom Monster",
    "Pirate Ship",
    "Prodigal Sorcerer",
    "Psionic Blast",
    "Psychic Venom",
    "Sea Serpent",
    "Siren's Call",
    "Spell Blast",
    "Steal Artifact",
    "Thoughtlace",
    "Time Walk",
    "Timetwister",
    "Twiddle",
    "Unsummon",
    "Wall of Air",
    "Wall of Water",
    "Water Elemental",
}


class BlueDefinitionMigrationTests(unittest.TestCase):
    def test_all_supported_blue_cards_are_migrated(self) -> None:
        self.assertEqual(len(BLUE_CARDS), 35)
        self.assertEqual(
            {card.name for card in BLUE_CARDS}, EXPECTED_NAMES
        )
        self.assertTrue(all(Color.BLUE in card.colors for card in BLUE_CARDS))

    def test_catalog_uses_canonical_blue_definitions(self) -> None:
        for card in BLUE_CARDS:
            self.assertIs(CARDS_BY_NAME[card.name], card)


if __name__ == "__main__":
    unittest.main()
