import unittest

from beta_magic import (
    BAYOU,
    EVIL_PRESENCE,
    FOREST,
    HOLY_STRENGTH,
    KORMUS_BELL,
    LIVING_LANDS,
    SWAMP,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
    WEAKNESS,
)


class LandAnimationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [SWAMP] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition, *, attached_to=None, tapped=False):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            enchanted_card_id=attached_to.id if attached_to else None,
            tapped=tapped,
        )
        player.battlefield.append(card)
        return card

    def test_definitions_match_beta_characteristics(self) -> None:
        self.assertEqual(LIVING_LANDS.mana_cost.compact, "3G")
        self.assertEqual(KORMUS_BELL.mana_cost.compact, "4")
        self.assertEqual(LIVING_LANDS.continuous_effects[0].land_subtype, "Forest")
        self.assertEqual(KORMUS_BELL.continuous_effects[0].land_subtype, "Swamp")

    def test_living_lands_animates_forests_for_both_players_as_colorless_lands(self) -> None:
        self.permanent(self.alice, LIVING_LANDS)
        alice_forest = self.permanent(self.alice, FOREST)
        bob_bayou = self.permanent(self.bob, BAYOU)
        swamp = self.permanent(self.bob, SWAMP)

        for land in (alice_forest, bob_bayou):
            self.assertEqual(
                self.game.card_types(land),
                frozenset({CardType.LAND, CardType.CREATURE}),
            )
            self.assertEqual(
                (self.game.creature_power(land), self.game.creature_toughness(land)),
                (1, 1),
            )
            self.assertEqual(self.game.card_colors(land), frozenset())
        self.assertNotIn(CardType.CREATURE, self.game.card_types(swamp))

    def test_current_converted_land_type_controls_which_effect_animates_it(self) -> None:
        self.permanent(self.alice, LIVING_LANDS)
        self.permanent(self.bob, KORMUS_BELL)
        forest = self.permanent(self.alice, FOREST)
        self.permanent(self.bob, EVIL_PRESENCE, attached_to=forest)

        self.assertEqual(self.game.land_subtypes(forest), ("Swamp",))
        self.assertIn(CardType.CREATURE, self.game.card_types(forest))

        bell = next(card for card in self.bob.battlefield if card.name == "Kormus Bell")
        bell.tapped = True
        self.assertNotIn(CardType.CREATURE, self.game.card_types(forest))

    def test_tapped_kormus_bell_stops_and_untapped_bell_restarts_animation(self) -> None:
        bell = self.permanent(self.alice, KORMUS_BELL)
        swamp = self.permanent(self.alice, SWAMP)
        self.assertIn(CardType.CREATURE, self.game.card_types(swamp))

        bell.tapped = True
        self.assertNotIn(CardType.CREATURE, self.game.card_types(swamp))
        bell.tapped = False
        self.assertIn(CardType.CREATURE, self.game.card_types(swamp))

    def test_aura_remains_attached_and_reactivates_with_land(self) -> None:
        lands = self.permanent(self.alice, LIVING_LANDS)
        forest = self.permanent(self.alice, FOREST)
        aura = self.permanent(self.alice, HOLY_STRENGTH, attached_to=forest)
        self.assertEqual(
            (self.game.creature_power(forest), self.game.creature_toughness(forest)),
            (2, 3),
        )

        self.game.put_permanent_in_graveyard(lands)
        self.assertIn(aura, self.alice.battlefield)
        self.assertEqual(aura.enchanted_card_id, forest.id)
        self.assertNotIn(CardType.CREATURE, self.game.card_types(forest))

        self.permanent(self.alice, LIVING_LANDS)
        self.assertEqual(
            (self.game.creature_power(forest), self.game.creature_toughness(forest)),
            (2, 3),
        )

    def test_new_animated_land_can_make_mana_but_cannot_attack(self) -> None:
        self.permanent(self.alice, LIVING_LANDS)
        forest = self.permanent(self.alice, FOREST)
        forest.entered_battlefield_turn = self.game.turn_number

        self.game.activate_ability(self.alice.id, forest, 0)
        self.assertTrue(forest.tapped)
        self.assertEqual(self.alice.mana_pool.green, 1)

        forest.tapped = False
        self.game.begin_combat()
        with self.assertRaisesRegex(ValueError, "did not begin the turn"):
            self.game.declare_attackers([forest])

    def test_land_already_in_play_can_attack_when_animation_begins(self) -> None:
        forest = self.permanent(self.alice, FOREST)
        forest.entered_battlefield_turn = self.game.turn_number - 1
        self.permanent(self.alice, LIVING_LANDS)

        self.game.begin_combat()
        self.game.declare_attackers([forest])
        self.assertIn(forest, self.game.combat.attackers)

    def test_untapping_bell_stabilizes_newly_animated_lands(self) -> None:
        bell = self.permanent(self.bob, KORMUS_BELL, tapped=True)
        swamp = self.permanent(self.bob, SWAMP)
        self.permanent(self.alice, WEAKNESS, attached_to=swamp)

        while self.game.current_phase is not TurnPhase.END:
            self.game.advance_phase()
        self.game.advance_phase()

        self.assertFalse(bell.tapped)
        self.assertEqual(swamp.zone, Zone.GRAVEYARD)


if __name__ == "__main__":
    unittest.main()
