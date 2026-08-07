import unittest

from beta_magic import (
    ContinuousEffect,
    ExileTargetsEffect,
    GameState,
    PlayerState,
    SWORDS_TO_PLOWSHARES,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import (
    GRIZZLY_BEARS,
    HOLY_STRENGTH,
    BLACK_KNIGHT,
    PERSONAL_INCARNATION,
)
from beta_magic.cards import Card
from beta_magic.types import CardType, Color


class SwordsToPlowsharesTests(unittest.TestCase):
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

    def cast_swords(self, target: Card) -> Card:
        spell = self.alice.library.pop()
        spell.definition = SWORDS_TO_PLOWSHARES
        spell.zone = Zone.HAND
        self.alice.hand.append(spell)
        self.alice.mana_pool.white = 1
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((target,))
        while self.game.stack:
            priority = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(priority.id)
        return spell

    def test_definition(self) -> None:
        self.assertEqual(SWORDS_TO_PLOWSHARES.mana_cost.compact, "W")
        self.assertEqual(
            SWORDS_TO_PLOWSHARES.card_types,
            frozenset({CardType.INSTANT}),
        )
        self.assertEqual(SWORDS_TO_PLOWSHARES.colors, frozenset({Color.WHITE}))
        self.assertEqual(
            SWORDS_TO_PLOWSHARES.spell_effects,
            (ExileTargetsEffect(True),),
        )

    def test_exiles_creature_and_its_controller_gains_current_power(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.game.temporary_creature_effects[bear.id] = [
            ContinuousEffect(power=3, toughness=3)
        ]

        spell = self.cast_swords(bear)

        self.assertIn(bear, self.bob.exile)
        self.assertNotIn(bear, self.bob.graveyard)
        self.assertEqual(self.bob.life, 25)
        self.assertIn(spell, self.alice.graveyard)

    def test_controller_not_owner_gains_life(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.game._change_controller(bear, self.alice.id)

        self.cast_swords(bear)

        self.assertIn(bear, self.bob.exile)
        self.assertEqual(self.alice.life, 22)
        self.assertEqual(self.bob.life, 20)

    def test_negative_power_counts_as_zero(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.game.temporary_creature_effects[bear.id] = [
            ContinuousEffect(power=-3)
        ]

        self.cast_swords(bear)

        self.assertEqual(self.bob.life, 20)
        self.assertIn(bear, self.bob.exile)

    def test_exile_is_not_death_and_cannot_be_regenerated(self) -> None:
        incarnation = self.put_in_play(self.bob, PERSONAL_INCARNATION)
        aura = self.put_in_play(self.alice, HOLY_STRENGTH)
        aura.enchanted_card_id = incarnation.id

        self.cast_swords(incarnation)

        self.assertIn(incarnation, self.bob.exile)
        self.assertIn(aura, self.alice.graveyard)
        self.assertEqual(self.bob.life, 27)
        self.assertIsNone(self.game.pending_destruction)
        self.assertFalse(self.game.event_opportunities)

    def test_protection_from_white_prevents_targeting(self) -> None:
        knight = self.put_in_play(self.bob, BLACK_KNIGHT)
        spell = self.alice.library.pop()
        spell.definition = SWORDS_TO_PLOWSHARES
        spell.zone = Zone.HAND
        self.alice.hand.append(spell)
        self.alice.mana_pool.white = 1

        with self.assertRaisesRegex(RuntimeError, "no legal targets"):
            self.game.begin_cast(spell)

        self.assertIn(knight, self.bob.battlefield)
        self.assertIn(spell, self.alice.hand)


if __name__ == "__main__":
    unittest.main()
