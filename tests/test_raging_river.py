import unittest

from beta_magic import (
    BENALISH_HERO,
    JADE_STATUE,
    MESA_PEGASUS,
    RAGING_RIVER,
    Card,
    CardType,
    CombatStep,
    GameState,
    PlayerState,
    RiverSide,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS, PHANTOM_MONSTER
from beta_magic.ui import GameViewModel


class RagingRiverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 12
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 12
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.permanent(self.alice, RAGING_RIVER)

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def close_response_window(self) -> None:
        first = self.game.players[self.game.priority_player_index]
        self.game.pass_priority(first.id)
        second = self.game.players[self.game.priority_player_index]
        self.game.pass_priority(second.id)

    def reach_attacker_placement(self, attackers, defender_sides):
        self.game.begin_combat()
        self.close_response_window()
        self.assertEqual(
            self.game.combat.step, CombatStep.RIVER_DEFENDER_ASSIGNMENT
        )
        self.game.choose_raging_river_sides(self.bob.id, defender_sides)
        self.game.declare_attackers(attackers)
        self.assertEqual(
            self.game.combat.step, CombatStep.RIVER_ATTACKER_ASSIGNMENT
        )

    def test_defender_divides_before_attackers_are_declared(self) -> None:
        first = self.permanent(self.bob, GRIZZLY_BEARS)
        second = self.permanent(self.bob, GRIZZLY_BEARS)
        flyer = self.permanent(self.bob, PHANTOM_MONSTER)

        self.game.begin_combat()
        self.close_response_window()

        self.assertEqual(
            set(self.game.combat.river_choice_card_ids),
            {first.id, second.id},
        )
        self.assertNotIn(flyer.id, self.game.combat.river_choice_card_ids)
        self.game.choose_raging_river_sides(
            self.bob.id,
            {first: RiverSide.LEFT, second: RiverSide.RIGHT},
        )
        self.assertEqual(self.game.combat.step, CombatStep.DECLARE_ATTACKERS)

    def test_ground_blockers_are_restricted_but_flyers_ignore_banks(self) -> None:
        attacker = self.permanent(self.alice, GRIZZLY_BEARS)
        ground = self.permanent(self.bob, GRIZZLY_BEARS)
        flyer = self.permanent(self.bob, PHANTOM_MONSTER)
        self.reach_attacker_placement(
            [attacker], {ground: RiverSide.LEFT}
        )
        self.game.choose_raging_river_sides(
            self.alice.id, {attacker: RiverSide.RIGHT}
        )
        self.close_response_window()

        with self.assertRaisesRegex(ValueError, "other side"):
            self.game.declare_blockers({ground: attacker})
        self.game.declare_blockers({flyer: attacker})
        self.assertEqual(self.game.combat.blockers[attacker.id], [flyer])

    def test_a_ground_blocker_can_block_a_band_member_on_its_bank(self) -> None:
        hero = self.permanent(self.alice, BENALISH_HERO)
        pegasus = self.permanent(self.alice, MESA_PEGASUS)
        blocker = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.close_response_window()
        self.game.choose_raging_river_sides(
            self.bob.id, {blocker: RiverSide.LEFT}
        )
        self.game.declare_attackers(
            [hero, pegasus], bands=[(hero, pegasus)]
        )
        self.game.choose_raging_river_sides(
            self.alice.id,
            {hero: RiverSide.LEFT, pegasus: RiverSide.RIGHT},
        )
        self.close_response_window()

        self.game.declare_blockers({blocker: pegasus})

        self.assertEqual(self.game.combat.blockers[hero.id], [blocker])
        self.assertEqual(self.game.combat.blockers[pegasus.id], [blocker])

    def test_multiple_rivers_still_make_only_one_split(self) -> None:
        self.permanent(self.alice, RAGING_RIVER)
        defender = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.close_response_window()

        self.assertEqual(self.game.combat.river_choice_card_ids, (defender.id,))

    def test_defending_jade_statue_is_placed_only_after_animation(self) -> None:
        attacker = self.permanent(self.alice, GRIZZLY_BEARS)
        statue = self.permanent(self.bob, JADE_STATUE)
        self.game.begin_combat()
        self.close_response_window()
        self.assertEqual(self.game.combat.step, CombatStep.DECLARE_ATTACKERS)
        self.game.declare_attackers([attacker])
        self.game.choose_raging_river_sides(
            self.alice.id, {attacker: RiverSide.LEFT}
        )

        self.game.pass_priority(self.alice.id)
        self.bob.mana_pool.colorless = 2
        self.game.activate_ability(self.bob.id, statue, 0)
        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)

        self.assertIn(CardType.CREATURE, self.game.card_types(statue))
        self.assertEqual(
            self.game.combat.step, CombatStep.RIVER_DEFENDER_ASSIGNMENT
        )
        self.assertEqual(self.game.combat.river_choice_card_ids, (statue.id,))

    def test_ui_supports_bulk_side_assignment_and_confirmation(self) -> None:
        first = self.permanent(self.bob, GRIZZLY_BEARS)
        second = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.close_response_window()
        view = GameViewModel(self.game)
        view.switchPerspective()

        view.toggleCard(str(first.id))
        view.setRiverSide("L")
        view.toggleCard(str(second.id))
        view.setRiverSide("R")

        state = view.state
        self.assertEqual(state["riverChoiceProgress"], "2 of 2 placed")
        self.assertTrue(state["canConfirmRiverSides"])
        cards = {card["id"]: card for card in state["perspective"]["battlefield"]}
        self.assertEqual(cards[str(first.id)]["riverSide"], "L")
        self.assertEqual(cards[str(second.id)]["riverSide"], "R")

        view.confirmRiverSides()
        self.assertEqual(self.game.combat.step, CombatStep.DECLARE_ATTACKERS)


if __name__ == "__main__":
    unittest.main()
