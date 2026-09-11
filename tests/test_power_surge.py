import unittest

from beta_magic import Card, CardType, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.green import GRIZZLY_BEARS
from beta_magic.card_defs.lands import MOUNTAIN
from beta_magic.card_defs.red import POWER_SURGE


class PowerSurgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 20)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 20)
        self.game = GameState([self.alice, self.bob])

    @staticmethod
    def permanent(player, definition, *, tapped=False, owner_id=None):
        card = Card(
            definition,
            owner_id or player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            tapped=tapped,
        )
        player.battlefield.append(card)
        return card

    def start_and_enter_upkeep(self):
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.advance_phase()
        self.assertIs(self.game.current_phase, TurnPhase.UPKEEP)

    def resolve_event(self):
        if self.game.pending_timed_event_order is not None:
            self.game.confirm_timed_event_order(self.alice.id)
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self):
        self.assertEqual(POWER_SURGE.mana_cost.compact, "RR")
        self.assertEqual(
            POWER_SURGE.card_types, frozenset({CardType.ENCHANTMENT})
        )
        self.assertTrue(
            POWER_SURGE.upkeep_effects[
                0
            ].counted_active_player_untapped_lands_at_turn_start
        )

    def test_uses_the_pre_untap_snapshot_and_deals_one_chunk(self):
        self.permanent(self.bob, POWER_SURGE)
        self.permanent(self.alice, MOUNTAIN)
        self.permanent(self.alice, MOUNTAIN)
        tapped = self.permanent(self.alice, MOUNTAIN, tapped=True)

        self.start_and_enter_upkeep()

        self.assertFalse(tapped.tapped)
        self.assertEqual(len(self.game.timed_events), 1)
        self.assertEqual(self.game.timed_events[0].effect.amount, 2)
        self.resolve_event()
        self.assertEqual(self.alice.life, 18)
        packets = self.game.resolved_damage_incidents[-1].packets
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0].amount, 2)

    def test_counts_controlled_lands_not_owned_lands(self):
        self.permanent(self.bob, POWER_SURGE)
        self.permanent(self.alice, MOUNTAIN, owner_id=self.bob.id)
        self.permanent(self.bob, MOUNTAIN, owner_id=self.alice.id)

        self.start_and_enter_upkeep()

        self.assertEqual(self.game.timed_events[0].effect.amount, 1)

    def test_no_untapped_lands_means_no_upkeep_event(self):
        self.permanent(self.bob, POWER_SURGE)
        self.permanent(self.alice, MOUNTAIN, tapped=True)
        self.permanent(self.alice, MOUNTAIN, tapped=True)

        self.start_and_enter_upkeep()

        self.assertEqual(self.game.timed_events, [])

    def test_each_power_surge_creates_a_separate_damage_event(self):
        self.permanent(self.alice, POWER_SURGE)
        self.permanent(self.bob, POWER_SURGE)
        self.permanent(self.alice, MOUNTAIN)

        self.start_and_enter_upkeep()

        self.assertEqual(len(self.game.timed_events), 2)
        self.resolve_event()
        self.assertEqual(self.alice.life, 19)
        self.assertEqual(len(self.game.timed_events), 1)
        self.resolve_event()
        self.assertEqual(self.alice.life, 18)


if __name__ == "__main__":
    unittest.main()
