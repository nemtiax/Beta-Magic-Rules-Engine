import unittest
from uuid import uuid4

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.blue import VOLCANIC_ERUPTION
from beta_magic.card_defs.green import GRIZZLY_BEARS
from beta_magic.card_defs.lands import BADLANDS, ISLAND, MOUNTAIN, VOLCANIC_ISLAND


class VolcanicEruptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState("a", "Alice")
        self.bob = PlayerState("b", "Bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def spell(self):
        card = Card(VOLCANIC_ERUPTION, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(card)
        return card

    def resolve_batch(self) -> None:
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_dual_lands_with_mountain_subtype_are_legal_targets(self) -> None:
        mountain = self.permanent(self.bob, MOUNTAIN)
        badlands = self.permanent(self.bob, BADLANDS)
        volcanic = self.permanent(self.alice, VOLCANIC_ISLAND)
        island = self.permanent(self.alice, ISLAND)
        spell = self.spell()
        self.alice.mana_pool.blue = 3
        self.alice.mana_pool.colorless = 3
        self.game.begin_cast(spell, x_value=3)
        legal = self.game.legal_targets_for()
        self.assertEqual(set(legal), {mountain, badlands, volcanic})
        self.assertNotIn(island, legal)

    def test_x_cannot_exceed_available_mountains(self) -> None:
        self.permanent(self.bob, MOUNTAIN)
        self.permanent(self.alice, BADLANDS)
        spell = self.spell()
        self.alice.mana_pool.blue = 3
        self.alice.mana_pool.colorless = 10
        self.assertEqual(self.game.maximum_affordable_x(spell), 2)
        with self.assertRaises(ValueError):
            self.game.begin_cast(spell, x_value=3)

    def test_x_zero_is_legal_with_no_mountains(self) -> None:
        spell = self.spell()
        self.alice.mana_pool.blue = 3
        pending = self.game.begin_cast(spell, x_value=0)
        self.assertIsNotNone(pending)
        self.game.complete_pending_cast(())

    def test_requires_exactly_x_distinct_mountain_targets(self) -> None:
        first = self.permanent(self.bob, MOUNTAIN)
        second = self.permanent(self.alice, BADLANDS)
        spell = self.spell()
        self.alice.mana_pool.blue = 3
        self.alice.mana_pool.colorless = 2
        self.game.begin_cast(spell, x_value=2)
        with self.assertRaises(ValueError):
            self.game.complete_pending_cast((first,))
        with self.assertRaises(ValueError):
            self.game.complete_pending_cast((first, first))
        self.game.complete_pending_cast((first, second))

    def test_destroys_targets_and_deals_x_to_every_creature_and_player(self) -> None:
        first = self.permanent(self.bob, MOUNTAIN)
        second = self.permanent(self.alice, VOLCANIC_ISLAND)
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        spell = self.spell()
        self.alice.mana_pool.blue = 3
        self.alice.mana_pool.colorless = 2
        self.game.begin_cast(spell, x_value=2)
        self.game.complete_pending_cast((first, second))
        self.resolve_batch()
        self.assertEqual(first.zone, Zone.GRAVEYARD)
        self.assertEqual(second.zone, Zone.GRAVEYARD)
        self.assertEqual(bear.zone, Zone.GRAVEYARD)
        self.assertEqual((self.alice.life, self.bob.life), (18, 18))

    def test_target_becoming_illegal_only_fizzles_that_portion(self) -> None:
        first = self.permanent(self.bob, MOUNTAIN)
        second = self.permanent(self.alice, MOUNTAIN)
        spell = self.spell()
        self.alice.mana_pool.blue = 3
        self.alice.mana_pool.colorless = 2
        self.game.begin_cast(spell, x_value=2)
        self.game.complete_pending_cast((first, second))

        # Stand in for an interrupt-speed characteristic change after the
        # targets and X have already been declared.
        second.land_type_marks[uuid4()] = ("Island", 1)
        self.resolve_batch()

        self.assertEqual(first.zone, Zone.GRAVEYARD)
        self.assertEqual(second.zone, Zone.BATTLEFIELD)
        self.assertEqual((self.alice.life, self.bob.life), (18, 18))


if __name__ == "__main__":
    unittest.main()
