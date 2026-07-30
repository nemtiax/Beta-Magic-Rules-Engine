import unittest

from beta_magic import (
    BLACK_KNIGHT,
    CIRCLE_OF_PROTECTION_BLACK,
    CIRCLE_OF_PROTECTION_BLUE,
    CIRCLE_OF_PROTECTION_GREEN,
    CIRCLE_OF_PROTECTION_RED,
    CIRCLE_OF_PROTECTION_WHITE,
    CIRCLES_OF_PROTECTION,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.damage import DamageIncidentKind, DamageResolutionStep
from beta_magic.card_defs import PHANTOM_MONSTER
from beta_magic.card_defs import GRIZZLY_BEARS


def player(player_id: str) -> PlayerState:
    return PlayerState.with_deck(
        player_id, player_id.title(), [GRIZZLY_BEARS] * 12
    )


class CircleOfProtectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = player("alice")
        self.bob = player("bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.game.pause_for_damage_windows = True

    @staticmethod
    def put_in_play(owner: PlayerState, definition):
        card = owner.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.entered_battlefield_turn = 0
        owner.battlefield.append(card)
        return card

    def open_damage(self, assignments) -> None:
        self.game._begin_damage_incident(DamageIncidentKind.FAST_EFFECT_BATCH)
        for recipient, amount, source in assignments:
            self.game._deal_damage(
                recipient, amount, source.name, source_card=source
            )
        self.game._resolve_damage_incident()
        self.assertEqual(
            self.game.pending_damage.step, DamageResolutionStep.PREVENTION
        )

    def finish_incident(self) -> None:
        while self.game.pending_damage is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_all_five_beta_circles_are_defined(self) -> None:
        self.assertEqual(
            CIRCLES_OF_PROTECTION,
            (
                CIRCLE_OF_PROTECTION_BLACK,
                CIRCLE_OF_PROTECTION_BLUE,
                CIRCLE_OF_PROTECTION_GREEN,
                CIRCLE_OF_PROTECTION_RED,
                CIRCLE_OF_PROTECTION_WHITE,
            ),
        )
        for circle in CIRCLES_OF_PROTECTION:
            self.assertEqual(circle.mana_cost.compact, "1W")
            ability = circle.activated_abilities[0]
            self.assertEqual(ability.mana_cost.compact, "1")
            self.assertFalse(ability.tap_cost)
            self.assertTrue(ability.controller_only)

    def test_circle_prevents_all_matching_damage_to_controller_only(self) -> None:
        circle = self.put_in_play(self.alice, CIRCLE_OF_PROTECTION_BLACK)
        black_source = self.put_in_play(self.bob, BLACK_KNIGHT)
        creature = self.put_in_play(self.alice, GRIZZLY_BEARS)
        self.alice.mana_pool.colorless = 1
        self.open_damage(
            (
                (self.alice, 4, black_source),
                (creature, 2, black_source),
            )
        )

        self.game.activate_ability(self.alice.id, circle, 0)
        choices = self.game.legal_prevention_packets()
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0].recipient_id, self.alice.id)
        self.assertEqual(self.game.prevent_damage(self.alice.id, choices[0].id), 4)
        self.assertFalse(circle.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.finish_incident()

        self.assertEqual(self.alice.life, 20)
        self.assertIn(creature, self.alice.graveyard)

    def test_circle_cannot_choose_wrong_colored_source(self) -> None:
        circle = self.put_in_play(self.alice, CIRCLE_OF_PROTECTION_BLACK)
        blue_source = self.put_in_play(self.bob, PHANTOM_MONSTER)
        self.alice.mana_pool.colorless = 1
        self.open_damage(((self.alice, 3, blue_source),))

        self.game.activate_ability(self.alice.id, circle, 0)

        self.assertEqual(self.game.legal_prevention_packets(), [])
        with self.assertRaisesRegex(ValueError, "source's color"):
            self.game.prevent_damage(
                self.alice.id, self.game.pending_damage.packets[0].id
            )


if __name__ == "__main__":
    unittest.main()
