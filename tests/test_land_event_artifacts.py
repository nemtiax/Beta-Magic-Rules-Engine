import unittest

from beta_magic import (
    ANKH_OF_MISHRA,
    ARMAGEDDON,
    DINGUS_EGG,
    STONE_RAIN,
    Card,
    DestructionIncident,
    DestructionResolutionStep,
    DestructionTarget,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS, MOUNTAIN, PLAINS


class LandEventArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "a", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck(
            "b", "Bob", [GRIZZLY_BEARS] * 20
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def card(player, definition, zone):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id if zone is Zone.BATTLEFIELD else None,
            base_controller_id=(player.id if zone is Zone.BATTLEFIELD else None),
            zone=zone,
            entered_battlefield_turn=0 if zone is Zone.BATTLEFIELD else None,
        )
        player.cards_in(zone).append(card)
        return card

    def pass_current_window(self) -> None:
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def resolve_all(self) -> None:
        while (
            self.game.stack
            or self.game.batch_abilities
            or self.game.event_opportunities
            or self.game.pending_damage
            or self.game.pending_destruction
        ):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_ankh_waits_for_responses_then_damages_land_player(self):
        self.card(self.bob, ANKH_OF_MISHRA, Zone.BATTLEFIELD)
        land = self.card(self.alice, PLAINS, Zone.HAND)

        self.game.play_land(land)

        self.assertEqual(self.alice.life, 20)
        self.assertEqual(len(self.game.event_opportunities), 1)
        self.pass_current_window()
        self.assertEqual(self.alice.life, 18)

    def test_multiple_ankhs_each_trigger(self):
        self.card(self.alice, ANKH_OF_MISHRA, Zone.BATTLEFIELD)
        self.card(self.bob, ANKH_OF_MISHRA, Zone.BATTLEFIELD)
        land = self.card(self.alice, MOUNTAIN, Zone.HAND)

        self.game.play_land(land)
        self.assertEqual(len(self.game.event_opportunities), 2)
        self.pass_current_window()
        self.assertEqual(self.alice.life, 16)

    def test_dingus_egg_triggers_after_land_destruction_resolves(self):
        self.card(self.bob, DINGUS_EGG, Zone.BATTLEFIELD)
        land = self.card(self.bob, PLAINS, Zone.BATTLEFIELD)
        rain = self.card(self.alice, STONE_RAIN, Zone.HAND)
        self.alice.mana_pool.red = 1
        self.alice.mana_pool.colorless = 2
        self.game.begin_cast(rain)
        self.game.complete_pending_cast((land,))

        self.resolve_all()

        self.assertEqual(land.zone, Zone.GRAVEYARD)
        self.assertEqual(self.bob.life, 18)

    def test_each_land_lost_to_armageddon_deals_two_to_its_controller(self):
        self.card(self.alice, DINGUS_EGG, Zone.BATTLEFIELD)
        self.card(self.alice, PLAINS, Zone.BATTLEFIELD)
        self.card(self.alice, MOUNTAIN, Zone.BATTLEFIELD)
        self.card(self.bob, PLAINS, Zone.BATTLEFIELD)
        armageddon = self.card(self.alice, ARMAGEDDON, Zone.HAND)
        self.alice.mana_pool.white = 2
        self.alice.mana_pool.colorless = 2
        self.game.begin_cast(armageddon)

        self.resolve_all()

        self.assertEqual(self.alice.life, 16)
        self.assertEqual(self.bob.life, 18)

    def test_land_returned_to_hand_does_not_trigger_dingus_egg(self):
        self.card(self.alice, DINGUS_EGG, Zone.BATTLEFIELD)
        land = self.card(self.bob, PLAINS, Zone.BATTLEFIELD)

        self.game.move_card(land, Zone.HAND)

        self.assertEqual(self.game.event_opportunities, [])
        self.assertEqual(self.bob.life, 20)

    def test_regenerated_land_was_not_lost(self):
        self.card(self.alice, DINGUS_EGG, Zone.BATTLEFIELD)
        land = self.card(self.bob, PLAINS, Zone.BATTLEFIELD)
        incident = DestructionIncident(
            [DestructionTarget(land.id, land.name)]
        )
        incident.step = DestructionResolutionStep.REGENERATION
        incident.regenerated_card_ids.add(land.id)
        self.game.pending_destruction = incident

        self.game._finish_destruction_incident()

        self.assertEqual(land.zone, Zone.BATTLEFIELD)
        self.assertEqual(self.game.event_opportunities, [])


if __name__ == "__main__":
    unittest.main()
