import unittest

from beta_magic import (
    CLOCKWORK_BEAST,
    GRIZZLY_BEARS,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class ClockworkBeastTests(unittest.TestCase):
    def setUp(self):
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        player.battlefield.append(card)
        return card

    def test_enters_fully_wound_as_a_seven_four(self):
        beast = self.permanent(self.alice, CLOCKWORK_BEAST)
        self.assertEqual(beast.counters, {"+1/+0": 7})
        self.assertEqual(self.game.creature_power(beast), 7)
        self.assertEqual(self.game.creature_toughness(beast), 4)

    def test_loses_counter_immediately_when_declared_attacker(self):
        beast = self.permanent(self.alice, CLOCKWORK_BEAST)
        self.game.begin_combat()
        self.game.declare_attackers((beast,))

        self.assertEqual(beast.counters["+1/+0"], 6)
        self.assertEqual(self.game.creature_power(beast), 6)

    def test_loses_counter_once_when_declared_blocker(self):
        attacker = self.permanent(self.alice, GRIZZLY_BEARS)
        beast = self.permanent(self.bob, CLOCKWORK_BEAST)
        self.game.begin_combat()
        self.game.declare_attackers((attacker,))
        self.game.declare_blockers({beast: attacker})

        self.assertEqual(beast.counters["+1/+0"], 6)

    def test_counter_loss_and_reentry_reset(self):
        beast = self.permanent(self.alice, CLOCKWORK_BEAST)
        beast.counters["+1/+0"] = 2
        self.game._move_card(beast, Zone.GRAVEYARD)
        self.assertEqual(beast.counters, {})
        beast.controller_id = self.alice.id
        self.game._move_card(beast, Zone.BATTLEFIELD)
        self.assertEqual(beast.counters, {"+1/+0": 7})

    def test_untap_choice_can_rewind_partially_and_keeps_beast_tapped(self):
        beast = self.permanent(self.alice, CLOCKWORK_BEAST)
        beast.counters["+1/+0"] = 4
        beast.tapped = True
        self.alice.mana_pool.colorless = 2
        self.game._enter_phase(TurnPhase.UNTAP)

        self.assertIs(self.game.current_counter_rewind(), beast)
        self.assertEqual(self.game.maximum_counter_rewind(), 2)
        self.game.choose_counter_rewind("a", 2)

        self.assertEqual(beast.counters["+1/+0"], 6)
        self.assertTrue(beast.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)

    def test_declining_rewind_allows_normal_untap(self):
        beast = self.permanent(self.alice, CLOCKWORK_BEAST)
        beast.counters["+1/+0"] = 6
        beast.tapped = True
        self.game._enter_phase(TurnPhase.UNTAP)

        self.game.choose_counter_rewind("a", 0)
        self.assertFalse(beast.tapped)
        self.assertEqual(beast.counters["+1/+0"], 6)

    def test_ui_exposes_counters_and_rewind_choice(self):
        beast = self.permanent(self.alice, CLOCKWORK_BEAST)
        beast.counters["+1/+0"] = 5
        self.alice.mana_pool.colorless = 1
        self.game._enter_phase(TurnPhase.UNTAP)
        view = GameViewModel(self.game)

        self.assertTrue(view.state["counterRewindRequired"])
        self.assertEqual(view.state["counterRewindMaximum"], 1)
        data = view._presentation._card_data(beast)
        self.assertEqual(data["counters"], [{"name": "+1/+0", "amount": 5}])


if __name__ == "__main__":
    unittest.main()
