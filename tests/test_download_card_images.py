import unittest

from tools.download_card_images import (
    build_downloads,
    card_filename,
    image_uris,
    load_expected_names,
    validate_remote_catalog,
)


class CardImageDownloadTests(unittest.TestCase):
    def test_all_beta_names_have_unique_stable_filenames(self):
        names = load_expected_names()
        stems = [card_filename(name) for name in names]

        self.assertEqual(len(stems), 292)
        self.assertEqual(len(set(stems)), 292)
        self.assertEqual(card_filename("Nevinyrral's Disk"), "nevinyrrals-disk")
        self.assertEqual(
            card_filename("Circle of Protection: Blue"),
            "circle-of-protection-blue",
        )

    def test_download_plan_uses_art_crop_and_requested_full_size(self):
        cards = [
            {
                "id": "abc",
                "name": "Air Elemental",
                "image_uris": {
                    "art_crop": "https://cards.example/art.jpg",
                    "large": "https://cards.example/large.jpg",
                    "png": "https://cards.example/card.png",
                },
            }
        ]

        downloads, manifest = build_downloads(cards, self.output_path(), full_size="png")

        self.assertEqual([item.kind for item in downloads], ["art crop", "full card"])
        self.assertEqual(downloads[0].destination.name, "air-elemental.jpg")
        self.assertEqual(downloads[1].destination.name, "air-elemental.png")
        self.assertEqual(manifest["Air Elemental"]["scryfall_id"], "abc")
        self.assertEqual(
            manifest["Air Elemental"]["full_card"],
            "full_cards/air-elemental.png",
        )

    def test_card_face_images_are_supported_as_a_fallback(self):
        card = {
            "name": "Example",
            "card_faces": [{"image_uris": {"art_crop": "art", "large": "large"}}],
        }

        self.assertEqual(image_uris(card)["art_crop"], "art")

    def test_remote_catalog_must_exactly_match_local_names(self):
        validate_remote_catalog(
            [{"name": "Air Elemental"}, {"name": "Ancestral Recall"}],
            {"Air Elemental", "Ancestral Recall"},
        )
        with self.assertRaisesRegex(ValueError, "missing"):
            validate_remote_catalog(
                [{"name": "Air Elemental"}],
                {"Air Elemental", "Ancestral Recall"},
            )

    @staticmethod
    def output_path():
        # Pure path planning only; this test deliberately creates no temp files.
        from pathlib import Path

        return Path("generated-images")


if __name__ == "__main__":
    unittest.main()
