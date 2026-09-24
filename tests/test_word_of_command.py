import unittest

from beta_magic.card_defs.blue import ANCESTRAL_RECALL
from beta_magic import (
    Card,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs.lands import (
    FOREST,
    MOUNTAIN,
)
from beta_magic.card_defs.red import LIGHTNING_BOLT
from beta_magic.card_defs.white import RESURRECTION
from beta_magic.card_defs.artifacts import SOL_RING
from beta_magic.card_defs.black import WORD_OF_COMMAND
from beta_magic.card_defs.black import DEMONIC_TUTOR
from beta_magic.card_defs.blue import CLONE
from beta_magic.card_defs.green import CHANNEL, GRIZZLY_BEARS
from beta_magic.ui import GameViewModel


class WordOfCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [MOUNTAIN] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def hand_card(player, definition):
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

    def resolve_current_batch(self) -> None:
        while self.game.stack:
            priority = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(priority.id)

    def resolve_word(self):
        word = self.hand_card(self.alice, WORD_OF_COMMAND)
        self.alice.mana_pool.black = 2
        self.game.begin_cast(word)
        self.resolve_current_batch()
        return self.game.current_word_command()

    def test_forced_spell_is_cast_by_opponent_but_chosen_by_commander(self) -> None:
        bolt = self.hand_card(self.bob, LIGHTNING_BOLT)
        mountain = self.permanent(self.bob, MOUNTAIN)
        choice = self.resolve_word()

        self.assertEqual(choice.commander_id, self.alice.id)
        self.assertEqual(choice.commanded_player_id, self.bob.id)
        self.assertEqual(self.game.word_commandable_cards(), (bolt,))

        pending = self.game.begin_word_command_cast(self.alice.id, bolt)
        self.assertEqual(pending.caster_id, self.bob.id)
        self.assertEqual(pending.decision_maker_id, self.alice.id)
        self.game.complete_pending_cast((self.alice,))

        option = self.game.word_command_mana_options()[0]
        self.game.complete_word_command_payment(
            self.alice.id, ((mountain.id, option.ability_index),)
        )

        declared = self.game.stack_spells[bolt.id]
        self.assertTrue(mountain.tapped)
        self.assertEqual(declared.caster_id, self.bob.id)
        self.assertEqual(declared.decision_maker_id, self.alice.id)
        self.assertEqual(declared.targets, (self.alice,))
        self.assertEqual(self.bob.mana_pool.total, 0)
        self.assertEqual(self.game.interruptible_spell_id, bolt.id)
        self.assertEqual(
            self.game.players[self.game.priority_player_index], self.alice
        )

    def test_commanded_land_is_played_by_the_opponent(self) -> None:
        forest = self.hand_card(self.bob, FOREST)
        self.game.active_player_index = 1
        self.game.priority_player_index = 0
        self.resolve_word()

        result = self.game.begin_word_command_cast(self.alice.id, forest)

        self.assertIsNone(result)
        self.assertIn(forest, self.bob.battlefield)
        self.assertEqual(forest.controller_id, self.bob.id)
        self.assertEqual(self.game.lands_played_this_turn, 1)
        self.assertFalse(self.game.pending_word_command_choices)

    def test_resolution_choice_for_commanded_tutor_belongs_to_commander(self) -> None:
        tutor = self.hand_card(self.bob, DEMONIC_TUTOR)
        self.game.active_player_index = 1
        self.game.priority_player_index = 0
        self.bob.mana_pool.black = 2
        self.resolve_word()
        self.game.begin_word_command_cast(self.alice.id, tutor)
        self.game.complete_word_command_payment(self.alice.id, ())

        self.resolve_current_batch()

        choice = self.game.pending_library_search_choices[0]
        self.assertEqual(choice.chooser_id, self.alice.id)
        self.assertEqual(choice.library_player_id, self.bob.id)

    def test_clone_choice_created_by_commanded_resurrection_belongs_to_commander(
        self,
    ) -> None:
        resurrection = self.hand_card(self.bob, RESURRECTION)
        clone = Card(CLONE, self.bob.id, zone=Zone.GRAVEYARD)
        self.bob.graveyard.append(clone)
        bear = self.permanent(self.alice, GRIZZLY_BEARS)
        self.game.active_player_index = 1
        self.game.priority_player_index = 0
        self.bob.mana_pool.white = 4
        self.resolve_word()
        self.game.begin_word_command_cast(self.alice.id, resurrection)
        self.game.complete_pending_cast((clone,))
        self.game.complete_word_command_payment(self.alice.id, ())

        self.resolve_current_batch()

        choice = self.game.pending_creature_copy_choices[0]
        self.assertEqual(choice.chooser_id, self.alice.id)
        self.assertIn(bear.id, choice.candidate_ids)

    def test_pool_mana_is_available_but_nonland_sources_are_not(self) -> None:
        recall = self.hand_card(self.bob, ANCESTRAL_RECALL)
        self.resolve_word()

        self.assertNotIn(recall, self.game.word_commandable_cards())
        self.bob.mana_pool.add(Color.BLUE)
        self.assertIn(recall, self.game.word_commandable_cards())

    def test_cannot_decline_when_a_legal_card_exists(self) -> None:
        self.hand_card(self.bob, LIGHTNING_BOLT)
        self.permanent(self.bob, MOUNTAIN)
        self.resolve_word()

        with self.assertRaisesRegex(RuntimeError, "must be played"):
            self.game.finish_word_command_without_play(self.alice.id)

    def test_may_finish_after_inspecting_a_hand_with_no_legal_play(self) -> None:
        self.hand_card(self.bob, ANCESTRAL_RECALL)
        self.resolve_word()

        self.game.finish_word_command_without_play(self.alice.id)

        self.assertFalse(self.game.pending_word_command_choices)

    def test_ui_reveals_hand_only_to_commander_and_collects_land_payment(self) -> None:
        bolt = self.hand_card(self.bob, LIGHTNING_BOLT)
        mountain = self.permanent(self.bob, MOUNTAIN)
        self.resolve_word()
        view = GameViewModel(self.game)

        commander_state = view.state
        self.assertTrue(commander_state["wordCommandDialog"])
        self.assertTrue(commander_state["canChooseWordCommand"])
        self.assertEqual(
            [item["name"] for item in commander_state["wordCommandCards"]],
            [bolt.name],
        )
        view.perspective_index = 1
        self.assertFalse(view.state["canChooseWordCommand"])
        self.assertEqual(view.state["wordCommandCards"], [])

        view.perspective_index = 0
        view.chooseWordCommandCard(str(bolt.id))
        self.assertIsNotNone(self.game.pending_cast)
        view.targetPlayer(self.alice.id)
        payment_state = view.state
        self.assertEqual(payment_state["wordCommandStage"], "choose_payment")
        self.assertFalse(payment_state["wordCommandPaymentValid"])
        option = payment_state["wordCommandManaOptions"][0]
        view.toggleWordCommandMana(option["landId"], option["abilityIndex"])
        self.assertTrue(view.state["wordCommandPaymentValid"])
        view.confirmWordCommandMana()

        self.assertTrue(mountain.tapped)
        self.assertIn(bolt, self.game.stack)

    def test_commander_chooses_which_pool_color_pays_a_generic_cost(self) -> None:
        ring = self.hand_card(self.bob, SOL_RING)
        self.game.active_player_index = 1
        self.game.priority_player_index = 0
        self.bob.mana_pool.red = 1
        self.bob.mana_pool.green = 1
        self.resolve_word()
        self.game.begin_word_command_cast(self.alice.id, ring)
        plans = self.game.land_mana_payment_plans(
            self.bob.id,
            ring.definition.mana_cost,
            (),
            require_exact_when_available=True,
        )
        green_plan = next(
            plan for plan in plans if plan.spending.green == 1
        )

        self.game.complete_word_command_payment(
            self.alice.id, (), green_plan.spending
        )

        self.assertEqual(self.bob.mana_pool.green, 0)
        self.assertEqual(self.bob.mana_pool.red, 1)

    def test_commanding_channel_does_not_grant_later_life_payment_authority(
        self,
    ) -> None:
        channel = self.hand_card(self.bob, CHANNEL)
        self.game.active_player_index = 1
        self.game.priority_player_index = 0
        self.bob.mana_pool.green = 2
        self.resolve_word()
        self.game.begin_word_command_cast(self.alice.id, channel)
        self.game.complete_word_command_payment(self.alice.id, ())
        self.resolve_current_batch()

        self.assertIn(self.bob.id, self.game.channel_active_players)
        self.assertNotIn(self.alice.id, self.game.channel_active_players)
        view = GameViewModel(self.game)
        self.assertFalse(view.state["canChannel"])
        view.switchPerspective()
        self.assertTrue(view.state["canChannel"])
        view.channelMana(2)
        self.assertEqual((self.bob.life, self.bob.mana_pool.colorless), (18, 2))
        self.assertEqual(self.alice.life, 20)


if __name__ == "__main__":
    unittest.main()
