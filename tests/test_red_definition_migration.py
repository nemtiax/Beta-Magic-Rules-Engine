import unittest

from beta_magic import CARDS_BY_NAME
from beta_magic.card_defs.red import RED_CARDS
from beta_magic.types import Color


EXPECTED_NAMES = {
    "Burrowing",
    "Chaoslace",
    "Disintegrate",
    "Dragon Whelp",
    "Dwarven Demolition Team",
    "Dwarven Warriors",
    "Earth Elemental",
    "Earthquake",
    "Fire Elemental",
    "Firebreathing",
    "Flashfires",
    "Goblin Balloon Brigade",
    "Goblin King",
    "Granite Gargoyle",
    "Gray Ogre",
    "Hill Giant",
    "Hurloon Minotaur",
    "Ironclaw Orcs",
    "Keldon Warlord",
    "Lightning Bolt",
    "Manabarbs",
    "Mana Flare",
    "Mons's Goblin Raiders",
    "Orcish Artillery",
    "Orcish Oriflamme",
    "Roc of Kher Ridges",
    "Red Elemental Blast",
    "Sedge Troll",
    "Shatter",
    "Shivan Dragon",
    "Smoke",
    "Stone Rain",
    "Stone Giant",
    "Tunnel",
    "Two-Headed Giant of Foriys",
    "Uthden Troll",
    "Wall of Stone",
    "Wall of Fire",
    "Wheel of Fortune",
}


class RedDefinitionMigrationTests(unittest.TestCase):
    def test_all_supported_red_cards_are_migrated(self) -> None:
        self.assertEqual(len(RED_CARDS), 39)
        self.assertEqual(
            {card.name for card in RED_CARDS}, EXPECTED_NAMES
        )
        self.assertTrue(all(Color.RED in card.colors for card in RED_CARDS))

    def test_catalog_uses_canonical_red_definitions(self) -> None:
        for card in RED_CARDS:
            self.assertIs(CARDS_BY_NAME[card.name], card)


if __name__ == "__main__":
    unittest.main()
