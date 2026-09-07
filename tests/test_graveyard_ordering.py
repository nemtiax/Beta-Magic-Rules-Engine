import unittest

from beta_magic import (
    GRIZZLY_BEARS,
    NETHER_SHADOW,
    SAVANNAH_LIONS,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class GraveyardOrderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
            summoned_turn=0,
        )
        player.battlefield.append(card)
        return card

    def test_owner_can_order_simultaneously_lethal_creatures(self):
        bears = self.permanent(self.alice, GRIZZLY_BEARS)
        lions = self.permanent(self.alice, SAVANNAH_LIONS)
        bears.damage = 2
        lions.damage = 1

        self.game.check_state_based_actions()

        choice = self.game.pending_graveyard_order_choices[0]
        self.assertEqual(choice.player_id, self.alice.id)
        self.assertEqual(choice.card_ids_bottom_to_top, [bears.id, lions.id])
        self.game.move_graveyard_order_card(self.alice.id, bears, 1)
        self.game.confirm_graveyard_order(self.alice.id)

        self.assertEqual(self.alice.graveyard[-2:], [lions, bears])
        self.assertIs(self.alice.graveyard[-1], bears)

    def test_each_owner_gets_a_separate_order_choice(self):
        alice_cards = [
            self.permanent(self.alice, GRIZZLY_BEARS),
            self.permanent(self.alice, SAVANNAH_LIONS),
        ]
        bob_cards = [
            self.permanent(self.bob, GRIZZLY_BEARS),
            self.permanent(self.bob, SAVANNAH_LIONS),
        ]
        for card in alice_cards + bob_cards:
            card.damage = 99

        self.game.check_state_based_actions()

        self.assertEqual(
            [choice.player_id for choice in self.game.pending_graveyard_order_choices],
            [self.alice.id, self.bob.id],
        )
        self.game.confirm_graveyard_order(self.alice.id)
        self.game.confirm_graveyard_order(self.bob.id)
        self.assertEqual(self.game.pending_graveyard_order_choices, [])

    def test_order_can_make_nether_shadow_eligible_next_upkeep(self):
        shadow = self.permanent(self.alice, NETHER_SHADOW)
        creatures = [
            self.permanent(self.alice, GRIZZLY_BEARS) for _ in range(3)
        ]
        for card in [shadow, *creatures]:
            card.damage = 99
        self.game.check_state_based_actions()

        choice = self.game.pending_graveyard_order_choices[0]
        while choice.card_ids_bottom_to_top.index(shadow.id) > 0:
            self.game.move_graveyard_order_card(self.alice.id, shadow, -1)
        self.game.confirm_graveyard_order(self.alice.id)

        while self.game.current_phase is not TurnPhase.UPKEEP:
            self.game.advance_phase()
        self.assertEqual(self.game.legal_graveyard_returns(), (shadow,))


if __name__ == "__main__":
    unittest.main()
