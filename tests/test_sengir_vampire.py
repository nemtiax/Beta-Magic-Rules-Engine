import unittest

from beta_magic import (
    DamageIncidentKind,
    GameState,
    KeywordAbility,
    PlayerState,
    SENGIR_VAMPIRE,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS, HILL_GIANT
from beta_magic.cards import Card


class SengirVampireTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 20
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        self.sengir = self.put_in_play(self.alice, SENGIR_VAMPIRE)

    @staticmethod
    def put_in_play(player: PlayerState, definition) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def test_definition(self) -> None:
        self.assertEqual(SENGIR_VAMPIRE.mana_cost.compact, "3BB")
        self.assertEqual((SENGIR_VAMPIRE.power, SENGIR_VAMPIRE.toughness), (4, 4))
        self.assertEqual(SENGIR_VAMPIRE.subtypes, ("Vampire",))
        self.assertIn(KeywordAbility.FLYING, SENGIR_VAMPIRE.abilities)
        self.assertTrue(SENGIR_VAMPIRE.grows_when_damaged_creature_dies)

    def test_counter_is_added_at_death_not_when_damage_is_dealt(self) -> None:
        giant = self.put_in_play(self.bob, HILL_GIANT)

        self.game._deal_damage(
            giant, 1, self.sengir.name, source_card=self.sengir
        )
        self.assertEqual(self.sengir.plus_one_counters, 0)

        self.game._put_creature_in_graveyard(giant)
        self.assertEqual(self.sengir.plus_one_counters, 1)

    def test_lethal_damage_awards_counter_after_creature_reaches_graveyard(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)

        self.game._deal_damage(
            bear, 2, self.sengir.name, source_card=self.sengir
        )

        self.assertIn(bear, self.bob.graveyard)
        self.assertEqual(self.sengir.plus_one_counters, 1)
        self.assertEqual(self.game.creature_power(self.sengir), 5)

    def test_prevented_damage_does_not_create_a_mark(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(
            bear, 1, self.sengir.name, source_card=self.sengir
        )
        self.game.pending_damage.packets[0].prevented = 1
        self.game._resolve_damage_incident()

        self.game._put_creature_in_graveyard(bear)

        self.assertEqual(self.sengir.plus_one_counters, 0)

    def test_unrelated_creature_death_does_not_award_counter(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)

        self.game._put_creature_in_graveyard(bear)

        self.assertEqual(self.sengir.plus_one_counters, 0)

    def test_removed_creature_does_not_award_counter(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.game._deal_damage(
            bear, 1, self.sengir.name, source_card=self.sengir
        )

        self.game._move_card(bear, Zone.EXILE)

        self.assertEqual(self.sengir.plus_one_counters, 0)

    def test_vampire_that_dies_simultaneously_gets_no_counter(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.game._begin_damage_incident(DamageIncidentKind.COMBAT)
        self.game._deal_damage(
            bear, 2, self.sengir.name, source_card=self.sengir, combat=True
        )
        self.game._deal_damage(
            self.sengir, 4, bear.name, source_card=bear, combat=True
        )

        self.game._resolve_damage_incident()

        self.assertIn(self.sengir, self.alice.graveyard)
        self.assertIn(bear, self.bob.graveyard)
        self.assertEqual(self.sengir.plus_one_counters, 0)

    def test_regenerated_vampire_survives_and_gets_counter(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.game._begin_damage_incident(DamageIncidentKind.COMBAT)
        self.game._deal_damage(
            bear, 2, self.sengir.name, source_card=self.sengir, combat=True
        )
        self.game._deal_damage(
            self.sengir, 4, bear.name, source_card=bear, combat=True
        )
        self.game.pending_damage.regenerated_card_ids.add(self.sengir.id)

        self.game._resolve_damage_incident()

        self.assertIn(self.sengir, self.alice.battlefield)
        self.assertIn(bear, self.bob.graveyard)
        self.assertEqual(self.sengir.plus_one_counters, 1)


if __name__ == "__main__":
    unittest.main()
