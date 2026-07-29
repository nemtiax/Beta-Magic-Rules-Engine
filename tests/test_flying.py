import unittest

from beta_magic import (
    CardType,
    FLYING_CREATURES,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.flying_creatures import (
    AIR_ELEMENTAL,
    SCRYB_SPRITES,
    WALL_OF_AIR,
)
from beta_magic.vanilla_creatures import GRIZZLY_BEARS


def player(player_id: str) -> PlayerState:
    return PlayerState.with_deck(player_id, player_id.title(), [GRIZZLY_BEARS] * 12)


class FlyingTests(unittest.TestCase):
    def test_seven_flying_only_creatures_are_defined(self) -> None:
        self.assertEqual(len(FLYING_CREATURES), 7)
        self.assertEqual(len({card.name for card in FLYING_CREATURES}), 7)
        self.assertTrue(
            all(
                CardType.CREATURE in card.card_types
                and card.abilities == frozenset({KeywordAbility.FLYING})
                and card.rules_text == "Flying"
                for card in FLYING_CREATURES
            )
        )
        self.assertEqual(
            (AIR_ELEMENTAL.mana_cost.mana_value, AIR_ELEMENTAL.power, AIR_ELEMENTAL.toughness),
            (5, 4, 4),
        )

    def setUp(self) -> None:
        self.alice = player("alice")
        self.bob = player("bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(owner: PlayerState, definition):
        card = owner.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        owner.battlefield.append(card)
        return card

    def begin_with_attacker(self, definition):
        attacker = self.put_in_play(self.alice, definition)
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        return attacker

    def test_ground_creature_cannot_block_flying_attacker(self) -> None:
        flyer = self.begin_with_attacker(SCRYB_SPRITES)
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        with self.assertRaisesRegex(ValueError, "cannot block.*Flying"):
            self.game.declare_blockers({bear: flyer})

    def test_flyer_can_block_flying_attacker(self) -> None:
        attacker = self.begin_with_attacker(SCRYB_SPRITES)
        blocker = self.put_in_play(self.bob, AIR_ELEMENTAL)
        self.game.declare_blockers({blocker: attacker})
        self.game.advance_combat()
        self.game.deal_combat_damage()
        self.assertIn(attacker, self.alice.graveyard)
        self.assertIn(blocker, self.bob.battlefield)

    def test_flyer_can_block_nonflying_attacker(self) -> None:
        attacker = self.begin_with_attacker(GRIZZLY_BEARS)
        blocker = self.put_in_play(self.bob, SCRYB_SPRITES)
        self.game.declare_blockers({blocker: attacker})
        self.game.advance_combat()
        self.game.deal_combat_damage()
        self.assertIn(blocker, self.bob.graveyard)
        self.assertEqual(self.bob.life, 20)

    def test_flying_wall_cannot_attack_but_can_block_flyers(self) -> None:
        wall = self.put_in_play(self.alice, WALL_OF_AIR)
        self.game.begin_combat()
        with self.assertRaisesRegex(ValueError, "Wall and cannot attack"):
            self.game.declare_attackers([wall])

        # Use a fresh game direction to exercise its legal blocking ability.
        game = GameState([player("charlie"), player("dana")])
        game.start(opening_hand_size=0, shuffle=False)
        while game.current_phase is not TurnPhase.MAIN:
            game.advance_phase()
        attacker = self.put_in_play(game.players[0], SCRYB_SPRITES)
        flying_wall = self.put_in_play(game.players[1], WALL_OF_AIR)
        game.begin_combat()
        game.declare_attackers([attacker])
        game.declare_blockers({flying_wall: attacker})


if __name__ == "__main__":
    unittest.main()
