import unittest

from beta_magic import (
    BADLANDS,
    CONVERSION,
    FOREST,
    GAUNTLET_OF_MIGHT,
    MOUNTAIN,
    PLAINS,
    Card,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRAY_OGRE, SCATHE_ZOMBIES


class GauntletOfMightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [MOUNTAIN] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [FOREST] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition, *, owner_id=None, tapped=False):
        card = Card(
            definition,
            owner_id or player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
            tapped=tapped,
        )
        player.battlefield.append(card)
        return card

    def test_definition(self) -> None:
        self.assertEqual(GAUNTLET_OF_MIGHT.mana_cost.compact, "4")
        bonus = GAUNTLET_OF_MIGHT.continuous_effects[0]
        self.assertEqual((bonus.power, bonus.toughness, bonus.color), (1, 1, Color.RED))
        mana = GAUNTLET_OF_MIGHT.land_tap_mana_effects[0]
        self.assertEqual((mana.color, mana.land_subtype), (Color.RED, "Mountain"))
        self.assertTrue(mana.owner_receives)

    def test_buffs_red_creatures_controlled_by_either_player(self) -> None:
        self.permanent(self.alice, GAUNTLET_OF_MIGHT)
        alice_ogre = self.permanent(self.alice, GRAY_OGRE)
        bob_ogre = self.permanent(self.bob, GRAY_OGRE)
        zombie = self.permanent(self.bob, SCATHE_ZOMBIES)

        self.assertEqual(
            (self.game.creature_power(alice_ogre), self.game.creature_toughness(alice_ogre)),
            (3, 3),
        )
        self.assertEqual(
            (self.game.creature_power(bob_ogre), self.game.creature_toughness(bob_ogre)),
            (3, 3),
        )
        self.assertEqual(
            (self.game.creature_power(zombie), self.game.creature_toughness(zombie)),
            (2, 2),
        )

    def test_mountain_produces_extra_red_when_tapped_for_any_reason(self) -> None:
        self.permanent(self.alice, GAUNTLET_OF_MIGHT)
        mountain = self.permanent(self.bob, MOUNTAIN)

        self.assertTrue(self.game._tap_permanent(mountain))

        self.assertEqual(self.bob.mana_pool.red, 1)

    def test_multiland_produces_red_even_when_other_color_is_chosen(self) -> None:
        self.permanent(self.alice, GAUNTLET_OF_MIGHT)
        badlands = self.permanent(self.bob, BADLANDS)

        self.game.activate_ability(self.bob.id, badlands, 0)

        self.assertEqual(self.bob.mana_pool.black, 1)
        self.assertEqual(self.bob.mana_pool.red, 1)

    def test_conversion_removes_mountain_type_and_gauntlet_mana(self) -> None:
        self.permanent(self.alice, GAUNTLET_OF_MIGHT)
        self.permanent(self.alice, CONVERSION)
        mountain = self.permanent(self.bob, MOUNTAIN)

        self.assertEqual(self.game.land_subtypes(mountain), ("Plains",))
        self.game.activate_ability(self.bob.id, mountain, 0)

        self.assertEqual(self.bob.mana_pool.white, 1)
        self.assertEqual(self.bob.mana_pool.red, 0)

    def test_extra_mana_goes_to_owner_not_current_controller(self) -> None:
        self.permanent(self.alice, GAUNTLET_OF_MIGHT)
        mountain = self.permanent(self.bob, MOUNTAIN, owner_id=self.alice.id)

        self.game.activate_ability(self.bob.id, mountain, 0)

        self.assertEqual(self.bob.mana_pool.red, 1)
        self.assertEqual(self.alice.mana_pool.red, 1)

    def test_tapped_gauntlet_supplies_neither_bonus(self) -> None:
        self.permanent(self.alice, GAUNTLET_OF_MIGHT, tapped=True)
        ogre = self.permanent(self.alice, GRAY_OGRE)
        mountain = self.permanent(self.alice, MOUNTAIN)

        self.game.activate_ability(self.alice.id, mountain, 0)

        self.assertEqual(self.alice.mana_pool.red, 1)
        self.assertEqual(
            (self.game.creature_power(ogre), self.game.creature_toughness(ogre)),
            (2, 2),
        )


if __name__ == "__main__":
    unittest.main()
