import unittest

from beta_magic import (
    ABILITY_ENCHANT_CREATURES,
    ASPECT_OF_WOLF,
    BLACK_WARD,
    BLUE_WARD,
    CONTROL_MAGIC,
    ENCHANT_CREATURES,
    FLIGHT,
    FEAR,
    BURROWING,
    HOLY_STRENGTH,
    LANCE,
    PUMP_ENCHANT_CREATURES,
    PROTECTION_ENCHANT_CREATURES,
    GREEN_WARD,
    RED_WARD,
    REGENERATION,
    SIMPLE_ENCHANT_CREATURES,
    UNHOLY_STRENGTH,
    WEAKNESS,
    WEB,
    WHITE_WARD,
    CardType,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import PLAINS
from beta_magic.card_defs import CRUSADE
from beta_magic.card_defs import GRIZZLY_BEARS, SAVANNAH_LIONS


def player(player_id: str) -> PlayerState:
    return PlayerState.with_deck(
        player_id, player_id.title(), [GRIZZLY_BEARS] * 16
    )


class EnchantCreatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = player("alice")
        self.bob = player("bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(owner: PlayerState, definition=GRIZZLY_BEARS):
        card = owner.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        owner.battlefield.append(card)
        return card

    def put_in_hand(self, owner: PlayerState, definition):
        card = owner.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        owner.hand.append(card)
        return card

    def test_card_definitions(self) -> None:
        self.assertEqual(
            SIMPLE_ENCHANT_CREATURES,
            (HOLY_STRENGTH, UNHOLY_STRENGTH, WEAKNESS, ASPECT_OF_WOLF),
        )
        self.assertEqual(HOLY_STRENGTH.mana_cost.compact, "W")
        self.assertEqual(UNHOLY_STRENGTH.mana_cost.compact, "B")
        self.assertEqual(WEAKNESS.mana_cost.compact, "B")
        self.assertEqual(
            ABILITY_ENCHANT_CREATURES,
            (LANCE, FLIGHT, BURROWING, FEAR, REGENERATION, WEB),
        )
        self.assertEqual(
            ENCHANT_CREATURES,
            (
                SIMPLE_ENCHANT_CREATURES
                + ABILITY_ENCHANT_CREATURES
                + PUMP_ENCHANT_CREATURES
                + PROTECTION_ENCHANT_CREATURES
                + (CONTROL_MAGIC,)
            ),
        )
        self.assertEqual(
            PROTECTION_ENCHANT_CREATURES,
            (BLACK_WARD, BLUE_WARD, GREEN_WARD, RED_WARD, WHITE_WARD),
        )
        self.assertEqual(LANCE.mana_cost.compact, "W")
        self.assertEqual(FLIGHT.mana_cost.compact, "U")
        self.assertEqual(BURROWING.mana_cost.compact, "R")
        self.assertTrue(
            all(
                CardType.ENCHANTMENT in definition.card_types
                and definition.continuous_effects
                for definition in SIMPLE_ENCHANT_CREATURES
            )
        )

    def test_holy_strength_targets_and_buffs_either_players_creature(self) -> None:
        bear = self.put_in_play(self.bob)
        aura = self.put_in_hand(self.alice, HOLY_STRENGTH)
        self.alice.mana_pool.white = 1

        self.game.cast_enchantment(aura, bear)

        self.assertIn(aura, self.alice.battlefield)
        self.assertEqual(aura.enchanted_card_id, bear.id)
        self.assertEqual(
            (self.game.creature_power(bear), self.game.creature_toughness(bear)),
            (3, 4),
        )
        self.assertEqual(self.alice.mana_pool.total, 0)

    def test_unholy_strength_bonuses_and_multiple_auras_stack(self) -> None:
        bear = self.put_in_play(self.alice)
        holy = self.put_in_hand(self.alice, HOLY_STRENGTH)
        unholy = self.put_in_hand(self.alice, UNHOLY_STRENGTH)
        self.alice.mana_pool.white = 1
        self.alice.mana_pool.black = 1

        self.game.cast_enchantment(holy, bear)
        self.game.cast_enchantment(unholy, bear)

        self.assertEqual(
            (self.game.creature_power(bear), self.game.creature_toughness(bear)),
            (5, 5),
        )

    def test_invalid_target_does_not_spend_mana_or_move_spell(self) -> None:
        land = self.put_in_play(self.alice, PLAINS)
        aura = self.put_in_hand(self.alice, HOLY_STRENGTH)
        self.alice.mana_pool.white = 1

        with self.assertRaisesRegex(ValueError, "must target a creature"):
            self.game.cast_enchantment(aura, land)

        self.assertIn(aura, self.alice.hand)
        self.assertEqual(self.alice.mana_pool.white, 1)

    def test_aura_goes_to_owners_graveyard_with_enchanted_creature(self) -> None:
        bear = self.put_in_play(self.bob)
        aura = self.put_in_hand(self.alice, HOLY_STRENGTH)
        self.alice.mana_pool.white = 1
        self.game.cast_enchantment(aura, bear)

        self.game.put_permanent_in_graveyard(bear)

        self.assertIn(bear, self.bob.graveyard)
        self.assertIn(aura, self.alice.graveyard)
        self.assertIsNone(aura.enchanted_card_id)

    def test_weakness_immediately_kills_a_one_toughness_creature(self) -> None:
        lion = self.put_in_play(self.bob, SAVANNAH_LIONS)
        weakness = self.put_in_hand(self.alice, WEAKNESS)
        self.alice.mana_pool.black = 1

        self.game.cast_enchantment(weakness, lion)

        self.assertIn(lion, self.bob.graveyard)
        self.assertIn(weakness, self.alice.graveyard)

    def test_engine_owns_pending_cast_and_blocks_other_actions(self) -> None:
        bear = self.put_in_play(self.bob)
        aura = self.put_in_hand(self.alice, HOLY_STRENGTH)
        land = self.put_in_play(self.alice, PLAINS)
        self.alice.mana_pool.white = 1

        pending = self.game.begin_cast(aura)

        self.assertIsNotNone(pending)
        self.assertIs(self.game.pending_cast.spell, aura)
        self.assertEqual(self.game.legal_targets_for(), [bear])
        self.assertIn(aura, self.alice.hand)
        self.assertEqual(self.alice.mana_pool.white, 1)
        with self.assertRaisesRegex(RuntimeError, "choose targets"):
            self.game.tap_land_for_mana(self.alice.id, land)
        with self.assertRaisesRegex(RuntimeError, "choose targets"):
            self.game.begin_combat()
        with self.assertRaisesRegex(RuntimeError, "choose targets"):
            self.game.advance_phase()

        self.game.complete_pending_cast((bear,))
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.assertIsNone(self.game.pending_cast)
        self.assertEqual(aura.enchanted_card_id, bear.id)

    def test_pending_cast_can_be_cancelled_without_spending_mana(self) -> None:
        self.put_in_play(self.alice)
        aura = self.put_in_hand(self.alice, HOLY_STRENGTH)
        self.alice.mana_pool.white = 1
        self.game.begin_cast(aura)

        self.game.cancel_pending_cast()

        self.assertIsNone(self.game.pending_cast)
        self.assertIn(aura, self.alice.hand)
        self.assertEqual(self.alice.mana_pool.white, 1)

    def test_central_zone_move_discards_attachments_when_creature_leaves(self) -> None:
        bear = self.put_in_play(self.bob)
        aura = self.put_in_hand(self.alice, HOLY_STRENGTH)
        self.alice.mana_pool.white = 1
        self.game.cast_enchantment(aura, bear)

        self.game.move_card(bear, Zone.EXILE)

        self.assertIn(bear, self.bob.exile)
        self.assertIn(aura, self.alice.graveyard)
        self.assertIsNone(aura.enchanted_card_id)

    def test_flight_grants_flying_and_changes_blocking_legality(self) -> None:
        attacker = self.put_in_play(self.alice)
        blocker = self.put_in_play(self.bob)
        enchantment = self.put_in_hand(self.alice, FLIGHT)
        self.alice.mana_pool.blue = 1
        self.game.cast_enchantment(enchantment, attacker)

        self.assertIn(
            KeywordAbility.FLYING, self.game.creature_abilities(attacker)
        )
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        with self.assertRaisesRegex(ValueError, "Flying"):
            self.game.declare_blockers({blocker: attacker})

    def test_lance_grants_first_strike_during_combat(self) -> None:
        attacker = self.put_in_play(self.alice)
        blocker = self.put_in_play(self.bob, SAVANNAH_LIONS)
        enchantment = self.put_in_hand(self.alice, LANCE)
        self.alice.mana_pool.white = 1
        self.game.cast_enchantment(enchantment, attacker)

        self.assertIn(
            KeywordAbility.FIRST_STRIKE,
            self.game.creature_abilities(attacker),
        )
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        self.game.declare_blockers({blocker: attacker})
        self.game.advance_combat()
        self.game.deal_combat_damage()

        self.assertIn(attacker, self.alice.battlefield)
        self.assertEqual(attacker.damage, 0)
        self.assertIn(blocker, self.bob.graveyard)

    def test_losing_crusade_causes_zero_toughness_creature_to_die(self) -> None:
        crusade = self.put_in_play(self.alice, CRUSADE)
        lion = self.put_in_play(self.alice, SAVANNAH_LIONS)
        weakness = self.put_in_hand(self.alice, WEAKNESS)
        self.alice.mana_pool.black = 1
        self.game.cast_enchantment(weakness, lion)
        self.assertEqual(
            (self.game.creature_power(lion), self.game.creature_toughness(lion)),
            (1, 1),
        )

        self.game.put_permanent_in_graveyard(crusade)

        self.assertIn(crusade, self.alice.graveyard)
        self.assertIn(lion, self.alice.graveyard)
        self.assertIn(weakness, self.alice.graveyard)


if __name__ == "__main__":
    unittest.main()
