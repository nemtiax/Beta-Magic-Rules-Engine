from types import SimpleNamespace
import unittest

from beta_draft import DraftSession, default_catalog


class _CyclingGenerator:
    def __init__(self):
        self.cards = tuple(default_catalog())
        self.calls = 0

    def generate_pack(self):
        start = self.calls % len(self.cards)
        self.calls += 1
        return tuple(
            self.cards[(start + offset) % len(self.cards)]
            for offset in range(15)
        )


class _FirstBot:
    def __init__(self):
        self._pool = []
        self.contexts = []

    @property
    def pool(self):
        return tuple(self._pool)

    def pick_with_details(self, pack, *, context=None):
        self.contexts.append(context)
        self._pool.append(pack[0])
        return SimpleNamespace(index=0, card=pack[0])


class DraftSessionTests(unittest.TestCase):
    def session(self, *, table_size=4, rounds=3):
        bots = [_FirstBot() for _ in range(table_size - 1)]
        session = DraftSession(
            generator=_CyclingGenerator(),
            bots=bots,
            table_size=table_size,
            rounds=rounds,
        )
        return session, bots

    def test_starts_with_a_fifteen_card_human_pack(self):
        session, _ = self.session()

        self.assertEqual(len(session.current_pack), 15)
        self.assertEqual((session.round_number, session.pick_number), (1, 1))
        self.assertEqual(session.passing_direction, "left")
        self.assertFalse(session.complete)

    def test_human_and_every_bot_pick_before_pack_is_passed_left(self):
        session, bots = self.session()
        initial_ids = tuple(session.pack_ids)
        chosen = session.current_pack[3]

        result = session.pick(chosen.id)

        self.assertIs(result, chosen)
        self.assertEqual(session.human_pool, [chosen])
        self.assertTrue(all(len(bot.pool) == 1 for bot in bots))
        self.assertEqual(len(session.current_pack), 14)
        self.assertEqual(session.pack_ids[0], initial_ids[-1])
        self.assertEqual(session.pick_number, 2)
        self.assertEqual(bots[0].contexts[0].pack_id, initial_ids[1])

    def test_second_round_passes_right(self):
        session, _ = self.session()
        for _ in range(15):
            session.pick(session.current_pack[0].id)
        second_round_ids = tuple(session.pack_ids)

        session.pick(session.current_pack[0].id)

        self.assertEqual((session.round_number, session.pick_number), (2, 2))
        self.assertEqual(session.passing_direction, "right")
        self.assertEqual(session.pack_ids[0], second_round_ids[1])

    def test_complete_draft_conserves_all_picks(self):
        session, bots = self.session(table_size=3, rounds=2)

        while not session.complete:
            session.pick(session.current_pack[-1].id)

        self.assertEqual(len(session.human_pool), 30)
        self.assertTrue(all(len(bot.pool) == 30 for bot in bots))
        self.assertEqual(
            len(session.human_pool) + sum(len(bot.pool) for bot in bots),
            3 * 2 * 15,
        )
        self.assertEqual(session.current_pack, ())

    def test_invalid_human_choice_does_not_advance_draft(self):
        session, bots = self.session()
        original_ids = [card.id for card in session.current_pack]

        with self.assertRaisesRegex(ValueError, "not in the current pack"):
            session.pick("not-a-card")

        self.assertEqual([card.id for card in session.current_pack], original_ids)
        self.assertEqual(session.pick_number, 1)
        self.assertFalse(session.human_pool)
        self.assertTrue(all(not bot.pool for bot in bots))

    def test_default_session_can_use_no_basic_land_packs(self):
        session = DraftSession(table_size=2, no_basic_lands=True, seed=5)

        self.assertTrue(session.no_basic_lands)
        self.assertFalse(
            {"Plains", "Island", "Swamp", "Mountain", "Forest"}
            & {offered.card.name for offered in session.current_pack}
        )

    def test_default_session_can_color_balance_its_common_slots(self):
        session = DraftSession(
            table_size=2,
            color_balanced=True,
            seed=6,
        )

        common_colors = {
            offered.card.colors[0]
            for offered in session.current_pack[4:]
            if len(offered.card.colors) == 1 and not offered.card.is_land
        }
        self.assertTrue(session.color_balanced)
        self.assertEqual(common_colors, set("WUBRG"))


if __name__ == "__main__":
    unittest.main()
