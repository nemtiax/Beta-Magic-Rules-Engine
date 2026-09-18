import unittest

from beta_magic.card_defs.lands import (
    BADLANDS,
    FOREST,
    MOUNTAIN,
)
from beta_magic.card_defs.black import EVIL_PRESENCE
from beta_magic.card_defs.artifacts import (
    GAUNTLET_OF_MIGHT,
    MOX_RUBY,
)
from beta_magic.card_defs.red import MANA_FLARE
from beta_magic.card_defs.green import WILD_GROWTH
from beta_magic import (
    Card,
    Color,
    GameState,
    ManaCost,
    ManaPool,
    PlayerState,
    TurnPhase,
    Zone,
)


class LandManaPlanningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [FOREST] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [MOUNTAIN] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def permanent(player, definition, *, attached_to=None):
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            entered_battlefield_turn=0,
            enchanted_card_id=attached_to.id if attached_to else None,
        )
        player.battlefield.append(card)
        return card

    def test_pool_exposes_each_valid_generic_payment_allocation(self) -> None:
        pool = ManaPool(red=1, green=1)

        plans = pool.payment_plans(ManaCost(generic=1))

        self.assertEqual(len(plans), 2)
        self.assertEqual(
            {(plan.amount(Color.RED), plan.amount(Color.GREEN)) for plan in plans},
            {(1, 0), (0, 1)},
        )

    def test_planner_uses_dual_land_modes_but_not_mana_artifacts(self) -> None:
        badlands = self.permanent(self.alice, BADLANDS)
        self.permanent(self.alice, MOX_RUBY)

        choices = self.game.land_mana_activations(self.alice.id)

        self.assertEqual({choice.land_id for choice in choices}, {badlands.id})
        self.assertEqual(
            {
                color
                for choice in choices
                for color in Color
                if choice.production.amount(color)
            },
            {Color.BLACK, Color.RED},
        )
        self.assertTrue(
            self.game.can_pay_mana_with_lands(
                self.alice.id, ManaCost.parse("{B}")
            )
        )

        badlands.tapped = True
        self.assertFalse(
            self.game.can_pay_mana_with_lands(
                self.alice.id, ManaCost.parse("{R}")
            )
        )

    def test_planner_counts_wild_growth_and_mana_flare(self) -> None:
        forest = self.permanent(self.alice, FOREST)
        self.permanent(self.alice, WILD_GROWTH, attached_to=forest)
        self.permanent(self.bob, MANA_FLARE)

        option = self.game.land_mana_activations(self.alice.id)[0]

        self.assertEqual(option.production.amount(Color.GREEN), 3)
        self.assertTrue(
            self.game.can_pay_mana_with_lands(
                self.alice.id, ManaCost.parse("{2}{G}")
            )
        )

    def test_planner_uses_current_land_type_and_gauntlet_mana(self) -> None:
        converted = self.permanent(self.alice, FOREST)
        self.permanent(self.bob, EVIL_PRESENCE, attached_to=converted)
        mountain = self.permanent(self.alice, MOUNTAIN)
        self.permanent(self.bob, GAUNTLET_OF_MIGHT)

        options = self.game.land_mana_activations(self.alice.id)
        converted_option = next(
            option for option in options if option.land_id == converted.id
        )
        mountain_option = next(
            option for option in options if option.land_id == mountain.id
        )

        self.assertEqual(converted_option.production.amount(Color.BLACK), 1)
        self.assertEqual(converted_option.production.amount(Color.GREEN), 0)
        self.assertEqual(mountain_option.production.amount(Color.RED), 2)

    def test_exact_payment_rejects_wild_growth_land_when_plain_land_works(self) -> None:
        plain = self.permanent(self.alice, FOREST)
        enchanted = self.permanent(self.alice, FOREST)
        self.permanent(self.alice, WILD_GROWTH, attached_to=enchanted)
        options = self.game.land_mana_activations(self.alice.id)
        by_land = {option.land_id: option for option in options}

        exact = self.game.plan_land_mana_payment(
            self.alice.id,
            ManaCost.parse("{G}"),
            ((plain.id, by_land[plain.id].ability_index),),
            require_exact_when_available=True,
        )
        self.assertTrue(exact.exact)

        with self.assertRaisesRegex(ValueError, "exact land-mana payment"):
            self.game.plan_land_mana_payment(
                self.alice.id,
                ManaCost.parse("{G}"),
                ((enchanted.id, by_land[enchanted.id].ability_index),),
                require_exact_when_available=True,
            )

        plain.tapped = True
        overproducing = self.game.plan_land_mana_payment(
            self.alice.id,
            ManaCost.parse("{G}"),
            ((enchanted.id, by_land[enchanted.id].ability_index),),
            require_exact_when_available=True,
        )
        self.assertFalse(overproducing.exact)
        self.assertEqual(overproducing.excess_production, 1)

    def test_existing_pool_can_remain_while_new_land_mana_is_spent_exactly(self) -> None:
        mountain = self.permanent(self.alice, MOUNTAIN)
        self.alice.mana_pool.green = 1
        option = self.game.land_mana_activations(self.alice.id)[0]

        plan = self.game.plan_land_mana_payment(
            self.alice.id,
            ManaCost.parse("{R}"),
            ((mountain.id, option.ability_index),),
            require_exact_when_available=True,
        )

        self.assertTrue(plan.exact)
        self.assertEqual(plan.spending.amount(Color.RED), 1)
        self.assertEqual(plan.spending.amount(Color.GREEN), 0)


if __name__ == "__main__":
    unittest.main()
