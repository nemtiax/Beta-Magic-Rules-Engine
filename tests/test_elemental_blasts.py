import unittest

from beta_magic import (
    BLUE_ELEMENTAL_BLAST,
    LIGHTNING_BOLT,
    RED_ELEMENTAL_BLAST,
    UTHDEN_TROLL,
    WATER_ELEMENTAL,
    Card,
    CardType,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS


class ElementalBlastTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "a", "Alice", [GRIZZLY_BEARS] * 12
        )
        self.bob = PlayerState.with_deck(
            "b", "Bob", [GRIZZLY_BEARS] * 12
        )
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

    def pass_twice(self) -> None:
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definitions_are_modal_interrupts(self) -> None:
        cases = (
            (BLUE_ELEMENTAL_BLAST, Color.BLUE, Color.RED, "U"),
            (RED_ELEMENTAL_BLAST, Color.RED, Color.BLUE, "R"),
        )
        for definition, color, target_color, cost in cases:
            with self.subTest(definition.name):
                self.assertIn(CardType.INTERRUPT, definition.card_types)
                self.assertEqual(definition.colors, frozenset({color}))
                self.assertEqual(
                    definition.target_requirement.color, target_color
                )
                self.assertEqual(definition.mana_cost.compact, cost)
                self.assertEqual(
                    definition.casting_modes,
                    ("Counter spell", "Destroy permanent"),
                )

    def test_modes_filter_stack_and_battlefield_targets(self) -> None:
        permanent = self.put_in_play(self.alice, UTHDEN_TROLL)
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.bob,))
        blast = self.put_in_hand(self.bob, BLUE_ELEMENTAL_BLAST)
        self.bob.mana_pool.blue = 2

        self.game.begin_cast(blast, mode="Counter spell")
        self.assertEqual(self.game.legal_targets_for(), [bolt])
        self.game.cancel_pending_cast()

        self.game.begin_cast(blast, mode="Destroy permanent")
        self.assertEqual(self.game.legal_targets_for(), [permanent])

    def test_counter_mode_counters_an_opposing_color_spell(self) -> None:
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.bob,))
        blast = self.put_in_hand(self.bob, BLUE_ELEMENTAL_BLAST)
        self.bob.mana_pool.blue = 1
        self.game.begin_cast(blast, mode="Counter spell")
        self.game.complete_pending_cast((bolt,))

        self.pass_twice()

        self.assertEqual(blast.zone, Zone.GRAVEYARD)
        self.assertEqual(bolt.zone, Zone.GRAVEYARD)
        self.assertEqual(self.bob.life, 20)

    def test_color_is_rechecked_after_an_earlier_interrupt(self) -> None:
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.bob,))
        blast = self.put_in_hand(self.bob, BLUE_ELEMENTAL_BLAST)
        self.bob.mana_pool.blue = 1
        self.game.begin_cast(blast, mode="Counter spell")
        self.game.complete_pending_cast((bolt,))

        # Models an earlier Lace in the interrupt sequence changing the spell.
        bolt.color_override = Color.BLUE
        self.pass_twice()
        self.assertEqual(bolt.zone, Zone.STACK)

        self.pass_twice()
        self.assertEqual(self.bob.life, 17)

    def test_destroy_mode_uses_the_regeneration_pathway(self) -> None:
        troll = self.put_in_play(self.alice, UTHDEN_TROLL)
        blast = self.put_in_hand(self.bob, BLUE_ELEMENTAL_BLAST)
        self.bob.mana_pool.blue = 1
        self.game.begin_cast(blast, mode="Destroy permanent")
        self.game.complete_pending_cast((troll,))

        self.pass_twice()

        self.assertIsNotNone(self.game.pending_destruction)
        self.assertEqual(troll.zone, Zone.BATTLEFIELD)

    def test_red_blast_destroys_a_blue_permanent(self) -> None:
        elemental = self.put_in_play(self.alice, WATER_ELEMENTAL)
        blast = self.put_in_hand(self.bob, RED_ELEMENTAL_BLAST)
        self.bob.mana_pool.red = 1
        self.game.begin_cast(blast, mode="Destroy permanent")
        self.game.complete_pending_cast((elemental,))

        self.pass_twice()

        self.assertEqual(elemental.zone, Zone.GRAVEYARD)
        self.assertIsNone(self.game.pending_destruction)


if __name__ == "__main__":
    unittest.main()
