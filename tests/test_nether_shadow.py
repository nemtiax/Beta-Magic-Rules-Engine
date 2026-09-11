import unittest

from beta_magic import (
    DARK_RITUAL,
    GRIZZLY_BEARS,
    ISLAND,
    NETHER_SHADOW,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class NetherShadowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [ISLAND] * 30)
        self.bob = PlayerState.with_deck("bob", "Bob", [ISLAND] * 30)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def grave_card(player, definition):
        card = Card(definition, player.id, zone=Zone.GRAVEYARD)
        player.graveyard.append(card)
        return card

    def enter_upkeep(self):
        while self.game.current_phase is not TurnPhase.UPKEEP:
            self.game.advance_phase()

    def resolve_batch(self):
        while self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self):
        self.assertEqual(NETHER_SHADOW.mana_cost.compact, "BB")
        self.assertEqual(
            NETHER_SHADOW.card_types, frozenset({CardType.CREATURE})
        )
        self.assertEqual((NETHER_SHADOW.power, NETHER_SHADOW.toughness), (1, 1))
        self.assertEqual(
            NETHER_SHADOW.activated_abilities[0].creatures_required_above, 3
        )

    def test_only_creature_cards_above_shadow_count(self):
        shadow = self.grave_card(self.alice, NETHER_SHADOW)
        self.grave_card(self.alice, GRIZZLY_BEARS)
        self.grave_card(self.alice, DARK_RITUAL)
        self.grave_card(self.alice, GRIZZLY_BEARS)
        self.enter_upkeep()
        self.assertEqual(self.game.legal_graveyard_returns(), ())

        self.grave_card(self.alice, GRIZZLY_BEARS)
        self.game._refresh_graveyard_return_choice()
        self.assertEqual(self.game.legal_graveyard_returns(), (shadow,))

    def test_return_is_a_fast_effect_and_not_a_spell(self):
        shadow = self.grave_card(self.alice, NETHER_SHADOW)
        for _ in range(3):
            self.grave_card(self.alice, GRIZZLY_BEARS)
        self.enter_upkeep()
        self.alice.mana_pool.black = 2

        self.game.activate_graveyard_return(self.alice.id, shadow)
        self.assertIn(shadow, self.alice.graveyard)
        self.assertEqual(self.game.stack, [])
        self.assertEqual(len(self.game.batch_abilities), 1)
        self.assertIs(self.game.players[self.game.priority_player_index], self.bob)

        self.resolve_batch()
        self.assertIn(shadow, self.alice.battlefield)
        self.assertIsNone(shadow.summoned_turn)
        self.assertEqual(self.alice.mana_pool.total, 0)

    def test_returned_shadow_can_attack_that_turn(self):
        shadow = self.grave_card(self.alice, NETHER_SHADOW)
        for _ in range(3):
            self.grave_card(self.alice, GRIZZLY_BEARS)
        self.enter_upkeep()
        self.alice.mana_pool.black = 2
        self.game.activate_graveyard_return(self.alice.id, shadow)
        self.resolve_batch()
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

        self.game.begin_combat()
        self.game.declare_attackers((shadow,))
        self.assertIn(shadow, self.game.combat.attackers)

    def test_player_can_decline_for_remainder_of_upkeep(self):
        self.grave_card(self.alice, NETHER_SHADOW)
        for _ in range(3):
            self.grave_card(self.alice, GRIZZLY_BEARS)
        self.enter_upkeep()

        self.game.finish_graveyard_returns(self.alice.id)
        self.assertIsNone(self.game.pending_graveyard_return_choice)
        self.game._refresh_graveyard_return_choice()
        self.assertIsNone(self.game.pending_graveyard_return_choice)


if __name__ == "__main__":
    unittest.main()
