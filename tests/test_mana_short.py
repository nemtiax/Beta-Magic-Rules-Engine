import unittest

from beta_magic import (
    FOREST,
    GRIZZLY_BEARS,
    ISLAND,
    MANA_SHORT,
    MOUNTAIN,
    PLAINS,
    PSYCHIC_VENOM,
    WILD_GROWTH,
    Card,
    GameState,
    ManaBurnEvent,
    PlayerState,
    TurnPhase,
    Zone,
)


class ManaShortTests(unittest.TestCase):
    def setUp(self):
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 20
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player, definition, zone=Zone.BATTLEFIELD, *, attached=None):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=zone,
        )
        card.enchanted_card_id = attached.id if attached is not None else None
        player.cards_in(zone).append(card)
        return card

    def begin_mana_short(self):
        spell = self.card(self.alice, MANA_SHORT, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 2
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((self.bob,))
        return spell

    def resolve_batch(self):
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self):
        self.assertEqual(MANA_SHORT.mana_cost.compact, "2U")
        requirement = MANA_SHORT.target_requirement
        self.assertTrue(requirement.players)
        self.assertTrue(requirement.opponent_only)

    def test_taps_only_opponents_lands_and_empties_only_their_pool(self):
        own_land = self.card(self.alice, PLAINS)
        island = self.card(self.bob, ISLAND)
        mountain = self.card(self.bob, MOUNTAIN)
        self.bob.mana_pool.red = 2
        self.alice.mana_pool.green = 1
        spell = self.begin_mana_short()

        self.resolve_batch()

        self.assertFalse(own_land.tapped)
        self.assertTrue(island.tapped)
        self.assertTrue(mountain.tapped)
        self.assertEqual(self.bob.mana_pool.total, 0)
        self.assertEqual(self.alice.mana_pool.green, 1)
        self.assertFalse(
            any(isinstance(event, ManaBurnEvent) for event in self.game.events)
        )
        self.assertIn(spell, self.alice.graveyard)

    def test_opponent_can_use_mana_abilities_before_it_resolves(self):
        island = self.card(self.bob, ISLAND)
        self.begin_mana_short()

        self.game.activate_ability(self.bob.id, island, 0)

        self.assertEqual(self.bob.mana_pool.blue, 1)
        self.resolve_batch()
        self.assertEqual(self.bob.mana_pool.total, 0)

    def test_tap_triggers_happen_before_generated_mana_is_emptied(self):
        forest = self.card(self.bob, FOREST)
        self.card(self.alice, WILD_GROWTH, attached=forest)
        self.card(self.alice, PSYCHIC_VENOM, attached=forest)
        self.begin_mana_short()

        self.resolve_batch()

        self.assertTrue(forest.tapped)
        self.assertEqual(self.bob.mana_pool.total, 0)
        self.assertEqual(len(self.game.event_opportunities), 1)
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        self.assertEqual(self.bob.life, 18)

    def test_already_tapped_lands_do_not_trigger_again(self):
        forest = self.card(self.bob, FOREST)
        forest.tapped = True
        self.card(self.alice, PSYCHIC_VENOM, attached=forest)
        self.bob.mana_pool.green = 3
        self.begin_mana_short()

        self.resolve_batch()

        self.assertEqual(self.bob.mana_pool.total, 0)
        self.assertEqual(self.game.event_opportunities, [])


if __name__ == "__main__":
    unittest.main()
