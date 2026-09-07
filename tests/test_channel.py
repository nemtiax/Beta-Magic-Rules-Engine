import unittest

from beta_magic import (
    CHANNEL,
    FOREST,
    LICH,
    LIVING_ARTIFACT,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.ui import GameViewModel


class ChannelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("b", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def cast_channel(self) -> Card:
        spell = Card(CHANNEL, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(spell)
        self.alice.mana_pool.green = 2
        self.game.begin_cast(spell)
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        return spell

    def test_definition(self) -> None:
        self.assertEqual(CHANNEL.mana_cost.compact, "GG")
        self.assertEqual(CHANNEL.card_types, frozenset({CardType.SORCERY}))

    def test_resolving_grants_repeatable_life_conversion_for_the_turn(self) -> None:
        spell = self.cast_channel()

        self.assertIn(spell, self.alice.graveyard)
        self.assertEqual(self.game.maximum_channel_mana(self.alice.id), 20)
        self.game.channel_life_for_mana(self.alice.id, 3)
        self.game.channel_life_for_mana(self.alice.id, 2)

        self.assertEqual(self.alice.life, 15)
        self.assertEqual(self.alice.mana_pool.colorless, 5)

    def test_channel_life_loss_is_not_prevented(self) -> None:
        self.cast_channel()
        self.game.life_loss_prevention[self.alice.id] = 3

        self.game.channel_life_for_mana(self.alice.id, 2)

        self.assertEqual(self.alice.life, 18)
        self.assertEqual(self.game.life_loss_prevention[self.alice.id], 3)

    def test_channel_life_loss_adds_living_artifact_counters(self) -> None:
        artifact = self.permanent(self.alice, LIVING_ARTIFACT)
        self.cast_channel()

        self.game.channel_life_for_mana(self.alice.id, 4)

        self.assertEqual(artifact.counters.get("life"), 4)

    def test_lich_controller_cannot_use_channel(self) -> None:
        self.cast_channel()
        self.permanent(self.alice, LICH)

        self.assertEqual(self.game.maximum_channel_mana(self.alice.id), 0)
        with self.assertRaisesRegex(ValueError, "1 to 0"):
            self.game.channel_life_for_mana(self.alice.id, 1)

    def test_channel_expires_when_the_next_turn_begins(self) -> None:
        self.cast_channel()
        self.game.current_phase = TurnPhase.END
        self.game.next_turn()

        self.assertNotIn(self.alice.id, self.game.channel_active_players)
        self.assertEqual(self.game.maximum_channel_mana(self.alice.id), 0)

    def test_ui_exposes_amount_action_to_the_correct_player(self) -> None:
        self.cast_channel()
        view = GameViewModel(self.game)

        self.assertTrue(view.state["canChannel"])
        self.assertEqual(view.state["channelMaximum"], 20)
        view.channelMana(3)
        self.assertEqual((self.alice.life, self.alice.mana_pool.colorless), (17, 3))

        view.switchPerspective()
        self.assertFalse(view.state["canChannel"])


if __name__ == "__main__":
    unittest.main()
