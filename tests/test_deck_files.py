import json
from pathlib import Path
import unittest
from unittest.mock import patch

from beta_magic.deck_files import deck_from_document, load_deck_file


def deck_document(*, count: int = 40) -> dict:
    return {
        "format": "beta-magic-deck",
        "version": 1,
        "name": "Ruby Lightning",
        "cards": [
            {"name": "Mountain", "count": count // 2},
            {"name": "Lightning Bolt", "count": count - count // 2},
        ],
    }


class DeckFileTests(unittest.TestCase):
    def test_valid_document_resolves_card_counts_and_name(self) -> None:
        deck = deck_from_document(deck_document())

        self.assertEqual(deck.name, "Ruby Lightning")
        self.assertEqual(len(deck.cards), 40)
        self.assertEqual(
            sum(card.name == "Mountain" for card in deck.cards), 20
        )
        self.assertEqual(
            sum(card.name == "Lightning Bolt" for card in deck.cards), 20
        )

    def test_load_reads_utf8_json_before_validating(self) -> None:
        with patch.object(
            Path,
            "read_text",
            return_value=json.dumps(deck_document()),
        ) as read_text:
            deck = load_deck_file("ruby.json")

        read_text.assert_called_once_with(encoding="utf-8")
        self.assertEqual(deck.name, "Ruby Lightning")

    def test_rejects_malformed_or_unsupported_documents(self) -> None:
        cases = (
            ({}, "format"),
            ({**deck_document(), "version": 2}, "version"),
            ({**deck_document(), "cards": []}, "at least one"),
            ({**deck_document(), "cards": [{"name": "Mountain", "count": 0}]}, "count"),
            (
                {
                    **deck_document(),
                    "cards": [
                        {"name": "Mountain", "count": 20},
                        {"name": "Mountain", "count": 20},
                    ],
                },
                "duplicate",
            ),
            (
                {
                    **deck_document(),
                    "cards": [{"name": "Not a Beta Card", "count": 40}],
                },
                "unsupported",
            ),
            (deck_document(count=39), "at least 40"),
        )
        for document, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    deck_from_document(document)


if __name__ == "__main__":
    unittest.main()
