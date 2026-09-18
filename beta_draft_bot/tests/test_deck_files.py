import json
from pathlib import Path
import unittest
from unittest.mock import patch

from beta_draft.deck_files import build_deck_document, save_deck_file


class DeckFileTests(unittest.TestCase):
    def test_document_is_versioned_and_aggregates_card_names(self):
        document = build_deck_document(
            "Ruby Lightning",
            ["Mountain"] * 17 + ["Lightning Bolt"] * 23,
        )

        self.assertEqual(document["format"], "beta-magic-deck")
        self.assertEqual(document["version"], 1)
        self.assertEqual(document["name"], "Ruby Lightning")
        self.assertEqual(
            document["cards"],
            [
                {"name": "Lightning Bolt", "count": 23},
                {"name": "Mountain", "count": 17},
            ],
        )

    def test_document_rejects_invalid_names(self):
        with self.assertRaisesRegex(ValueError, "deck name"):
            build_deck_document("", ["Mountain"] * 40)
        with self.assertRaisesRegex(ValueError, "card names"):
            build_deck_document("Deck", [""])

    def test_save_adds_json_suffix_and_writes_utf8(self):
        with patch.object(Path, "write_text") as write_text:
            destination = save_deck_file(
                "ruby-lightning",
                "Ruby Lightning",
                ["Mountain"] * 40,
            )

        self.assertEqual(destination, Path("ruby-lightning.json"))
        payload = json.loads(write_text.call_args.args[0])
        self.assertEqual(payload["cards"], [{"name": "Mountain", "count": 40}])
        self.assertEqual(write_text.call_args.kwargs, {"encoding": "utf-8"})


if __name__ == "__main__":
    unittest.main()
