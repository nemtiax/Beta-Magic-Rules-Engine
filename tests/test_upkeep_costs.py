import unittest

from beta_magic import (
    LIGHTNING_BOLT,
    FORCE_OF_NATURE,
    PHANTASMAL_FORCES,
    UPKEEP_CREATURES,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
    UpkeepFailure,
)
from beta_magic.card_defs import GRIZZLY_BEARS


class UpkeepCostTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 30
        )
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 30)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def put_in_play(player, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = player.id
        player.battlefield.append(card)
        return card

    @staticmethod
    def put_in_hand(player, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        player.hand.append(card)
        return card

    def enter_upkeep(self) -> None:
        self.game.advance_phase()
        self.assertIs(self.game.current_phase, TurnPhase.UPKEEP)

    def finish_event(self) -> None:
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_phantasmal_forces_definition(self) -> None:
        self.assertEqual(
            UPKEEP_CREATURES, (PHANTASMAL_FORCES, FORCE_OF_NATURE)
        )
        self.assertEqual(PHANTASMAL_FORCES.mana_cost.compact, "3U")
        self.assertEqual(
            (PHANTASMAL_FORCES.power, PHANTASMAL_FORCES.toughness), (4, 1)
        )
        self.assertIn(KeywordAbility.FLYING, PHANTASMAL_FORCES.abilities)
        self.assertEqual(
            PHANTASMAL_FORCES.upkeep_effects[0].mana_cost.compact, "U"
        )

    def test_force_of_nature_definition(self) -> None:
        self.assertEqual(FORCE_OF_NATURE.mana_cost.compact, "2GGGG")
        self.assertEqual((FORCE_OF_NATURE.power, FORCE_OF_NATURE.toughness), (8, 8))
        self.assertIn(KeywordAbility.TRAMPLE, FORCE_OF_NATURE.abilities)
        upkeep = FORCE_OF_NATURE.upkeep_effects[0]
        self.assertEqual(upkeep.mana_cost.compact, "GGGG")
        self.assertIs(upkeep.failure, UpkeepFailure.DAMAGE_CONTROLLER)
        self.assertEqual(upkeep.damage, 8)

    def test_controller_must_choose_before_passing_priority(self) -> None:
        self.put_in_play(self.alice, PHANTASMAL_FORCES)
        self.enter_upkeep()

        self.assertTrue(self.game.upkeep_payment_required)
        with self.assertRaisesRegex(RuntimeError, "choose whether to pay"):
            self.game.pass_priority(self.alice.id)

    def test_paying_upkeep_spends_mana_and_keeps_creature(self) -> None:
        forces = self.put_in_play(self.alice, PHANTASMAL_FORCES)
        self.enter_upkeep()
        self.alice.mana_pool.blue = 1

        self.assertTrue(self.game.can_pay_upkeep_cost(self.alice.id))
        self.game.choose_upkeep_payment(self.alice.id, pay=True)
        self.assertEqual(self.alice.mana_pool.blue, 0)
        self.assertFalse(self.game.upkeep_payment_required)
        self.finish_event()

        self.assertIn(forces, self.alice.battlefield)

    def test_declining_upkeep_destroys_creature_after_response_window(self) -> None:
        forces = self.put_in_play(self.alice, PHANTASMAL_FORCES)
        self.enter_upkeep()

        self.game.choose_upkeep_payment(self.alice.id, pay=False)
        self.assertIn(forces, self.alice.battlefield)
        self.finish_event()

        self.assertIn(forces, self.alice.graveyard)

    def test_tapped_creature_still_requires_upkeep(self) -> None:
        forces = self.put_in_play(self.alice, PHANTASMAL_FORCES)
        forces.tapped = True

        self.enter_upkeep()

        self.assertTrue(forces.tapped)
        self.assertTrue(self.game.upkeep_payment_required)

    def test_source_removed_during_response_needs_no_payment(self) -> None:
        forces = self.put_in_play(self.alice, PHANTASMAL_FORCES)
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        self.enter_upkeep()
        self.alice.mana_pool.red = 1

        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((forces,))
        self.finish_event()
        self.assertIn(forces, self.alice.graveyard)
        self.assertFalse(self.game.upkeep_payment_required)

        self.finish_event()
        self.assertEqual(self.game.timed_events, [])

    def test_declining_force_upkeep_deals_damage_but_keeps_creature(self) -> None:
        force = self.put_in_play(self.alice, FORCE_OF_NATURE)
        self.enter_upkeep()

        self.game.choose_upkeep_payment(self.alice.id, pay=False)
        self.finish_event()

        self.assertEqual(self.alice.life, 12)
        self.assertIn(force, self.alice.battlefield)
        self.game.advance_phase()
        self.game.advance_phase()
        self.game.begin_combat()
        self.game.declare_attackers([force])
        self.assertIn(force, self.game.combat.attackers)

    def test_paying_force_upkeep_prevents_damage(self) -> None:
        force = self.put_in_play(self.alice, FORCE_OF_NATURE)
        self.enter_upkeep()
        self.alice.mana_pool.green = 4

        self.game.choose_upkeep_payment(self.alice.id, pay=True)
        self.finish_event()

        self.assertEqual(self.alice.life, 20)
        self.assertEqual(self.alice.mana_pool.green, 0)
        self.assertIn(force, self.alice.battlefield)


if __name__ == "__main__":
    unittest.main()
