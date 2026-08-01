import unittest

from beta_magic import (
    CHAOSLACE,
    CRYSTAL_ROD,
    DEATHLACE,
    IRON_STAR,
    LACES,
    LIFELACE,
    LIGHTNING_BOLT,
    PURELACE,
    THOUGHTLACE,
    Card,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS, ISLAND, SOL_RING


class LaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def hand(player, definition):
        card = Card(definition, owner_id=player.id, zone=Zone.HAND)
        player.hand.append(card)
        return card

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        player.battlefield.append(card)
        return card

    def resolve_interrupt(self):
        first = self.game.players[self.game.priority_player_index]
        second = self.game.players[1 - self.game.priority_player_index]
        self.game.pass_priority(first.id)
        self.game.pass_priority(second.id)

    def cast_lace(self, player, definition, target):
        lace = self.hand(player, definition)
        color = next(iter(definition.colors))
        player.mana_pool.add(color)
        self.game.begin_cast(lace)
        self.game.complete_pending_cast((target,))
        self.resolve_interrupt()
        return lace

    def test_cycle_definitions(self):
        self.assertEqual(
            LACES,
            (PURELACE, THOUGHTLACE, DEATHLACE, CHAOSLACE, LIFELACE),
        )
        self.assertEqual(
            [lace.mana_cost.compact for lace in LACES],
            ["W", "U", "B", "R", "G"],
        )

    def test_lace_can_color_an_artifact_or_land_in_play(self):
        artifact = self.permanent(self.alice, SOL_RING)
        land = self.permanent(self.bob, ISLAND)

        self.cast_lace(self.alice, CHAOSLACE, artifact)
        self.cast_lace(self.alice, DEATHLACE, land)

        self.assertEqual(self.game.card_colors(artifact), {Color.RED})
        self.assertEqual(self.game.card_colors(land), {Color.BLACK})
        self.assertEqual(land.definition.mana_cost.compact, "")

    def test_color_change_is_forgotten_when_card_leaves_play(self):
        creature = self.permanent(self.bob, GRIZZLY_BEARS)
        self.cast_lace(self.alice, PURELACE, creature)
        self.assertEqual(self.game.card_colors(creature), {Color.WHITE})

        self.game._move_card(creature, Zone.GRAVEYARD)

        self.assertIsNone(creature.color_override)
        self.assertEqual(self.game.card_colors(creature), {Color.GREEN})

    def test_laced_permanent_spell_keeps_color_when_it_enters_play(self):
        creature = self.hand(self.alice, GRIZZLY_BEARS)
        self.alice.mana_pool.green = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(creature)
        self.game.pass_priority(self.bob.id)

        self.cast_lace(self.alice, THOUGHTLACE, creature)
        self.assertEqual(self.game.card_colors(creature), {Color.BLUE})

        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)
        self.assertEqual(creature.zone, Zone.BATTLEFIELD)
        self.assertEqual(self.game.card_colors(creature), {Color.BLUE})

    def test_lucky_charm_uses_the_spells_final_color(self):
        self.permanent(self.alice, IRON_STAR)
        self.permanent(self.alice, CRYSTAL_ROD)
        bolt = self.hand(self.bob, LIGHTNING_BOLT)
        self.bob.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.alice,))
        self.assertEqual(self.game.event_opportunities[0].spell_colors, {Color.RED})
        self.game.pass_priority(self.alice.id)

        self.cast_lace(self.bob, THOUGHTLACE, bolt)

        self.assertEqual(self.game.event_opportunities[0].spell_colors, {Color.BLUE})

    def test_target_spells_caster_has_same_target_interrupt_precedence(self):
        bolt = self.hand(self.alice, LIGHTNING_BOLT)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.bob,))

        # Opponent declares blue first; the spell's caster declares white
        # second. The FAQ says the caster's Lace nevertheless resolves first.
        blue = self.hand(self.bob, THOUGHTLACE)
        white = self.hand(self.alice, PURELACE)
        self.bob.mana_pool.blue = 1
        self.alice.mana_pool.white = 1
        self.game.begin_cast(blue)
        self.game.complete_pending_cast((bolt,))
        self.game.begin_cast(white)
        self.game.complete_pending_cast((bolt,))

        self.resolve_interrupt()
        self.assertEqual(self.game.card_colors(bolt), {Color.WHITE})
        self.resolve_interrupt()
        self.assertEqual(self.game.card_colors(bolt), {Color.BLUE})


if __name__ == "__main__":
    unittest.main()
