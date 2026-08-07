import unittest

from beta_magic import CARDS_BY_NAME
from beta_magic.card_defs.white import WHITE_CARDS
from beta_magic.types import Color


EXPECTED_NAMES = {
    "Balance",
    "Benalish Hero",
    "Animate Wall",
    "Armageddon",
    "Black Ward",
    "Blaze of Glory",
    "Blessing",
    "Blue Ward",
    "Castle",
    "Circle of Protection: Black",
    "Circle of Protection: Blue",
    "Circle of Protection: Green",
    "Circle of Protection: Red",
    "Circle of Protection: White",
    "Conversion",
    "Crusade",
    "Death Ward",
    "Disenchant",
    "Farmstead",
    "Green Ward",
    "Healing Salve",
    "Holy Armor",
    "Holy Strength",
    "Karma",
    "Lance",
    "Mesa Pegasus",
    "Northern Paladin",
    "Pearled Unicorn",
    "Personal Incarnation",
    "Purelace",
    "Red Ward",
    "Resurrection",
    "Reverse Damage",
    "Righteousness",
    "Samite Healer",
    "Savannah Lions",
    "Serra Angel",
    "Swords to Plowshares",
    "Wall of Swords",
    "Veteran Bodyguard",
    "White Knight",
    "White Ward",
    "Wrath of God",
}


class WhiteDefinitionMigrationTests(unittest.TestCase):
    def test_all_supported_white_cards_are_migrated(self) -> None:
        self.assertEqual(len(WHITE_CARDS), 43)
        self.assertEqual(
            {card.name for card in WHITE_CARDS}, EXPECTED_NAMES
        )
        self.assertTrue(
            all(Color.WHITE in card.colors for card in WHITE_CARDS)
        )

    def test_catalog_uses_canonical_white_definitions(self) -> None:
        for card in WHITE_CARDS:
            self.assertIs(CARDS_BY_NAME[card.name], card)


if __name__ == "__main__":
    unittest.main()
