import unittest

from beta_magic import (
    BIRDS_OF_PARADISE,
    BLACK_LOTUS,
    BLUE_ELEMENTAL_BLAST,
    CONVERSION,
    COUNTERSPELL,
    DARK_RITUAL,
    DISENCHANT,
    GIANT_GROWTH,
    IRON_STAR,
    LLANOWAR_ELVES,
    LIVING_WALL,
    LIGHTNING_BOLT,
    MAGICAL_HACK,
    MOX_SAPPHIRE,
    RED_ELEMENTAL_BLAST,
    SOL_RING,
    SPELL_BLAST,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    WATER_ELEMENTAL,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS
from beta_magic.damage import DamageResolutionStep


class InterruptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [GRIZZLY_BEARS] * 12)
        self.bob = PlayerState.with_deck("b", "Bob", [GRIZZLY_BEARS] * 12)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_hand(player, definition):
        card = Card(definition, owner_id=player.id, zone=Zone.HAND)
        player.hand.append(card)
        return card

    @staticmethod
    def put_in_play(player, definition):
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

    def cast_bolt(self):
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.bob,))
        return bolt

    def resolve_batch(self):
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def open_damage_window(self):
        """Resolve a Bolt far enough to open its prevention window."""

        target = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.game.pause_for_damage_windows = True
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((target,))
        self.resolve_batch()
        self.assertIsNotNone(self.game.pending_damage)
        self.assertIs(
            self.game.pending_damage.step,
            DamageResolutionStep.PREVENTION,
        )
        return target

    def test_definitions_are_interrupts(self):
        self.assertEqual(COUNTERSPELL.mana_cost.compact, "UU")
        self.assertEqual(SPELL_BLAST.mana_cost.compact, "XU")
        self.assertIn(CardType.INTERRUPT, COUNTERSPELL.card_types)
        self.assertIn(CardType.INTERRUPT, SPELL_BLAST.card_types)

    def test_counterspell_resolves_before_and_counters_target(self):
        bolt = self.cast_bolt()
        counter = self.put_in_hand(self.bob, COUNTERSPELL)
        self.bob.mana_pool.blue = 2

        pending = self.game.begin_cast(counter)
        self.assertEqual(self.game.legal_targets_for(), [bolt])
        self.game.complete_pending_cast((bolt,))
        self.assertEqual(self.game.stack, [bolt, counter])

        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)

        self.assertEqual(bolt.zone, Zone.GRAVEYARD)
        self.assertEqual(counter.zone, Zone.GRAVEYARD)
        self.assertEqual(self.game.stack, [])
        self.assertEqual(self.bob.life, 20)

    def test_an_interrupt_can_counter_an_interrupt(self):
        bolt = self.cast_bolt()
        first = self.put_in_hand(self.bob, COUNTERSPELL)
        second = self.put_in_hand(self.alice, COUNTERSPELL)
        self.bob.mana_pool.blue = 2
        self.alice.mana_pool.blue = 2

        self.game.begin_cast(first)
        self.game.complete_pending_cast((bolt,))
        self.game.begin_cast(second)
        self.assertEqual(self.game.legal_targets_for(), [bolt, first])
        self.game.complete_pending_cast((first,))

        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        self.assertEqual(first.zone, Zone.GRAVEYARD)
        self.assertEqual(bolt.zone, Zone.STACK)

        self.resolve_batch()
        self.assertEqual(self.bob.life, 17)

    def test_spell_blast_x_must_equal_declared_target_cost(self):
        bolt = self.cast_bolt()
        blast = self.put_in_hand(self.bob, SPELL_BLAST)
        self.bob.mana_pool.blue = 1
        self.bob.mana_pool.colorless = 2

        self.game.begin_cast(blast, x_value=2)
        self.assertEqual(self.game.legal_targets_for(), [])
        with self.assertRaisesRegex(ValueError, "illegal target"):
            self.game.complete_pending_cast((bolt,))
        self.game.cancel_pending_cast()

        self.game.begin_cast(blast, x_value=1)
        self.assertEqual(self.game.legal_targets_for(), [bolt])
        self.game.complete_pending_cast((bolt,))

    def test_interrupt_cannot_be_cast_without_current_spell(self):
        counter = self.put_in_hand(self.alice, COUNTERSPELL)
        self.alice.mana_pool.blue = 2
        with self.assertRaisesRegex(RuntimeError, "immediately"):
            self.game.begin_cast(counter)

    def test_spell_has_interrupt_window_before_ordinary_responses(self):
        target = self.put_in_play(self.bob, GRIZZLY_BEARS)
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        growth = self.put_in_hand(self.bob, GIANT_GROWTH)
        star = self.put_in_play(self.bob, IRON_STAR)
        self.alice.mana_pool.red = 1
        self.bob.mana_pool.green = 1
        self.bob.mana_pool.colorless = 1

        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((target,))
        self.assertEqual(self.game.interruptible_spell_id, bolt.id)

        with self.assertRaisesRegex(RuntimeError, "interrupt window"):
            self.game.begin_cast(growth)
        with self.assertRaisesRegex(RuntimeError, "interrupt sequence"):
            self.game.activate_ability(self.bob.id, star, 0)

        self.game.pass_priority(self.bob.id)
        self.assertIs(
            self.game.players[self.game.priority_player_index], self.alice
        )
        self.game.pass_priority(self.alice.id)

        self.assertIsNone(self.game.interruptible_spell_id)
        self.assertIs(
            self.game.players[self.game.priority_player_index], self.bob
        )
        self.game.begin_cast(growth)
        self.game.complete_pending_cast((target,))
        self.assertEqual(self.game.interruptible_spell_id, growth.id)

    def test_later_spell_closes_the_earlier_interrupt_window(self):
        target = self.put_in_play(self.bob, GRIZZLY_BEARS)
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        growth = self.put_in_hand(self.bob, GIANT_GROWTH)
        counter = self.put_in_hand(self.alice, COUNTERSPELL)
        blast = self.put_in_hand(self.bob, BLUE_ELEMENTAL_BLAST)
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.blue = 2
        self.bob.mana_pool.green = 1
        self.bob.mana_pool.blue = 1

        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((target,))
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

        self.game.begin_cast(growth)
        self.game.complete_pending_cast((target,))
        self.game.begin_cast(counter)
        self.assertEqual(self.game.legal_targets_for(), [growth])
        self.game.complete_pending_cast((growth,))

        self.assertNotIn(
            bolt,
            self.game.legal_targets_for(blast, mode="Counter spell"),
        )
        with self.assertRaisesRegex(RuntimeError, "no legal targets"):
            self.game.begin_cast(blast, mode="Counter spell")

    def test_interrupt_speed_mana_abilities_invalidate_prior_passes(self):
        sources = (
            (LLANOWAR_ELVES, 0),
            (BIRDS_OF_PARADISE, 1),
            (MOX_SAPPHIRE, 0),
            (SOL_RING, 0),
            (BLACK_LOTUS, 0),
        )
        for definition, ability_index in sources:
            with self.subTest(definition.name):
                self.setUp()
                source = self.put_in_play(self.alice, definition)
                bolt = self.cast_bolt()

                # Bob's pass cannot remain counted after Alice takes the
                # interrupt-speed action of producing mana.
                self.game.pass_priority(self.bob.id)
                self.assertEqual(self.game.consecutive_passes, 1)
                self.game.activate_ability(
                    self.alice.id, source, ability_index
                )

                self.assertEqual(self.game.consecutive_passes, 0)
                self.assertIs(
                    self.game.players[self.game.priority_player_index],
                    self.alice,
                )
                self.assertEqual(self.game.interruptible_spell_id, bolt.id)

                self.game.pass_priority(self.alice.id)
                self.assertEqual(bolt.zone, Zone.STACK)
                self.resolve_batch()
                self.assertEqual(self.bob.life, 17)

    def test_mana_ability_preserves_an_interrupt_chain(self):
        bolt = self.cast_bolt()
        counter = self.put_in_hand(self.bob, COUNTERSPELL)
        mox = self.put_in_play(self.bob, MOX_SAPPHIRE)
        self.bob.mana_pool.blue = 2
        self.game.begin_cast(counter)
        self.game.complete_pending_cast((bolt,))

        self.game.pass_priority(self.alice.id)
        self.game.activate_ability(self.bob.id, mox, 0)

        self.assertEqual(self.game.consecutive_passes, 0)
        self.assertEqual(self.game.interruptible_spell_id, bolt.id)
        self.assertEqual(self.game.stack, [bolt, counter])
        self.game.pass_priority(self.bob.id)
        self.assertEqual(counter.zone, Zone.STACK)
        self.game.pass_priority(self.alice.id)
        self.assertEqual(counter.zone, Zone.GRAVEYARD)
        self.assertEqual(bolt.zone, Zone.GRAVEYARD)

    def test_dark_ritual_resolves_inside_each_damage_window(self):
        for passes_to_step, expected_step in enumerate(
            (
                DamageResolutionStep.PREVENTION,
                DamageResolutionStep.REDIRECTION,
                DamageResolutionStep.REGENERATION,
            )
        ):
            with self.subTest(step=expected_step):
                self.setUp()
                self.open_damage_window()
                for _ in range(passes_to_step):
                    self.game.pass_priority(self.alice.id)
                    self.game.pass_priority(self.bob.id)
                self.assertIs(self.game.pending_damage.step, expected_step)

                ritual = self.put_in_hand(self.alice, DARK_RITUAL)
                self.alice.mana_pool.black = 1
                self.game.begin_cast(ritual)
                self.game.pass_priority(self.bob.id)
                self.game.pass_priority(self.alice.id)

                self.assertEqual(self.alice.mana_pool.black, 3)
                self.assertIs(ritual.zone, Zone.GRAVEYARD)
                self.assertIsNotNone(self.game.pending_damage)
                self.assertIs(self.game.pending_damage.step, expected_step)
                self.assertIs(
                    self.game.players[self.game.priority_player_index],
                    self.alice,
                )

    def test_interrupt_can_be_countered_inside_damage_window(self):
        self.open_damage_window()
        ritual = self.put_in_hand(self.alice, DARK_RITUAL)
        counter = self.put_in_hand(self.bob, COUNTERSPELL)
        self.alice.mana_pool.black = 1
        self.bob.mana_pool.blue = 2

        self.game.begin_cast(ritual)
        self.game.begin_cast(counter)
        self.game.complete_pending_cast((ritual,))
        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)

        self.assertEqual(self.alice.mana_pool.black, 0)
        self.assertIs(ritual.zone, Zone.GRAVEYARD)
        self.assertIs(counter.zone, Zone.GRAVEYARD)
        self.assertIsNotNone(self.game.pending_damage)
        self.assertIs(
            self.game.pending_damage.step,
            DamageResolutionStep.PREVENTION,
        )

    def test_battlefield_targeting_interrupt_resumes_damage_window(self):
        self.open_damage_window()
        conversion = self.put_in_play(self.alice, CONVERSION)
        hack = self.put_in_hand(self.alice, MAGICAL_HACK)
        self.alice.mana_pool.blue = 1

        self.game.begin_cast(hack)
        self.game.complete_pending_cast(
            (conversion,), word_from="Mountain", word_to="Forest"
        )
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

        self.assertEqual(conversion.land_word_changes["Mountain"], "Forest")
        self.assertIsNotNone(self.game.pending_damage)
        self.assertIs(
            self.game.pending_damage.step,
            DamageResolutionStep.PREVENTION,
        )

    def test_dark_ritual_resumes_destroy_effect_regeneration_window(self):
        target = self.put_in_play(self.bob, LIVING_WALL)
        self.game.pause_for_damage_windows = True
        disenchant = self.put_in_hand(self.alice, DISENCHANT)
        self.alice.mana_pool.white = 2
        self.game.begin_cast(disenchant)
        self.game.complete_pending_cast((target,))
        self.resolve_batch()
        self.assertIsNotNone(self.game.pending_destruction)

        ritual = self.put_in_hand(self.alice, DARK_RITUAL)
        self.alice.mana_pool.black = 1
        self.game.begin_cast(ritual)
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

        self.assertEqual(self.alice.mana_pool.black, 3)
        self.assertIs(ritual.zone, Zone.GRAVEYARD)
        self.assertIsNotNone(self.game.pending_destruction)
        self.assertIs(target.zone, Zone.BATTLEFIELD)

    def test_interrupt_destruction_finishes_before_surrounding_damage(self):
        self.open_damage_window()
        elemental = self.put_in_play(self.bob, WATER_ELEMENTAL)
        blast = self.put_in_hand(self.alice, RED_ELEMENTAL_BLAST)
        self.alice.mana_pool.red = 1

        self.game.begin_cast(blast, mode="Destroy permanent")
        self.game.complete_pending_cast((elemental,))
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        self.assertIsNotNone(self.game.pending_damage)
        self.assertIsNotNone(self.game.pending_destruction)

        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)
        self.assertIs(elemental.zone, Zone.GRAVEYARD)
        self.assertIsNone(self.game.pending_destruction)
        self.assertIsNotNone(self.game.pending_damage)
        self.assertIs(
            self.game.pending_damage.step,
            DamageResolutionStep.PREVENTION,
        )

    def test_interrupt_destruction_can_nest_in_regeneration_window(self):
        living_wall = self.put_in_play(self.bob, LIVING_WALL)
        elemental = self.put_in_play(self.bob, WATER_ELEMENTAL)
        self.game.pause_for_damage_windows = True
        disenchant = self.put_in_hand(self.alice, DISENCHANT)
        self.alice.mana_pool.white = 2
        self.game.begin_cast(disenchant)
        self.game.complete_pending_cast((living_wall,))
        self.resolve_batch()

        blast = self.put_in_hand(self.alice, RED_ELEMENTAL_BLAST)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(blast, mode="Destroy permanent")
        self.game.complete_pending_cast((elemental,))
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        self.assertEqual(len(self.game.suspended_destruction_incidents), 1)

        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)
        self.assertIs(elemental.zone, Zone.GRAVEYARD)
        self.assertIs(living_wall.zone, Zone.BATTLEFIELD)
        self.assertIsNotNone(self.game.pending_destruction)

        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)
        self.assertIs(living_wall.zone, Zone.GRAVEYARD)
        self.assertIsNone(self.game.pending_destruction)


if __name__ == "__main__":
    unittest.main()
