import unittest

from beta_magic import (
    GIANT_WASP_TOKEN,
    SHATTER,
    THE_HIVE,
    UNSUMMON,
    Card,
    CardType,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS
from beta_magic.ui import GameViewModel


class TheHiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player, definition, zone=Zone.BATTLEFIELD):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=zone,
            entered_battlefield_turn=0 if zone is Zone.BATTLEFIELD else None,
        )
        player.cards_in(zone).append(card)
        return card

    def resolve(self):
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def make_wasp(self):
        hive = self.card(self.alice, THE_HIVE)
        self.alice.mana_pool.colorless = 5
        self.game.activate_ability("a", hive, 0)
        self.resolve()
        return hive, next(card for card in self.alice.battlefield if card.is_token)

    def test_definition_and_token_characteristics(self):
        self.assertEqual(THE_HIVE.mana_cost.compact, "5")
        self.assertEqual(THE_HIVE.activated_abilities[0].mana_cost.compact, "5")
        self.assertEqual(GIANT_WASP_TOKEN.mana_cost.mana_value, 0)
        self.assertEqual(
            GIANT_WASP_TOKEN.card_types,
            frozenset({CardType.ARTIFACT, CardType.CREATURE}),
        )
        self.assertIn(KeywordAbility.FLYING, GIANT_WASP_TOKEN.abilities)

    def test_activation_taps_hive_and_creates_summoning_sick_wasp(self):
        hive, wasp = self.make_wasp()

        self.assertTrue(hive.tapped)
        self.assertTrue(wasp.is_token)
        self.assertEqual((self.game.creature_power(wasp), self.game.creature_toughness(wasp)), (1, 1))
        self.assertTrue(self.game.has_summoning_sickness(wasp))
        self.assertEqual(self.alice.mana_pool.total, 0)

    def test_hive_destruction_does_not_remove_existing_wasps(self):
        hive, wasp = self.make_wasp()
        self.game._move_card(hive, Zone.GRAVEYARD)

        self.assertIn(wasp, self.alice.battlefield)

    def test_destroyed_or_unsummoned_token_ceases_to_exist_in_game_zones(self):
        for spell_definition, destination in ((SHATTER, Zone.GRAVEYARD), (UNSUMMON, Zone.HAND)):
            with self.subTest(spell=spell_definition.name):
                self.setUp()
                _, wasp = self.make_wasp()
                spell = self.card(self.bob, spell_definition, Zone.HAND)
                self.game.priority_player_index = self.game.players.index(
                    self.bob
                )
                if spell_definition is SHATTER:
                    self.bob.mana_pool.red = 1
                    self.bob.mana_pool.colorless = 1
                else:
                    self.bob.mana_pool.blue = 1
                self.game.begin_cast(spell)
                self.game.complete_pending_cast((wasp,))
                self.resolve()
                while self.game.pending_destruction is not None:
                    player = self.game.players[self.game.priority_player_index]
                    self.game.pass_priority(player.id)

                self.assertEqual(wasp.zone, destination)
                self.assertFalse(
                    any(wasp in player.cards_in(zone) for player in self.game.players for zone in (Zone.LIBRARY, Zone.HAND, Zone.BATTLEFIELD, Zone.GRAVEYARD, Zone.EXILE))
                )

    def test_ui_marks_wasp_as_token(self):
        _, wasp = self.make_wasp()
        data = GameViewModel(self.game)._presentation._card_data(wasp)
        self.assertTrue(data["isToken"])
        self.assertEqual(data["manaCost"], "0")


if __name__ == "__main__":
    unittest.main()
