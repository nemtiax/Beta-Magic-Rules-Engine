import unittest

from beta_magic import (
    DEATH_WARD,
    LIGHTNING_BOLT,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS


class RegenerationSpellTests(unittest.TestCase):
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
    def put_in_play(player: PlayerState, definition) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    @staticmethod
    def put_in_hand(player: PlayerState, definition) -> Card:
        card = Card(definition, player.id, zone=Zone.HAND)
        player.hand.append(card)
        return card

    def test_death_ward_can_answer_lethal_damage_in_same_batch(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        ward = self.put_in_hand(self.bob, DEATH_WARD)
        self.alice.mana_pool.red = 1
        self.bob.mana_pool.white = 1

        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((bear,))
        self.game.begin_cast(ward)
        self.game.complete_pending_cast((bear,))
        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)

        self.assertIn(bear, self.bob.battlefield)
        self.assertTrue(bear.tapped)
        self.assertEqual(bear.damage, 0)
        self.assertIn(bolt, self.alice.graveyard)
        self.assertIn(ward, self.bob.graveyard)

    def test_death_ward_does_not_override_tunnels_regeneration_ban(self) -> None:
        from beta_magic import TUNNEL, WALL_OF_BRAMBLES

        wall = self.put_in_play(self.bob, WALL_OF_BRAMBLES)
        tunnel = self.put_in_hand(self.alice, TUNNEL)
        ward = self.put_in_hand(self.bob, DEATH_WARD)
        self.alice.mana_pool.red = 1
        self.bob.mana_pool.white = 1

        self.game.begin_cast(tunnel)
        self.game.complete_pending_cast((wall,))
        self.game.begin_cast(ward)
        self.game.complete_pending_cast((wall,))
        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)

        self.assertIn(wall, self.bob.graveyard)


if __name__ == "__main__":
    unittest.main()
