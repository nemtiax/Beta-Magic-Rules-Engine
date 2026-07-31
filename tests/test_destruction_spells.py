import unittest

from beta_magic import (
    CRUSADE,
    DISENCHANT,
    HOLY_STRENGTH,
    LAND_DESTRUCTION_SPELLS,
    PERMANENT_DESTRUCTION_SPELLS,
    SHATTER,
    TERROR,
    TRANQUILITY,
    TUNNEL,
    WEAKNESS,
    CardType,
    DestructionIncident,
    DestructionResolutionStep,
    DestructionTarget,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import (
    GRIZZLY_BEARS,
    OBSIANUS_GOLEM,
    SAVANNAH_LIONS,
)
from beta_magic.card_defs import WALL_OF_BONE, WALL_OF_BRAMBLES


class PermanentDestructionSpellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 24
        )
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 24)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(player: PlayerState, definition=GRIZZLY_BEARS):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = player.id
        player.battlefield.append(card)
        return card

    @staticmethod
    def put_in_hand(player: PlayerState, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        player.hand.append(card)
        return card

    def cast(self, definition, target=None):
        spell = self.put_in_hand(self.alice, definition)
        self.alice.mana_pool.white = 10
        self.alice.mana_pool.red = 10
        self.alice.mana_pool.green = 10
        self.game.begin_cast(spell)
        if target is not None:
            self.game.complete_pending_cast((target,))
        self.resolve_stack()
        return spell

    def resolve_stack(self) -> None:
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_card_definitions(self) -> None:
        self.assertEqual(
            PERMANENT_DESTRUCTION_SPELLS,
            (DISENCHANT, SHATTER, TERROR, TUNNEL, TRANQUILITY)
            + LAND_DESTRUCTION_SPELLS,
        )
        self.assertEqual(DISENCHANT.mana_cost.compact, "1W")
        self.assertEqual(SHATTER.mana_cost.compact, "1R")
        self.assertEqual(TRANQUILITY.mana_cost.compact, "2G")
        self.assertIn(CardType.SORCERY, TRANQUILITY.card_types)
        self.assertEqual(TUNNEL.mana_cost.compact, "R")

    def test_tunnel_targets_only_walls(self) -> None:
        wall = self.put_in_play(self.bob, WALL_OF_BONE)
        creature = self.put_in_play(self.bob)
        spell = self.put_in_hand(self.alice, TUNNEL)

        self.assertEqual(self.game.legal_targets_for(spell), [wall])
        self.assertNotIn(creature, self.game.legal_targets_for(spell))

    def test_tunnel_destroys_a_wall_without_a_regeneration_window(self) -> None:
        self.game.pause_for_damage_windows = True
        wall = self.put_in_play(self.bob, WALL_OF_BRAMBLES)
        spell = self.put_in_hand(self.alice, TUNNEL)
        self.alice.mana_pool.red = 1
        self.bob.mana_pool.green = 1

        self.game.begin_cast(spell)
        self.game.complete_pending_cast((wall,))
        self.resolve_stack()

        self.assertIsNone(self.game.pending_damage)
        self.assertIsNone(self.game.pending_destruction)
        self.assertIn(wall, self.bob.graveyard)
        self.assertIn(spell, self.alice.graveyard)
        self.assertFalse(
            self.game.resolved_destruction_incidents[-1]
            .targets[0]
            .regeneration_allowed
        )

    def test_mixed_destruction_incident_only_allows_eligible_target_to_regenerate(
        self,
    ) -> None:
        eligible_wall = self.put_in_play(self.bob, WALL_OF_BONE)
        forbidden_wall = self.put_in_play(self.bob, WALL_OF_BRAMBLES)
        self.game.pending_destruction = DestructionIncident(
            [
                DestructionTarget(
                    eligible_wall.id, eligible_wall.name, True
                ),
                DestructionTarget(
                    forbidden_wall.id, forbidden_wall.name, False
                ),
            ],
            step=DestructionResolutionStep.REGENERATION,
        )
        self.game.priority_player_index = 1
        self.bob.mana_pool.black = 1
        self.bob.mana_pool.green = 1

        self.assertTrue(
            self.game.can_activate_ability(self.bob.id, eligible_wall, 0)
        )
        self.assertFalse(
            self.game.can_activate_ability(self.bob.id, forbidden_wall, 0)
        )
        with self.assertRaisesRegex(RuntimeError, "cannot regenerate"):
            self.game.activate_ability(self.bob.id, forbidden_wall, 0)

    def test_disenchant_accepts_artifacts_and_enchantments_only(self) -> None:
        enchantment = self.put_in_play(self.bob, CRUSADE)
        artifact = self.put_in_play(self.bob, OBSIANUS_GOLEM)
        creature = self.put_in_play(self.bob)
        spell = self.put_in_hand(self.alice, DISENCHANT)

        self.assertEqual(
            set(self.game.legal_targets_for(spell)),
            {enchantment, artifact},
        )
        self.alice.mana_pool.white = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((enchantment,))
        self.resolve_stack()

        self.assertIn(enchantment, self.bob.graveyard)
        self.assertIn(spell, self.alice.graveyard)
        self.assertIn(artifact, self.bob.battlefield)
        self.assertIn(creature, self.bob.battlefield)

    def test_disenchant_removes_an_aura_without_removing_its_creature(self) -> None:
        bear = self.put_in_play(self.bob)
        aura = self.put_in_play(self.bob, HOLY_STRENGTH)
        aura.enchanted_card_id = bear.id

        spell = self.cast(DISENCHANT, aura)

        self.assertIn(aura, self.bob.graveyard)
        self.assertIsNone(aura.enchanted_card_id)
        self.assertIn(bear, self.bob.battlefield)
        self.assertEqual(
            (self.game.creature_power(bear), self.game.creature_toughness(bear)),
            (2, 2),
        )
        self.assertIn(spell, self.alice.graveyard)

    def test_destroy_effect_opens_only_a_regeneration_window(self) -> None:
        self.game.pause_for_damage_windows = True
        enchantment = self.put_in_play(self.bob, CRUSADE)
        spell = self.put_in_hand(self.alice, DISENCHANT)
        self.alice.mana_pool.white = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((enchantment,))
        self.resolve_stack()

        self.assertIsNone(self.game.pending_damage)
        self.assertEqual(
            self.game.pending_destruction.step,
            DestructionResolutionStep.REGENERATION,
        )
        self.assertIn(enchantment, self.bob.battlefield)

        self.game.pass_priority(self.alice.id)
        self.game.pass_priority(self.bob.id)
        self.assertIsNone(self.game.pending_destruction)
        self.assertIn(enchantment, self.bob.graveyard)

    def test_shatter_destroys_an_artifact_creature(self) -> None:
        golem = self.put_in_play(self.bob, OBSIANUS_GOLEM)
        enchantment = self.put_in_play(self.bob, CRUSADE)
        spell = self.put_in_hand(self.alice, SHATTER)
        self.assertEqual(self.game.legal_targets_for(spell), [golem])

        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = 1
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((golem,))
        self.resolve_stack()

        self.assertIn(golem, self.bob.graveyard)
        self.assertIn(enchantment, self.bob.battlefield)
        self.assertIn(spell, self.alice.graveyard)

    def test_tranquility_removes_global_and_local_enchantments_from_all_players(
        self,
    ) -> None:
        crusade = self.put_in_play(self.alice, CRUSADE)
        bear = self.put_in_play(self.bob)
        aura = self.put_in_play(self.bob, HOLY_STRENGTH)
        aura.enchanted_card_id = bear.id
        artifact = self.put_in_play(self.bob, OBSIANUS_GOLEM)

        spell = self.cast(TRANQUILITY)

        self.assertIn(crusade, self.alice.graveyard)
        self.assertIn(aura, self.bob.graveyard)
        self.assertIsNone(aura.enchanted_card_id)
        self.assertIn(bear, self.bob.battlefield)
        self.assertIn(artifact, self.bob.battlefield)
        self.assertIn(spell, self.alice.graveyard)
        self.assertFalse(
            any(
                CardType.ENCHANTMENT in card.definition.card_types
                for player in self.game.players
                for card in player.battlefield
            )
        )

    def test_tranquility_removes_all_enchantments_before_state_based_actions(
        self,
    ) -> None:
        lion = self.put_in_play(self.alice, SAVANNAH_LIONS)
        crusade = self.put_in_play(self.alice, CRUSADE)
        weakness = self.put_in_play(self.bob, WEAKNESS)
        weakness.enchanted_card_id = lion.id
        self.assertEqual(self.game.creature_toughness(lion), 1)

        self.cast(TRANQUILITY)

        self.assertIn(lion, self.alice.battlefield)
        self.assertIn(crusade, self.alice.graveyard)
        self.assertIn(weakness, self.bob.graveyard)
        self.assertEqual(self.game.creature_toughness(lion), 1)

    def test_tranquility_obeys_sorcery_timing(self) -> None:
        spell = self.put_in_hand(self.bob, TRANQUILITY)
        self.bob.mana_pool.green = 1
        self.bob.mana_pool.colorless = 2

        with self.assertRaisesRegex(RuntimeError, "active player"):
            self.game.begin_cast(spell)
