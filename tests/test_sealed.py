from collections import Counter
from contextlib import redirect_stderr
from io import StringIO
import random
import unittest

from beta_magic.card_defs.catalog import ALL_CARDS
from beta_magic.decks import make_random_starter_game
from beta_magic.sealed import (
    BASIC_LAND_NAMES,
    BetaBoosterGenerator,
    BetaStarterGenerator,
    build_beta_print_sheets,
)
from beta_magic.ui import parse_args


class BetaSealedTests(unittest.TestCase):
    def test_print_sheets_include_historical_basic_land_slots(self) -> None:
        sheets = build_beta_print_sheets()

        self.assertEqual(len(sheets.rare), 121)
        self.assertEqual(len(sheets.uncommon), 121)
        self.assertEqual(len(sheets.common), 121)
        self.assertEqual(
            Counter(name for name in sheets.rare if name in BASIC_LAND_NAMES),
            {"Island": 4},
        )
        self.assertEqual(
            Counter(name for name in sheets.uncommon if name in BASIC_LAND_NAMES),
            {"Plains": 6, "Island": 2, "Swamp": 6, "Mountain": 6, "Forest": 6},
        )
        self.assertEqual(
            Counter(name for name in sheets.common if name in BASIC_LAND_NAMES),
            {"Plains": 8, "Island": 10, "Swamp": 9, "Mountain": 10, "Forest": 9},
        )

    def test_booster_and_starter_use_the_expected_sheet_counts(self) -> None:
        sheets = build_beta_print_sheets()
        booster = BetaBoosterGenerator(rng=random.Random(42)).generate_pack()
        starter = BetaStarterGenerator(rng=random.Random(42)).generate_starter()

        self.assertEqual(len(booster), 15)
        self.assertIn(booster[0], sheets.rare)
        self.assertTrue(all(name in sheets.uncommon for name in booster[1:4]))
        self.assertTrue(all(name in sheets.common for name in booster[4:]))
        self.assertEqual(len(starter), 60)
        self.assertTrue(all(name in sheets.rare for name in starter[:2]))
        self.assertTrue(all(name in sheets.uncommon for name in starter[2:15]))
        self.assertTrue(all(name in sheets.common for name in starter[15:]))

    def test_seeded_starters_are_reproducible_and_nonbasics_do_not_repeat(self) -> None:
        first = BetaStarterGenerator(rng=random.Random(1993)).generate_starter()
        second = BetaStarterGenerator(rng=random.Random(1993)).generate_starter()

        self.assertEqual(first, second)
        nonbasics = [name for name in first if name not in BASIC_LAND_NAMES]
        self.assertEqual(len(nonbasics), len(set(nonbasics)))

    def test_available_name_filter_preserves_slot_counts(self) -> None:
        available = {definition.name for definition in ALL_CARDS}
        generator = BetaStarterGenerator(
            rng=random.Random(7), available_names=available
        )

        starter = generator.generate_starter()

        self.assertEqual(len(starter), 60)
        self.assertTrue(set(starter) <= available)
        self.assertEqual(len(starter[:2]), 2)
        self.assertEqual(len(starter[2:15]), 13)
        self.assertEqual(len(starter[15:]), 45)

    def test_game_factory_gives_each_player_a_full_playable_starter(self) -> None:
        game = make_random_starter_game(rng=random.Random(94))
        supported = {
            definition.name
            for definition in ALL_CARDS
            if not definition.requires_ante
        }

        self.assertEqual([player.name for player in game.players], ["Worzel", "Thomil"])
        for player in game.players:
            cards = player.library + player.hand + player.graveyard + player.exile
            self.assertEqual(len(cards), 60)
            self.assertTrue({card.name for card in cards} <= supported)
            self.assertFalse(any(card.definition.requires_ante for card in cards))

    def test_random_starter_option_is_a_deck_mode(self) -> None:
        args = parse_args(["--random-starter-decks"])

        self.assertTrue(args.random_starter_decks)
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            parse_args(["--random-starter-decks", "--test-decks"])


if __name__ == "__main__":
    unittest.main()
