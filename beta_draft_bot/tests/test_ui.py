from importlib.util import find_spec
from types import SimpleNamespace
import unittest

from beta_draft import DraftCard, DraftSession, default_catalog


PYSIDE_AVAILABLE = find_spec("PySide6") is not None
if PYSIDE_AVAILABLE:
    from beta_draft.ui import DraftViewModel, _pool_sort_key, _present_card


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

    @property
    def pool(self):
        return tuple(self._pool)

    def pick_with_details(self, pack, *, context=None):
        self._pool.append(pack[0])
        return SimpleNamespace(index=0, card=pack[0])


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is an optional dependency")
class DraftPresentationTests(unittest.TestCase):
    def test_preview_contains_printed_rules_text_and_display_fields(self):
        card = DraftCard("bolt-1", default_catalog().get("Lightning Bolt"))

        presented = _present_card(card)

        self.assertEqual(presented["name"], "Lightning Bolt")
        self.assertEqual(presented["manaCost"], "R")
        self.assertIn("3 damage", presented["rulesText"])
        self.assertEqual(presented["colorLabel"], "Red")
        self.assertIn("artCropUrl", presented)
        self.assertIn("fullCardUrl", presented)

    def test_pool_sorting_uses_color_then_mana_value(self):
        catalog = default_catalog()
        cards = [
            DraftCard("land", catalog.get("Island")),
            DraftCard("red", catalog.get("Fireball")),
            DraftCard("blue-five", catalog.get("Air Elemental")),
            DraftCard("blue-one", catalog.get("Flight")),
            DraftCard("white", catalog.get("Healing Salve")),
            DraftCard("artifact", catalog.get("Sol Ring")),
        ]

        ordered = [card.card.name for card in sorted(cards, key=_pool_sort_key)]

        self.assertEqual(
            ordered,
            ["Healing Salve", "Flight", "Air Elemental", "Fireball", "Sol Ring", "Island"],
        )

    def test_drafting_updates_pack_pool_message_and_preview(self):
        session = DraftSession(
            generator=_CyclingGenerator(),
            bots=[_FirstBot()],
            table_size=2,
            rounds=1,
        )
        model = DraftViewModel(session=session)
        choice = session.current_pack[3]

        model.draftCard(choice.id)
        state = model.state

        self.assertEqual(len(state["pack"]), 14)
        self.assertEqual(state["poolCount"], 1)
        self.assertEqual(state["pool"][0]["id"], choice.id)
        group = next(group for group in state["poolGroups"] if group["count"])
        self.assertEqual(group["cards"][0]["id"], choice.id)
        self.assertEqual(state["preview"]["id"], choice.id)
        self.assertIn(choice.card.name, state["message"])

    def test_pool_groups_are_fixed_and_each_stack_is_mana_value_ordered(self):
        session = DraftSession(
            generator=_CyclingGenerator(),
            bots=[_FirstBot()],
            table_size=2,
            rounds=1,
        )
        catalog = default_catalog()
        session.human_pool[:] = [
            DraftCard("blue-five", catalog.get("Air Elemental")),
            DraftCard("land", catalog.get("Island")),
            DraftCard("blue-one", catalog.get("Flight")),
        ]
        groups = DraftViewModel(session=session).state["poolGroups"]

        self.assertEqual(
            [group["label"] for group in groups],
            ["White", "Blue", "Black", "Red", "Green", "Multicolor", "Colorless", "Lands"],
        )
        self.assertEqual(
            [card["name"] for card in groups[1]["cards"]],
            ["Flight", "Air Elemental"],
        )
        self.assertEqual([card["name"] for card in groups[7]["cards"]], ["Island"])

    def test_hovering_an_offered_card_changes_preview_without_changing_draft(self):
        session = DraftSession(
            generator=_CyclingGenerator(),
            bots=[_FirstBot()],
            table_size=2,
            rounds=1,
        )
        model = DraftViewModel(session=session)
        first = session.current_pack[0]
        model.draftCard(first.id)
        second = session.current_pack[1]

        model.inspectCard(second.id)

        self.assertEqual(model.state["preview"]["id"], second.id)
        self.assertEqual(model.state["poolCount"], 1)

    def test_advisor_highlights_exactly_one_physical_card(self):
        session = DraftSession(
            generator=_CyclingGenerator(),
            bots=[_FirstBot()],
            table_size=2,
            rounds=1,
        )
        model = DraftViewModel(session=session, advisor_enabled=True)

        state = model.state
        recommended = [card for card in state["pack"] if card["botRecommended"]]

        self.assertEqual(len(recommended), 1)
        self.assertEqual(state["advisorPickName"], recommended[0]["name"])

    def test_advisor_records_human_override_instead_of_its_recommendation(self):
        session = DraftSession(
            generator=_CyclingGenerator(),
            bots=[_FirstBot()],
            table_size=2,
            rounds=1,
        )
        model = DraftViewModel(session=session, advisor_enabled=True)
        recommendation_id = next(
            card["id"] for card in model.state["pack"] if card["botRecommended"]
        )
        human_choice = next(
            card for card in session.current_pack if card.id != recommendation_id
        )

        model.draftCard(human_choice.id)

        self.assertEqual(model._advisor.pool, (human_choice.card.name,))
        self.assertEqual(
            sum(card["botRecommended"] for card in model.state["pack"]),
            1,
        )

    def test_hidden_advisor_tracks_picks_and_can_be_revealed_later(self):
        session = DraftSession(
            generator=_CyclingGenerator(),
            bots=[_FirstBot()],
            table_size=2,
            rounds=1,
        )
        model = DraftViewModel(session=session)
        human_choice = session.current_pack[-1]

        self.assertFalse(any(card["botRecommended"] for card in model.state["pack"]))
        model.draftCard(human_choice.id)
        model.setAdvisorEnabled(True)

        self.assertEqual(model._advisor.pool, (human_choice.card.name,))
        self.assertTrue(model.state["advisorEnabled"])
        self.assertEqual(
            sum(card["botRecommended"] for card in model.state["pack"]),
            1,
        )

    def test_score_display_exposes_every_ranked_card_score(self):
        session = DraftSession(
            generator=_CyclingGenerator(),
            bots=[_FirstBot()],
            table_size=2,
            rounds=1,
        )
        model = DraftViewModel(
            session=session,
            advisor_enabled=True,
            score_display_enabled=True,
        )
        expected = {
            evaluation.index: evaluation.score
            for evaluation in model._advisor.rank(
                [card.card.name for card in session.current_pack],
                context=model._draft_context(),
            )
        }

        state = model.state

        self.assertTrue(state["scoreDisplayEnabled"])
        self.assertEqual(len(expected), len(state["pack"]))
        for index, card in enumerate(state["pack"]):
            self.assertAlmostEqual(card["botScore"], expected[index])
            self.assertEqual(card["botScoreText"], f"{expected[index]:.2f}")
        recommended = next(card for card in state["pack"] if card["botRecommended"])
        self.assertEqual(
            recommended["botScore"],
            max(card["botScore"] for card in state["pack"]),
        )

    def test_score_display_can_be_toggled_without_enabling_pick_highlight(self):
        model = DraftViewModel(seed=17, table_size=2, rounds=1)

        model.setScoreDisplayEnabled(True)
        state = model.state

        self.assertTrue(state["scoreDisplayEnabled"])
        self.assertTrue(all(card["botScoreText"] for card in state["pack"]))
        self.assertFalse(any(card["botRecommended"] for card in state["pack"]))

        model.setScoreDisplayEnabled(False)
        self.assertTrue(
            all(card["botScore"] is None for card in model.state["pack"])
        )

    def test_color_plan_display_exposes_all_weighted_hypotheses(self):
        model = DraftViewModel(
            seed=23,
            table_size=2,
            rounds=1,
            color_plan_display_enabled=True,
        )

        state = model.state
        plans = state["colorPlans"]

        self.assertTrue(state["colorPlanDisplayEnabled"])
        self.assertEqual(len(plans), 15)
        self.assertAlmostEqual(sum(plan["weight"] for plan in plans), 1.0)
        self.assertEqual(
            [plan["weight"] for plan in plans],
            sorted((plan["weight"] for plan in plans), reverse=True),
        )
        self.assertEqual(plans[0]["relativeWeight"], 1.0)
        self.assertTrue(all(plan["weightText"].endswith("%") for plan in plans))

    def test_new_draft_settings_are_applied_together(self):
        model = DraftViewModel(seed=12, table_size=2, rounds=1)
        model.draftCard(model.state["pack"][0]["id"])

        model.startNewDraft(True, True, 3, 2)
        state = model.state
        common_colors = {
            card["colorLabel"] for card in state["pack"][4:]
            if card["colorLabel"] in {"White", "Blue", "Black", "Red", "Green"}
        }

        self.assertTrue(state["noBasicLands"])
        self.assertTrue(state["colorBalanced"])
        self.assertEqual(state["tableSize"], 3)
        self.assertEqual(state["rounds"], 2)
        self.assertEqual(state["poolCount"], 0)
        self.assertEqual(
            common_colors,
            {"White", "Blue", "Black", "Red", "Green"},
        )
        self.assertIn("No-basic boosters", state["packStyle"])
        self.assertIn("3 players", state["packStyle"])
        self.assertIn("2 rounds", state["packStyle"])

    def test_invalid_new_draft_settings_do_not_replace_current_draft(self):
        model = DraftViewModel(seed=13, table_size=2, rounds=1)
        model.draftCard(model.state["pack"][0]["id"])
        pack_ids = [card["id"] for card in model.state["pack"]]

        model.startNewDraft(False, True, 1, 0)

        self.assertEqual(model.state["poolCount"], 1)
        self.assertEqual(
            [card["id"] for card in model.state["pack"]],
            pack_ids,
        )
        self.assertFalse(model.state["colorBalanced"])
        self.assertIn("at least two players", model.state["message"])


if __name__ == "__main__":
    unittest.main()
