import unittest

from beta_magic import (
    BLACK_LOTUS,
    MANA_ARTIFACTS,
    MOX_EMERALD,
    MOX_JET,
    MOX_PEARL,
    MOX_RUBY,
    MOX_SAPPHIRE,
    MOXEN,
    SOL_RING,
    CardType,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import FOREST


class ManaArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 24)
        self.bob = PlayerState.with_deck("bob", "Bob", [FOREST] * 24)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    def put_in_play(self, definition):
        card = self.alice.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = self.alice.id
        card.entered_battlefield_turn = self.game.turn_number
        self.alice.battlefield.append(card)
        return card

    def put_in_hand(self, definition):
        card = self.alice.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        self.alice.hand.append(card)
        return card

    def test_definitions(self) -> None:
        self.assertEqual(
            MOXEN,
            (MOX_PEARL, MOX_SAPPHIRE, MOX_JET, MOX_RUBY, MOX_EMERALD),
        )
        self.assertEqual(MANA_ARTIFACTS, MOXEN + (SOL_RING, BLACK_LOTUS))
        self.assertTrue(
            all(CardType.ARTIFACT in card.card_types for card in MANA_ARTIFACTS)
        )
        self.assertTrue(all(card.mana_cost.mana_value == 0 for card in MOXEN))
        self.assertEqual(SOL_RING.mana_cost.mana_value, 1)
        self.assertEqual(
            [ability.color for card in MOXEN for ability in card.activated_abilities],
            [
                Color.WHITE,
                Color.BLUE,
                Color.BLACK,
                Color.RED,
                Color.GREEN,
            ],
        )

    def test_mox_can_tap_immediately_after_being_cast(self) -> None:
        mox = self.put_in_hand(MOX_SAPPHIRE)
        self.game.begin_cast(mox)
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.assertIn(mox, self.alice.battlefield)
        self.assertTrue(self.game.can_activate_ability(self.alice.id, mox, 0))
        self.game.activate_ability(self.alice.id, mox, 0)

        self.assertTrue(mox.tapped)
        self.assertEqual(self.alice.mana_pool.blue, 1)

    def test_sol_ring_produces_two_colorless_mana(self) -> None:
        ring = self.put_in_play(SOL_RING)

        self.game.activate_ability(self.alice.id, ring, 0)

        self.assertTrue(ring.tapped)
        self.assertEqual(self.alice.mana_pool.colorless, 2)

    def test_black_lotus_offers_each_color_and_produces_three(self) -> None:
        lotus = self.put_in_play(BLACK_LOTUS)
        self.assertEqual(
            [ability.label for ability in BLACK_LOTUS.activated_abilities],
            ["Add WWW", "Add UUU", "Add BBB", "Add RRR", "Add GGG"],
        )

        self.game.activate_ability(self.alice.id, lotus, 3)

        self.assertEqual(self.alice.mana_pool.red, 3)
        self.assertIn(lotus, self.alice.graveyard)
        self.assertNotIn(lotus, self.alice.battlefield)
        self.assertFalse(lotus.tapped)

    def test_artifact_mana_abilities_do_not_have_summoning_sickness(self) -> None:
        ring = self.put_in_play(SOL_RING)
        self.assertEqual(ring.entered_battlefield_turn, self.game.turn_number)

        self.assertTrue(self.game.can_activate_ability(self.alice.id, ring, 0))


if __name__ == "__main__":
    unittest.main()
