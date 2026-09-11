import unittest

from beta_magic import (
    ELVISH_ARCHERS,
    FOG,
    GRIZZLY_BEARS,
    HILL_GIANT,
    MONSS_GOBLIN_RAIDERS,
    THICKET_BASILISK,
    WAR_MAMMOTH,
    Card,
    CardType,
    CombatStep,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class FogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 30
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 30
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player: PlayerState, definition) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        player.battlefield.append(card)
        return card

    def cast_fog(self) -> Card:
        fog = Card(FOG, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(fog)
        self.alice.mana_pool.green += 1
        self.game.begin_cast(fog)
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        return fog

    def reach_damage(self, attacker: Card, blocker: Card | None = None) -> None:
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        self.game.declare_blockers({blocker: attacker} if blocker else {})
        self.game.advance_combat()
        self.assertEqual(self.game.combat.step, CombatStep.DAMAGE)

    def test_definition(self) -> None:
        self.assertEqual(FOG.mana_cost.compact, "G")
        self.assertEqual(FOG.card_types, frozenset({CardType.INSTANT}))
        self.assertFalse(FOG.target_requirement)

    def test_prevents_attacker_and_blocker_damage(self) -> None:
        attacker = self.permanent(self.alice, HILL_GIANT)
        blocker = self.permanent(self.bob, GRIZZLY_BEARS)
        self.cast_fog()
        self.reach_damage(attacker, blocker)

        self.game.deal_combat_damage()

        self.assertIn(attacker, self.alice.battlefield)
        self.assertIn(blocker, self.bob.battlefield)
        self.assertEqual((attacker.damage, blocker.damage), (0, 0))

    def test_skips_empty_damage_windows(self) -> None:
        attacker = self.permanent(self.alice, HILL_GIANT)
        blocker = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game.pause_for_damage_windows = True
        self.cast_fog()
        self.reach_damage(attacker, blocker)
        resolved_before = len(self.game.resolved_damage_incidents)

        self.game.deal_combat_damage()

        self.assertIsNone(self.game.pending_damage)
        self.assertIsNone(self.game.combat)
        self.assertEqual(
            len(self.game.resolved_damage_incidents), resolved_before
        )
        self.assertEqual((attacker.damage, blocker.damage), (0, 0))

    def test_prevents_unblocked_and_trample_damage_to_player(self) -> None:
        mammoth = self.permanent(self.alice, WAR_MAMMOTH)
        goblin = self.permanent(self.bob, MONSS_GOBLIN_RAIDERS)
        self.cast_fog()
        self.reach_damage(mammoth, goblin)

        self.game.deal_combat_damage()

        self.assertEqual(self.bob.life, 20)
        self.assertEqual((mammoth.damage, goblin.damage), (0, 0))
        self.assertIn(goblin, self.bob.battlefield)

    def test_captures_first_strike_and_regular_damage_waves(self) -> None:
        archer = self.permanent(self.alice, ELVISH_ARCHERS)
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.cast_fog()
        self.reach_damage(archer, bear)

        self.game.deal_combat_damage()

        self.assertIn(archer, self.alice.battlefield)
        self.assertIn(bear, self.bob.battlefield)
        self.assertEqual((archer.damage, bear.damage), (0, 0))

    def test_does_not_prevent_basilisk_blocking_destruction(self) -> None:
        basilisk = self.permanent(self.alice, THICKET_BASILISK)
        giant = self.permanent(self.bob, HILL_GIANT)
        self.cast_fog()
        self.reach_damage(basilisk, giant)

        self.game.deal_combat_damage()

        self.assertIn(giant, self.bob.graveyard)
        self.assertIn(basilisk, self.alice.battlefield)
        self.assertEqual(basilisk.damage, 0)

    def test_noncombat_damage_during_attack_is_not_prevented(self) -> None:
        attacker = self.permanent(self.alice, GRIZZLY_BEARS)
        self.cast_fog()
        self.game.begin_combat()
        self.game.declare_attackers([attacker])

        self.game._deal_damage(self.bob, 3, "noncombat effect")

        self.assertEqual(self.bob.life, 17)

    def test_can_be_cast_during_the_last_pre_damage_response_window(self) -> None:
        attacker = self.permanent(self.alice, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        self.game.declare_blockers({})
        self.assertEqual(self.game.combat.step, CombatStep.BLOCKER_RESPONSE)

        self.cast_fog()
        self.game.advance_combat()
        self.game.deal_combat_damage()

        self.assertEqual(self.bob.life, 20)

    def test_cannot_be_cast_after_combat_damage(self) -> None:
        attacker = self.permanent(self.alice, GRIZZLY_BEARS)
        self.reach_damage(attacker)
        self.game.deal_combat_damage()
        fog = Card(FOG, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(fog)
        self.alice.mana_pool.green = 1

        with self.assertRaisesRegex(RuntimeError, "after.*combat damage"):
            self.game.begin_cast(fog)


if __name__ == "__main__":
    unittest.main()
