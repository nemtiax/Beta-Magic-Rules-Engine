import unittest

from beta_magic import (
    DWARVEN_WARRIORS,
    FEAR,
    TERROR,
    Card,
    ContinuousEffect,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import (
    GRIZZLY_BEARS,
    HILL_GIANT,
    LIVING_WALL,
    SCATHE_ZOMBIES,
)


class FearTerrorDwarvenWarriorsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player, definition, zone):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=zone,
            entered_battlefield_turn=0,
        )
        player.cards_in(zone).append(card)
        return card

    def resolve_all(self):
        while self.game.priority_player_index is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_fear_allows_black_and_artifact_creatures_only(self):
        for legal_definition in (SCATHE_ZOMBIES, LIVING_WALL):
            with self.subTest(blocker=legal_definition.name):
                game = GameState(
                    [
                        PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 8),
                        PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 8),
                    ]
                )
                game.start(opening_hand_size=0, shuffle=False)
                while game.current_phase is not TurnPhase.MAIN:
                    game.advance_phase()
                attacker = self.card(game.players[0], GRIZZLY_BEARS, Zone.BATTLEFIELD)
                aura = self.card(game.players[0], FEAR, Zone.BATTLEFIELD)
                aura.enchanted_card_id = attacker.id
                blocker = self.card(
                    game.players[1], legal_definition, Zone.BATTLEFIELD
                )
                game.begin_combat()
                game.declare_attackers([attacker])
                game.declare_blockers({blocker: attacker})

        attacker = self.card(self.alice, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        aura = self.card(self.alice, FEAR, Zone.BATTLEFIELD)
        aura.enchanted_card_id = attacker.id
        blocker = self.card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        with self.assertRaisesRegex(ValueError, "cannot block"):
            self.game.declare_blockers({blocker: attacker})

    def test_terror_excludes_black_and_artifact_creatures(self):
        bear = self.card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        black = self.card(self.bob, SCATHE_ZOMBIES, Zone.BATTLEFIELD)
        artifact = self.card(self.bob, LIVING_WALL, Zone.BATTLEFIELD)
        spell = self.card(self.alice, TERROR, Zone.HAND)

        self.assertEqual(self.game.legal_targets_for(spell), [bear])

    def test_terror_destroys_without_regeneration(self):
        bear = self.card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        spell = self.card(self.alice, TERROR, Zone.HAND)
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 1

        self.game.begin_cast(spell)
        self.game.complete_pending_cast((bear,))
        self.resolve_all()

        self.assertIn(bear, self.bob.graveyard)
        self.assertFalse(
            self.game.resolved_destruction_incidents[-1]
            .targets[0]
            .regeneration_allowed
        )

    def test_dwarven_warriors_checks_power_on_activation_then_locks_effect(self):
        warriors = self.card(self.alice, DWARVEN_WARRIORS, Zone.BATTLEFIELD)
        small = self.card(self.alice, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        large = self.card(self.alice, HILL_GIANT, Zone.BATTLEFIELD)

        self.game.activate_ability(self.alice.id, warriors, 0)
        self.assertIn(small, self.game.legal_targets_for())
        self.assertIn(warriors, self.game.legal_targets_for())
        self.assertNotIn(large, self.game.legal_targets_for())
        self.game.complete_pending_activation((small,))
        self.resolve_all()
        self.game.temporary_creature_effects.setdefault(small.id, []).append(
            ContinuousEffect(power=3)
        )

        blocker = self.card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.game.begin_combat()
        self.game.declare_attackers([small])
        with self.assertRaisesRegex(ValueError, "cannot be blocked"):
            self.game.declare_blockers({blocker: small})


if __name__ == "__main__":
    unittest.main()
