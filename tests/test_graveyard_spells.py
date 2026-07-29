import unittest

from beta_magic import (
    GRAVEYARD_RECURSION_SPELLS,
    RAISE_DEAD,
    REGROWTH,
    RESURRECTION,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.basic_lands import FOREST
from beta_magic.mana_creatures import LLANOWAR_ELVES
from beta_magic.vanilla_creatures import GRIZZLY_BEARS


class GraveyardSpellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 30
        )
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 30)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_zone(player, definition, zone):
        card = player.library.pop()
        card.definition = definition
        card.zone = zone
        player.cards_in(zone).append(card)
        return card

    def cast(self, definition, target):
        spell = self.put_in_zone(self.alice, definition, Zone.HAND)
        self.alice.mana_pool.white = 10
        self.alice.mana_pool.black = 10
        self.alice.mana_pool.green = 10
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((target,))
        while self.game.stack:
            priority = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(priority.id)
        return spell

    def test_definitions(self) -> None:
        self.assertEqual(
            GRAVEYARD_RECURSION_SPELLS,
            (REGROWTH, RAISE_DEAD, RESURRECTION),
        )
        self.assertEqual(
            tuple(card.mana_cost.compact for card in GRAVEYARD_RECURSION_SPELLS),
            ("1G", "B", "2WW"),
        )

    def test_regrowth_returns_any_owned_card_to_hand(self) -> None:
        forest = self.put_in_zone(self.alice, FOREST, Zone.GRAVEYARD)

        spell = self.cast(REGROWTH, forest)

        self.assertIn(forest, self.alice.hand)
        self.assertIn(spell, self.alice.graveyard)

    def test_raise_dead_only_targets_owned_creature_cards(self) -> None:
        own_creature = self.put_in_zone(
            self.alice, GRIZZLY_BEARS, Zone.GRAVEYARD
        )
        own_land = self.put_in_zone(self.alice, FOREST, Zone.GRAVEYARD)
        opposing_creature = self.put_in_zone(
            self.bob, GRIZZLY_BEARS, Zone.GRAVEYARD
        )
        spell = self.put_in_zone(self.alice, RAISE_DEAD, Zone.HAND)

        self.assertEqual(self.game.legal_targets_for(spell), [own_creature])
        self.assertNotIn(own_land, self.game.legal_targets_for(spell))
        self.assertNotIn(opposing_creature, self.game.legal_targets_for(spell))

    def test_resurrection_returns_creature_to_play_with_summoning_sickness(self) -> None:
        elves = self.put_in_zone(
            self.alice, LLANOWAR_ELVES, Zone.GRAVEYARD
        )

        self.cast(RESURRECTION, elves)

        self.assertIn(elves, self.alice.battlefield)
        self.assertEqual(elves.controller_id, self.alice.id)
        self.assertEqual(elves.entered_battlefield_turn, self.game.turn_number)
        self.alice.mana_pool.green = 0
        self.assertFalse(self.game.can_activate_ability(self.alice.id, elves, 0))
        self.game.begin_combat()
        with self.assertRaisesRegex(ValueError, "did not begin the turn"):
            self.game.declare_attackers([elves])


if __name__ == "__main__":
    unittest.main()
