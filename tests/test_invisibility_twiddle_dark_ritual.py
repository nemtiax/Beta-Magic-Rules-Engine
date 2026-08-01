import unittest

from beta_magic import (
    DARK_RITUAL,
    INVISIBILITY,
    TWIDDLE,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS, WALL_OF_WOOD


class InvisibilityTwiddleDarkRitualTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player, definition, zone):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=zone,
            entered_battlefield_turn=0,
        )
        player.cards_in(zone).append(card)
        return card

    def pass_both(self):
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

    def test_invisibility_allows_only_walls_to_block(self):
        attacker = self.card(self.alice, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        aura = self.card(self.alice, INVISIBILITY, Zone.BATTLEFIELD)
        aura.enchanted_card_id = attacker.id
        bear = self.card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        wall = self.card(self.bob, WALL_OF_WOOD, Zone.BATTLEFIELD)

        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        with self.assertRaisesRegex(ValueError, "only a Wall"):
            self.game.declare_blockers({bear: attacker})
        self.game.declare_blockers({wall: attacker})

    def test_twiddle_records_mode_and_sets_rather_than_toggles(self):
        target = self.card(self.alice, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        spell = self.card(self.alice, TWIDDLE, Zone.HAND)
        self.alice.mana_pool.blue = 1

        with self.assertRaisesRegex(ValueError, "casting mode"):
            self.game.begin_cast(spell)
        self.game.begin_cast(spell, mode="Tap")
        self.game.complete_pending_cast((target,))
        target.tapped = True
        self.pass_both()

        self.assertTrue(target.tapped)
        self.assertIn(spell, self.alice.graveyard)

    def test_dark_ritual_is_a_resolving_interrupt_spell(self):
        ritual = self.card(self.alice, DARK_RITUAL, Zone.HAND)
        self.alice.mana_pool.black = 1

        self.game.begin_cast(ritual)
        self.assertIn(ritual, self.game.stack)
        self.assertEqual(self.alice.mana_pool.black, 0)
        self.pass_both()

        self.assertEqual(self.alice.mana_pool.black, 3)
        self.assertIn(ritual, self.alice.graveyard)


if __name__ == "__main__":
    unittest.main()
