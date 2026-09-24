import unittest

from beta_magic import Card, CardType, Color, GameState, PlayerState, TurnPhase, Zone
from beta_magic.batch_resolution import BatchIntentKind
from beta_magic.card_defs.artifacts import (
    CYCLOPEAN_TOMB,
    GLASSES_OF_URZA,
    ICY_MANIPULATOR,
    LIBRARY_OF_LENG,
    MANA_VAULT,
    NEVINYRRALS_DISK,
    ROD_OF_RUIN,
    SOL_RING,
    TIME_VAULT,
    KORMUS_BELL,
)
from beta_magic.card_defs.black import (
    DEMONIC_TUTOR,
    DARKPACT,
    EVIL_PRESENCE,
    LICH,
    MIND_TWIST,
    PARALYZE,
    NIGHTMARE,
    TERROR,
    DRAIN_LIFE,
    WORD_OF_COMMAND,
)
from beta_magic.card_defs.blue import (
    AIR_ELEMENTAL,
    ANIMATE_ARTIFACT,
    ANCESTRAL_RECALL,
    CLONE,
    CONTROL_MAGIC,
    COPY_ARTIFACT,
    CREATURE_BOND,
    DRAIN_POWER,
    MANA_SHORT,
    PHANTASMAL_TERRAIN,
    PSYCHIC_VENOM,
    TIME_WALK,
    TWIDDLE,
    UNSUMMON,
    VESUVAN_DOPPELGANGER,
)
from beta_magic.card_defs.green import (
    GRIZZLY_BEARS,
    GAEAS_LIEGE,
    NATURAL_SELECTION,
    STREAM_OF_LIFE,
    WALL_OF_BRAMBLES,
    LIVING_LANDS,
)
from beta_magic.card_defs.green import BERSERK, GIANT_GROWTH
from beta_magic.card_defs.lands import BADLANDS, FOREST, ISLAND, MOUNTAIN, SWAMP
from beta_magic.card_defs.red import (
    EARTHQUAKE,
    FIREBREATHING,
    KELDON_WARLORD,
    LIGHTNING_BOLT,
    STONE_RAIN,
    WHEEL_OF_FORTUNE,
)
from beta_magic.card_defs.white import (
    BALANCE,
    CONSECRATE_LAND,
    CONVERSION,
    CRUSADE,
    DISENCHANT,
    HOLY_STRENGTH,
    SWORDS_TO_PLOWSHARES,
    PEARLED_UNICORN,
    WHITE_KNIGHT,
    WRATH_OF_GOD,
)
from beta_magic.casting import AbilityOnStack, SpellOnStack
from beta_magic.effects import DamageEffect
from beta_magic.ui import GameViewModel


class BatchResolutionPlanningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 20
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    @staticmethod
    def add_card(player, definition, zone):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=zone,
        )
        player.cards_in(zone).append(card)
        return card

    def cast_bolt_at_bob(self):
        bolt = self.add_card(self.alice, LIGHTNING_BOLT, Zone.HAND)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.bob,))
        return bolt

    def queue_spell(
        self,
        player,
        definition,
        target,
        sequence,
        *,
        chosen_mode=None,
        chosen_land_subtype=None,
        x_value=0,
    ):
        spell = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.STACK,
        )
        spell.chosen_land_subtype = chosen_land_subtype
        self.game.stack.append(spell)
        self.game.stack_spells[spell.id] = SpellOnStack(
            spell,
            player.id,
            player.id,
            () if target is None else (target,),
            x_value=x_value,
            chosen_mode=chosen_mode,
            declaration_sequence=sequence,
        )
        self.game.interrupt_declaration_sequence = max(
            self.game.interrupt_declaration_sequence, sequence
        )
        return spell

    def test_planning_describes_a_batch_without_mutating_game_state(self):
        bolt = self.cast_bolt_at_bob()
        stack_before = tuple(self.game.stack)
        life_before = self.bob.life
        pending_damage_before = self.game.pending_damage

        plan = self.game._plan_batch_resolution()

        self.assertEqual(tuple(self.game.stack), stack_before)
        self.assertEqual(self.bob.life, life_before)
        self.assertIs(self.game.pending_damage, pending_damage_before)
        self.assertEqual(plan.cards, (bolt,))
        self.assertTrue(plan.legality.spells[bolt.id])
        self.assertEqual(len(plan.intents), 1)
        intent = plan.intents[0]
        self.assertIs(intent.kind, BatchIntentKind.SPELL_EFFECT)
        self.assertIs(intent.source, bolt)
        self.assertEqual(intent.targets, (self.bob,))
        self.assertIsInstance(intent.operation, DamageEffect)
        self.assertEqual(
            intent.declaration_sequence,
            self.game.stack_spells[bolt.id].declaration_sequence,
        )
        self.assertEqual(self.game._detect_batch_conflicts(plan), ())

    def test_spell_and_ability_intents_share_announcement_order(self):
        bolt = self.cast_bolt_at_bob()
        rod = self.add_card(self.alice, ROD_OF_RUIN, Zone.BATTLEFIELD)
        declared = AbilityOnStack(
            source=rod,
            source_name=rod.name,
            controller_id=self.alice.id,
            ability=rod.definition.activated_abilities[0],
            targets=(self.bob,),
        )

        self.game._queue_batch_ability(declared)
        plan = self.game._plan_batch_resolution()

        self.assertGreater(
            declared.declaration_sequence,
            self.game.stack_spells[bolt.id].declaration_sequence,
        )
        self.assertEqual(
            tuple(intent.kind for intent in plan.intents),
            (
                BatchIntentKind.SPELL_EFFECT,
                BatchIntentKind.ACTIVATED_ABILITY,
            ),
        )
        self.assertEqual(
            tuple(intent.declaration_sequence for intent in plan.intents),
            (
                self.game.stack_spells[bolt.id].declaration_sequence,
                declared.declaration_sequence,
            ),
        )

    def test_time_walk_and_opposing_time_vault_need_an_ordering_choice(self):
        self.queue_spell(self.alice, TIME_WALK, None, 1)
        vault = self.add_card(self.bob, TIME_VAULT, Zone.BATTLEFIELD)
        vault.tapped = True  # Its tap cost was paid when the ability was announced.
        self.game.batch_abilities.append(
            AbilityOnStack(
                vault,
                vault.name,
                self.bob.id,
                vault.definition.activated_abilities[0],
                (),
                declaration_sequence=2,
            )
        )

        self.game._resolve_batch()

        choice = self.game.pending_batch_conflict_choices[0]
        self.assertEqual(choice.conflict.chooser_id, self.bob.id)
        self.assertEqual(
            choice.conflict.affected_player_ids,
            (self.alice.id, self.bob.id),
        )
        self.assertEqual(
            [
                self.game.batch_conflict_intent_label(choice, index)
                for index in choice.intent_indexes_first_to_last
            ],
            [
                "Time Walk \u2192 Alice takes an extra turn",
                "Time Vault \u2192 Bob takes an extra turn",
            ],
        )
        state = GameViewModel(self.game).state
        self.assertEqual(
            state["batchConflictTitle"], "Order extra-turn effects"
        )

        self.game.confirm_batch_conflict_order(self.bob.id)

        # Time Vault is applied last, so its newly created turn is closest
        # to the current turn.
        self.assertEqual(self.game.upcoming_turns, [self.bob.id, self.alice.id])

    def test_extra_turn_effects_can_be_reordered(self):
        self.queue_spell(self.alice, TIME_WALK, None, 1)
        vault = self.add_card(self.bob, TIME_VAULT, Zone.BATTLEFIELD)
        vault.tapped = True
        self.game.batch_abilities.append(
            AbilityOnStack(
                vault,
                vault.name,
                self.bob.id,
                vault.definition.activated_abilities[0],
                (),
                declaration_sequence=2,
            )
        )
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        vault_index = choice.intent_indexes_first_to_last[1]

        self.game.move_batch_conflict_intent(self.bob.id, vault_index, -1)
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(self.game.upcoming_turns, [self.alice.id, self.bob.id])

    def test_extra_turn_effects_for_one_player_commute(self):
        self.queue_spell(self.alice, TIME_WALK, None, 1)
        vault = self.add_card(self.alice, TIME_VAULT, Zone.BATTLEFIELD)
        vault.tapped = True
        self.game.batch_abilities.append(
            AbilityOnStack(
                vault,
                vault.name,
                self.alice.id,
                vault.definition.activated_abilities[0],
                (),
                declaration_sequence=2,
            )
        )

        self.game._resolve_batch()

        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertEqual(self.game.upcoming_turns, [self.alice.id, self.alice.id])

    def test_later_effect_caster_orders_terror_and_unsummon(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, TERROR, bear, 1)
        self.queue_spell(self.bob, UNSUMMON, bear, 2)

        resolved = self.game._resolve_batch()

        self.assertEqual(resolved, ())
        self.assertIs(bear.zone, Zone.BATTLEFIELD)
        self.assertEqual(len(self.game.pending_batch_conflict_choices), 1)
        choice = self.game.pending_batch_conflict_choices[0]
        self.assertEqual(choice.conflict.chooser_id, self.bob.id)
        self.assertEqual(choice.conflict.target_ids, (bear.id,))
        self.assertEqual(
            [
                self.game.batch_conflict_intent_label(choice, index)
                for index in choice.intent_indexes_first_to_last
            ],
            ["Terror → graveyard", "Unsummon → hand"],
        )

        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(bear.zone, Zone.GRAVEYARD)
        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertIsNone(self.game.pending_batch_resolution)

    def test_chooser_can_put_unsummon_before_terror(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, TERROR, bear, 1)
        self.queue_spell(self.bob, UNSUMMON, bear, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        unsummon_index = choice.intent_indexes_first_to_last[1]

        self.game.move_batch_conflict_intent(
            self.bob.id, unsummon_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(bear.zone, Zone.HAND)

    def test_reversing_announcement_order_changes_the_chooser(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.queue_spell(self.bob, UNSUMMON, bear, 1)
        self.queue_spell(self.alice, TERROR, bear, 2)

        self.game._resolve_batch()

        choice = self.game.pending_batch_conflict_choices[0]
        self.assertEqual(choice.conflict.chooser_id, self.alice.id)
        self.game.confirm_batch_conflict_order(self.alice.id)
        self.assertIs(bear.zone, Zone.HAND)

    def test_later_destination_applies_if_first_destruction_is_regenerated(self):
        self.game.pause_for_damage_windows = True
        wall = self.add_card(
            self.bob, WALL_OF_BRAMBLES, Zone.BATTLEFIELD
        )
        disk = self.add_card(
            self.alice, NEVINYRRALS_DISK, Zone.BATTLEFIELD
        )
        self.game.batch_abilities.append(
            AbilityOnStack(
                disk,
                disk.name,
                self.alice.id,
                disk.definition.activated_abilities[0],
                (),
                declaration_sequence=1,
            )
        )
        self.queue_spell(self.bob, UNSUMMON, wall, 2)
        self.game._resolve_batch()

        self.game.confirm_batch_conflict_order(self.bob.id)
        self.assertIsNotNone(self.game.pending_destruction)
        self.game.pending_destruction.regenerated_card_ids.add(wall.id)
        self.game._finish_destruction_incident()

        self.assertIs(wall.zone, Zone.HAND)
        self.assertIsNone(self.game.pending_batch_resolution)
        self.assertFalse(self.game.pending_batch_destination_fallbacks)

    def test_ui_exposes_first_to_last_destination_order(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, TERROR, bear, 1)
        self.queue_spell(self.bob, UNSUMMON, bear, 2)
        self.game._resolve_batch()
        view = GameViewModel(self.game)
        view.perspective_index = 1

        state = view.state

        self.assertTrue(state["batchConflictChoice"])
        self.assertEqual(state["batchConflictPlayer"], self.bob.id)
        self.assertIn("Grizzly Bears", state["batchConflictReason"])
        self.assertEqual(
            [item["label"] for item in state["batchConflictItems"]],
            ["Terror → graveyard", "Unsummon → hand"],
        )

    def test_only_the_winning_destination_keeps_its_secondary_effect(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, SWORDS_TO_PLOWSHARES, bear, 1)
        self.queue_spell(self.bob, UNSUMMON, bear, 2)
        self.game._resolve_batch()

        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(bear.zone, Zone.EXILE)
        self.assertEqual(self.bob.life, 22)

    def test_effects_with_the_same_destination_do_not_prompt(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, TERROR, bear, 1)
        self.queue_spell(self.bob, TERROR, bear, 2)

        self.game._resolve_batch()

        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertIs(bear.zone, Zone.GRAVEYARD)

    def test_global_destruction_participates_in_destination_conflicts(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, WRATH_OF_GOD, None, 1)
        self.queue_spell(self.bob, UNSUMMON, bear, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        unsummon_index = choice.intent_indexes_first_to_last[1]

        self.game.move_batch_conflict_intent(
            self.bob.id, unsummon_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(bear.zone, Zone.HAND)

    def test_opposed_twiddles_are_replayed_in_chosen_order(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.queue_spell(
            self.alice, TWIDDLE, bear, 1, chosen_mode="Tap"
        )
        self.queue_spell(
            self.bob, TWIDDLE, bear, 2, chosen_mode="Untap"
        )

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        self.assertEqual(choice.conflict.chooser_id, self.bob.id)
        self.assertEqual(
            [
                self.game.batch_conflict_intent_label(choice, index)
                for index in choice.intent_indexes_first_to_last
            ],
            ["Twiddle → tapped", "Twiddle → untapped"],
        )
        state = GameViewModel(self.game).state
        self.assertEqual(
            state["batchConflictTitle"], "Order tap and untap effects"
        )
        self.game.confirm_batch_conflict_order(self.bob.id)
        self.assertFalse(bear.tapped)

        second = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.queue_spell(
            self.alice, TWIDDLE, second, 3, chosen_mode="Tap"
        )
        self.queue_spell(
            self.bob, TWIDDLE, second, 4, chosen_mode="Untap"
        )
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        untap_index = choice.intent_indexes_first_to_last[1]
        self.game.move_batch_conflict_intent(
            self.bob.id, untap_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)
        self.assertTrue(second.tapped)

    def test_ordered_untap_then_tap_preserves_tap_triggers(self):
        island = self.add_card(self.bob, ISLAND, Zone.BATTLEFIELD)
        island.tapped = True
        venom = self.add_card(self.alice, PSYCHIC_VENOM, Zone.BATTLEFIELD)
        venom.enchanted_card_id = island.id
        self.queue_spell(
            self.alice, TWIDDLE, island, 1, chosen_mode="Untap"
        )
        self.queue_spell(
            self.bob, TWIDDLE, island, 2, chosen_mode="Tap"
        )

        self.game._resolve_batch()
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertTrue(island.tapped)
        self.assertEqual(len(self.game.event_opportunities), 1)
        self.assertEqual(
            self.game.event_opportunities[0].source_name, "Psychic Venom"
        )

    def test_activated_tap_and_untap_abilities_join_the_choice(self):
        vault = self.add_card(self.alice, MANA_VAULT, Zone.BATTLEFIELD)
        icy = self.add_card(self.bob, ICY_MANIPULATOR, Zone.BATTLEFIELD)
        self.game.batch_abilities.extend(
            (
                AbilityOnStack(
                    vault,
                    vault.name,
                    self.alice.id,
                    vault.definition.activated_abilities[1],
                    (vault,),
                    declaration_sequence=1,
                ),
                AbilityOnStack(
                    icy,
                    icy.name,
                    self.bob.id,
                    icy.definition.activated_abilities[0],
                    (vault,),
                    declaration_sequence=2,
                ),
            )
        )

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        self.assertEqual(
            [item for item in choice.intent_indexes_first_to_last], [0, 1]
        )
        self.game.confirm_batch_conflict_order(self.bob.id)
        self.assertTrue(vault.tapped)

    def test_mana_short_tap_conflicts_with_twiddle_untap(self):
        island = self.add_card(self.bob, ISLAND, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, MANA_SHORT, self.bob, 1)
        self.queue_spell(
            self.bob, TWIDDLE, island, 2, chosen_mode="Untap"
        )

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        self.assertIn("Island", choice.conflict.reason)
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertFalse(island.tapped)

    def test_drain_power_still_produces_mana_when_its_tap_is_ordered(self):
        island = self.add_card(self.bob, ISLAND, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, DRAIN_POWER, self.bob, 1)
        self.queue_spell(
            self.bob, TWIDDLE, island, 2, chosen_mode="Untap"
        )

        self.game._resolve_batch()
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertFalse(island.tapped)
        self.assertEqual(self.alice.mana_pool.blue, 1)

    def test_permanent_entry_tap_effect_joins_the_choice(self):
        creature = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD
        )
        self.queue_spell(self.alice, PARALYZE, creature, 1)
        self.queue_spell(
            self.bob, TWIDDLE, creature, 2, chosen_mode="Untap"
        )

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        self.assertEqual(
            [
                self.game.batch_conflict_intent_label(choice, index)
                for index in choice.intent_indexes_first_to_last
            ],
            ["Paralyze → tapped", "Twiddle → untapped"],
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertFalse(creature.tapped)

    def test_two_tap_effects_do_not_require_an_ordering_choice(self):
        creature = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD
        )
        icy = self.add_card(
            self.bob, ICY_MANIPULATOR, Zone.BATTLEFIELD
        )
        self.queue_spell(
            self.alice, TWIDDLE, creature, 1, chosen_mode="Tap"
        )
        self.game.batch_abilities.append(
            AbilityOnStack(
                icy,
                icy.name,
                self.bob.id,
                icy.definition.activated_abilities[0],
                (creature,),
                declaration_sequence=2,
            )
        )

        self.game._resolve_batch()

        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertTrue(creature.tapped)

    def test_tap_cost_does_not_join_the_effect_ordering_choice(self):
        creature = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD
        )
        icy = self.add_card(
            self.bob, ICY_MANIPULATOR, Zone.BATTLEFIELD
        )
        # The source was tapped as a cost when the ability was announced.
        icy.tapped = True
        self.game.batch_abilities.append(
            AbilityOnStack(
                icy,
                icy.name,
                self.bob.id,
                icy.definition.activated_abilities[0],
                (creature,),
                declaration_sequence=1,
            )
        )
        self.queue_spell(
            self.alice, TWIDDLE, icy, 2, chosen_mode="Untap"
        )

        self.game._resolve_batch()

        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertFalse(icy.tapped)
        self.assertTrue(creature.tapped)

    def test_growth_then_berserk_can_resolve_in_announcement_order(self):
        creature = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD
        )
        self.queue_spell(self.alice, GIANT_GROWTH, creature, 1)
        self.queue_spell(self.bob, BERSERK, creature, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        self.assertEqual(choice.conflict.chooser_id, self.bob.id)
        self.assertEqual(
            [
                self.game.batch_conflict_intent_label(choice, index)
                for index in choice.intent_indexes_first_to_last
            ],
            ["Giant Growth → +3 power", "Berserk → ×2 power"],
        )
        state = GameViewModel(self.game).state
        self.assertEqual(state["batchConflictTitle"], "Order power modifiers")

        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(self.game.creature_power(creature), 10)
        self.assertEqual(self.game.creature_toughness(creature), 5)

    def test_growth_and_berserk_can_be_reordered(self):
        creature = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD
        )
        self.queue_spell(self.alice, GIANT_GROWTH, creature, 1)
        self.queue_spell(self.bob, BERSERK, creature, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        berserk_index = choice.intent_indexes_first_to_last[1]

        self.game.move_batch_conflict_intent(
            self.bob.id, berserk_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(self.game.creature_power(creature), 7)
        self.assertEqual(self.game.creature_toughness(creature), 5)

    def test_swords_can_read_power_before_a_simultaneous_pump(self):
        creature = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD
        )
        self.queue_spell(self.alice, SWORDS_TO_PLOWSHARES, creature, 1)
        self.queue_spell(self.bob, GIANT_GROWTH, creature, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        self.assertEqual(choice.conflict.chooser_id, self.bob.id)
        self.assertEqual(choice.conflict.kind.value, "swords_read")
        self.assertEqual(
            GameViewModel(self.game).state["batchConflictTitle"],
            "Order Swords resolution",
        )

        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(creature.zone, Zone.EXILE)
        self.assertEqual(self.bob.life, 22)

    def test_swords_can_read_power_after_a_simultaneous_pump(self):
        creature = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD
        )
        self.queue_spell(self.alice, SWORDS_TO_PLOWSHARES, creature, 1)
        growth = self.queue_spell(self.bob, GIANT_GROWTH, creature, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        growth_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is growth
        )

        self.game.move_batch_conflict_intent(
            self.bob.id, growth_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(creature.zone, Zone.EXILE)
        self.assertEqual(self.bob.life, 25)

    def test_swords_power_read_accounts_for_destroyed_swamp(self):
        nightmare = self.add_card(self.bob, NIGHTMARE, Zone.BATTLEFIELD)
        first_swamp = self.add_card(self.bob, SWAMP, Zone.BATTLEFIELD)
        self.add_card(self.bob, SWAMP, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, SWORDS_TO_PLOWSHARES, nightmare, 1)
        rain = self.queue_spell(self.bob, STONE_RAIN, first_swamp, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        rain_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is rain
        )
        self.game.move_batch_conflict_intent(
            self.bob.id, rain_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(nightmare.zone, Zone.EXILE)
        self.assertIs(first_swamp.zone, Zone.GRAVEYARD)
        self.assertEqual(self.bob.life, 21)

    def test_swords_does_not_prompt_for_irrelevant_land_destruction(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        swamp = self.add_card(self.bob, SWAMP, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, SWORDS_TO_PLOWSHARES, bear, 1)
        self.queue_spell(self.bob, STONE_RAIN, swamp, 2)

        self.game._resolve_batch()

        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertIs(bear.zone, Zone.EXILE)
        self.assertIs(swamp.zone, Zone.GRAVEYARD)
        self.assertEqual(self.bob.life, 22)

    def test_swords_power_read_accounts_for_destroyed_creature(self):
        warlord = self.add_card(
            self.bob, KELDON_WARLORD, Zone.BATTLEFIELD
        )
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, SWORDS_TO_PLOWSHARES, warlord, 1)
        terror = self.queue_spell(self.bob, TERROR, bear, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        terror_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is terror
        )
        self.game.move_batch_conflict_intent(
            self.bob.id, terror_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(warlord.zone, Zone.EXILE)
        self.assertIs(bear.zone, Zone.GRAVEYARD)
        self.assertEqual(self.bob.life, 21)

    def test_swords_power_read_accounts_for_removed_animation_aura(self):
        ring = self.add_card(self.bob, SOL_RING, Zone.BATTLEFIELD)
        animation = self.add_card(
            self.bob, ANIMATE_ARTIFACT, Zone.BATTLEFIELD
        )
        animation.enchanted_card_id = ring.id
        self.assertEqual(self.game.creature_power(ring), 1)
        self.queue_spell(self.alice, SWORDS_TO_PLOWSHARES, ring, 1)
        disenchant = self.queue_spell(
            self.bob, DISENCHANT, animation, 2
        )

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        disenchant_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is disenchant
        )
        self.game.move_batch_conflict_intent(
            self.bob.id, disenchant_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(ring.zone, Zone.EXILE)
        self.assertIs(animation.zone, Zone.GRAVEYARD)
        self.assertEqual(self.bob.life, 20)

    def test_control_magic_before_swords_gives_life_to_new_controller(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        control = self.queue_spell(self.alice, CONTROL_MAGIC, bear, 1)
        self.queue_spell(self.bob, SWORDS_TO_PLOWSHARES, bear, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        self.assertEqual(choice.conflict.kind.value, "swords_read")
        self.assertIn(control.id, {intent.source.id for intent in (
            self.game.pending_batch_resolution.intents[index]
            for index in choice.intent_indexes_first_to_last
        )})
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(bear.zone, Zone.EXILE)
        self.assertEqual(self.alice.life, 22)
        self.assertEqual(self.bob.life, 20)
        self.assertIs(control.zone, Zone.GRAVEYARD)

    def test_swords_before_control_magic_gives_life_to_old_controller(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        control = self.queue_spell(self.alice, CONTROL_MAGIC, bear, 1)
        swords = self.queue_spell(
            self.bob, SWORDS_TO_PLOWSHARES, bear, 2
        )
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        swords_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is swords
        )
        self.game.move_batch_conflict_intent(
            self.bob.id, swords_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(bear.zone, Zone.EXILE)
        self.assertEqual(self.alice.life, 20)
        self.assertEqual(self.bob.life, 22)
        self.assertIs(control.zone, Zone.GRAVEYARD)

    def test_creature_bond_before_terror_observes_the_destruction(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        bond = self.queue_spell(self.alice, CREATURE_BOND, bear, 1)
        self.queue_spell(self.bob, TERROR, bear, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        self.assertEqual(choice.conflict.kind.value, "aura_entry")
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(bear.zone, Zone.GRAVEYARD)
        self.assertIs(bond.zone, Zone.GRAVEYARD)
        self.assertTrue(
            any(
                event.source_name == "Creature Bond"
                for event in self.game.event_opportunities
            )
        )

    def test_terror_before_creature_bond_prevents_the_attachment(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        bond = self.queue_spell(self.alice, CREATURE_BOND, bear, 1)
        terror = self.queue_spell(self.bob, TERROR, bear, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        terror_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is terror
        )
        self.game.move_batch_conflict_intent(
            self.bob.id, terror_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(bear.zone, Zone.GRAVEYARD)
        self.assertIs(bond.zone, Zone.GRAVEYARD)
        self.assertFalse(
            any(
                event.source_name == "Creature Bond"
                for event in self.game.event_opportunities
            )
        )

    def test_aura_ordered_after_regenerated_destruction_still_attaches(self):
        self.game.pause_for_damage_windows = True
        wall = self.add_card(
            self.bob, WALL_OF_BRAMBLES, Zone.BATTLEFIELD
        )
        bond = self.queue_spell(self.alice, CREATURE_BOND, wall, 1)
        disk = self.add_card(
            self.bob, NEVINYRRALS_DISK, Zone.BATTLEFIELD
        )
        self.game.batch_abilities.append(
            AbilityOnStack(
                disk,
                disk.name,
                self.bob.id,
                disk.definition.activated_abilities[0],
                (),
                declaration_sequence=2,
            )
        )
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        disk_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is disk
        )
        self.game.move_batch_conflict_intent(
            self.bob.id, disk_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIsNotNone(self.game.pending_destruction)
        self.game.pending_destruction.regenerated_card_ids.add(wall.id)
        self.game._finish_destruction_incident()

        self.assertIs(wall.zone, Zone.BATTLEFIELD)
        self.assertIs(bond.zone, Zone.BATTLEFIELD)
        self.assertEqual(bond.enchanted_card_id, wall.id)

    def test_clone_before_terror_copies_then_survives_its_model(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        clone = self.queue_spell(self.alice, CLONE, bear, 1)
        self.queue_spell(self.bob, TERROR, bear, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]

        self.assertEqual(choice.conflict.kind.value, "copy_entry")
        self.assertEqual(
            GameViewModel(self.game).state["batchConflictTitle"],
            "Order copying and source removal",
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(bear.zone, Zone.GRAVEYARD)
        self.assertIs(clone.zone, Zone.BATTLEFIELD)
        self.assertEqual(clone.name, "Grizzly Bears")

    def test_terror_before_clone_prevents_copy_from_entering(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        clone = self.queue_spell(self.alice, CLONE, bear, 1)
        terror = self.queue_spell(self.bob, TERROR, bear, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        terror_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is terror
        )
        self.game.move_batch_conflict_intent(
            self.bob.id, terror_index, -1
        )

        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(bear.zone, Zone.GRAVEYARD)
        self.assertIs(clone.zone, Zone.GRAVEYARD)
        self.assertIs(clone.definition, CLONE)

    def test_unsummon_before_clone_fails_without_destruction_window(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        clone = self.queue_spell(self.alice, CLONE, bear, 1)
        unsummon = self.queue_spell(self.bob, UNSUMMON, bear, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        unsummon_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is unsummon
        )
        self.game.move_batch_conflict_intent(
            self.bob.id, unsummon_index, -1
        )

        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(bear.zone, Zone.HAND)
        self.assertIs(clone.zone, Zone.GRAVEYARD)
        self.assertIsNone(self.game.pending_destruction)

    def test_copy_artifact_uses_the_same_source_removal_ordering(self):
        ring = self.add_card(self.bob, SOL_RING, Zone.BATTLEFIELD)
        copy = self.queue_spell(self.alice, COPY_ARTIFACT, ring, 1)
        disenchant = self.queue_spell(self.bob, DISENCHANT, ring, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        disenchant_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is disenchant
        )
        self.game.move_batch_conflict_intent(
            self.bob.id, disenchant_index, -1
        )

        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(ring.zone, Zone.GRAVEYARD)
        self.assertIs(copy.zone, Zone.GRAVEYARD)
        self.assertIs(copy.definition, COPY_ARTIFACT)

    def test_vesuvan_doppelganger_copies_before_source_removal(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        doppelganger = self.queue_spell(
            self.alice, VESUVAN_DOPPELGANGER, bear, 1
        )
        self.queue_spell(self.bob, TERROR, bear, 2)

        self.game._resolve_batch()
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(doppelganger.zone, Zone.BATTLEFIELD)
        self.assertEqual(doppelganger.name, "Grizzly Bears")
        self.assertTrue(doppelganger.definition.is_vesuvan_doppelganger)

    def test_copy_ordered_after_regenerated_destruction_still_enters(self):
        self.game.pause_for_damage_windows = True
        wall = self.add_card(
            self.bob, WALL_OF_BRAMBLES, Zone.BATTLEFIELD
        )
        clone = self.queue_spell(self.alice, CLONE, wall, 1)
        disk = self.add_card(
            self.bob, NEVINYRRALS_DISK, Zone.BATTLEFIELD
        )
        self.game.batch_abilities.append(
            AbilityOnStack(
                disk,
                disk.name,
                self.bob.id,
                disk.definition.activated_abilities[0],
                (),
                declaration_sequence=2,
            )
        )
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        disk_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is disk
        )
        self.game.move_batch_conflict_intent(
            self.bob.id, disk_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIsNotNone(self.game.pending_destruction)
        self.assertEqual(
            self.game.pending_batch_resolution.pending_copy_entry_intents,
            [
                index
                for index, intent in enumerate(
                    self.game.pending_batch_resolution.intents
                )
                if intent.source is clone
            ],
        )
        self.game.pending_destruction.regenerated_card_ids.add(wall.id)
        self.game._finish_destruction_incident()

        self.assertIs(wall.zone, Zone.BATTLEFIELD)
        self.assertIs(clone.zone, Zone.BATTLEFIELD)
        self.assertEqual(clone.name, "Wall of Brambles")

    def test_consecrate_land_before_stone_rain_prevents_destruction(self):
        land = self.add_card(self.bob, SWAMP, Zone.BATTLEFIELD)
        aura = self.queue_spell(self.alice, CONSECRATE_LAND, land, 1)
        self.queue_spell(self.bob, STONE_RAIN, land, 2)

        self.game._resolve_batch()
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(land.zone, Zone.BATTLEFIELD)
        self.assertIs(aura.zone, Zone.BATTLEFIELD)
        self.assertEqual(aura.enchanted_card_id, land.id)

    def test_stone_rain_before_consecrate_land_destroys_land(self):
        land = self.add_card(self.bob, SWAMP, Zone.BATTLEFIELD)
        aura = self.queue_spell(self.alice, CONSECRATE_LAND, land, 1)
        rain = self.queue_spell(self.bob, STONE_RAIN, land, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        rain_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is rain
        )
        self.game.move_batch_conflict_intent(
            self.bob.id, rain_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(land.zone, Zone.GRAVEYARD)
        self.assertIs(aura.zone, Zone.GRAVEYARD)

    def test_reversed_announcement_changes_power_chooser(self):
        creature = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD
        )
        self.queue_spell(self.alice, BERSERK, creature, 1)
        self.queue_spell(self.bob, GIANT_GROWTH, creature, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]

        self.assertEqual(choice.conflict.chooser_id, self.bob.id)
        self.game.confirm_batch_conflict_order(self.bob.id)
        self.assertEqual(self.game.creature_power(creature), 7)

    def test_additive_power_modifiers_do_not_prompt(self):
        creature = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD
        )
        self.queue_spell(self.alice, GIANT_GROWTH, creature, 1)
        self.queue_spell(self.bob, GIANT_GROWTH, creature, 2)

        self.game._resolve_batch()

        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertEqual(self.game.creature_power(creature), 8)

    def test_pure_power_multipliers_do_not_prompt(self):
        creature = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD
        )
        self.queue_spell(self.alice, BERSERK, creature, 1)
        self.queue_spell(self.bob, BERSERK, creature, 2)

        self.game._resolve_batch()

        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertEqual(self.game.creature_power(creature), 8)

    def test_connected_power_conflict_orders_all_three_modifiers(self):
        creature = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD
        )
        self.queue_spell(self.alice, GIANT_GROWTH, creature, 1)
        self.queue_spell(self.alice, BERSERK, creature, 2)
        self.queue_spell(self.bob, GIANT_GROWTH, creature, 3)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        last_growth_index = choice.intent_indexes_first_to_last[2]

        self.assertEqual(len(choice.intent_indexes_first_to_last), 3)
        self.game.move_batch_conflict_intent(
            self.bob.id, last_growth_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(self.game.creature_power(creature), 16)

    def test_activated_power_modifier_participates_in_choice(self):
        creature = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD
        )
        firebreathing = self.add_card(
            self.alice, FIREBREATHING, Zone.BATTLEFIELD
        )
        firebreathing.enchanted_card_id = creature.id
        self.game.batch_abilities.append(
            AbilityOnStack(
                firebreathing,
                firebreathing.name,
                self.alice.id,
                firebreathing.definition.activated_abilities[0],
                (creature,),
                declaration_sequence=1,
            )
        )
        self.queue_spell(self.bob, BERSERK, creature, 2)

        self.game._resolve_batch()
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(self.game.creature_power(creature), 6)

    def test_entering_aura_can_be_ordered_after_berserk(self):
        creature = self.add_card(
            self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD
        )
        self.queue_spell(self.alice, HOLY_STRENGTH, creature, 1)
        self.queue_spell(self.bob, BERSERK, creature, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        berserk_index = choice.intent_indexes_first_to_last[1]

        self.game.move_batch_conflict_intent(
            self.bob.id, berserk_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(self.game.creature_power(creature), 5)

    def test_entering_global_power_modifier_participates_in_choice(self):
        knight = self.add_card(
            self.alice, WHITE_KNIGHT, Zone.BATTLEFIELD
        )
        self.queue_spell(self.alice, CRUSADE, None, 1)
        self.queue_spell(self.bob, BERSERK, knight, 2)

        self.game._resolve_batch()
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(self.game.creature_power(knight), 6)

    def test_pure_draws_do_not_require_an_ordering_choice(self):
        self.queue_spell(self.alice, ANCESTRAL_RECALL, self.alice, 1)
        self.queue_spell(self.bob, ANCESTRAL_RECALL, self.alice, 2)

        self.game._resolve_batch()

        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertEqual(len(self.alice.hand), 6)

    def test_identical_hand_replacements_do_not_prompt(self):
        self.queue_spell(self.alice, WHEEL_OF_FORTUNE, None, 1)
        self.queue_spell(self.bob, WHEEL_OF_FORTUNE, None, 2)

        self.game._resolve_batch()

        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertEqual(len(self.alice.hand), 7)
        self.assertEqual(len(self.bob.hand), 7)

    def test_hand_effects_on_different_players_do_not_conflict(self):
        self.add_card(self.bob, ISLAND, Zone.HAND)
        self.queue_spell(self.alice, ANCESTRAL_RECALL, self.alice, 1)
        self.queue_spell(self.alice, MIND_TWIST, self.bob, 2, x_value=1)

        self.game._resolve_batch()

        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertEqual(len(self.alice.hand), 3)
        self.assertFalse(self.bob.hand)

    def test_draw_and_wheel_are_applied_in_the_chosen_order(self):
        self.add_card(self.alice, ISLAND, Zone.HAND)
        self.queue_spell(self.alice, ANCESTRAL_RECALL, self.alice, 1)
        self.queue_spell(self.bob, WHEEL_OF_FORTUNE, None, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]

        self.assertEqual(choice.conflict.chooser_id, self.bob.id)
        self.assertEqual(choice.conflict.affected_player_ids, (self.alice.id,))
        self.assertEqual(
            [
                self.game.batch_conflict_intent_label(choice, index)
                for index in choice.intent_indexes_first_to_last
            ],
            [
                "Ancestral Recall → Alice draws 3",
                "Wheel of Fortune → each player discards their hand, then draws 7",
            ],
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(len(self.alice.hand), 7)

    def test_wheel_then_draw_leaves_the_extra_drawn_cards_in_hand(self):
        self.add_card(self.alice, ISLAND, Zone.HAND)
        self.queue_spell(self.alice, ANCESTRAL_RECALL, self.alice, 1)
        self.queue_spell(self.bob, WHEEL_OF_FORTUNE, None, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        wheel_index = choice.intent_indexes_first_to_last[1]

        self.game.move_batch_conflict_intent(
            self.bob.id, wheel_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(len(self.alice.hand), 10)

    def test_library_of_leng_choice_pauses_before_the_next_ordered_draw(self):
        self.add_card(self.alice, LIBRARY_OF_LENG, Zone.BATTLEFIELD)
        self.add_card(self.alice, ISLAND, Zone.HAND)
        self.queue_spell(self.bob, WHEEL_OF_FORTUNE, None, 1)
        self.queue_spell(self.alice, ANCESTRAL_RECALL, self.alice, 2)

        self.game._resolve_batch()
        self.game.confirm_batch_conflict_order(self.alice.id)

        self.assertEqual(len(self.game.pending_library_discard_choices), 1)
        self.assertFalse(self.alice.hand[:-1])
        self.assertFalse(self.game.pending_batch_resolution.finalized)

        self.game.confirm_library_discard(self.alice.id)

        self.assertEqual(len(self.alice.hand), 10)
        self.assertIsNone(self.game.pending_batch_resolution)

    def test_natural_selection_finishes_before_a_later_ordered_draw(self):
        self.queue_spell(self.alice, NATURAL_SELECTION, self.alice, 1)
        self.queue_spell(self.bob, ANCESTRAL_RECALL, self.alice, 2)

        self.game._resolve_batch()
        state = GameViewModel(self.game).state
        self.assertEqual(
            state["batchConflictTitle"], "Order hand and library effects"
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(len(self.game.pending_natural_selection_choices), 1)
        self.assertFalse(self.alice.hand)
        self.assertEqual(len(self.game.stack), 2)

        self.game.choose_natural_selection(self.alice.id, shuffle=False)

        self.assertEqual(len(self.alice.hand), 3)
        self.assertFalse(self.game.stack)
        self.assertIsNone(self.game.pending_batch_resolution)

    def test_library_search_finishes_before_a_later_ordered_draw(self):
        self.queue_spell(self.alice, DEMONIC_TUTOR, None, 1)
        self.queue_spell(self.bob, ANCESTRAL_RECALL, self.alice, 2)

        self.game._resolve_batch()
        self.game.confirm_batch_conflict_order(self.bob.id)
        tutored = self.game.legal_library_search_cards()[0]

        self.assertFalse(self.alice.hand)
        self.game.choose_library_search_card(self.alice.id, tutored)

        self.assertIn(tutored, self.alice.hand)
        self.assertEqual(len(self.alice.hand), 4)
        self.assertIsNone(self.game.pending_batch_resolution)

    def test_return_to_hand_and_wheel_are_ordered(self):
        bear = self.add_card(self.bob, GRIZZLY_BEARS, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, UNSUMMON, bear, 1)
        self.queue_spell(self.bob, WHEEL_OF_FORTUNE, None, 2)

        self.game._resolve_batch()
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(bear.zone, Zone.GRAVEYARD)
        self.assertNotIn(bear, self.bob.hand)

    def test_balance_choice_completes_before_a_later_ordered_draw(self):
        first = self.add_card(self.alice, ISLAND, Zone.HAND)
        second = self.add_card(self.alice, ISLAND, Zone.HAND)
        self.add_card(self.alice, ISLAND, Zone.HAND)
        self.add_card(self.bob, ISLAND, Zone.HAND)
        self.queue_spell(self.alice, BALANCE, None, 1)
        self.queue_spell(self.bob, ANCESTRAL_RECALL, self.bob, 2)

        self.game._resolve_batch()
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIsNotNone(self.game.pending_balance)
        self.assertEqual(self.game.pending_balance.current_choice.player_id, self.alice.id)
        self.game.choose_balance_cards(self.alice.id, (first, second))

        self.assertEqual(len(self.alice.hand), 1)
        self.assertEqual(len(self.bob.hand), 4)
        self.assertIsNone(self.game.pending_batch_resolution)

    def test_life_gain_replaced_by_lich_participates_as_a_draw(self):
        self.add_card(self.alice, LICH, Zone.BATTLEFIELD)
        self.queue_spell(
            self.alice, STREAM_OF_LIFE, self.alice, 1, x_value=3
        )
        self.queue_spell(self.bob, WHEEL_OF_FORTUNE, None, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        wheel_index = choice.intent_indexes_first_to_last[1]
        self.game.move_batch_conflict_intent(
            self.bob.id, wheel_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(len(self.alice.hand), 10)

    def test_darkpact_library_exchange_can_precede_a_draw(self):
        ante_card = self.add_card(self.bob, ISLAND, Zone.ANTE)
        self.queue_spell(self.alice, DARKPACT, ante_card, 1)
        self.queue_spell(self.bob, ANCESTRAL_RECALL, self.alice, 2)

        self.game._resolve_batch()
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIn(ante_card, self.alice.hand)
        self.assertEqual(ante_card.owner_id, self.alice.id)
        self.assertEqual(len(self.alice.hand), 3)

    def test_random_discard_and_draw_use_the_selected_order(self):
        self.add_card(self.bob, ISLAND, Zone.HAND)
        self.queue_spell(self.alice, MIND_TWIST, self.bob, 1, x_value=2)
        self.queue_spell(self.bob, ANCESTRAL_RECALL, self.bob, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        recall_index = choice.intent_indexes_first_to_last[1]
        self.game.move_batch_conflict_intent(
            self.bob.id, recall_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(len(self.bob.hand), 2)

    def test_glasses_snapshots_hand_before_a_later_wheel(self):
        old_card = self.add_card(self.bob, ISLAND, Zone.HAND)
        glasses = self.add_card(
            self.alice, GLASSES_OF_URZA, Zone.BATTLEFIELD
        )
        self.game.batch_abilities.append(
            AbilityOnStack(
                glasses,
                glasses.name,
                self.alice.id,
                glasses.definition.activated_abilities[0],
                (),
                declaration_sequence=1,
            )
        )
        self.queue_spell(self.bob, WHEEL_OF_FORTUNE, None, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]

        self.assertEqual(choice.conflict.chooser_id, self.bob.id)
        self.assertEqual(
            [
                self.game.batch_conflict_intent_label(choice, index)
                for index in choice.intent_indexes_first_to_last
            ],
            [
                "Glasses of Urza \u2192 look at opponent's hand",
                "Wheel of Fortune \u2192 each player discards their hand, then draws 7",
            ],
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        reveal = self.game.pending_hand_reveals[0]
        self.assertEqual(reveal.cards, (old_card,))
        self.assertFalse(self.game.pending_batch_resolution.finalized)

        self.game.finish_hand_reveal(self.alice.id)

        self.assertNotIn(old_card, self.bob.hand)
        self.assertEqual(len(self.bob.hand), 7)
        self.assertIsNone(self.game.pending_batch_resolution)

    def test_wheel_before_glasses_reveals_the_replacement_hand(self):
        old_card = self.add_card(self.bob, ISLAND, Zone.HAND)
        glasses = self.add_card(
            self.alice, GLASSES_OF_URZA, Zone.BATTLEFIELD
        )
        self.game.batch_abilities.append(
            AbilityOnStack(
                glasses,
                glasses.name,
                self.alice.id,
                glasses.definition.activated_abilities[0],
                (),
                declaration_sequence=1,
            )
        )
        self.queue_spell(self.bob, WHEEL_OF_FORTUNE, None, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        wheel_index = choice.intent_indexes_first_to_last[1]
        self.game.move_batch_conflict_intent(
            self.bob.id, wheel_index, -1
        )

        self.game.confirm_batch_conflict_order(self.bob.id)

        reveal = self.game.pending_hand_reveals[0]
        self.assertEqual(reveal.cards, tuple(self.bob.hand))
        self.assertEqual(len(reveal.cards), 7)
        self.assertNotIn(old_card, reveal.cards)

    def test_word_forces_announcement_before_a_later_wheel(self):
        bolt = self.add_card(self.bob, LIGHTNING_BOLT, Zone.HAND)
        mountain = self.add_card(self.bob, MOUNTAIN, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, WORD_OF_COMMAND, None, 1)
        self.queue_spell(self.bob, WHEEL_OF_FORTUNE, None, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(self.game.word_commandable_cards(), (bolt,))
        self.assertFalse(self.game.pending_batch_resolution.finalized)
        self.game.begin_word_command_cast(self.alice.id, bolt)
        self.game.complete_pending_cast((self.alice,))
        option = self.game.word_command_mana_options()[0]
        self.game.complete_word_command_payment(
            self.alice.id, ((mountain.id, option.ability_index),)
        )

        self.assertIn(bolt, self.game.stack)
        self.assertEqual(len(self.bob.hand), 7)
        self.assertEqual(self.game.interruptible_spell_id, bolt.id)
        self.assertIs(
            self.game.players[self.game.priority_player_index], self.alice
        )
        self.assertIsNone(self.game.pending_batch_resolution)

    def test_wheel_before_word_changes_the_hand_word_may_inspect(self):
        old_bolt = self.add_card(self.bob, LIGHTNING_BOLT, Zone.HAND)
        self.add_card(self.bob, MOUNTAIN, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, WORD_OF_COMMAND, None, 1)
        self.queue_spell(self.bob, WHEEL_OF_FORTUNE, None, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        wheel_index = choice.intent_indexes_first_to_last[1]
        self.game.move_batch_conflict_intent(
            self.bob.id, wheel_index, -1
        )

        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertNotIn(old_bolt, self.bob.hand)
        self.assertFalse(self.game.word_commandable_cards())
        self.assertFalse(self.game.pending_batch_resolution.finalized)
        self.game.finish_word_command_without_play(self.alice.id)

        self.assertFalse(self.game.pending_word_command_choices)
        self.assertIsNone(self.game.pending_batch_resolution)

    def test_word_preserves_commanded_spell_priority_across_later_choice(self):
        bolt = self.add_card(self.bob, LIGHTNING_BOLT, Zone.HAND)
        self.add_card(self.bob, ISLAND, Zone.HAND)
        mountain = self.add_card(self.bob, MOUNTAIN, Zone.BATTLEFIELD)
        self.add_card(self.bob, LIBRARY_OF_LENG, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, WORD_OF_COMMAND, None, 1)
        self.queue_spell(self.bob, WHEEL_OF_FORTUNE, None, 2)
        self.game._resolve_batch()
        self.game.confirm_batch_conflict_order(self.bob.id)
        self.game.begin_word_command_cast(self.alice.id, bolt)
        self.game.complete_pending_cast((self.alice,))
        option = self.game.word_command_mana_options()[0]

        self.game.complete_word_command_payment(
            self.alice.id, ((mountain.id, option.ability_index),)
        )

        self.assertTrue(self.game.pending_library_discard_choices)
        self.assertFalse(self.game.pending_batch_resolution.finalized)
        self.game.confirm_library_discard(self.bob.id)

        self.assertIn(bolt, self.game.stack)
        self.assertEqual(self.game.interruptible_spell_id, bolt.id)
        self.assertIs(
            self.game.players[self.game.priority_player_index], self.alice
        )
        self.assertIsNone(self.game.pending_batch_resolution)

    def test_two_hand_inspections_do_not_require_an_ordering_choice(self):
        first = self.add_card(
            self.alice, GLASSES_OF_URZA, Zone.BATTLEFIELD
        )
        second = self.add_card(
            self.alice, GLASSES_OF_URZA, Zone.BATTLEFIELD
        )
        for sequence, glasses in enumerate((first, second), start=1):
            self.game.batch_abilities.append(
                AbilityOnStack(
                    glasses,
                    glasses.name,
                    self.alice.id,
                    glasses.definition.activated_abilities[0],
                    (),
                    declaration_sequence=sequence,
                )
            )

        self.game._resolve_batch()

        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertEqual(len(self.game.pending_hand_reveals), 2)

    def test_competing_land_auras_use_the_selected_order(self):
        land = self.add_card(self.bob, BADLANDS, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, EVIL_PRESENCE, land, 1)
        self.queue_spell(
            self.bob,
            PHANTASMAL_TERRAIN,
            land,
            2,
            chosen_land_subtype="Island",
        )

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        state = GameViewModel(self.game).state

        self.assertEqual(choice.conflict.chooser_id, self.bob.id)
        self.assertEqual(choice.conflict.target_ids, (land.id,))
        self.assertEqual(state["batchConflictTitle"], "Order land-type settings")
        self.assertEqual(
            [
                self.game.batch_conflict_intent_label(choice, index)
                for index in choice.intent_indexes_first_to_last
            ],
            [
                "Evil Presence → set land type to Swamp",
                "Phantasmal Terrain → set land type to Island",
            ],
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(self.game.land_subtypes(land), ("Island",))
        self.assertEqual(
            [ability.color for ability in self.game.activated_abilities(land)],
            [Color.BLUE],
        )

    def test_competing_land_auras_can_be_reversed(self):
        land = self.add_card(self.bob, BADLANDS, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, EVIL_PRESENCE, land, 1)
        self.queue_spell(
            self.bob,
            PHANTASMAL_TERRAIN,
            land,
            2,
            chosen_land_subtype="Island",
        )
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        terrain_index = choice.intent_indexes_first_to_last[1]

        self.game.move_batch_conflict_intent(
            self.bob.id, terrain_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(self.game.land_subtypes(land), ("Swamp",))

    def test_activated_land_setters_keep_marks_in_the_selected_order(self):
        land = self.add_card(self.bob, ISLAND, Zone.BATTLEFIELD)
        liege = self.add_card(self.alice, GAEAS_LIEGE, Zone.BATTLEFIELD)
        self.add_card(self.alice, FOREST, Zone.BATTLEFIELD)
        tomb = self.add_card(self.bob, CYCLOPEAN_TOMB, Zone.BATTLEFIELD)
        self.game.batch_abilities.extend(
            (
                AbilityOnStack(
                    liege,
                    liege.name,
                    self.alice.id,
                    liege.definition.activated_abilities[0],
                    (land,),
                    declaration_sequence=1,
                ),
                AbilityOnStack(
                    tomb,
                    tomb.name,
                    self.bob.id,
                    tomb.definition.activated_abilities[0],
                    (land,),
                    declaration_sequence=2,
                ),
            )
        )

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        tomb_index = choice.intent_indexes_first_to_last[1]
        self.game.move_batch_conflict_intent(self.bob.id, tomb_index, -1)
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(self.game.land_subtypes(land), ("Forest",))
        self.assertEqual(land.counters["mire"], 1)
        self.assertIn(liege.id, land.land_type_marks)

        self.game._move_card(liege, Zone.GRAVEYARD)
        self.assertEqual(self.game.land_subtypes(land), ("Swamp",))

    def test_identical_land_type_settings_do_not_prompt(self):
        land = self.add_card(self.bob, ISLAND, Zone.BATTLEFIELD)
        tomb = self.add_card(self.bob, CYCLOPEAN_TOMB, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, EVIL_PRESENCE, land, 1)
        self.game.batch_abilities.append(
            AbilityOnStack(
                tomb,
                tomb.name,
                self.bob.id,
                tomb.definition.activated_abilities[0],
                (land,),
                declaration_sequence=2,
            )
        )

        self.game._resolve_batch()

        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertEqual(self.game.land_subtypes(land), ("Swamp",))
        self.assertEqual(land.counters["mire"], 1)

    def test_global_conversion_applies_after_the_selected_local_setting(self):
        land = self.add_card(self.bob, ISLAND, Zone.BATTLEFIELD)
        self.add_card(self.alice, CONVERSION, Zone.BATTLEFIELD)
        self.queue_spell(
            self.alice,
            PHANTASMAL_TERRAIN,
            land,
            1,
            chosen_land_subtype="Mountain",
        )
        self.queue_spell(
            self.bob,
            PHANTASMAL_TERRAIN,
            land,
            2,
            chosen_land_subtype="Forest",
        )
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        forest_index = choice.intent_indexes_first_to_last[1]

        self.game.move_batch_conflict_intent(
            self.bob.id, forest_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(self.game.land_subtypes(land), ("Plains",))

    def test_living_lands_and_wrath_use_a_characteristic_order(self):
        forest = self.add_card(self.bob, FOREST, Zone.BATTLEFIELD)
        living_lands = self.queue_spell(
            self.alice, LIVING_LANDS, None, 1
        )
        self.queue_spell(self.bob, WRATH_OF_GOD, None, 2)

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]

        self.assertEqual(choice.conflict.kind.value, "characteristics")
        self.assertEqual(choice.conflict.chooser_id, self.bob.id)
        self.assertEqual(
            GameViewModel(self.game).state["batchConflictTitle"],
            "Order characteristic-dependent effects",
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(living_lands.zone, Zone.BATTLEFIELD)
        self.assertIs(forest.zone, Zone.GRAVEYARD)

    def test_wrath_before_living_lands_does_not_destroy_the_forest(self):
        forest = self.add_card(self.bob, FOREST, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, LIVING_LANDS, None, 1)
        wrath = self.queue_spell(self.bob, WRATH_OF_GOD, None, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        wrath_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is wrath
        )

        self.game.move_batch_conflict_intent(
            self.bob.id, wrath_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(forest.zone, Zone.BATTLEFIELD)
        self.assertIn(CardType.CREATURE, self.game.card_types(forest))

    def test_removing_living_lands_before_earthquake_spares_the_forest(self):
        forest = self.add_card(self.bob, FOREST, Zone.BATTLEFIELD)
        living_lands = self.add_card(
            self.bob, LIVING_LANDS, Zone.BATTLEFIELD
        )
        self.queue_spell(
            self.alice, EARTHQUAKE, None, 1, x_value=1
        )
        disenchant = self.queue_spell(
            self.bob, DISENCHANT, living_lands, 2
        )

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        disenchant_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is disenchant
        )
        self.game.move_batch_conflict_intent(
            self.bob.id, disenchant_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(living_lands.zone, Zone.GRAVEYARD)
        self.assertIs(forest.zone, Zone.BATTLEFIELD)
        self.assertEqual(forest.damage, 0)

    def test_removing_animate_artifact_can_precede_wrath(self):
        ring = self.add_card(self.bob, SOL_RING, Zone.BATTLEFIELD)
        animation = self.add_card(
            self.bob, ANIMATE_ARTIFACT, Zone.BATTLEFIELD
        )
        animation.enchanted_card_id = ring.id
        self.queue_spell(self.alice, WRATH_OF_GOD, None, 1)
        disenchant = self.queue_spell(
            self.bob, DISENCHANT, animation, 2
        )

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        disenchant_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is disenchant
        )
        self.game.move_batch_conflict_intent(
            self.bob.id, disenchant_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIs(animation.zone, Zone.GRAVEYARD)
        self.assertIs(ring.zone, Zone.BATTLEFIELD)
        self.assertNotIn(CardType.CREATURE, self.game.card_types(ring))

    def test_crusade_order_changes_drain_life_toughness_cap(self):
        knight = self.add_card(
            self.bob, PEARLED_UNICORN, Zone.BATTLEFIELD
        )
        crusade = self.add_card(
            self.bob, CRUSADE, Zone.BATTLEFIELD
        )
        self.queue_spell(
            self.alice, DRAIN_LIFE, knight, 1, x_value=5
        )
        disenchant = self.queue_spell(
            self.bob, DISENCHANT, crusade, 2
        )

        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(choice.conflict.kind.value, "characteristics")
        self.assertEqual(self.alice.life, 23)

    def test_removing_crusade_first_lowers_drain_life_cap(self):
        creature = self.add_card(
            self.bob, PEARLED_UNICORN, Zone.BATTLEFIELD
        )
        crusade = self.add_card(
            self.bob, CRUSADE, Zone.BATTLEFIELD
        )
        self.queue_spell(
            self.alice, DRAIN_LIFE, creature, 1, x_value=5
        )
        disenchant = self.queue_spell(
            self.bob, DISENCHANT, crusade, 2
        )
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        disenchant_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is disenchant
        )

        self.game.move_batch_conflict_intent(
            self.bob.id, disenchant_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertEqual(self.alice.life, 22)

    def test_balance_counts_kormus_swamps_at_its_ordered_position(self):
        bell = self.add_card(self.alice, KORMUS_BELL, Zone.BATTLEFIELD)
        swamps = (
            self.add_card(self.alice, SWAMP, Zone.BATTLEFIELD),
            self.add_card(self.alice, SWAMP, Zone.BATTLEFIELD),
        )
        self.add_card(self.bob, FOREST, Zone.BATTLEFIELD)
        self.add_card(self.bob, FOREST, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, BALANCE, None, 1)
        self.queue_spell(self.bob, DISENCHANT, bell, 2)

        self.game._resolve_batch()
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIsNotNone(self.game.pending_balance)
        choice = self.game.pending_balance.current_choice
        self.assertEqual(choice.category, "creature")
        self.assertEqual(choice.amount, 2)
        self.assertEqual(choice.candidate_ids, frozenset(card.id for card in swamps))

    def test_removing_kormus_before_balance_avoids_double_counting(self):
        bell = self.add_card(self.alice, KORMUS_BELL, Zone.BATTLEFIELD)
        self.add_card(self.alice, SWAMP, Zone.BATTLEFIELD)
        self.add_card(self.alice, SWAMP, Zone.BATTLEFIELD)
        self.add_card(self.bob, FOREST, Zone.BATTLEFIELD)
        self.add_card(self.bob, FOREST, Zone.BATTLEFIELD)
        self.queue_spell(self.alice, BALANCE, None, 1)
        disenchant = self.queue_spell(self.bob, DISENCHANT, bell, 2)
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        disenchant_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is disenchant
        )

        self.game.move_batch_conflict_intent(
            self.bob.id, disenchant_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertIsNone(self.game.pending_balance)
        self.assertIs(bell.zone, Zone.GRAVEYARD)

    def test_tapping_kormus_before_earthquake_stops_its_animation(self):
        bell = self.add_card(self.bob, KORMUS_BELL, Zone.BATTLEFIELD)
        swamp = self.add_card(self.bob, SWAMP, Zone.BATTLEFIELD)
        self.queue_spell(
            self.alice, EARTHQUAKE, None, 1, x_value=1
        )
        twiddle = self.queue_spell(
            self.bob, TWIDDLE, bell, 2, chosen_mode="Tap"
        )
        self.game._resolve_batch()
        choice = self.game.pending_batch_conflict_choices[0]
        twiddle_index = next(
            index
            for index in choice.intent_indexes_first_to_last
            if self.game.pending_batch_resolution.intents[index].source
            is twiddle
        )

        self.game.move_batch_conflict_intent(
            self.bob.id, twiddle_index, -1
        )
        self.game.confirm_batch_conflict_order(self.bob.id)

        self.assertTrue(bell.tapped)
        self.assertIs(swamp.zone, Zone.BATTLEFIELD)
        self.assertEqual(swamp.damage, 0)

    def test_target_legality_stays_frozen_when_animation_is_removed(self):
        ring = self.add_card(self.bob, SOL_RING, Zone.BATTLEFIELD)
        animation = self.add_card(
            self.bob, ANIMATE_ARTIFACT, Zone.BATTLEFIELD
        )
        animation.enchanted_card_id = ring.id
        self.queue_spell(self.alice, LIGHTNING_BOLT, ring, 1)
        self.queue_spell(self.bob, DISENCHANT, animation, 2)

        self.game._resolve_batch()

        self.assertFalse(self.game.pending_batch_conflict_choices)
        self.assertIs(ring.zone, Zone.GRAVEYARD)
        self.assertIs(animation.zone, Zone.GRAVEYARD)


if __name__ == "__main__":
    unittest.main()
