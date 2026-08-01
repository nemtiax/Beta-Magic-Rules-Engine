import unittest

from beta_magic import (
    FARMSTEAD,
    MANA_VAULT,
    PARALYZE,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS, PLAINS


class OptionalUpkeepPaymentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "a", "Alice", [GRIZZLY_BEARS] * 30
        )
        self.bob = PlayerState.with_deck(
            "b", "Bob", [GRIZZLY_BEARS] * 30
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def permanent(player, definition, *, attached=None):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
            enchanted_card_id=attached.id if attached else None,
        )
        player.battlefield.append(card)
        return card

    def enter_upkeep(self) -> None:
        if self.game.current_phase is TurnPhase.UNTAP:
            self.game.advance_phase()
        else:
            self.game._enter_phase(TurnPhase.UPKEEP)

    def finish_event(self) -> None:
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def resolve_batch(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_farmstead_land_controller_may_buy_one_life(self):
        land = self.permanent(self.alice, PLAINS)
        self.permanent(self.bob, FARMSTEAD, attached=land)
        self.enter_upkeep()
        self.alice.mana_pool.white = 2

        self.assertTrue(self.game.upkeep_payment_required)
        self.assertEqual(self.game.timed_events[0].affected_player_id, "a")
        self.game.choose_upkeep_payment(self.alice.id, pay=True)
        self.finish_event()

        self.assertEqual(self.alice.life, 21)
        self.assertEqual(self.alice.mana_pool.white, 0)
        self.assertEqual(self.game.timed_events, [])

    def test_declining_farmstead_has_no_consequence(self):
        land = self.permanent(self.alice, PLAINS)
        farmstead = self.permanent(self.alice, FARMSTEAD, attached=land)
        self.enter_upkeep()

        self.game.choose_upkeep_payment(self.alice.id, pay=False)
        self.finish_event()

        self.assertEqual(self.alice.life, 20)
        self.assertIn(farmstead, self.alice.battlefield)

    def test_paralyze_prevents_normal_untap(self):
        creature = self.permanent(self.alice, GRIZZLY_BEARS)
        self.permanent(self.bob, PARALYZE, attached=creature)
        creature.tapped = True

        self.game._enter_phase(TurnPhase.UNTAP)

        self.assertTrue(creature.tapped)

    def test_each_paralyze_must_be_paid_before_creature_untaps(self):
        creature = self.permanent(self.alice, GRIZZLY_BEARS)
        self.permanent(self.bob, PARALYZE, attached=creature)
        self.permanent(self.bob, PARALYZE, attached=creature)
        creature.tapped = True
        self.enter_upkeep()
        self.alice.mana_pool.colorless = 8

        self.game.choose_upkeep_payment(self.alice.id, pay=True)
        self.finish_event()
        self.assertTrue(creature.tapped)

        self.game.choose_upkeep_payment(self.alice.id, pay=True)
        self.finish_event()
        self.assertFalse(creature.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)

    def test_mana_vault_makes_three_mana_and_does_not_untap_normally(self):
        vault = self.permanent(self.alice, MANA_VAULT)
        self.game._enter_phase(TurnPhase.MAIN)

        self.game.activate_ability(self.alice.id, vault, 0)
        self.assertTrue(vault.tapped)
        self.assertEqual(self.alice.mana_pool.colorless, 3)
        self.game._enter_phase(TurnPhase.UNTAP)
        self.assertTrue(vault.tapped)

    def test_mana_vault_can_be_paid_to_untap_at_any_time(self):
        vault = self.permanent(self.alice, MANA_VAULT)
        self.game._enter_phase(TurnPhase.MAIN)
        vault.tapped = True
        self.alice.mana_pool.colorless = 4

        self.game.activate_ability(self.alice.id, vault, 1)
        self.assertTrue(vault.tapped)
        self.resolve_batch()

        self.assertFalse(vault.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)

    def test_tapped_mana_vault_deals_one_during_controller_upkeep(self):
        vault = self.permanent(self.alice, MANA_VAULT)
        vault.tapped = True
        self.enter_upkeep()

        self.finish_event()

        self.assertEqual(self.alice.life, 19)

    def test_untapping_vault_in_response_avoids_upkeep_damage(self):
        vault = self.permanent(self.alice, MANA_VAULT)
        vault.tapped = True
        self.enter_upkeep()
        self.alice.mana_pool.colorless = 4

        self.game.activate_ability(self.alice.id, vault, 1)
        self.resolve_batch()
        self.finish_event()

        self.assertFalse(vault.tapped)
        self.assertEqual(self.alice.life, 20)


if __name__ == "__main__":
    unittest.main()
