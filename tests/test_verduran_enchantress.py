import unittest

from beta_magic import (
    COUNTERSPELL,
    CRUSADE,
    GIANT_GROWTH,
    HOLY_STRENGTH,
    VERDURAN_ENCHANTRESS,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import FOREST, GRIZZLY_BEARS


class VerduranEnchantressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player: PlayerState, definition, zone: Zone) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id if zone is Zone.BATTLEFIELD else None,
            zone=zone,
            entered_battlefield_turn=0 if zone is Zone.BATTLEFIELD else None,
        )
        player.cards_in(zone).append(card)
        return card

    def resolve_all(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def claim_draw(self, enchantress: Card) -> None:
        while self.game.interruptible_spell_id is not None:
            self.game.pass_priority(
                self.game.players[self.game.priority_player_index].id
            )
        while (
            self.game.players[self.game.priority_player_index] is not self.alice
        ):
            self.game.pass_priority(
                self.game.players[self.game.priority_player_index].id
            )
        self.game.activate_ability(self.alice.id, enchantress, 0)

    def test_definition(self) -> None:
        self.assertEqual(VERDURAN_ENCHANTRESS.mana_cost.compact, "1GG")
        self.assertEqual(
            VERDURAN_ENCHANTRESS.card_types,
            frozenset({CardType.CREATURE}),
        )
        self.assertEqual(
            (VERDURAN_ENCHANTRESS.power, VERDURAN_ENCHANTRESS.toughness),
            (0, 2),
        )
        self.assertEqual(
            VERDURAN_ENCHANTRESS.activated_abilities[0].label,
            "Draw 1 card for casting an enchantment",
        )

    def test_may_draw_for_global_enchantment_cast_by_controller(self) -> None:
        enchantress = self.card(
            self.alice, VERDURAN_ENCHANTRESS, Zone.BATTLEFIELD
        )
        crusade = self.card(self.alice, CRUSADE, Zone.HAND)
        self.alice.mana_pool.white = 2
        before = len(self.alice.hand)

        self.game.begin_cast(crusade)
        self.claim_draw(enchantress)
        self.resolve_all()

        self.assertEqual(len(self.alice.hand), before)
        self.assertIn(crusade, self.alice.battlefield)

    def test_may_draw_for_enchant_creature_spell(self) -> None:
        enchantress = self.card(
            self.alice, VERDURAN_ENCHANTRESS, Zone.BATTLEFIELD
        )
        creature = self.card(self.alice, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        aura = self.card(self.alice, HOLY_STRENGTH, Zone.HAND)
        self.alice.mana_pool.white = 1
        before = len(self.alice.hand)

        self.game.begin_cast(aura)
        self.game.complete_pending_cast((creature,))
        self.claim_draw(enchantress)
        self.resolve_all()

        self.assertIn(aura, self.alice.battlefield)
        self.assertEqual(aura.enchanted_card_id, creature.id)
        self.assertEqual(len(self.alice.hand), before)

    def test_does_not_trigger_for_non_enchantment_or_opponents_spell(self) -> None:
        enchantress = self.card(
            self.alice, VERDURAN_ENCHANTRESS, Zone.BATTLEFIELD
        )
        growth = self.card(self.alice, GIANT_GROWTH, Zone.HAND)
        creature = self.card(self.alice, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.alice.mana_pool.green = 1
        self.game.begin_cast(growth)
        self.game.complete_pending_cast((creature,))
        self.assertEqual(self.game.event_opportunities, [])
        self.resolve_all()

        opposing_enchantment = self.card(self.bob, CRUSADE, Zone.HAND)
        opposing_enchantment.controller_id = self.bob.id
        self.game._record_spell_cast_opportunity(opposing_enchantment)
        self.assertEqual(self.game.event_opportunities, [])
        self.assertFalse(
            self.game.can_activate_ability(self.alice.id, enchantress, 0)
        )

    def test_does_not_trigger_for_itself_entering_play(self) -> None:
        enchantress = self.card(self.alice, VERDURAN_ENCHANTRESS, Zone.HAND)
        self.alice.mana_pool.green = 2
        self.alice.mana_pool.colorless = 1

        self.game.begin_cast(enchantress)

        self.assertEqual(self.game.event_opportunities, [])
        self.resolve_all()
        self.assertIn(enchantress, self.alice.battlefield)

    def test_countered_enchantment_is_not_a_cast_event(self) -> None:
        enchantress = self.card(
            self.alice, VERDURAN_ENCHANTRESS, Zone.BATTLEFIELD
        )
        creature = self.card(self.alice, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        aura = self.card(self.alice, HOLY_STRENGTH, Zone.HAND)
        counter = self.card(self.bob, COUNTERSPELL, Zone.HAND)
        self.alice.mana_pool.white = 1
        self.bob.mana_pool.blue = 2

        self.game.begin_cast(aura)
        self.game.complete_pending_cast((creature,))
        self.assertEqual(len(self.game.event_opportunities), 1)
        self.game.begin_cast(counter)
        self.game.complete_pending_cast((aura,))
        self.resolve_all()

        self.assertIn(aura, self.alice.graveyard)
        self.assertEqual(self.game.event_opportunities, [])
        self.assertFalse(
            self.game.can_activate_ability(self.alice.id, enchantress, 0)
        )

    def test_each_enchantress_may_catch_the_event_once(self) -> None:
        first = self.card(self.alice, VERDURAN_ENCHANTRESS, Zone.BATTLEFIELD)
        second = self.card(self.alice, VERDURAN_ENCHANTRESS, Zone.BATTLEFIELD)
        crusade = self.card(self.alice, CRUSADE, Zone.HAND)
        self.alice.mana_pool.white = 2
        before = len(self.alice.hand)

        self.game.begin_cast(crusade)
        self.claim_draw(first)
        self.game.pass_priority(self.bob.id)
        self.game.activate_ability(self.alice.id, second, 0)
        self.resolve_all()

        self.assertEqual(len(self.alice.hand), before + 1)


if __name__ == "__main__":
    unittest.main()
