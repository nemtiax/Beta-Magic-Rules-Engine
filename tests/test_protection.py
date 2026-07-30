import unittest

from beta_magic import (
    BLACK_KNIGHT,
    BLACK_WARD,
    BLUE_WARD,
    GREEN_WARD,
    PROTECTION_CREATURES,
    RED_WARD,
    WHITE_KNIGHT,
    WHITE_WARD,
    CardType,
    Color,
    ContinuousEffect,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.cards import CardDefinition, EffectScope
from beta_magic.card_defs import WEAKNESS
from beta_magic.card_defs import GRIZZLY_BEARS


def player(player_id: str) -> PlayerState:
    return PlayerState.with_deck(
        player_id, player_id.title(), [GRIZZLY_BEARS] * 16
    )


class ProtectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = player("alice")
        self.bob = player("bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(owner: PlayerState, definition):
        card = owner.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        owner.battlefield.append(card)
        return card

    @staticmethod
    def put_in_hand(owner: PlayerState, definition):
        card = owner.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        owner.hand.append(card)
        return card

    def test_knight_definitions(self) -> None:
        self.assertEqual(PROTECTION_CREATURES, (WHITE_KNIGHT, BLACK_KNIGHT))
        self.assertEqual(WHITE_KNIGHT.mana_cost.compact, "WW")
        self.assertEqual(BLACK_KNIGHT.mana_cost.compact, "BB")
        self.assertEqual((WHITE_KNIGHT.power, WHITE_KNIGHT.toughness), (2, 2))
        self.assertIn(KeywordAbility.FIRST_STRIKE, WHITE_KNIGHT.abilities)
        self.assertIn(
            KeywordAbility.PROTECTION_FROM_BLACK, WHITE_KNIGHT.abilities
        )
        self.assertIn(
            KeywordAbility.PROTECTION_FROM_WHITE, BLACK_KNIGHT.abilities
        )

    def test_ward_definitions(self) -> None:
        expected = (
            (BLACK_WARD, KeywordAbility.PROTECTION_FROM_BLACK),
            (BLUE_WARD, KeywordAbility.PROTECTION_FROM_BLUE),
            (GREEN_WARD, KeywordAbility.PROTECTION_FROM_GREEN),
            (RED_WARD, KeywordAbility.PROTECTION_FROM_RED),
            (WHITE_WARD, KeywordAbility.PROTECTION_FROM_WHITE),
        )
        for ward, ability in expected:
            self.assertEqual(ward.mana_cost.compact, "W")
            self.assertEqual(ward.colors, frozenset({Color.WHITE}))
            self.assertIn(
                ability, ward.continuous_effects[0].granted_abilities
            )

    def test_ward_stays_attached_and_prevents_later_colored_aura(self) -> None:
        bear = self.put_in_play(self.alice, GRIZZLY_BEARS)
        ward = self.put_in_hand(self.alice, BLACK_WARD)
        self.alice.mana_pool.white = 1
        self.game.cast_enchantment(ward, bear)

        self.assertIn(ward, self.alice.battlefield)
        self.assertEqual(ward.enchanted_card_id, bear.id)
        self.assertIn(
            KeywordAbility.PROTECTION_FROM_BLACK,
            self.game.creature_abilities(bear),
        )

        weakness = self.put_in_hand(self.alice, WEAKNESS)
        self.alice.mana_pool.black = 1
        with self.assertRaisesRegex(RuntimeError, "no legal targets"):
            self.game.begin_cast(weakness)

    def test_protection_prevents_colored_targeting(self) -> None:
        knight = self.put_in_play(self.bob, WHITE_KNIGHT)
        weakness = self.put_in_hand(self.alice, WEAKNESS)
        self.alice.mana_pool.black = 1

        with self.assertRaisesRegex(RuntimeError, "no legal targets"):
            self.game.begin_cast(weakness)

        self.assertIn(knight, self.bob.battlefield)
        self.assertIn(weakness, self.alice.hand)

    def test_protection_prevents_damage_from_that_color(self) -> None:
        white_knight = self.put_in_play(self.alice, WHITE_KNIGHT)
        black_knight = self.put_in_play(self.bob, BLACK_KNIGHT)

        self.game._deal_damage(
            white_knight,
            2,
            black_knight.name,
            source_card=black_knight,
        )

        self.assertEqual(white_knight.damage, 0)
        incident = self.game.resolved_damage_incidents[-1]
        self.assertEqual(incident.packets[0].prevented, 2)

    def test_protected_attacker_cannot_be_blocked_by_that_color(self) -> None:
        attacker = self.put_in_play(self.alice, WHITE_KNIGHT)
        blocker = self.put_in_play(self.bob, BLACK_KNIGHT)
        self.game.begin_combat()
        self.game.declare_attackers([attacker])

        with self.assertRaisesRegex(ValueError, "protection"):
            self.game.declare_blockers({blocker: attacker})

    def test_existing_aura_remains_when_protection_is_gained(self) -> None:
        bear = self.put_in_play(self.alice, GRIZZLY_BEARS)
        weakness = self.put_in_hand(self.alice, WEAKNESS)
        self.alice.mana_pool.black = 1
        self.game.cast_enchantment(weakness, bear)

        self.game.temporary_creature_effects.setdefault(bear.id, []).append(
            ContinuousEffect(
                scope=EffectScope.ALL_CREATURES,
                granted_abilities=frozenset(
                    {KeywordAbility.PROTECTION_FROM_BLACK}
                ),
            )
        )

        self.assertIn(weakness, self.alice.battlefield)
        self.assertEqual(weakness.enchanted_card_id, bear.id)
        self.assertEqual(
            (self.game.creature_power(bear), self.game.creature_toughness(bear)),
            (0, 1),
        )

    def test_protection_does_not_stop_untargeted_effects(self) -> None:
        effect_source = CardDefinition(
            name="Black General Effect",
            card_types=frozenset({CardType.ENCHANTMENT}),
            colors=frozenset({Color.BLACK}),
            continuous_effects=(ContinuousEffect(power=-1),),
        )
        knight = self.put_in_play(self.alice, WHITE_KNIGHT)
        self.put_in_play(self.bob, effect_source)

        self.assertEqual(self.game.creature_power(knight), 1)

    def test_protection_is_inactive_outside_battlefield(self) -> None:
        knight = self.put_in_hand(self.bob, WHITE_KNIGHT)
        self.assertFalse(
            self.game._is_protected_from(knight, frozenset({Color.BLACK}))
        )


if __name__ == "__main__":
    unittest.main()
