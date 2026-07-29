import unittest

from beta_magic import (
    DRUDGE_SKELETONS,
    ELVISH_ARCHERS,
    MOUNTAIN,
    REGENERATION_CREATURES,
    ROYAL_ASSASSIN,
    SWAMP,
    UTHDEN_TROLL,
    WALL_OF_BONE,
    WALL_OF_BRAMBLES,
    WILL_O_THE_WISP,
    Card,
    DamageResolutionStep,
    GameState,
    KeywordAbility,
    PlayerState,
    Zone,
)
from beta_magic.vanilla_creatures import GRIZZLY_BEARS


class RegenerationCreatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = GameState(
            [
                PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 20),
                PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 20),
            ],
            pause_for_damage_windows=True,
        )
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.advance_phase()
        self.alice, self.bob = self.game.players

    def put_in_play(self, player, definition):
        card = Card(
            definition=definition,
            owner_id=player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def pass_window(self) -> None:
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def reach_regeneration_window(self) -> None:
        self.pass_window()
        self.pass_window()
        self.assertEqual(
            self.game.pending_damage.step,
            DamageResolutionStep.REGENERATION,
        )

    def test_card_definitions(self) -> None:
        self.assertEqual(
            REGENERATION_CREATURES,
            (
                DRUDGE_SKELETONS,
                UTHDEN_TROLL,
                WILL_O_THE_WISP,
                WALL_OF_BONE,
                WALL_OF_BRAMBLES,
            ),
        )
        self.assertEqual(
            [(card.mana_cost.compact, card.power, card.toughness) for card in REGENERATION_CREATURES],
            [("1B", 1, 1), ("2R", 2, 2), ("B", 0, 1), ("2B", 1, 4), ("2G", 2, 3)],
        )
        self.assertIn(KeywordAbility.FLYING, WILL_O_THE_WISP.abilities)
        self.assertEqual(WALL_OF_BONE.subtypes, ("Wall",))
        self.assertEqual(WALL_OF_BRAMBLES.subtypes, ("Wall",))

    def test_regeneration_taps_creature_clears_damage_and_prevents_death(self) -> None:
        skeleton = self.put_in_play(self.bob, DRUDGE_SKELETONS)
        self.game._deal_damage(skeleton, 1, "test")
        self.reach_regeneration_window()
        self.bob.mana_pool.black = 1

        self.game.pass_priority(self.alice.id)
        self.game.activate_ability(self.bob.id, skeleton, 0)

        self.assertTrue(skeleton.tapped)
        self.assertEqual(skeleton.damage, 0)
        self.assertIn(skeleton.id, self.game.pending_damage.regenerated_card_ids)
        self.pass_window()
        self.assertIn(skeleton, self.bob.battlefield)
        self.assertNotIn(skeleton, self.bob.graveyard)

    def test_mana_can_be_generated_during_regeneration_window(self) -> None:
        skeleton = self.put_in_play(self.bob, DRUDGE_SKELETONS)
        swamp = self.put_in_play(self.bob, SWAMP)
        self.game._deal_damage(skeleton, 1, "test")
        self.reach_regeneration_window()

        self.game.pass_priority(self.alice.id)
        self.game.activate_ability(self.bob.id, swamp, 0)
        self.assertEqual(self.bob.mana_pool.black, 1)
        self.game.activate_ability(self.bob.id, skeleton, 0)

        self.assertEqual(self.bob.mana_pool.black, 0)
        self.assertTrue(swamp.tapped)

    def test_regeneration_is_unavailable_before_lethal_damage(self) -> None:
        skeleton = self.put_in_play(self.bob, DRUDGE_SKELETONS)
        self.bob.mana_pool.black = 1

        self.assertFalse(
            self.game.can_activate_ability(self.bob.id, skeleton, 0)
        )
        with self.assertRaisesRegex(RuntimeError, "regeneration window"):
            self.game.activate_ability(self.bob.id, skeleton, 0)

    def test_regeneration_prevents_an_ordinary_destroy_effect(self) -> None:
        assassin = self.put_in_play(self.alice, ROYAL_ASSASSIN)
        skeleton = self.put_in_play(self.bob, DRUDGE_SKELETONS)
        skeleton.tapped = True
        self.bob.mana_pool.black = 1
        self.game.activate_ability(self.alice.id, assassin, 0)
        self.game.complete_pending_activation((skeleton,))
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        self.reach_regeneration_window()

        self.game.pass_priority(self.alice.id)
        self.game.activate_ability(self.bob.id, skeleton, 0)
        self.pass_window()

        self.assertIn(skeleton, self.bob.battlefield)
        self.assertNotIn(skeleton, self.bob.graveyard)

    def test_regenerated_first_strike_blocker_deals_no_regular_damage(self) -> None:
        while self.game.current_phase.value != "main":
            self.game.advance_phase()
        archer = self.put_in_play(self.alice, ELVISH_ARCHERS)
        troll = self.put_in_play(self.bob, UTHDEN_TROLL)
        mountain = self.put_in_play(self.bob, MOUNTAIN)
        self.game.begin_combat()
        self.game.declare_attackers([archer])
        self.game.declare_blockers({troll: archer})
        self.game.advance_combat()
        self.game.deal_combat_damage()
        self.reach_regeneration_window()

        self.game.pass_priority(self.alice.id)
        self.game.activate_ability(self.bob.id, mountain, 0)
        self.game.activate_ability(self.bob.id, troll, 0)
        self.pass_window()

        self.assertIsNone(self.game.combat)
        self.assertIn(troll, self.bob.battlefield)
        self.assertEqual(troll.damage, 0)
        self.assertEqual(archer.damage, 0)


if __name__ == "__main__":
    unittest.main()
