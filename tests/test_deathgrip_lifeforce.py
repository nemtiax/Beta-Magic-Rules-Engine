import unittest

from beta_magic import (
    DEATHGRIP,
    DEATHLACE,
    GIANT_GROWTH,
    GRIZZLY_BEARS,
    LIFEFORCE,
    TERROR,
    ActivatedCounterSpellAbility,
    Card,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class DeathgripLifeforceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 20)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.bear = self.permanent(self.alice, GRIZZLY_BEARS)

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        player.battlefield.append(card)
        return card

    @staticmethod
    def hand(player, definition):
        card = Card(definition, owner_id=player.id, zone=Zone.HAND)
        player.hand.append(card)
        return card

    def pass_both(self):
        first = self.game.players[self.game.priority_player_index].id
        self.game.pass_priority(first)
        second = self.game.players[self.game.priority_player_index].id
        self.game.pass_priority(second)

    def cast_growth(self):
        growth = self.hand(self.alice, GIANT_GROWTH)
        self.alice.mana_pool.green = 1
        self.game.begin_cast(growth)
        self.game.complete_pending_cast((self.bear,))
        return growth

    def test_symmetric_definitions(self):
        self.assertEqual(DEATHGRIP.mana_cost.compact, "BB")
        self.assertEqual(LIFEFORCE.mana_cost.compact, "GG")
        deathgrip = DEATHGRIP.activated_abilities[0]
        lifeforce = LIFEFORCE.activated_abilities[0]
        self.assertIsInstance(deathgrip, ActivatedCounterSpellAbility)
        self.assertEqual(deathgrip.spell_color, Color.GREEN)
        self.assertEqual(lifeforce.spell_color, Color.BLACK)
        self.assertFalse(deathgrip.tap_cost)

    def test_deathgrip_counters_a_green_spell_as_an_interrupt(self):
        grip = self.permanent(self.bob, DEATHGRIP)
        growth = self.cast_growth()
        self.bob.mana_pool.black = 2

        self.game.activate_ability(self.bob.id, grip, 0)
        self.assertEqual(self.game.legal_targets_for(), [growth])
        self.game.complete_pending_activation((growth,))
        self.assertEqual(self.bob.mana_pool.black, 0)

        self.pass_both()

        self.assertEqual(growth.zone, Zone.GRAVEYARD)
        self.assertEqual(self.game.creature_power(self.bear), 2)

    def test_lifeforce_counters_a_black_spell(self):
        force = self.permanent(self.alice, LIFEFORCE)
        terror = self.hand(self.bob, TERROR)
        self.bob.mana_pool.black = 1
        self.bob.mana_pool.colorless = 1
        self.game.begin_cast(terror)
        self.game.complete_pending_cast((self.bear,))
        self.alice.mana_pool.green = 2

        self.game.activate_ability(self.alice.id, force, 0)
        self.game.complete_pending_activation((terror,))
        self.pass_both()

        self.assertEqual(terror.zone, Zone.GRAVEYARD)
        self.assertEqual(self.bear.zone, Zone.BATTLEFIELD)

    def test_color_is_rechecked_after_a_lace_resolves(self):
        grip = self.permanent(self.bob, DEATHGRIP)
        growth = self.cast_growth()
        self.bob.mana_pool.black = 2
        self.game.activate_ability(self.bob.id, grip, 0)
        self.game.complete_pending_activation((growth,))
        self.game.pass_priority(self.bob.id)

        lace = self.hand(self.alice, DEATHLACE)
        self.alice.mana_pool.black = 1
        self.game.begin_cast(lace)
        self.game.complete_pending_cast((growth,))
        self.pass_both()  # Deathlace resolves first.
        self.assertEqual(self.game.card_colors(growth), {Color.BLACK})

        self.pass_both()  # Deathgrip now sees a black spell and does nothing.
        self.assertEqual(growth.zone, Zone.STACK)
        self.pass_both()  # Giant Growth resolves normally.
        self.assertEqual(self.game.creature_power(self.bear), 5)


if __name__ == "__main__":
    unittest.main()
