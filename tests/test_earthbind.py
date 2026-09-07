import unittest

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.blue import AIR_ELEMENTAL, FLIGHT
from beta_magic.card_defs.green import GRIZZLY_BEARS
from beta_magic.card_defs.red import EARTHBIND
from beta_magic.types import KeywordAbility


class EarthbindTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState("a", "Alice")
        self.bob = PlayerState("b", "Bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    def permanent(self, player, definition, *, attached=None):
        self.game.battlefield_entry_sequence += 1
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            enchanted_card_id=attached.id if attached else None,
            battlefield_entry_sequence=self.game.battlefield_entry_sequence,
        )
        player.battlefield.append(card)
        return card

    def in_hand(self, definition):
        card = Card(definition, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(card)
        return card

    def resolve_cast(self, card, target):
        self.game.begin_cast(card)
        self.game.complete_pending_cast((target,))
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

    def test_only_currently_flying_creatures_are_legal_targets(self) -> None:
        flyer = self.permanent(self.bob, AIR_ELEMENTAL)
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        earthbind = self.in_hand(EARTHBIND)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(earthbind)
        self.assertIn(flyer, self.game.legal_targets_for())
        self.assertNotIn(bear, self.game.legal_targets_for())

    def test_granted_flying_makes_creature_a_legal_target(self) -> None:
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.permanent(self.bob, FLIGHT, attached=bear)
        earthbind = self.in_hand(EARTHBIND)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(earthbind)
        self.assertIn(bear, self.game.legal_targets_for())

    def test_resolution_deals_two_damage_and_removes_flying(self) -> None:
        flyer = self.permanent(self.bob, AIR_ELEMENTAL)
        earthbind = self.in_hand(EARTHBIND)
        self.alice.mana_pool.red = 1
        self.resolve_cast(earthbind, flyer)
        self.assertEqual(flyer.damage, 2)
        self.assertNotIn(KeywordAbility.FLYING, self.game.creature_abilities(flyer))
        self.assertEqual(earthbind.enchanted_card_id, flyer.id)

    def test_earthbind_remains_after_it_removes_flying(self) -> None:
        flyer = self.permanent(self.bob, AIR_ELEMENTAL)
        earthbind = self.permanent(self.alice, EARTHBIND, attached=flyer)
        self.game.check_state_based_actions()
        self.assertEqual(earthbind.zone, Zone.BATTLEFIELD)
        self.assertNotIn(KeywordAbility.FLYING, self.game.creature_abilities(flyer))

    def test_later_flight_overrides_earthbind(self) -> None:
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        earthbind = self.permanent(self.alice, EARTHBIND, attached=bear)
        self.permanent(self.bob, FLIGHT, attached=bear)
        self.assertIn(KeywordAbility.FLYING, self.game.creature_abilities(bear))
        self.assertEqual(earthbind.zone, Zone.BATTLEFIELD)

    def test_later_earthbind_overrides_flight(self) -> None:
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.permanent(self.bob, FLIGHT, attached=bear)
        self.permanent(self.alice, EARTHBIND, attached=bear)
        self.assertNotIn(KeywordAbility.FLYING, self.game.creature_abilities(bear))


if __name__ == "__main__":
    unittest.main()
