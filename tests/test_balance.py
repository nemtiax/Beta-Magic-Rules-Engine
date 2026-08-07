import unittest

from beta_magic import (
    BALANCE,
    FOREST,
    LIVING_LANDS,
    MOUNTAIN,
    PLAINS,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import (
    DRUDGE_SKELETONS,
    GRIZZLY_BEARS,
    OBSIANUS_GOLEM,
    WHITE_KNIGHT,
)
from beta_magic.ui import GameViewModel


class BalanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 30)
        self.bob = PlayerState.with_deck("bob", "Bob", [MOUNTAIN] * 30)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        for player in self.game.players:
            for card in tuple(player.hand):
                player.hand.remove(card)
                card.zone = Zone.LIBRARY
                player.library.append(card)

    @staticmethod
    def card(player, definition, zone=Zone.BATTLEFIELD):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=zone,
            entered_battlefield_turn=0 if zone is Zone.BATTLEFIELD else None,
        )
        player.cards_in(zone).append(card)
        return card

    def resolve_batch(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self) -> None:
        self.assertEqual(BALANCE.mana_cost.compact, "1W")
        self.assertEqual(len(BALANCE.spell_effects), 1)

    def test_all_counts_are_snapshotted_and_animated_land_is_double_counted(self) -> None:
        self.card(self.alice, LIVING_LANDS)
        animated = self.card(self.alice, FOREST)
        mountain = self.card(self.alice, MOUNTAIN)
        self.card(self.alice, PLAINS)
        bear = self.card(self.alice, GRIZZLY_BEARS)
        golem = self.card(self.alice, OBSIANUS_GOLEM)
        self.card(self.bob, MOUNTAIN)
        self.card(self.bob, GRIZZLY_BEARS)
        alice_hand = [self.card(self.alice, FOREST, Zone.HAND) for _ in range(4)]
        for _ in range(2):
            self.card(self.bob, MOUNTAIN, Zone.HAND)

        self.game._begin_balance()
        pending = self.game.pending_balance
        self.assertIsNotNone(pending)
        self.assertEqual(
            [(choice.category, choice.amount) for choice in pending.choices],
            [("land", 2), ("hand", 2), ("creature", 2)],
        )
        self.assertIn(animated.id, pending.choices[0].candidate_ids)
        self.assertIn(animated.id, pending.choices[2].candidate_ids)
        self.assertIn(golem.id, pending.choices[2].candidate_ids)

        self.game.choose_balance_cards(self.alice.id, (animated, mountain))
        self.game.choose_balance_cards(self.alice.id, alice_hand[:2])
        self.game.choose_balance_cards(self.alice.id, (animated, golem))

        self.assertIsNone(self.game.pending_balance)
        self.assertEqual(animated.zone, Zone.GRAVEYARD)
        self.assertEqual(mountain.zone, Zone.GRAVEYARD)
        self.assertEqual(golem.zone, Zone.GRAVEYARD)
        self.assertEqual(bear.zone, Zone.BATTLEFIELD)
        self.assertEqual(len(self.alice.hand), 2)

    def test_artifact_creatures_count_only_as_creatures(self) -> None:
        golem = self.card(self.alice, OBSIANUS_GOLEM)
        self.game._begin_balance()

        choice = self.game.pending_balance.current_choice
        self.assertEqual((choice.category, choice.amount), ("creature", 1))
        self.assertEqual(choice.candidate_ids, frozenset({golem.id}))

    def test_balance_destruction_ignores_protection_and_regeneration(self) -> None:
        knight = self.card(self.alice, WHITE_KNIGHT)
        skeleton = self.card(self.alice, DRUDGE_SKELETONS)
        self.game._begin_balance()

        self.game.choose_balance_cards(self.alice.id, (knight, skeleton))

        self.assertEqual(knight.zone, Zone.GRAVEYARD)
        self.assertEqual(skeleton.zone, Zone.GRAVEYARD)
        self.assertIsNone(self.game.pending_destruction)

    def test_casting_balance_opens_choices_after_the_spell_resolves(self) -> None:
        self.card(self.alice, FOREST)
        self.card(self.alice, MOUNTAIN)
        self.card(self.bob, MOUNTAIN)
        spell = self.card(self.alice, BALANCE, Zone.HAND)
        self.alice.mana_pool.white = 1
        self.alice.mana_pool.colorless = 1

        self.game.begin_cast(spell)
        self.resolve_batch()

        self.assertEqual(spell.zone, Zone.GRAVEYARD)
        self.assertIsNotNone(self.game.pending_balance)
        self.assertEqual(self.game.pending_balance.current_choice.category, "land")

    def test_invalid_or_out_of_order_choice_does_not_lose_progress(self) -> None:
        first = self.card(self.alice, FOREST)
        second = self.card(self.alice, MOUNTAIN)
        self.card(self.bob, MOUNTAIN)
        self.game._begin_balance()

        with self.assertRaisesRegex(ValueError, "exactly 1"):
            self.game.choose_balance_cards(self.alice.id, (first, second))

        self.assertEqual(self.game.pending_balance.selections, [])
        self.game.choose_balance_cards(self.alice.id, (first,))
        self.assertIsNone(self.game.pending_balance)

    def test_ui_reports_and_preserves_multistep_progress(self) -> None:
        first = self.card(self.alice, FOREST)
        self.card(self.alice, MOUNTAIN)
        self.card(self.bob, MOUNTAIN)
        hand = self.card(self.alice, FOREST, Zone.HAND)
        self.game._begin_balance()
        view = GameViewModel(self.game)

        state = view.state
        self.assertTrue(state["balanceRequired"])
        self.assertTrue(state["canChooseBalance"])
        self.assertEqual(state["balanceProgress"], "Balance choice 1 of 2")
        self.assertEqual((state["balanceCategory"], state["balanceCount"]), ("land", 1))

        view.selected_card_ids = {first.id}
        view.chooseBalanceSelected()
        state = view.state
        self.assertEqual(state["balanceProgress"], "Balance choice 2 of 2")
        self.assertEqual(state["balanceCategory"], "hand")
        self.assertEqual(first.zone, Zone.BATTLEFIELD)

        view.selected_card_ids = {hand.id}
        view.chooseBalanceSelected()
        self.assertIsNone(self.game.pending_balance)
        self.assertEqual(first.zone, Zone.GRAVEYARD)
        self.assertEqual(hand.zone, Zone.GRAVEYARD)


if __name__ == "__main__":
    unittest.main()
