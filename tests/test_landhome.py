import unittest

from beta_magic import (
    LANDHOME_CREATURES,
    PIRATE_SHIP,
    SEA_SERPENT,
    Card,
    CardType,
    CombatStep,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import ISLAND, TROPICAL_ISLAND


class LandhomeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState("alice", "Alice")
        self.bob = PlayerState("bob", "Bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(player: PlayerState, definition) -> Card:
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
            controller_at_turn_start_id=player.id,
        )
        player.battlefield.append(card)
        return card

    def test_card_definitions(self) -> None:
        self.assertEqual(LANDHOME_CREATURES, (PIRATE_SHIP, SEA_SERPENT))
        self.assertEqual(PIRATE_SHIP.mana_cost.compact, "4U")
        self.assertEqual((PIRATE_SHIP.power, PIRATE_SHIP.toughness), (4, 3))
        self.assertEqual(SEA_SERPENT.mana_cost.compact, "5U")
        self.assertEqual((SEA_SERPENT.power, SEA_SERPENT.toughness), (5, 5))
        self.assertEqual(PIRATE_SHIP.landhome.land_subtype, "Island")
        self.assertEqual(SEA_SERPENT.landhome.land_subtype, "Island")
        self.assertEqual(len(PIRATE_SHIP.activated_abilities), 1)

    def test_landhome_creature_dies_without_controller_island(self) -> None:
        serpent = self.put_in_play(self.alice, SEA_SERPENT)

        self.game.check_state_based_actions()

        self.assertIn(serpent, self.alice.graveyard)
        self.assertNotIn(serpent, self.alice.battlefield)

    def test_losing_last_island_immediately_kills_landhome_creatures(
        self,
    ) -> None:
        island = self.put_in_play(self.alice, ISLAND)
        ship = self.put_in_play(self.alice, PIRATE_SHIP)
        serpent = self.put_in_play(self.alice, SEA_SERPENT)
        self.game.check_state_based_actions()

        self.game.put_permanent_in_graveyard(island)

        self.assertIn(ship, self.alice.graveyard)
        self.assertIn(serpent, self.alice.graveyard)

    def test_dual_land_with_island_subtype_satisfies_landhome(self) -> None:
        self.put_in_play(self.alice, TROPICAL_ISLAND)
        ship = self.put_in_play(self.alice, PIRATE_SHIP)

        self.game.check_state_based_actions()

        self.assertIn(ship, self.alice.battlefield)

    def test_cannot_attack_without_defending_island(self) -> None:
        self.put_in_play(self.alice, ISLAND)
        serpent = self.put_in_play(self.alice, SEA_SERPENT)
        self.game.begin_combat()

        with self.assertRaisesRegex(ValueError, "defender controls an Island"):
            self.game.declare_attackers([serpent])

        self.assertIs(self.game.combat.step, CombatStep.DECLARE_ATTACKERS)

    def test_defending_dual_land_allows_attack(self) -> None:
        self.put_in_play(self.alice, ISLAND)
        serpent = self.put_in_play(self.alice, SEA_SERPENT)
        self.put_in_play(self.bob, TROPICAL_ISLAND)

        self.game.begin_combat()
        step = self.game.declare_attackers([serpent])

        self.assertIs(step, CombatStep.ATTACKER_RESPONSE)
        self.assertIn(serpent, self.game.combat.attackers)

    def test_pirate_ship_can_tap_when_opponent_has_no_island(self) -> None:
        self.put_in_play(self.alice, ISLAND)
        ship = self.put_in_play(self.alice, PIRATE_SHIP)

        self.game.activate_ability(self.alice.id, ship, 0)
        self.game.complete_pending_activation([self.bob])
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

        self.assertTrue(ship.tapped)
        self.assertEqual(self.bob.life, 19)

    def test_landhome_is_a_creature_requirement_not_a_keyword(self) -> None:
        self.assertIn(CardType.CREATURE, PIRATE_SHIP.card_types)
        self.assertFalse(
            any(
                ability.value.endswith("landhome")
                for ability in PIRATE_SHIP.abilities
            )
        )


if __name__ == "__main__":
    unittest.main()
