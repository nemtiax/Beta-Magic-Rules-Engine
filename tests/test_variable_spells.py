import unittest

from beta_magic import (
    BRAINGEYSER,
    EARTHQUAKE,
    HOWL_FROM_BEYOND,
    HURRICANE,
    VARIABLE_SPELLS,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.flying_creatures import PHANTOM_MONSTER
from beta_magic.vanilla_creatures import GRIZZLY_BEARS


class VariableSpellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 30
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 30
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
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        player.hand.append(card)
        return card

    def resolve(self) -> None:
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def cast(self, definition, x_value, target=None) -> Card:
        spell = self.put_in_hand(self.alice, definition)
        self.alice.mana_pool.white = 10
        self.alice.mana_pool.blue = 10
        self.alice.mana_pool.black = 10
        self.alice.mana_pool.red = 10
        self.alice.mana_pool.green = 10
        pending = self.game.begin_cast(spell, x_value=x_value)
        if pending is not None:
            self.game.complete_pending_cast((target,))
        self.resolve()
        return spell

    def test_definitions(self) -> None:
        self.assertEqual(
            VARIABLE_SPELLS,
            (BRAINGEYSER, HOWL_FROM_BEYOND, EARTHQUAKE, HURRICANE),
        )
        self.assertEqual(
            [card.mana_cost.compact for card in VARIABLE_SPELLS],
            ["XUU", "XB", "XR", "XG"],
        )

    def test_braingeyser_makes_either_player_draw_x(self) -> None:
        self.cast(BRAINGEYSER, 3, self.bob)
        self.assertEqual(len(self.bob.hand), 3)
        self.assertEqual(len(self.bob.library), 27)

    def test_howl_from_beyond_grants_x_power_until_end_of_turn(self) -> None:
        bear = self.put_in_play(self.alice, GRIZZLY_BEARS)
        self.cast(HOWL_FROM_BEYOND, 4, bear)
        self.assertEqual(self.game.creature_power(bear), 6)
        self.game.temporary_creature_effects.clear()
        self.assertEqual(self.game.creature_power(bear), 2)

    def test_earthquake_hits_players_and_nonflying_creatures(self) -> None:
        ground = self.put_in_play(self.bob, GRIZZLY_BEARS)
        flyer = self.put_in_play(self.bob, PHANTOM_MONSTER)
        self.cast(EARTHQUAKE, 3)

        self.assertEqual((self.alice.life, self.bob.life), (17, 17))
        self.assertIn(ground, self.bob.graveyard)
        self.assertIn(flyer, self.bob.battlefield)
        self.assertEqual(flyer.damage, 0)

    def test_hurricane_hits_players_and_flying_creatures(self) -> None:
        ground = self.put_in_play(self.bob, GRIZZLY_BEARS)
        flyer = self.put_in_play(self.bob, PHANTOM_MONSTER)
        self.cast(HURRICANE, 4)

        self.assertEqual((self.alice.life, self.bob.life), (16, 16))
        self.assertIn(flyer, self.bob.graveyard)
        self.assertIn(ground, self.bob.battlefield)
        self.assertEqual(ground.damage, 0)


if __name__ == "__main__":
    unittest.main()
