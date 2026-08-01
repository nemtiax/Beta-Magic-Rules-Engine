import unittest

from beta_magic import (
    BIRDS_OF_PARADISE,
    BLACK_LOTUS,
    COUNTERSPELL,
    LLANOWAR_ELVES,
    LIGHTNING_BOLT,
    MOX_SAPPHIRE,
    SOL_RING,
    SPELL_BLAST,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS


class InterruptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_hand(player, definition):
        card = Card(definition, owner_id=player.id, zone=Zone.HAND)
        player.hand.append(card)
        return card

    @staticmethod
    def put_in_play(player, definition):
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

    def cast_bolt(self):
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.bob,))
        return bolt

    def test_definitions_are_interrupts(self):
        self.assertEqual(COUNTERSPELL.mana_cost.compact, "UU")
        self.assertEqual(SPELL_BLAST.mana_cost.compact, "XU")
        self.assertIn(CardType.INTERRUPT, COUNTERSPELL.card_types)
        self.assertIn(CardType.INTERRUPT, SPELL_BLAST.card_types)

    def test_counterspell_resolves_before_and_counters_target(self):
        bolt = self.cast_bolt()
        counter = self.put_in_hand(self.bob, COUNTERSPELL)
        self.bob.mana_pool.blue = 2

        pending = self.game.begin_cast(counter)
        self.assertEqual(self.game.legal_targets_for(), [bolt])
        self.game.complete_pending_cast((bolt,))
        self.assertEqual(self.game.stack, [bolt, counter])

        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)

        self.assertEqual(bolt.zone, Zone.GRAVEYARD)
        self.assertEqual(counter.zone, Zone.GRAVEYARD)
        self.assertEqual(self.game.stack, [])
        self.assertEqual(self.bob.life, 20)

    def test_an_interrupt_can_counter_an_interrupt(self):
        bolt = self.cast_bolt()
        first = self.put_in_hand(self.bob, COUNTERSPELL)
        second = self.put_in_hand(self.alice, COUNTERSPELL)
        self.bob.mana_pool.blue = 2
        self.alice.mana_pool.blue = 2

        self.game.begin_cast(first)
        self.game.complete_pending_cast((bolt,))
        self.game.begin_cast(second)
        self.assertEqual(self.game.legal_targets_for(), [bolt, first])
        self.game.complete_pending_cast((first,))

        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        self.assertEqual(first.zone, Zone.GRAVEYARD)
        self.assertEqual(bolt.zone, Zone.STACK)

        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)
        self.assertEqual(self.bob.life, 17)

    def test_spell_blast_x_must_equal_declared_target_cost(self):
        bolt = self.cast_bolt()
        blast = self.put_in_hand(self.bob, SPELL_BLAST)
        self.bob.mana_pool.blue = 1
        self.bob.mana_pool.colorless = 2

        self.game.begin_cast(blast, x_value=2)
        self.assertEqual(self.game.legal_targets_for(), [])
        with self.assertRaisesRegex(ValueError, "illegal target"):
            self.game.complete_pending_cast((bolt,))
        self.game.cancel_pending_cast()

        self.game.begin_cast(blast, x_value=1)
        self.assertEqual(self.game.legal_targets_for(), [bolt])
        self.game.complete_pending_cast((bolt,))

    def test_interrupt_cannot_be_cast_without_current_spell(self):
        counter = self.put_in_hand(self.alice, COUNTERSPELL)
        self.alice.mana_pool.blue = 2
        with self.assertRaisesRegex(RuntimeError, "immediately"):
            self.game.begin_cast(counter)

    def test_interrupt_speed_mana_abilities_invalidate_prior_passes(self):
        sources = (
            (LLANOWAR_ELVES, 0),
            (BIRDS_OF_PARADISE, 1),
            (MOX_SAPPHIRE, 0),
            (SOL_RING, 0),
            (BLACK_LOTUS, 0),
        )
        for definition, ability_index in sources:
            with self.subTest(definition.name):
                self.setUp()
                source = self.put_in_play(self.alice, definition)
                bolt = self.cast_bolt()

                # Bob's pass cannot remain counted after Alice takes the
                # interrupt-speed action of producing mana.
                self.game.pass_priority(self.bob.id)
                self.assertEqual(self.game.consecutive_passes, 1)
                self.game.activate_ability(
                    self.alice.id, source, ability_index
                )

                self.assertEqual(self.game.consecutive_passes, 0)
                self.assertIs(
                    self.game.players[self.game.priority_player_index],
                    self.alice,
                )
                self.assertEqual(self.game.interruptible_spell_id, bolt.id)

                self.game.pass_priority(self.alice.id)
                self.assertEqual(bolt.zone, Zone.STACK)
                self.game.pass_priority(self.bob.id)
                self.assertEqual(self.bob.life, 17)

    def test_mana_ability_preserves_an_interrupt_chain(self):
        bolt = self.cast_bolt()
        counter = self.put_in_hand(self.bob, COUNTERSPELL)
        mox = self.put_in_play(self.bob, MOX_SAPPHIRE)
        self.bob.mana_pool.blue = 2
        self.game.begin_cast(counter)
        self.game.complete_pending_cast((bolt,))

        self.game.pass_priority(self.alice.id)
        self.game.activate_ability(self.bob.id, mox, 0)

        self.assertEqual(self.game.consecutive_passes, 0)
        self.assertEqual(self.game.interruptible_spell_id, bolt.id)
        self.assertEqual(self.game.stack, [bolt, counter])
        self.game.pass_priority(self.bob.id)
        self.assertEqual(counter.zone, Zone.STACK)
        self.game.pass_priority(self.alice.id)
        self.assertEqual(counter.zone, Zone.GRAVEYARD)
        self.assertEqual(bolt.zone, Zone.GRAVEYARD)


if __name__ == "__main__":
    unittest.main()
