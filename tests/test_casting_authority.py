import unittest

from beta_magic.card_defs.lands import (
    BADLANDS,
    FOREST,
)
from beta_magic import (
    Card,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs.black import DEMONIC_TUTOR
from beta_magic.card_defs.blue import DRAIN_POWER
from beta_magic.card_defs.red import LIGHTNING_BOLT


class CastingAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    def card_in_hand(self, player, definition):
        card = Card(definition, player.id, zone=Zone.HAND)
        player.hand.append(card)
        return card

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        player.battlefield.append(card)
        return card

    def resolve_stack(self) -> None:
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_ordinary_pending_cast_uses_caster_as_decision_maker(self) -> None:
        bolt = self.card_in_hand(self.alice, LIGHTNING_BOLT)
        self.alice.mana_pool.red = 1

        pending = self.game.begin_cast(bolt)

        self.assertIsNotNone(pending)
        self.assertEqual(pending.caster_id, self.alice.id)
        self.assertEqual(pending.decision_maker_id, self.alice.id)

    def test_stack_tracks_caster_and_decision_maker_separately(self) -> None:
        tutor = self.card_in_hand(self.bob, DEMONIC_TUTOR)
        self.bob.mana_pool.black = 2

        self.game._cast_spell(
            tutor,
            (),
            self.bob,
            decision_maker_id=self.alice.id,
        )

        spell = self.game.stack_spells[tutor.id]
        self.assertEqual(spell.caster_id, self.bob.id)
        self.assertEqual(spell.decision_maker_id, self.alice.id)

    def test_resolution_choice_uses_decision_maker_but_caster_library(self) -> None:
        tutor = self.card_in_hand(self.bob, DEMONIC_TUTOR)
        self.bob.mana_pool.black = 2
        chosen = self.bob.library[-1]

        self.game._cast_spell(
            tutor,
            (),
            self.bob,
            decision_maker_id=self.alice.id,
        )
        self.resolve_stack()

        choice = self.game.pending_library_search_choices[0]
        self.assertEqual(choice.chooser_id, self.alice.id)
        self.assertEqual(choice.library_player_id, self.bob.id)

        self.game.choose_library_search_card(self.alice.id, chosen)

        self.assertIn(chosen, self.bob.hand)
        self.assertNotIn(chosen, self.alice.hand)

    def test_resolution_mana_choice_is_separate_from_mana_recipient(self) -> None:
        land = self.permanent(self.alice, BADLANDS)
        drain_power = self.card_in_hand(self.bob, DRAIN_POWER)
        self.bob.mana_pool.blue = 2

        self.game._cast_spell(
            drain_power,
            (self.alice,),
            self.bob,
            decision_maker_id=self.alice.id,
        )
        self.resolve_stack()

        choice = self.game.pending_drain_power_choices[0]
        self.assertEqual(choice.caster_id, self.bob.id)
        self.assertEqual(choice.decision_maker_id, self.alice.id)
        self.assertEqual(choice.land_id, land.id)

        self.game.choose_drain_power_mana(self.alice.id, Color.RED)

        self.assertEqual(self.bob.mana_pool.red, 1)
        self.assertEqual(self.alice.mana_pool.red, 0)


if __name__ == "__main__":
    unittest.main()
