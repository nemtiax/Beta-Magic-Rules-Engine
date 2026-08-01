import unittest

from beta_magic import (
    CREATURE_BOND,
    ICY_MANIPULATOR,
    PSYCHIC_VENOM,
    Card,
    ContinuousEffect,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS, ISLAND


class TriggeredDamageAuraTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "a", "Alice", [GRIZZLY_BEARS] * 24
        )
        self.bob = PlayerState.with_deck(
            "b", "Bob", [GRIZZLY_BEARS] * 24
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition, *, attached=None, owner_id=None):
        card = Card(
            definition,
            owner_id=owner_id or player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
            enchanted_card_id=attached.id if attached else None,
        )
        player.battlefield.append(card)
        return card

    def pass_current_window(self) -> None:
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def resolve_batch(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_creature_bond_uses_toughness_when_creature_is_destroyed(self):
        creature = self.permanent(self.bob, GRIZZLY_BEARS)
        bond = self.permanent(self.alice, CREATURE_BOND, attached=creature)
        self.game.temporary_creature_effects[creature.id] = [
            ContinuousEffect(toughness=2)
        ]

        self.game.put_permanent_in_graveyard(creature)

        self.assertEqual(self.bob.life, 20)
        self.assertEqual(len(self.game.event_opportunities), 1)
        self.assertEqual(bond.zone, Zone.GRAVEYARD)
        self.pass_current_window()
        self.assertEqual(self.bob.life, 16)

    def test_creature_bond_damages_controller_not_owner(self):
        creature = self.permanent(
            self.alice, GRIZZLY_BEARS, owner_id=self.bob.id
        )
        self.permanent(self.bob, CREATURE_BOND, attached=creature)

        self.game.put_permanent_in_graveyard(creature)
        self.pass_current_window()

        self.assertEqual(self.alice.life, 18)
        self.assertEqual(self.bob.life, 20)

    def test_creature_bond_does_not_trigger_when_creature_is_exiled(self):
        creature = self.permanent(self.bob, GRIZZLY_BEARS)
        self.permanent(self.alice, CREATURE_BOND, attached=creature)

        self.game.move_card(creature, Zone.EXILE)

        self.assertEqual(self.game.event_opportunities, [])
        self.assertEqual(self.bob.life, 20)

    def test_psychic_venom_triggers_when_land_is_tapped_for_mana(self):
        land = self.permanent(self.bob, ISLAND)
        self.permanent(self.alice, PSYCHIC_VENOM, attached=land)

        self.game.activate_ability(self.bob.id, land, 0)

        self.assertEqual(self.bob.mana_pool.blue, 1)
        self.assertEqual(self.bob.life, 20)
        self.assertEqual(len(self.game.event_opportunities), 1)
        self.pass_current_window()
        self.assertEqual(self.bob.life, 18)

    def test_psychic_venom_triggers_when_icy_taps_land(self):
        land = self.permanent(self.bob, ISLAND)
        self.permanent(self.alice, PSYCHIC_VENOM, attached=land)
        icy = self.permanent(self.alice, ICY_MANIPULATOR)
        self.alice.mana_pool.colorless = 1

        self.game.activate_ability(self.alice.id, icy, 0)
        self.game.complete_pending_activation((land,))
        self.resolve_batch()

        self.assertTrue(land.tapped)
        self.assertEqual(len(self.game.event_opportunities), 1)
        self.pass_current_window()
        self.assertEqual(self.bob.life, 18)

    def test_tapping_an_already_tapped_land_does_not_trigger_again(self):
        land = self.permanent(self.bob, ISLAND)
        self.permanent(self.alice, PSYCHIC_VENOM, attached=land)
        land.tapped = True

        self.assertFalse(self.game._tap_permanent(land))
        self.assertEqual(self.game.event_opportunities, [])


if __name__ == "__main__":
    unittest.main()
