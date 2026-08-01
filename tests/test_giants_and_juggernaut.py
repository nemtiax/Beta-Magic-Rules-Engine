import unittest

from beta_magic import (
    JUGGERNAUT,
    STONE_GIANT,
    TWO_HEADED_GIANT_OF_FORIYS,
    Card,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS, WALL_OF_WOOD


class GiantsAndJuggernautTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "a", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck(
            "b", "Bob", [GRIZZLY_BEARS] * 20
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        player.battlefield.append(card)
        return card

    def resolve_batch(self) -> None:
        while self.game.batch_abilities or self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_stone_giant_targets_only_owned_creatures_below_its_power(self):
        giant = self.permanent(self.alice, STONE_GIANT)
        bear = self.permanent(self.alice, GRIZZLY_BEARS)
        other_bear = self.permanent(self.bob, GRIZZLY_BEARS)
        too_tough = self.permanent(self.alice, WALL_OF_WOOD)

        self.game.activate_ability(self.alice.id, giant, 0)

        self.assertEqual(self.game.legal_targets_for(), [bear])
        self.assertNotIn(other_bear, self.game.legal_targets_for())
        self.assertNotIn(too_tough, self.game.legal_targets_for())

    def test_stone_giant_grants_flying_then_destroys_target_at_end_of_turn(self):
        giant = self.permanent(self.alice, STONE_GIANT)
        bear = self.permanent(self.alice, GRIZZLY_BEARS)
        self.game.activate_ability(self.alice.id, giant, 0)
        self.game.complete_pending_activation((bear,))
        self.resolve_batch()

        self.assertTrue(giant.tapped)
        self.assertIn(KeywordAbility.FLYING, self.game.creature_abilities(bear))
        self.assertIn(bear.id, self.game.destroy_at_end_of_turn)

        while self.game.current_phase is not TurnPhase.END:
            self.game.advance_phase()
        self.game.next_turn()
        self.assertEqual(bear.zone, Zone.GRAVEYARD)

    def test_two_headed_giant_blocks_two_and_divides_its_damage(self):
        attacker_one = self.permanent(self.alice, GRIZZLY_BEARS)
        attacker_two = self.permanent(self.alice, GRIZZLY_BEARS)
        giant = self.permanent(self.bob, TWO_HEADED_GIANT_OF_FORIYS)

        self.game.begin_combat()
        self.game.declare_attackers((attacker_one, attacker_two))
        self.game.declare_blockers({giant: (attacker_one, attacker_two)})
        self.game.advance_combat()
        self.game.deal_combat_damage(
            {giant: {attacker_one: 2, attacker_two: 2}}
        )

        self.assertEqual(attacker_one.zone, Zone.GRAVEYARD)
        self.assertEqual(attacker_two.zone, Zone.GRAVEYARD)
        self.assertEqual(giant.zone, Zone.GRAVEYARD)

    def test_normal_creature_cannot_block_two_attackers(self):
        attacker_one = self.permanent(self.alice, GRIZZLY_BEARS)
        attacker_two = self.permanent(self.alice, GRIZZLY_BEARS)
        blocker = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game.begin_combat()
        self.game.declare_attackers((attacker_one, attacker_two))

        with self.assertRaisesRegex(ValueError, "cannot block 2 attackers"):
            self.game.declare_blockers(
                {blocker: (attacker_one, attacker_two)}
            )

    def test_juggernaut_must_attack_if_able(self):
        juggernaut = self.permanent(self.alice, JUGGERNAUT)
        self.game.begin_combat()
        with self.assertRaisesRegex(ValueError, "must attack if possible"):
            self.game.declare_attackers(())
        self.game.declare_attackers((juggernaut,))

    def test_tapped_juggernaut_is_not_required_to_attack(self):
        juggernaut = self.permanent(self.alice, JUGGERNAUT)
        juggernaut.tapped = True
        self.game.begin_combat()
        self.game.declare_attackers(())

    def test_juggernaut_cannot_be_blocked_by_a_wall(self):
        juggernaut = self.permanent(self.alice, JUGGERNAUT)
        wall = self.permanent(self.bob, WALL_OF_WOOD)
        self.game.begin_combat()
        self.game.declare_attackers((juggernaut,))

        with self.assertRaisesRegex(ValueError, "cannot be blocked"):
            self.game.declare_blockers({wall: juggernaut})


if __name__ == "__main__":
    unittest.main()
