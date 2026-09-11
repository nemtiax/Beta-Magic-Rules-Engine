import unittest

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.black import DRAIN_LIFE
from beta_magic.card_defs.green import GRIZZLY_BEARS
from beta_magic.card_defs.lands import SWAMP
from beta_magic.card_defs.white import WHITE_KNIGHT


class DrainLifeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [SWAMP] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [SWAMP] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    @staticmethod
    def add(player, definition, zone) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id if zone is Zone.BATTLEFIELD else None,
            base_controller_id=player.id if zone is Zone.BATTLEFIELD else None,
            zone=zone,
        )
        player.cards_in(zone).append(card)
        return card

    def begin(self, x_value, target):
        spell = self.add(self.alice, DRAIN_LIFE, Zone.HAND)
        self.game.begin_cast(spell, x_value=x_value)
        self.game.complete_pending_cast((target,))
        return spell

    def resolve(self):
        while self.game.stack or self.game.pending_damage:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_x_must_be_paid_with_black_mana(self):
        spell = self.add(self.alice, DRAIN_LIFE, Zone.HAND)
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 4
        self.assertEqual(self.game.maximum_affordable_x(spell), 0)
        with self.assertRaisesRegex(RuntimeError, "not enough mana"):
            self.game.begin_cast(spell, x_value=1)

    def test_generic_one_may_be_paid_with_nonblack_mana(self):
        self.alice.mana_pool.black = 4
        self.alice.mana_pool.colorless = 1
        self.begin(3, self.bob)
        self.resolve()
        self.assertEqual((self.alice.life, self.bob.life), (23, 17))

    def test_creature_life_gain_is_capped_at_toughness_but_overkill_remains(self):
        bear = self.add(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.alice.mana_pool.black = 6
        self.alice.mana_pool.colorless = 1
        self.begin(5, bear)
        self.resolve()
        self.assertEqual(self.alice.life, 22)
        self.assertIn(bear, self.bob.graveyard)

    def test_prevented_damage_does_not_gain_life(self):
        self.game.pause_for_damage_windows = True
        self.alice.mana_pool.black = 4
        self.alice.mana_pool.colorless = 1
        self.begin(3, self.bob)
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        packet = self.game.pending_damage.packets[0]
        packet.prevented = 2
        self.resolve()
        self.assertEqual((self.alice.life, self.bob.life), (21, 19))

    def test_protection_from_black_prevents_targeting(self):
        knight = self.add(self.bob, WHITE_KNIGHT, Zone.BATTLEFIELD)
        self.alice.mana_pool.black = 4
        self.alice.mana_pool.colorless = 1
        spell = self.add(self.alice, DRAIN_LIFE, Zone.HAND)
        self.game.begin_cast(spell, x_value=3)
        self.assertNotIn(knight, self.game.legal_targets_for())
        with self.assertRaisesRegex(ValueError, "illegal target"):
            self.game.complete_pending_cast((knight,))
        self.assertEqual(self.alice.life, 20)
        self.assertIn(knight, self.bob.battlefield)

    def test_extra_black_is_not_part_of_casting_cost(self):
        spell = self.add(self.alice, DRAIN_LIFE, Zone.HAND)
        self.assertEqual(self.game.spell_casting_cost_value(spell, 7), 2)
        self.alice.mana_pool.black = 5
        self.alice.mana_pool.colorless = 1
        self.begin(4, self.bob)
        self.assertEqual(self.game.spell_casting_cost_value(spell, 4), 2)


if __name__ == "__main__":
    unittest.main()
