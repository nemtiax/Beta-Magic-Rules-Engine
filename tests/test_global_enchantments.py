import unittest

from beta_magic import (
    BAD_MOON,
    CASTLE,
    CRUSADE,
    GLOBAL_ENCHANTMENTS,
    ORCISH_ORIFLAMME,
    CardType,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import (
    GRAY_OGRE,
    GRIZZLY_BEARS,
    MONSS_GOBLIN_RAIDERS,
    SAVANNAH_LIONS,
    SCATHE_ZOMBIES,
)


def player(player_id: str) -> PlayerState:
    return PlayerState.with_deck(player_id, player_id.title(), [GRIZZLY_BEARS] * 16)


class GlobalEnchantmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = player("alice")
        self.bob = player("bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(owner: PlayerState, definition):
        card = owner.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        owner.battlefield.append(card)
        return card

    def test_three_global_enchantment_definitions(self) -> None:
        self.assertEqual(
            GLOBAL_ENCHANTMENTS,
            (CRUSADE, BAD_MOON, ORCISH_ORIFLAMME, CASTLE),
        )
        self.assertEqual(CRUSADE.mana_cost.compact, "WW")
        self.assertEqual(BAD_MOON.mana_cost.compact, "1B")
        self.assertEqual(ORCISH_ORIFLAMME.mana_cost.compact, "3R")
        self.assertTrue(
            all(CardType.ENCHANTMENT in card.card_types for card in GLOBAL_ENCHANTMENTS)
        )

    def test_crusade_buffs_white_creatures_on_both_sides(self) -> None:
        self.put_in_play(self.alice, CRUSADE)
        alice_lion = self.put_in_play(self.alice, SAVANNAH_LIONS)
        bob_lion = self.put_in_play(self.bob, SAVANNAH_LIONS)
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.assertEqual(
            (self.game.creature_power(alice_lion), self.game.creature_toughness(alice_lion)),
            (3, 2),
        )
        self.assertEqual(
            (self.game.creature_power(bob_lion), self.game.creature_toughness(bob_lion)),
            (3, 2),
        )
        self.assertEqual(
            (self.game.creature_power(bear), self.game.creature_toughness(bear)),
            (2, 2),
        )

    def test_bad_moon_only_buffs_black_creatures_and_copies_stack(self) -> None:
        self.put_in_play(self.alice, BAD_MOON)
        self.put_in_play(self.bob, BAD_MOON)
        zombie = self.put_in_play(self.alice, SCATHE_ZOMBIES)
        bear = self.put_in_play(self.alice, GRIZZLY_BEARS)
        self.assertEqual(
            (self.game.creature_power(zombie), self.game.creature_toughness(zombie)),
            (4, 4),
        )
        self.assertEqual(self.game.creature_power(bear), 2)

    def test_oriflamme_only_buffs_its_controllers_attacking_creatures(self) -> None:
        self.put_in_play(self.alice, ORCISH_ORIFLAMME)
        ogre = self.put_in_play(self.alice, GRAY_OGRE)
        bob_ogre = self.put_in_play(self.bob, GRAY_OGRE)
        self.assertEqual(self.game.creature_power(ogre), 2)
        self.game.begin_combat()
        self.game.declare_attackers([ogre])
        self.assertEqual(self.game.creature_power(ogre), 3)
        self.assertEqual(self.game.creature_power(bob_ogre), 2)
        self.game.declare_blockers({})
        self.game.advance_combat()
        self.game.deal_combat_damage()
        self.assertEqual(self.bob.life, 17)
        self.assertEqual(self.game.creature_power(ogre), 2)

    def test_toughness_bonus_is_used_for_lethal_damage(self) -> None:
        self.put_in_play(self.alice, CRUSADE)
        lion = self.put_in_play(self.alice, SAVANNAH_LIONS)
        goblin = self.put_in_play(self.bob, MONSS_GOBLIN_RAIDERS)
        self.game.begin_combat()
        self.game.declare_attackers([lion])
        self.game.declare_blockers({goblin: lion})
        self.game.advance_combat()
        self.game.deal_combat_damage()
        self.assertIn(lion, self.alice.battlefield)
        self.assertEqual(lion.damage, 1)
        self.assertIn(goblin, self.bob.graveyard)

    def test_enchantment_can_be_cast_by_paying_its_cost(self) -> None:
        enchantment = self.alice.library.pop()
        enchantment.definition = CRUSADE
        enchantment.zone = Zone.HAND
        self.alice.hand.append(enchantment)
        self.alice.mana_pool.white = 2
        self.game.cast_enchantment(enchantment)
        self.assertIn(enchantment, self.alice.battlefield)
        self.assertEqual(self.alice.mana_pool.total, 0)


if __name__ == "__main__":
    unittest.main()
