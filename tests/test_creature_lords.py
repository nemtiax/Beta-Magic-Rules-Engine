import unittest

from beta_magic import (
    BURROWING,
    CREATURE_LORDS,
    GOBLIN_KING,
    LORD_OF_ATLANTIS,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import TAIGA, TUNDRA
from beta_magic.card_defs import (
    GRIZZLY_BEARS,
    MERFOLK_OF_THE_PEARL_TRIDENT,
    MONSS_GOBLIN_RAIDERS,
)


class CreatureLordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 30)
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 30)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(player, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = player.id
        player.battlefield.append(card)
        return card

    def test_definitions_preserve_beta_creature_categories(self) -> None:
        self.assertEqual(CREATURE_LORDS, (LORD_OF_ATLANTIS, GOBLIN_KING))
        self.assertEqual(LORD_OF_ATLANTIS.mana_cost.compact, "UU")
        self.assertEqual(GOBLIN_KING.mana_cost.compact, "1RR")
        self.assertEqual(LORD_OF_ATLANTIS.subtypes, ("Lord of Atlantis",))
        self.assertEqual(GOBLIN_KING.subtypes, ("Goblin King",))
        self.assertEqual(MERFOLK_OF_THE_PEARL_TRIDENT.subtypes, ("Merfolk",))
        self.assertEqual(MONSS_GOBLIN_RAIDERS.subtypes, ("Goblins",))

    def test_lords_buff_matching_creatures_on_both_sides_not_themselves(self) -> None:
        cases = (
            (
                LORD_OF_ATLANTIS,
                MERFOLK_OF_THE_PEARL_TRIDENT,
                KeywordAbility.ISLANDWALK,
            ),
            (
                GOBLIN_KING,
                MONSS_GOBLIN_RAIDERS,
                KeywordAbility.MOUNTAINWALK,
            ),
        )
        for lord_definition, subject_definition, ability in cases:
            with self.subTest(lord_definition.name):
                lord = self.put_in_play(self.alice, lord_definition)
                subjects = (
                    self.put_in_play(self.alice, subject_definition),
                    self.put_in_play(self.bob, subject_definition),
                )
                for subject in subjects:
                    self.assertEqual(
                        (
                            self.game.creature_power(subject),
                            self.game.creature_toughness(subject),
                        ),
                        (2, 2),
                    )
                    self.assertIn(ability, self.game.creature_abilities(subject))
                self.assertEqual(
                    (
                        self.game.creature_power(lord),
                        self.game.creature_toughness(lord),
                    ),
                    (2, 2),
                )
                self.assertNotIn(ability, self.game.creature_abilities(lord))
                for card in (*subjects, lord):
                    self.game.put_permanent_in_graveyard(card)

    def test_lord_bonus_ends_when_source_leaves_play(self) -> None:
        lord = self.put_in_play(self.alice, LORD_OF_ATLANTIS)
        merfolk = self.put_in_play(self.alice, MERFOLK_OF_THE_PEARL_TRIDENT)
        self.game.put_permanent_in_graveyard(lord)

        self.assertEqual(
            (self.game.creature_power(merfolk), self.game.creature_toughness(merfolk)),
            (1, 1),
        )
        self.assertNotIn(
            KeywordAbility.ISLANDWALK, self.game.creature_abilities(merfolk)
        )

    def test_granted_landwalk_recognizes_a_dual_land_type(self) -> None:
        self.put_in_play(self.alice, LORD_OF_ATLANTIS)
        merfolk = self.put_in_play(self.alice, MERFOLK_OF_THE_PEARL_TRIDENT)
        blocker = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.put_in_play(self.bob, TUNDRA)
        self.game.begin_combat()
        self.game.declare_attackers([merfolk])

        with self.assertRaisesRegex(ValueError, "islandwalk"):
            self.game.declare_blockers({blocker: merfolk})

    def test_burrowing_grants_mountainwalk_against_a_dual_land(self) -> None:
        attacker = self.put_in_play(self.alice, GRIZZLY_BEARS)
        blocker = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.put_in_play(self.bob, TAIGA)
        aura = self.alice.library.pop()
        aura.definition = BURROWING
        aura.zone = Zone.HAND
        self.alice.hand.append(aura)
        self.alice.mana_pool.red = 1
        self.game.cast_enchantment(aura, attacker)
        self.game.begin_combat()
        self.game.declare_attackers([attacker])

        with self.assertRaisesRegex(ValueError, "mountainwalk"):
            self.game.declare_blockers({blocker: attacker})


if __name__ == "__main__":
    unittest.main()
