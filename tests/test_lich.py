import unittest

from beta_magic import Card, DamageIncidentKind, GameState, PlayerState, Zone
from beta_magic.card_defs.black import LICH
from beta_magic.card_defs.green import GRIZZLY_BEARS
from beta_magic.card_defs.artifacts import GIANT_WASP_TOKEN
from beta_magic.card_defs.lands import SWAMP
from beta_magic.ui import GameViewModel


class LichTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [SWAMP] * 20)
        self.bob = PlayerState.with_deck("b", "Bob", [SWAMP] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def add(player, definition, zone=Zone.BATTLEFIELD, *, token=False):
        card = Card(definition, player.id, zone=zone, is_token=token)
        player.cards_in(zone).append(card)
        return card

    def add_lich(self):
        lich = self.add(self.alice, LICH, Zone.HAND)
        self.game._move_card(lich, Zone.BATTLEFIELD)
        return lich

    def damage_alice(self, amount, *other_packets):
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        for target, damage in other_packets:
            self.game._deal_damage(target, damage, "test")
        self.game._deal_damage(self.alice, amount, "test")
        self.game._resolve_damage_incident()

    def test_entering_play_sets_life_to_zero_and_life_gain_becomes_draws(self):
        self.add_lich()
        self.assertEqual(self.alice.life, 0)
        before = len(self.alice.hand)
        self.game._gain_life(self.alice, 3)
        self.assertEqual(self.alice.life, 0)
        self.assertEqual(len(self.alice.hand), before + 3)
        self.assertFalse(self.alice.has_lost)

    def test_each_lich_multiplies_draws_and_damage_payment(self):
        self.add_lich()
        self.add_lich()
        permanents = [self.add(self.alice, SWAMP) for _ in range(4)]
        before = len(self.alice.hand)
        self.game._gain_life(self.alice, 2)
        self.assertEqual(len(self.alice.hand), before + 4)
        self.damage_alice(1)
        self.assertEqual(self.game.pending_lich_choices[0].amount, 2)
        self.game.choose_lich_cards(self.alice.id, tuple(permanents[:2]))
        self.assertTrue(all(card in self.alice.graveyard for card in permanents[:2]))

    def test_tokens_and_simultaneously_lethal_creatures_are_not_candidates(self):
        self.add_lich()
        safe = self.add(self.alice, SWAMP)
        lethal = self.add(self.alice, GRIZZLY_BEARS)
        token = self.add(self.alice, GIANT_WASP_TOKEN, token=True)
        self.damage_alice(1, (lethal, 2))
        choice = self.game.pending_lich_choices[0]
        self.assertIn(safe.id, choice.candidate_ids)
        self.assertNotIn(lethal.id, choice.candidate_ids)
        self.assertNotIn(token.id, choice.candidate_ids)

    def test_damage_does_not_change_life_but_requires_cards(self):
        self.add_lich()
        swamp = self.add(self.alice, SWAMP)
        self.damage_alice(1)
        self.assertEqual(self.alice.life, 0)
        self.assertFalse(self.alice.has_lost)
        self.game.choose_lich_cards(self.alice.id, (swamp,))
        self.assertIn(swamp, self.alice.graveyard)
        self.assertIsNone(self.game.pending_damage)

    def test_insufficient_cards_is_an_absolute_loss(self):
        self.add_lich()
        self.damage_alice(2)
        self.assertTrue(self.alice.has_lost)
        self.assertFalse(self.game.pending_lich_choices)

    def test_destroying_lich_is_an_absolute_loss(self):
        lich = self.add_lich()
        self.game._move_card(lich, Zone.GRAVEYARD)
        self.assertTrue(self.alice.has_lost)
        self.game._gain_life(self.alice, 10)
        self.assertTrue(self.alice.has_lost)

    def test_mana_burn_style_life_loss_does_not_affect_lich(self):
        self.add_lich()
        lost, prevented = self.game._lose_life(self.alice, 5)
        self.assertEqual((lost, prevented, self.alice.life), (0, 0, 0))
        self.assertFalse(self.game.pending_lich_choices)
        self.assertFalse(self.alice.has_lost)

    def test_ui_exposes_eligible_cards_and_completes_the_choice(self):
        self.add_lich()
        swamp = self.add(self.alice, SWAMP)
        self.damage_alice(1)
        view = GameViewModel(self.game)
        state = view.state
        self.assertTrue(state["lichChoiceRequired"])
        self.assertTrue(state["canChooseLich"])
        self.assertEqual(state["lichChoiceCount"], 1)
        shown = state["perspective"]["battlefield"]
        swamp_data = next(card for card in shown if card["id"] == str(swamp.id))
        self.assertTrue(swamp_data["lichEligible"])
        view.toggleCard(str(swamp.id))
        view.chooseLichSelected()
        self.assertFalse(self.game.pending_lich_choices)
        self.assertIn(swamp, self.alice.graveyard)


if __name__ == "__main__":
    unittest.main()
