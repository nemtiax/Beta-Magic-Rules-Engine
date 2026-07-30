import unittest

from beta_magic import ALL_CARDS, CARDS_BY_NAME, LIGHTNING_BOLT, card_named
from beta_magic.card_defs import (
    ARTIFACT_CARDS,
    BLACK_CARDS,
    BLUE_CARDS,
    GREEN_CARDS,
    LAND_CARDS,
    RED_CARDS,
    WHITE_CARDS,
)
from beta_magic.types import CardType, Color


class CardCatalogTests(unittest.TestCase):
    def test_catalog_has_unique_sorted_names(self) -> None:
        names = [card.name for card in ALL_CARDS]
        self.assertEqual(names, sorted(names))
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), set(CARDS_BY_NAME))

    def test_lookup_returns_canonical_definition(self) -> None:
        self.assertIs(card_named("Lightning Bolt"), LIGHTNING_BOLT)
        self.assertIs(CARDS_BY_NAME["Lightning Bolt"], LIGHTNING_BOLT)
        with self.assertRaisesRegex(KeyError, "unsupported Beta card"):
            card_named("Definitely Not a Beta Card")

    def test_color_modules_are_catalog_views(self) -> None:
        expected = {
            Color.WHITE: WHITE_CARDS,
            Color.BLUE: BLUE_CARDS,
            Color.BLACK: BLACK_CARDS,
            Color.RED: RED_CARDS,
            Color.GREEN: GREEN_CARDS,
        }
        for color, cards in expected.items():
            self.assertEqual(
                cards,
                tuple(card for card in ALL_CARDS if color in card.colors),
            )

    def test_artifact_and_land_modules_are_catalog_views(self) -> None:
        self.assertEqual(
            ARTIFACT_CARDS,
            tuple(
                card
                for card in ALL_CARDS
                if CardType.ARTIFACT in card.card_types
            ),
        )
        self.assertEqual(
            LAND_CARDS,
            tuple(
                card for card in ALL_CARDS if CardType.LAND in card.card_types
            ),
        )

    def test_mapping_is_read_only(self) -> None:
        with self.assertRaises(TypeError):
            CARDS_BY_NAME["Lightning Bolt"] = LIGHTNING_BOLT


if __name__ == "__main__":
    unittest.main()
