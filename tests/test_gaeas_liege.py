import unittest

from beta_magic import (
    BAYOU,
    EVIL_PRESENCE,
    FOREST,
    GAEAS_LIEGE,
    ISLAND,
    MOUNTAIN,
    Card,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class GaeasLiegeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [MOUNTAIN] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition, *, attached_to=None, sequence=0):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
            battlefield_entry_sequence=sequence,
            enchanted_card_id=attached_to.id if attached_to else None,
        )
        player.battlefield.append(card)
        return card

    def resolve_batch(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def convert(self, liege, land) -> None:
        self.game.activate_ability(liege.controller_id, liege, 0)
        self.game.complete_pending_activation((land,))
        self.resolve_batch()

    def test_definition(self) -> None:
        self.assertEqual(GAEAS_LIEGE.mana_cost.compact, "3GGG")
        self.assertEqual(GAEAS_LIEGE.subtypes, ("Avatar",))
        self.assertEqual(GAEAS_LIEGE.activated_abilities[0].replacement_subtype, "Forest")

    def test_defending_stats_count_controllers_current_forests(self) -> None:
        liege = self.permanent(self.alice, GAEAS_LIEGE)
        self.permanent(self.alice, FOREST)
        self.permanent(self.alice, BAYOU)
        self.permanent(self.alice, MOUNTAIN)
        self.permanent(self.bob, FOREST)

        self.assertEqual(
            (self.game.creature_power(liege), self.game.creature_toughness(liege)),
            (2, 2),
        )

    def test_attacking_stats_count_defending_players_forests(self) -> None:
        liege = self.permanent(self.alice, GAEAS_LIEGE)
        self.permanent(self.alice, FOREST)
        for _ in range(3):
            self.permanent(self.bob, FOREST)

        self.game.begin_combat()
        self.game.declare_attackers([liege])
        self.assertEqual(
            (self.game.creature_power(liege), self.game.creature_toughness(liege)),
            (3, 3),
        )

        self.game._finish_combat_damage()
        self.assertEqual(
            (self.game.creature_power(liege), self.game.creature_toughness(liege)),
            (1, 1),
        )

    def test_damage_can_become_lethal_when_attack_ends(self) -> None:
        liege = self.permanent(self.alice, GAEAS_LIEGE)
        self.permanent(self.alice, FOREST)
        for _ in range(3):
            self.permanent(self.bob, FOREST)
        liege.damage = 2

        self.game.begin_combat()
        self.game.declare_attackers([liege])
        self.assertIn(liege, self.alice.battlefield)

        self.game._finish_combat_damage()
        self.assertEqual(liege.zone, Zone.GRAVEYARD)

    def test_tap_ability_changes_any_land_and_its_mana_ability(self) -> None:
        liege = self.permanent(self.alice, GAEAS_LIEGE)
        self.permanent(self.alice, FOREST)
        island = self.permanent(self.bob, ISLAND)

        self.convert(liege, island)

        self.assertTrue(liege.tapped)
        self.assertEqual(self.game.land_subtypes(island), ("Forest",))
        abilities = self.game.activated_abilities(island)
        self.assertEqual([ability.color for ability in abilities], [Color.GREEN])

    def test_each_liege_independently_marks_the_same_land(self) -> None:
        first = self.permanent(self.alice, GAEAS_LIEGE)
        second = self.permanent(self.alice, GAEAS_LIEGE)
        self.permanent(self.alice, FOREST)
        island = self.permanent(self.bob, ISLAND)

        self.convert(first, island)
        self.game.priority_player_index = None
        self.convert(second, island)
        self.assertEqual(set(island.land_type_marks), {first.id, second.id})

        self.game.priority_player_index = None
        self.game.put_permanent_in_graveyard(first)
        self.assertEqual(self.game.land_subtypes(island), ("Forest",))
        self.assertEqual(set(island.land_type_marks), {second.id})

        self.game.priority_player_index = None
        self.game.put_permanent_in_graveyard(second)
        self.assertEqual(self.game.land_subtypes(island), ("Island",))
        self.assertEqual(island.land_type_marks, {})

    def test_land_forgets_marks_if_it_leaves_play(self) -> None:
        liege = self.permanent(self.alice, GAEAS_LIEGE)
        self.permanent(self.alice, FOREST)
        island = self.permanent(self.bob, ISLAND)
        self.convert(liege, island)
        self.game.priority_player_index = None

        self.game.put_permanent_in_graveyard(island)

        self.assertEqual(island.land_type_marks, {})

    def test_newest_local_land_type_change_wins(self) -> None:
        liege = self.permanent(self.alice, GAEAS_LIEGE)
        self.permanent(self.alice, FOREST)
        island = self.permanent(self.bob, ISLAND)
        self.convert(liege, island)
        self.game.priority_player_index = None

        self.game.battlefield_entry_sequence += 1
        self.permanent(
            self.alice,
            EVIL_PRESENCE,
            attached_to=island,
            sequence=self.game.battlefield_entry_sequence,
        )
        self.assertEqual(self.game.land_subtypes(island), ("Swamp",))

        liege.tapped = False
        self.convert(liege, island)
        self.assertEqual(self.game.land_subtypes(island), ("Forest",))


if __name__ == "__main__":
    unittest.main()
