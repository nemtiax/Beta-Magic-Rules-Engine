import unittest

from beta_magic import (
    GRIZZLY_BEARS,
    HOWLING_MINE,
    ISLAND,
    ISLAND_SANCTUARY,
    PHANTOM_MONSTER,
    Card,
    CardDefinition,
    CardType,
    Color,
    GameState,
    KeywordAbility,
    ManaCost,
    PlayerState,
    TurnPhase,
    Zone,
)


ISLANDWALKER = CardDefinition(
    name="Test Islandwalker",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{U}"),
    colors=frozenset({Color.BLUE}),
    abilities=frozenset({KeywordAbility.ISLANDWALK}),
    power=2,
    toughness=2,
)


class IslandSanctuaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [ISLAND] * 30)
        self.bob = PlayerState.with_deck("bob", "Bob", [ISLAND] * 30)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
            summoned_turn=0,
        )
        player.battlefield.append(card)
        return card

    def enter_draw(self):
        while self.game.current_phase is not TurnPhase.DRAW:
            self.game.advance_phase()

    def enter_main(self):
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    def test_definition(self):
        self.assertEqual(ISLAND_SANCTUARY.mana_cost.compact, "1W")
        self.assertEqual(
            ISLAND_SANCTUARY.card_types, frozenset({CardType.ENCHANTMENT})
        )
        effect = ISLAND_SANCTUARY.optional_draw_skip_effects[0]
        self.assertEqual(effect.allowed_landwalk_subtype, "Island")

    def test_player_may_draw_normally_or_skip_the_draw(self):
        self.permanent(self.alice, ISLAND_SANCTUARY)
        starting_library = len(self.alice.library)
        self.enter_draw()

        self.assertIsNotNone(self.game.pending_draw_choice)
        self.game.choose_draw_skips(self.alice.id, 0)
        self.assertEqual(len(self.alice.library), starting_library - 1)
        self.assertNotIn(
            self.alice.id, self.game.island_sanctuary_protected_players
        )

    def test_howling_mine_still_draws_one_card_after_one_skip(self):
        self.permanent(self.alice, ISLAND_SANCTUARY)
        self.permanent(self.bob, HOWLING_MINE)
        starting_library = len(self.alice.library)
        self.enter_draw()

        choice = self.game.pending_draw_choice
        self.assertEqual((choice.total_draws, choice.maximum_skips), (2, 1))
        self.game.choose_draw_skips(self.alice.id, 1)
        self.assertEqual(len(self.alice.library), starting_library - 1)
        self.assertIn(self.alice.id, self.game.island_sanctuary_protected_players)

    def test_each_sanctuary_can_replace_one_draw(self):
        self.permanent(self.alice, ISLAND_SANCTUARY)
        self.permanent(self.alice, ISLAND_SANCTUARY)
        self.permanent(self.bob, HOWLING_MINE)
        starting_library = len(self.alice.library)
        self.enter_draw()

        self.assertEqual(self.game.pending_draw_choice.maximum_skips, 2)
        self.game.choose_draw_skips(self.alice.id, 2)
        self.assertEqual(len(self.alice.library), starting_library)

    def test_only_flying_and_islandwalk_creatures_may_attack(self):
        self.game.island_sanctuary_protected_players.add(self.bob.id)
        bear = self.permanent(self.alice, GRIZZLY_BEARS)
        flyer = self.permanent(self.alice, PHANTOM_MONSTER)
        islandwalker = self.permanent(self.alice, ISLANDWALKER)
        self.enter_main()
        self.game.begin_combat()

        with self.assertRaisesRegex(ValueError, "Island Sanctuary"):
            self.game.declare_attackers((bear,))
        self.game.declare_attackers((flyer, islandwalker))
        self.assertEqual(self.game.combat.attackers, [flyer, islandwalker])

    def test_protection_ends_at_start_of_players_next_turn(self):
        self.game.island_sanctuary_protected_players.add(self.bob.id)
        self.enter_main()
        while self.game.current_phase is not TurnPhase.END:
            self.game.advance_phase()
        self.game.advance_phase()
        self.assertNotIn(self.bob.id, self.game.island_sanctuary_protected_players)


if __name__ == "__main__":
    unittest.main()
