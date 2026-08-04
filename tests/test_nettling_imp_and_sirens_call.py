import unittest

from beta_magic import (
    ANIMATE_WALL,
    DRUDGE_SKELETONS,
    GRIZZLY_BEARS,
    NETTLING_IMP,
    SEA_SERPENT,
    SIRENS_CALL,
    WALL_OF_WOOD,
    WHITE_KNIGHT,
    Card,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class AttackCompulsionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.active_player_index = 1
        self.game.current_phase = TurnPhase.MAIN
        self.imp = self.permanent(self.alice, NETTLING_IMP)

    def permanent(self, player, definition, *, summoned=False):
        card = Card(
            definition, player.id, controller_id=player.id,
            zone=Zone.BATTLEFIELD, entered_battlefield_turn=0,
            controller_at_turn_start_id=player.id,
            summoned_turn=self.game.turn_number if summoned else None,
        )
        player.battlefield.append(card)
        return card

    def hand(self, player, definition):
        card = Card(definition, player.id, controller_id=player.id, zone=Zone.HAND)
        player.hand.append(card)
        return card

    def resolve_priority(self):
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def nettle(self, target):
        self.game.activate_ability(self.alice.id, self.imp, 0)
        self.game.complete_pending_activation((target,))
        self.resolve_priority()

    def finish_current_turn(self):
        self.game.current_phase = TurnPhase.END
        self.game.next_turn()

    def test_imp_can_nettle_tapped_creature_which_is_destroyed_if_it_does_not_attack(self):
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        bear.tapped = True
        self.nettle(bear)
        self.finish_current_turn()
        self.assertIn(bear, self.bob.graveyard)

    def test_imp_cannot_target_walls_protection_from_black_or_true_summons(self):
        wall = self.permanent(self.bob, WALL_OF_WOOD)
        warded = self.permanent(self.bob, WHITE_KNIGHT)
        summoned = self.permanent(self.bob, GRIZZLY_BEARS, summoned=True)
        legal_bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game.activate_ability(self.alice.id, self.imp, 0)
        legal = self.game.legal_targets_for()
        self.assertIn(legal_bear, legal)
        self.assertNotIn(wall, legal)
        self.assertNotIn(warded, legal)
        self.assertNotIn(summoned, legal)

    def test_nettled_creature_that_attacks_survives(self):
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.nettle(bear)
        self.game.begin_combat()
        with self.assertRaisesRegex(ValueError, "must attack"):
            self.game.declare_attackers(())
        self.game.declare_attackers((bear,))
        self.finish_current_turn()
        self.assertIn(bear, self.bob.battlefield)

    def test_nettled_landhome_creature_dies_when_it_cannot_attack(self):
        serpent = self.permanent(self.bob, SEA_SERPENT)
        self.nettle(serpent)
        self.finish_current_turn()
        self.assertIn(serpent, self.bob.graveyard)

    def test_nettling_destruction_allows_regeneration(self):
        skeleton = self.permanent(self.bob, DRUDGE_SKELETONS)
        self.nettle(skeleton)
        self.game.current_phase = TurnPhase.END
        self.game.next_turn()
        self.assertIsNotNone(self.game.pending_destruction)
        self.bob.mana_pool.black = 1
        self.game.activate_ability(self.bob.id, skeleton, 0)
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        self.assertIn(skeleton, self.bob.battlefield)
        self.assertTrue(skeleton.tapped)

    def test_imp_cannot_be_used_on_its_controllers_turn_or_after_attack(self):
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game.active_player_index = 0
        with self.assertRaisesRegex(RuntimeError, "opponent's turn"):
            self.game.activate_ability(self.alice.id, self.imp, 0)
        self.game.active_player_index = 1
        self.game.attacks_this_turn = 1
        with self.assertRaisesRegex(RuntimeError, "before the attack"):
            self.game.activate_ability(self.alice.id, self.imp, 0)

    def test_sirens_call_snapshots_non_summoned_creatures_and_kills_nonattackers(self):
        old_bear = self.permanent(self.bob, GRIZZLY_BEARS)
        summoned = self.permanent(self.bob, GRIZZLY_BEARS, summoned=True)
        wall = self.permanent(self.bob, WALL_OF_WOOD)
        old_bear.tapped = True
        call = self.hand(self.alice, SIRENS_CALL)
        self.alice.mana_pool.blue = 1
        self.game.begin_cast(call)
        self.resolve_priority()
        late_bear = self.permanent(self.bob, GRIZZLY_BEARS)

        self.finish_current_turn()

        self.assertIn(old_bear, self.bob.graveyard)
        self.assertIn(summoned, self.bob.battlefield)
        self.assertIn(wall, self.bob.battlefield)
        self.assertIn(late_bear, self.bob.battlefield)

    def test_sirens_call_can_force_an_animated_wall_but_never_destroys_it(self):
        wall = self.permanent(self.bob, WALL_OF_WOOD)
        aura = self.permanent(self.bob, ANIMATE_WALL)
        aura.enchanted_card_id = wall.id
        call = self.hand(self.alice, SIRENS_CALL)
        self.alice.mana_pool.blue = 1
        self.game.begin_cast(call)
        self.resolve_priority()
        self.game.begin_combat()
        with self.assertRaisesRegex(ValueError, "must attack"):
            self.game.declare_attackers(())
        self.game.declare_attackers((wall,))
        self.assertIn(wall, self.bob.battlefield)


if __name__ == "__main__":
    unittest.main()
