import unittest

from beta_magic import (
    DISINTEGRATE,
    FIREBREATHING,
    GRIZZLY_BEARS,
    LIGHTNING_BOLT,
    SUNGLASSES_OF_URZA,
    Card,
    CardDefinition,
    CardType,
    GameState,
    ManaCost,
    PlayerState,
    TurnPhase,
    UpkeepCostEffect,
    UpkeepFailure,
    Zone,
)


class SunglassesOfUrzaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 30
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 30
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player: PlayerState, definition, *, attached=None) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
        )
        card.enchanted_card_id = attached.id if attached is not None else None
        player.battlefield.append(card)
        return card

    def install_sunglasses(self) -> Card:
        return self.permanent(self.alice, SUNGLASSES_OF_URZA)

    def resolve_stack(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self) -> None:
        self.assertEqual(SUNGLASSES_OF_URZA.mana_cost.compact, "3")
        self.assertEqual(
            SUNGLASSES_OF_URZA.card_types, frozenset({CardType.ARTIFACT})
        )
        effect = SUNGLASSES_OF_URZA.mana_payment_effects[0]
        self.assertEqual(
            (effect.source_color.value, effect.paid_as_color.value), ("W", "R")
        )

    def test_white_mana_casts_a_red_spell(self) -> None:
        self.install_sunglasses()
        bolt = Card(LIGHTNING_BOLT, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(bolt)
        self.alice.mana_pool.white = 1

        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.bob,))
        self.resolve_stack()

        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertEqual(self.bob.life, 17)

    def test_white_mana_pays_for_a_red_activated_ability(self) -> None:
        self.install_sunglasses()
        bear = self.permanent(self.alice, GRIZZLY_BEARS)
        firebreathing = self.permanent(
            self.alice, FIREBREATHING, attached=bear
        )
        self.alice.mana_pool.white = 1

        self.game.activate_ability(self.alice.id, firebreathing, 0)
        self.resolve_stack()

        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertEqual(self.game.creature_power(bear), 3)

    def test_white_mana_counts_for_x_affordability(self) -> None:
        self.install_sunglasses()
        spell = Card(DISINTEGRATE, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(spell)
        self.alice.mana_pool.white = 1
        self.alice.mana_pool.colorless = 4

        self.assertEqual(self.game.maximum_affordable_x(spell), 4)

    def test_white_mana_can_pay_a_red_upkeep_cost(self) -> None:
        upkeep_card = CardDefinition(
            name="Test Red Upkeep",
            card_types=frozenset({CardType.CREATURE}),
            mana_cost=ManaCost.parse("{1}"),
            power=1,
            toughness=1,
            upkeep_effects=(
                UpkeepCostEffect(
                    ManaCost.parse("{R}"), UpkeepFailure.DESTROY_SOURCE
                ),
            ),
        )
        self.install_sunglasses()
        source = self.permanent(self.alice, upkeep_card)
        self.alice.mana_pool.white = 1
        self.game._enter_phase(TurnPhase.UPKEEP)

        self.assertTrue(self.game.can_pay_upkeep_cost(self.alice.id))
        self.game.choose_upkeep_payment(self.alice.id, pay=True)

        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertIn(source, self.alice.battlefield)

    def test_tapped_sunglasses_have_no_effect(self) -> None:
        sunglasses = self.install_sunglasses()
        sunglasses.tapped = True
        self.alice.mana_pool.white = 1

        self.assertFalse(
            self.game.can_pay_mana(self.alice, ManaCost.parse("{R}"))
        )

    def test_only_the_controller_gets_the_payment_option(self) -> None:
        self.install_sunglasses()
        self.alice.mana_pool.white = 1
        self.bob.mana_pool.white = 1

        self.assertTrue(
            self.game.can_pay_mana(self.alice, ManaCost.parse("{R}"))
        )
        self.assertFalse(
            self.game.can_pay_mana(self.bob, ManaCost.parse("{R}"))
        )

    def test_white_still_pays_white_and_generic_requirements(self) -> None:
        self.install_sunglasses()
        self.alice.mana_pool.white = 3

        self.game.pay_mana(self.alice, ManaCost.parse("{1}{W}{R}"))

        self.assertEqual(self.alice.mana_pool.total, 0)


if __name__ == "__main__":
    unittest.main()
