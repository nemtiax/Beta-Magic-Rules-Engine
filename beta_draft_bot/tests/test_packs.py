from collections import Counter
import random
import unittest

from beta_draft import (
    BASIC_LAND_NAMES,
    BetaBoosterGenerator,
    DraftBot,
    NoBasicLandBetaBoosterGenerator,
    build_beta_print_sheets,
    default_catalog,
    generate_beta_pack,
    generate_no_basic_land_beta_pack,
)
from beta_draft.packs import _balance_common_colors


class _TakeLastSlots:
    def sample(self, population, k):
        return list(population[-k:])


class BetaPackTests(unittest.TestCase):
    @staticmethod
    def common_colors(cards):
        return {
            card.colors[0]
            for card in cards
            if card.name not in BASIC_LAND_NAMES and len(card.colors) == 1
        }

    def test_print_sheets_have_historical_basic_land_slots(self):
        sheets = build_beta_print_sheets()

        self.assertEqual(len(sheets.rare), 121)
        self.assertEqual(len(sheets.uncommon), 121)
        self.assertEqual(len(sheets.common), 121)
        self.assertEqual(
            Counter(card.name for card in sheets.rare if card.name in BASIC_LAND_NAMES),
            {"Island": 4},
        )
        self.assertEqual(
            Counter(
                card.name
                for card in sheets.uncommon
                if card.name in BASIC_LAND_NAMES
            ),
            {"Plains": 6, "Island": 2, "Swamp": 6, "Mountain": 6, "Forest": 6},
        )
        self.assertEqual(
            Counter(
                card.name
                for card in sheets.common
                if card.name in BASIC_LAND_NAMES
            ),
            {"Plains": 8, "Island": 10, "Swamp": 9, "Mountain": 10, "Forest": 9},
        )

    def test_each_nonbasic_occupies_one_slot_on_its_rarity_sheet(self):
        sheets = build_beta_print_sheets()

        for rarity, expected in (("rare", 117), ("uncommon", 95), ("common", 75)):
            nonbasics = [
                card
                for card in sheets.for_rarity(rarity)
                if card.name not in BASIC_LAND_NAMES
            ]
            self.assertEqual(len(nonbasics), expected)
            self.assertEqual(len({card.name for card in nonbasics}), expected)
            self.assertTrue(all(card.rarity == rarity for card in nonbasics))

    def test_pack_contains_one_rare_three_uncommon_and_eleven_common_slots(self):
        generator = BetaBoosterGenerator(rng=random.Random(1993))

        pack = generator.generate_pack()

        self.assertEqual(len(pack), 15)
        self.assertIn(pack[0], generator.sheets.rare)
        self.assertTrue(all(card in generator.sheets.uncommon for card in pack[1:4]))
        self.assertTrue(all(card in generator.sheets.common for card in pack[4:]))

    def test_seeded_generation_is_reproducible(self):
        first = BetaBoosterGenerator(rng=random.Random(42))
        second = BetaBoosterGenerator(rng=random.Random(42))

        self.assertEqual(
            [card.name for card in first.generate_pack()],
            [card.name for card in second.generate_pack()],
        )

    def test_distinct_basic_slots_can_make_duplicate_lands_in_one_pack(self):
        pack = BetaBoosterGenerator(rng=_TakeLastSlots()).generate_pack()
        counts = Counter(card.name for card in pack)

        self.assertEqual(counts["Island"], 1)
        self.assertEqual(counts["Forest"], 12)
        self.assertEqual(counts["Mountain"], 2)

    def test_nonbasic_card_cannot_repeat_within_one_pack(self):
        generator = BetaBoosterGenerator(rng=random.Random(7))

        for _ in range(250):
            pack = generator.generate_pack()
            nonbasic_names = [
                card.name for card in pack if card.name not in BASIC_LAND_NAMES
            ]
            self.assertEqual(len(nonbasic_names), len(set(nonbasic_names)))

    def test_convenience_function_returns_catalog_cards(self):
        catalog = default_catalog()
        pack = generate_beta_pack(catalog=catalog, rng=random.Random(1))

        self.assertEqual(len(pack), 15)
        self.assertTrue(all(catalog.get(card.name) is card for card in pack))

    def test_generated_pack_can_be_passed_directly_to_draft_bot_by_name(self):
        pack = generate_beta_pack(rng=random.Random(1994))
        names = [card.name for card in pack]

        choice = DraftBot().pick(names)

        self.assertIn(choice, names)

    def test_unknown_sheet_name_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown Beta sheet rarity"):
            build_beta_print_sheets().for_rarity("mythic")

    def test_no_basic_land_generator_uses_only_actual_rarity_cards(self):
        generator = NoBasicLandBetaBoosterGenerator(rng=random.Random(1993))

        self.assertEqual(len(generator.rare_pool), 117)
        self.assertEqual(len(generator.uncommon_pool), 95)
        self.assertEqual(len(generator.common_pool), 75)
        for _ in range(250):
            pack = generator.generate_pack()
            self.assertEqual(len(pack), 15)
            self.assertTrue(all(card.name not in BASIC_LAND_NAMES for card in pack))
            self.assertEqual(pack[0].rarity, "rare")
            self.assertTrue(all(card.rarity == "uncommon" for card in pack[1:4]))
            self.assertTrue(all(card.rarity == "common" for card in pack[4:]))
            self.assertEqual(len({card.name for card in pack}), 15)

    def test_no_basic_land_generator_is_seedable(self):
        first = NoBasicLandBetaBoosterGenerator(rng=random.Random(94))
        second = NoBasicLandBetaBoosterGenerator(rng=random.Random(94))

        self.assertEqual(
            [card.name for card in first.generate_pack()],
            [card.name for card in second.generate_pack()],
        )

    def test_no_basic_land_convenience_function_integrates_with_bot(self):
        pack = generate_no_basic_land_beta_pack(rng=random.Random(2026))
        names = [card.name for card in pack]

        self.assertFalse(BASIC_LAND_NAMES.intersection(names))
        self.assertIn(DraftBot().pick(names), names)

    def test_balanced_historical_packs_represent_every_color_in_commons(self):
        generator = BetaBoosterGenerator(
            rng=random.Random(1993), color_balanced=True
        )

        for _ in range(250):
            pack = generator.generate_pack()
            self.assertEqual(self.common_colors(pack[4:]), set("WUBRG"))
            self.assertEqual(len(pack), 15)

    def test_balanced_no_basic_packs_represent_every_color(self):
        generator = NoBasicLandBetaBoosterGenerator(
            rng=random.Random(1994), color_balanced=True
        )

        for _ in range(250):
            pack = generator.generate_pack()
            self.assertEqual(self.common_colors(pack[4:]), set("WUBRG"))
            self.assertFalse(BASIC_LAND_NAMES.intersection(card.name for card in pack))

    def test_balancing_preserves_rare_and_uncommon_selections(self):
        ordinary = BetaBoosterGenerator(rng=random.Random(42))
        balanced = BetaBoosterGenerator(
            rng=random.Random(42), color_balanced=True
        )

        self.assertEqual(
            ordinary.generate_pack()[:4],
            balanced.generate_pack()[:4],
        )

    def test_balancing_replaces_surplus_colors_before_basic_lands(self):
        catalog = default_catalog()
        common_pool = build_beta_print_sheets().common
        selected = [
            catalog.get("Benalish Hero"),
            catalog.get("Holy Strength"),
            catalog.get("Flight"),
            catalog.get("Phantom Monster"),
            catalog.get("Scathe Zombies"),
            *([catalog.get("Plains")] * 6),
        ]

        balanced = _balance_common_colors(
            selected, common_pool, random.Random(8)
        )

        self.assertEqual(self.common_colors(balanced), set("WUBRG"))
        self.assertEqual(
            sum(card.name in BASIC_LAND_NAMES for card in balanced),
            6,
        )

    def test_balancing_replaces_a_basic_when_fewer_than_five_are_colored(self):
        catalog = default_catalog()
        common_pool = build_beta_print_sheets().common
        selected = [
            catalog.get("Benalish Hero"),
            catalog.get("Holy Strength"),
            catalog.get("Flight"),
            catalog.get("Scathe Zombies"),
            *([catalog.get("Plains")] * 7),
        ]

        balanced = _balance_common_colors(
            selected, common_pool, random.Random(9)
        )

        self.assertEqual(self.common_colors(balanced), set("WUBRG"))
        self.assertEqual(
            sum(card.name in BASIC_LAND_NAMES for card in balanced),
            6,
        )

    def test_color_balancing_flag_must_be_boolean(self):
        with self.assertRaisesRegex(TypeError, "color_balanced"):
            BetaBoosterGenerator(color_balanced=1)
        with self.assertRaisesRegex(TypeError, "color_balanced"):
            NoBasicLandBetaBoosterGenerator(color_balanced="yes")


if __name__ == "__main__":
    unittest.main()
