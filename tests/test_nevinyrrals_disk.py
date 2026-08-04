import unittest

from beta_magic import (
    ANIMATE_ARTIFACT,
    HOLY_STRENGTH,
    ISLAND,
    NEVINYRRALS_DISK,
    SOL_RING,
    WALL_OF_BONE,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS


class NevinyrralsDiskTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [ISLAND] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [ISLAND] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player: PlayerState, definition, *, attached_to=None) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            enchanted_card_id=attached_to.id if attached_to is not None else None,
        )
        player.battlefield.append(card)
        return card

    def pass_until_destruction_window(self) -> None:
        while self.game.pending_destruction is None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def finish_destruction(self) -> None:
        while self.game.pending_destruction is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition_begins_tapped_and_has_the_printed_costs(self) -> None:
        self.assertEqual(NEVINYRRALS_DISK.mana_cost.compact, "4")
        self.assertTrue(NEVINYRRALS_DISK.enters_tapped)
        ability = NEVINYRRALS_DISK.activated_abilities[0]
        self.assertEqual(ability.mana_cost.compact, "1")
        self.assertTrue(ability.tap_cost)

    def test_cast_disk_enters_tapped_and_cannot_immediately_activate(self) -> None:
        disk = Card(NEVINYRRALS_DISK, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(disk)
        self.alice.mana_pool.colorless = 5

        self.game.begin_cast(disk)
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.assertEqual(disk.zone, Zone.BATTLEFIELD)
        self.assertTrue(disk.tapped)
        with self.assertRaisesRegex(RuntimeError, "already tapped"):
            self.game.activate_ability(self.alice.id, disk, 0)

    def test_disk_destroys_matching_permanents_but_not_lands(self) -> None:
        disk = self.permanent(self.alice, NEVINYRRALS_DISK)
        creature = self.permanent(self.alice, GRIZZLY_BEARS)
        ring = self.permanent(self.bob, SOL_RING)
        enchantment = self.permanent(self.bob, HOLY_STRENGTH, attached_to=creature)
        land = self.permanent(self.bob, ISLAND)
        self.alice.mana_pool.colorless = 1
        self.game.pause_for_damage_windows = True

        self.game.activate_ability(self.alice.id, disk, 0)
        self.assertTrue(disk.tapped)
        self.pass_until_destruction_window()
        self.finish_destruction()

        self.assertEqual(
            {disk.zone, creature.zone, ring.zone, enchantment.zone},
            {Zone.GRAVEYARD},
        )
        self.assertEqual(land.zone, Zone.BATTLEFIELD)

    def test_regenerated_creature_survives_but_its_aura_does_not(self) -> None:
        disk = self.permanent(self.alice, NEVINYRRALS_DISK)
        wall = self.permanent(self.bob, WALL_OF_BONE)
        aura = self.permanent(self.bob, HOLY_STRENGTH, attached_to=wall)
        self.alice.mana_pool.colorless = 1
        self.bob.mana_pool.black = 1
        self.game.pause_for_damage_windows = True

        self.game.activate_ability(self.alice.id, disk, 0)
        self.pass_until_destruction_window()
        while self.game.players[self.game.priority_player_index] is not self.bob:
            self.game.pass_priority(self.alice.id)
        self.game.activate_ability(self.bob.id, wall, 0)
        self.finish_destruction()

        self.assertEqual(wall.zone, Zone.BATTLEFIELD)
        self.assertTrue(wall.tapped)
        self.assertEqual(aura.zone, Zone.GRAVEYARD)
        self.assertEqual(disk.zone, Zone.GRAVEYARD)

    def test_animated_artifact_is_only_listed_once(self) -> None:
        disk = self.permanent(self.alice, NEVINYRRALS_DISK)
        ring = self.permanent(self.bob, SOL_RING)
        self.permanent(self.bob, ANIMATE_ARTIFACT, attached_to=ring)
        self.alice.mana_pool.colorless = 1
        self.game.pause_for_damage_windows = True

        self.game.activate_ability(self.alice.id, disk, 0)
        self.pass_until_destruction_window()

        incident = self.game.pending_destruction
        self.assertIsNotNone(incident)
        self.assertEqual(
            sum(target.card_id == ring.id for target in incident.targets), 1
        )


if __name__ == "__main__":
    unittest.main()
