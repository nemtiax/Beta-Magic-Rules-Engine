import unittest

from beta_magic import (
    FOREST,
    ISLAND,
    MEEKSTONE,
    MOUNTAIN,
    SAVANNAH_LIONS,
    SMOKE,
    STASIS,
    WAR_MAMMOTH,
    WINTER_ORB,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class UntapRestrictionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [ISLAND] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def permanent(player: PlayerState, definition, *, tapped=True) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            tapped=tapped,
        )
        player.battlefield.append(card)
        return card

    def enter_untap(self) -> None:
        self.game._enter_phase(TurnPhase.UNTAP)

    def test_definitions_describe_the_four_restrictions(self) -> None:
        self.assertEqual(MEEKSTONE.mana_cost.compact, "1")
        self.assertEqual(WINTER_ORB.mana_cost.compact, "2")
        self.assertEqual(SMOKE.mana_cost.compact, "RR")
        self.assertEqual(STASIS.mana_cost.compact, "1U")
        self.assertEqual(MEEKSTONE.untap_effects[0].maximum_creature_power, 2)
        self.assertEqual(WINTER_ORB.untap_effects[0].card_type, CardType.LAND)
        self.assertEqual(SMOKE.untap_effects[0].card_type, CardType.CREATURE)
        self.assertTrue(STASIS.untap_effects[0].skip_untap)

    def test_meekstone_uses_current_power(self) -> None:
        self.permanent(self.bob, MEEKSTONE, tapped=False)
        lion = self.permanent(self.alice, SAVANNAH_LIONS)
        mammoth = self.permanent(self.alice, WAR_MAMMOTH)

        self.enter_untap()

        self.assertFalse(lion.tapped)
        self.assertTrue(mammoth.tapped)

    def test_tapped_continuous_artifact_does_not_apply(self) -> None:
        self.permanent(self.bob, WINTER_ORB, tapped=True)
        lands = [
            self.permanent(self.alice, FOREST),
            self.permanent(self.alice, MOUNTAIN),
        ]

        self.enter_untap()

        self.assertTrue(all(not land.tapped for land in lands))
        self.assertIsNone(self.game.pending_untap_choice)

    def test_winter_orb_requires_a_land_choice(self) -> None:
        self.permanent(self.bob, WINTER_ORB, tapped=False)
        forest = self.permanent(self.alice, FOREST)
        mountain = self.permanent(self.alice, MOUNTAIN)
        creature = self.permanent(self.alice, SAVANNAH_LIONS)

        self.enter_untap()

        self.assertIsNotNone(self.game.pending_untap_choice)
        self.game.choose_untap_cards(self.alice.id, (forest,))
        self.assertFalse(forest.tapped)
        self.assertTrue(mountain.tapped)
        self.assertFalse(creature.tapped)

    def test_smoke_requires_a_creature_choice(self) -> None:
        self.permanent(self.bob, SMOKE, tapped=False)
        lion = self.permanent(self.alice, SAVANNAH_LIONS)
        mammoth = self.permanent(self.alice, WAR_MAMMOTH)
        land = self.permanent(self.alice, FOREST)

        self.enter_untap()
        self.game.choose_untap_cards(self.alice.id, (lion,))

        self.assertFalse(lion.tapped)
        self.assertTrue(mammoth.tapped)
        self.assertFalse(land.tapped)

    def test_stasis_suppresses_all_untapping(self) -> None:
        self.permanent(self.bob, STASIS, tapped=False)
        land = self.permanent(self.alice, FOREST)
        creature = self.permanent(self.alice, SAVANNAH_LIONS)

        self.enter_untap()

        self.assertTrue(land.tapped)
        self.assertTrue(creature.tapped)
        self.assertIsNone(self.game.pending_untap_choice)

    def test_duplicate_caps_do_not_compound(self) -> None:
        self.permanent(self.bob, SMOKE, tapped=False)
        self.permanent(self.alice, SMOKE, tapped=False)
        lion = self.permanent(self.alice, SAVANNAH_LIONS)
        mammoth = self.permanent(self.alice, WAR_MAMMOTH)

        self.enter_untap()
        self.game.choose_untap_cards(self.alice.id, (mammoth,))

        self.assertTrue(lion.tapped)
        self.assertFalse(mammoth.tapped)


if __name__ == "__main__":
    unittest.main()
