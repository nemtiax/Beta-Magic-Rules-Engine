import unittest

from beta_magic import (
    DRAIN_POWER,
    FOREST,
    ISLAND,
    MANA_FLARE,
    MANA_SHORT,
    TUNDRA,
    WILD_GROWTH,
    Card,
    CardType,
    Color,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS
from beta_magic.ui import GameViewModel


class DrainPowerTests(unittest.TestCase):
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

    @staticmethod
    def card(player, definition, zone=Zone.BATTLEFIELD, *, attached=None):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id if zone is Zone.BATTLEFIELD else None,
            zone=zone,
            entered_battlefield_turn=0 if zone is Zone.BATTLEFIELD else None,
        )
        card.enchanted_card_id = attached.id if attached is not None else None
        player.cards_in(zone).append(card)
        return card

    def begin_drain(self):
        spell = self.card(self.alice, DRAIN_POWER, Zone.HAND)
        self.alice.mana_pool.blue = 2
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((self.bob,))
        return spell

    def resolve_batch(self):
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definition(self) -> None:
        self.assertEqual(DRAIN_POWER.mana_cost.compact, "UU")
        self.assertEqual(DRAIN_POWER.card_types, frozenset({CardType.SORCERY}))
        self.assertTrue(DRAIN_POWER.target_requirement.players)
        self.assertTrue(DRAIN_POWER.target_requirement.opponent_only)
        effect = DRAIN_POWER.spell_effects[0]
        self.assertTrue(effect.transfer_to_caster)
        self.assertTrue(effect.produce_land_mana)

    def test_takes_pool_and_mana_from_each_untapped_basic_land(self) -> None:
        island = self.card(self.bob, ISLAND)
        forest = self.card(self.bob, FOREST)
        self.bob.mana_pool.red = 2
        spell = self.begin_drain()

        self.resolve_batch()

        self.assertTrue(island.tapped)
        self.assertTrue(forest.tapped)
        self.assertEqual(self.bob.mana_pool.total, 0)
        self.assertEqual(self.alice.mana_pool.blue, 1)
        self.assertEqual(self.alice.mana_pool.green, 1)
        self.assertEqual(self.alice.mana_pool.red, 2)
        self.assertIn(spell, self.alice.graveyard)

    def test_caster_chooses_which_color_an_untapped_dual_produces(self) -> None:
        tundra = self.card(self.bob, TUNDRA)
        self.begin_drain()

        self.resolve_batch()

        self.assertTrue(tundra.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)
        choice = self.game.pending_drain_power_choices[0]
        self.assertEqual(
            choice.mana_options,
            ((Color.WHITE, 1), (Color.BLUE, 1)),
        )
        with self.assertRaisesRegex(RuntimeError, "choose mana"):
            self.game.propose_phase_advance()

        self.game.choose_drain_power_mana(self.alice.id, Color.BLUE)

        self.assertEqual(self.alice.mana_pool.blue, 1)
        self.assertEqual(self.game.pending_drain_power_choices, [])

    def test_pre_tapped_dual_transfers_the_opponents_chosen_color(self) -> None:
        tundra = self.card(self.bob, TUNDRA)
        self.begin_drain()

        # Bob responds by taking white mana from Tundra before Drain Power.
        self.game.activate_ability(self.bob.id, tundra, 0)
        self.resolve_batch()

        self.assertEqual(self.game.pending_drain_power_choices, [])
        self.assertEqual(self.bob.mana_pool.total, 0)
        self.assertEqual(self.alice.mana_pool.white, 1)
        self.assertEqual(self.alice.mana_pool.blue, 0)

    def test_mana_flare_doubles_the_chosen_dual_land_color(self) -> None:
        self.card(self.alice, MANA_FLARE)
        self.card(self.bob, TUNDRA)
        self.begin_drain()
        self.resolve_batch()

        choice = self.game.pending_drain_power_choices[0]
        self.assertEqual(
            choice.mana_options,
            ((Color.WHITE, 2), (Color.BLUE, 2)),
        )
        self.game.choose_drain_power_mana(self.alice.id, Color.WHITE)
        self.assertEqual(self.alice.mana_pool.white, 2)

    def test_wild_growth_mana_is_also_transferred(self) -> None:
        forest = self.card(self.bob, FOREST)
        self.card(self.alice, WILD_GROWTH, attached=forest)
        self.begin_drain()

        self.resolve_batch()

        self.assertEqual(self.bob.mana_pool.total, 0)
        self.assertEqual(self.alice.mana_pool.green, 2)

    def test_mana_short_does_not_produce_mana_or_request_dual_choice(self) -> None:
        tundra = self.card(self.bob, TUNDRA)
        spell = self.card(self.alice, MANA_SHORT, Zone.HAND)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 2
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((self.bob,))

        self.resolve_batch()

        self.assertTrue(tundra.tapped)
        self.assertEqual(self.alice.mana_pool.total, 0)
        self.assertEqual(self.game.pending_drain_power_choices, [])

    def test_ui_exposes_choices_only_to_drain_power_caster(self) -> None:
        self.card(self.bob, TUNDRA)
        self.begin_drain()
        self.resolve_batch()
        view_model = GameViewModel(self.game)

        alice_state = view_model.state
        self.assertTrue(alice_state["drainPowerChoice"])
        self.assertTrue(alice_state["drainPowerCanChoose"])
        self.assertEqual(
            [choice["color"] for choice in alice_state["drainPowerManaChoices"]],
            ["W", "U"],
        )

        view_model.switchPerspective()
        bob_state = view_model.state
        self.assertFalse(bob_state["drainPowerCanChoose"])
        view_model.switchPerspective()
        view_model.chooseDrainPowerMana("W")
        self.assertFalse(view_model.state["drainPowerChoice"])


if __name__ == "__main__":
    unittest.main()
