import unittest

from beta_magic import CARDS_BY_NAME
from beta_magic.card_defs.black import BLACK_CARDS
from beta_magic.types import Color


EXPECTED_NAMES = {
    "Bad Moon",
    "Black Knight",
    "Bog Wraith",
    "Contract from Below",
    "Cursed Land",
    "Deathlace",
    "Deathgrip",
    "Demonic Hordes",
    "Dark Ritual",
    "Drudge Skeletons",
    "Evil Presence",
    "Fear",
    "Frozen Shade",
    "Gloom",
    "Howl from Beyond",
    "Hypnotic Specter",
    "Lord of the Pit",
    "Mind Twist",
    "Nettling Imp",
    "Nightmare",
    "Paralyze",
    "Pestilence",
    "Plague Rats",
    "Raise Dead",
    "Royal Assassin",
    "Scathe Zombies",
    "Scavenging Ghoul",
    "Sengir Vampire",
    "Simulacrum",
    "Sinkhole",
    "Terror",
    "Unholy Strength",
    "Wall of Bone",
    "Warp Artifact",
    "Weakness",
    "Will-o'-the-Wisp",
    "Zombie Master",
}


class BlackDefinitionMigrationTests(unittest.TestCase):
    def test_all_supported_black_cards_are_migrated(self) -> None:
        self.assertEqual(len(BLACK_CARDS), 37)
        self.assertEqual(
            {card.name for card in BLACK_CARDS}, EXPECTED_NAMES
        )
        self.assertTrue(all(Color.BLACK in card.colors for card in BLACK_CARDS))

    def test_catalog_uses_canonical_black_definitions(self) -> None:
        for card in BLACK_CARDS:
            self.assertIs(CARDS_BY_NAME[card.name], card)


if __name__ == "__main__":
    unittest.main()
