import unittest

from beta_magic import (
    BENALISH_HERO,
    FALSE_ORDERS,
    GRIZZLY_BEARS,
    LURE,
    MESA_PEGASUS,
    PHANTOM_MONSTER,
    THICKET_BASILISK,
    TWO_HEADED_GIANT_OF_FORIYS,
    Card,
    CombatStep,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class FalseOrdersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 20
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player, definition, zone=Zone.BATTLEFIELD):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=zone,
        )
        player.cards_in(zone).append(card)
        return card

    def begin_blocked_combat(self, attackers, assignments) -> None:
        self.game.begin_combat()
        self.game.declare_attackers(attackers)
        self.game.declare_blockers(assignments)
        self.assertEqual(self.game.combat.step, CombatStep.BLOCKER_RESPONSE)

    def cast_false_orders(self, blocker, caster=None):
        caster = caster or self.alice
        spell = self.card(caster, FALSE_ORDERS, Zone.HAND)
        caster.mana_pool.red = 1
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((blocker,))
        while self.game.stack:
            priority = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(priority.id)
        return spell

    def test_definition_casting_window_and_targets(self) -> None:
        spell = self.card(self.alice, FALSE_ORDERS, Zone.HAND)
        self.alice.mana_pool.red = 1
        with self.assertRaisesRegex(RuntimeError, "after blockers"):
            self.game.begin_cast(spell)

        attacker = self.card(self.alice, GRIZZLY_BEARS)
        blocker = self.card(self.bob, GRIZZLY_BEARS)
        nonblocker = self.card(self.bob, GRIZZLY_BEARS)
        self.begin_blocked_combat([attacker], {blocker: attacker})

        self.alice.mana_pool.red = 1
        self.game.begin_cast(spell)
        self.assertEqual(
            set(self.game.legal_targets_for()), {blocker, nonblocker}
        )

    def test_reassignment_retroactively_unblocks_the_old_attacker(self) -> None:
        first = self.card(self.alice, GRIZZLY_BEARS)
        second = self.card(self.alice, GRIZZLY_BEARS)
        blocker = self.card(self.bob, GRIZZLY_BEARS)
        self.begin_blocked_combat([first, second], {blocker: first})
        spell = self.cast_false_orders(blocker)

        self.assertEqual(
            self.game.pending_false_orders_choices[0].chooser_id,
            self.alice.id,
        )
        self.game.choose_false_orders_assignment(self.alice.id, (second,))

        self.assertEqual(self.game.combat.blockers[first.id], [])
        self.assertEqual(self.game.combat.blockers[second.id], [blocker])
        self.assertIn(spell, self.alice.graveyard)

        self.game.advance_combat()
        self.game.deal_combat_damage()
        self.assertEqual(self.bob.life, 18)

    def test_a_nonblocking_defender_can_be_made_to_block(self) -> None:
        attacker = self.card(self.alice, GRIZZLY_BEARS)
        blocker = self.card(self.bob, GRIZZLY_BEARS)
        self.begin_blocked_combat([attacker], {})
        self.cast_false_orders(blocker)

        self.game.choose_false_orders_assignment(self.alice.id, (attacker,))

        self.assertEqual(self.game.combat.blockers[attacker.id], [blocker])

    def test_replacement_order_must_be_a_legal_block(self) -> None:
        flyer = self.card(self.alice, PHANTOM_MONSTER)
        ground_creature = self.card(self.alice, GRIZZLY_BEARS)
        blocker = self.card(self.bob, GRIZZLY_BEARS)
        self.begin_blocked_combat([flyer, ground_creature], {blocker: ground_creature})
        self.cast_false_orders(blocker)

        with self.assertRaisesRegex(ValueError, "cannot legally block"):
            self.game.choose_false_orders_assignment(self.alice.id, (flyer,))
        self.assertTrue(self.game.pending_false_orders_choices)

    def test_false_orders_cannot_remove_a_mandatory_lure_block(self) -> None:
        lured = self.card(self.alice, GRIZZLY_BEARS)
        other = self.card(self.alice, GRIZZLY_BEARS)
        lure = self.card(self.alice, LURE)
        lure.enchanted_card_id = lured.id
        blocker = self.card(self.bob, GRIZZLY_BEARS)
        self.begin_blocked_combat([lured, other], {blocker: lured})
        self.cast_false_orders(blocker)

        with self.assertRaisesRegex(ValueError, "Lured attacker"):
            self.game.choose_false_orders_assignment(self.alice.id, ())
        with self.assertRaisesRegex(ValueError, "Lured attacker"):
            self.game.choose_false_orders_assignment(self.alice.id, (other,))
        self.game.choose_false_orders_assignment(self.alice.id, (lured,))

    def test_reassignment_handles_bands_and_multiple_block_capacity(self) -> None:
        hero = self.card(self.alice, BENALISH_HERO)
        pegasus = self.card(self.alice, MESA_PEGASUS)
        other = self.card(self.alice, GRIZZLY_BEARS)
        giant = self.card(self.bob, TWO_HEADED_GIANT_OF_FORIYS)
        self.game.begin_combat()
        self.game.declare_attackers(
            [hero, pegasus, other], bands=[(hero, pegasus)]
        )
        self.game.declare_blockers({giant: other})
        self.cast_false_orders(giant)

        self.game.choose_false_orders_assignment(self.alice.id, (hero, other))

        self.assertEqual(self.game.combat.blockers[hero.id], [giant])
        self.assertEqual(self.game.combat.blockers[pegasus.id], [giant])
        self.assertEqual(self.game.combat.blockers[other.id], [giant])

    def test_reassignment_updates_basilisk_delayed_destruction(self) -> None:
        basilisk = self.card(self.alice, THICKET_BASILISK)
        bear = self.card(self.alice, GRIZZLY_BEARS)
        blocker = self.card(self.bob, GRIZZLY_BEARS)
        self.begin_blocked_combat([basilisk, bear], {blocker: basilisk})
        self.assertIn(blocker.id, self.game.combat.end_of_combat_destruction_ids)
        self.cast_false_orders(blocker)

        self.game.choose_false_orders_assignment(self.alice.id, (bear,))

        self.assertNotIn(
            blocker.id, self.game.combat.end_of_combat_destruction_ids
        )

    def test_ui_preloads_edits_and_confirms_the_assignment(self) -> None:
        first = self.card(self.alice, GRIZZLY_BEARS)
        second = self.card(self.alice, GRIZZLY_BEARS)
        blocker = self.card(self.bob, GRIZZLY_BEARS)
        self.begin_blocked_combat([first, second], {blocker: first})
        self.cast_false_orders(blocker)
        view = GameViewModel(self.game)

        state = view.state
        self.assertTrue(state["falseOrdersChoiceRequired"])
        self.assertTrue(state["canChooseFalseOrders"])
        self.assertTrue(state["settingBlockers"])
        self.assertEqual(
            view._combat_ui.false_orders_assignment(self.game), (first,)
        )

        view.toggleCard(str(second.id))
        view.setBlocks()
        view.confirmFalseOrders()

        self.assertFalse(self.game.pending_false_orders_choices)
        self.assertEqual(self.game.combat.blockers[first.id], [])
        self.assertEqual(self.game.combat.blockers[second.id], [blocker])


if __name__ == "__main__":
    unittest.main()
