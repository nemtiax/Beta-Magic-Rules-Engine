import unittest

from beta_magic import (
    CombatStep,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import (
    GRAY_OGRE,
    GRIZZLY_BEARS,
    HILL_GIANT,
    MONSS_GOBLIN_RAIDERS,
)


def player(player_id: str) -> PlayerState:
    return PlayerState.with_deck(player_id, player_id.title(), [GRIZZLY_BEARS] * 8)


class CombatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = player("alice")
        self.bob = player("bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    def put_in_play(self, owner: PlayerState, definition, *, entered_turn=None):
        card = owner.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.entered_battlefield_turn = entered_turn
        owner.battlefield.append(card)
        return card

    def reach_damage(self, attackers, blockers=None):
        self.game.begin_combat()
        self.game.declare_attackers(attackers)
        self.game.declare_blockers(blockers or {})
        self.game.advance_combat()
        self.assertEqual(self.game.combat.step, CombatStep.DAMAGE)

    def test_unblocked_attacker_damages_player(self) -> None:
        bear = self.put_in_play(self.alice, GRIZZLY_BEARS)
        self.reach_damage([bear])
        self.game.deal_combat_damage()
        self.assertEqual(self.bob.life, 18)
        self.assertTrue(bear.tapped)
        self.assertIsNone(self.game.combat)

    def test_blocked_creatures_deal_simultaneous_lethal_damage(self) -> None:
        bear = self.put_in_play(self.alice, GRIZZLY_BEARS)
        ogre = self.put_in_play(self.bob, GRAY_OGRE)
        self.reach_damage([bear], {ogre: bear})
        self.game.deal_combat_damage()
        self.assertIn(bear, self.alice.graveyard)
        self.assertIn(ogre, self.bob.graveyard)
        self.assertEqual(self.bob.life, 20)

    def test_multiple_blockers_require_attacker_damage_assignment(self) -> None:
        giant = self.put_in_play(self.alice, HILL_GIANT)
        goblin_one = self.put_in_play(self.bob, MONSS_GOBLIN_RAIDERS)
        goblin_two = self.put_in_play(self.bob, MONSS_GOBLIN_RAIDERS)
        self.reach_damage([giant], {goblin_one: giant, goblin_two: giant})
        with self.assertRaises(ValueError):
            self.game.deal_combat_damage()
        self.game.deal_combat_damage(
            {giant: {goblin_one: 2, goblin_two: 1}}
        )
        self.assertIn(goblin_one, self.bob.graveyard)
        self.assertIn(goblin_two, self.bob.graveyard)
        self.assertIn(giant, self.alice.battlefield)
        self.assertEqual(giant.damage, 2)

    def test_summoning_sick_and_tapped_creatures_cannot_attack(self) -> None:
        new_bear = self.put_in_play(
            self.alice, GRIZZLY_BEARS, entered_turn=self.game.turn_number
        )
        self.game.begin_combat()
        with self.assertRaises(ValueError):
            self.game.declare_attackers([new_bear])

    def test_only_one_attack_and_phase_cannot_advance_during_combat(self) -> None:
        self.game.begin_combat()
        with self.assertRaises(RuntimeError):
            self.game.advance_phase()
        self.game.declare_attackers([])
        self.game.declare_blockers({})
        self.game.advance_combat()
        self.game.deal_combat_damage()
        with self.assertRaises(RuntimeError):
            self.game.begin_combat()

    def test_mana_burn_occurs_at_attack_boundaries(self) -> None:
        self.alice.mana_pool.green = 1
        self.game.begin_combat()
        self.assertEqual(self.alice.life, 20)
        self.assertEqual(self.alice.mana_pool.green, 1)
        self.game.declare_attackers([])
        self.assertEqual(self.alice.life, 19)
        self.game.declare_blockers({})
        self.game.advance_combat()
        self.bob.mana_pool.blue = 1
        self.game.deal_combat_damage()
        self.assertEqual(self.bob.life, 19)

    def test_combat_exposes_all_three_fast_effect_windows(self) -> None:
        bear = self.put_in_play(self.alice, GRIZZLY_BEARS)
        self.assertEqual(self.game.begin_combat(), CombatStep.ATTACK_RESPONSE)
        self.assertEqual(self.game.priority_player_index, 1)
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        self.assertEqual(self.game.combat.step, CombatStep.DECLARE_ATTACKERS)
        self.assertIsNone(self.game.priority_player_index)
        self.assertEqual(
            self.game.declare_attackers([bear]), CombatStep.ATTACKER_RESPONSE
        )
        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)
        self.assertEqual(self.game.combat.step, CombatStep.DECLARE_BLOCKERS)
        self.assertIsNone(self.game.priority_player_index)
        self.assertEqual(
            self.game.declare_blockers({}), CombatStep.BLOCKER_RESPONSE
        )
        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)
        self.assertEqual(self.game.combat.step, CombatStep.DAMAGE)


if __name__ == "__main__":
    unittest.main()
