import unittest

from beta_magic import (
    LORD_OF_THE_PIT,
    Card,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS, WHITE_KNIGHT
from beta_magic.ui import GameViewModel


class LordOfThePitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 30)
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 30)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        player.battlefield.append(card)
        return card

    def enter_upkeep(self) -> None:
        self.game.advance_phase()
        self.assertIs(self.game.current_phase, TurnPhase.UPKEEP)

    def finish_event(self) -> None:
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self) -> None:
        self.assertEqual(LORD_OF_THE_PIT.mana_cost.compact, "4BBB")
        self.assertEqual((LORD_OF_THE_PIT.power, LORD_OF_THE_PIT.toughness), (7, 7))
        self.assertIn(KeywordAbility.FLYING, LORD_OF_THE_PIT.abilities)
        self.assertIn(KeywordAbility.TRAMPLE, LORD_OF_THE_PIT.abilities)
        self.assertEqual(LORD_OF_THE_PIT.upkeep_effects[0].damage, 7)

    def test_an_eligible_creature_must_be_sacrificed(self) -> None:
        lord = self.permanent(self.alice, LORD_OF_THE_PIT)
        bear = self.permanent(self.alice, GRIZZLY_BEARS)
        self.enter_upkeep()

        self.assertTrue(self.game.upkeep_payment_required)
        self.assertEqual(self.game.legal_upkeep_sacrifices(self.alice.id), [bear])
        with self.assertRaisesRegex(RuntimeError, "choose whether to pay"):
            self.game.pass_priority(self.alice.id)

        self.game.choose_upkeep_sacrifice(self.alice.id, bear)
        self.assertEqual(bear.zone, Zone.GRAVEYARD)
        self.assertIn(lord, self.alice.battlefield)
        self.finish_event()
        self.assertEqual(self.alice.life, 20)

    def test_lord_cannot_sacrifice_itself(self) -> None:
        lord = self.permanent(self.alice, LORD_OF_THE_PIT)
        self.enter_upkeep()

        self.assertEqual(self.game.legal_upkeep_sacrifices(self.alice.id), [])
        self.assertFalse(self.game.upkeep_payment_required)
        self.finish_event()

        self.assertEqual(self.alice.life, 13)
        self.assertIn(lord, self.alice.battlefield)

    def test_protection_from_black_makes_creature_ineligible(self) -> None:
        self.permanent(self.alice, LORD_OF_THE_PIT)
        knight = self.permanent(self.alice, WHITE_KNIGHT)
        self.enter_upkeep()

        self.assertNotIn(knight, self.game.legal_upkeep_sacrifices(self.alice.id))
        self.finish_event()

        self.assertEqual(self.alice.life, 13)
        self.assertIn(knight, self.alice.battlefield)

    def test_failure_damage_is_black_and_uses_damage_windows(self) -> None:
        self.permanent(self.alice, LORD_OF_THE_PIT)
        self.game.pause_for_damage_windows = True
        self.enter_upkeep()
        self.finish_event()

        self.assertIsNotNone(self.game.pending_damage)
        packet = self.game.pending_damage.packets[0]
        self.assertEqual(packet.amount, 7)
        self.assertIn(next(iter(LORD_OF_THE_PIT.colors)), packet.colors)
        self.assertEqual(self.alice.life, 20)

    def test_ui_highlights_and_records_the_required_sacrifice(self) -> None:
        self.permanent(self.alice, LORD_OF_THE_PIT)
        bear = self.permanent(self.alice, GRIZZLY_BEARS)
        self.enter_upkeep()
        view = GameViewModel(self.game)

        state = view.state
        self.assertTrue(state["upkeepSacrificeRequired"])
        self.assertTrue(view._card_data(bear)["upkeepSacrificeEligible"])
        view.selected_card_ids = {bear.id}
        view.chooseUpkeepSacrifice()

        self.assertEqual(bear.zone, Zone.GRAVEYARD)
        self.assertFalse(view.state["upkeepSacrificeRequired"])


if __name__ == "__main__":
    unittest.main()
