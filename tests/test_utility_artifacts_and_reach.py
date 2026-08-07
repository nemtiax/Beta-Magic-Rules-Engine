import unittest

from beta_magic import (
    GIANT_SPIDER,
    DISRUPTING_SCEPTER,
    ICY_MANIPULATOR,
    HOWLING_MINE,
    GAUNTLET_OF_MIGHT,
    HELM_OF_CHATZUK,
    JAYEMDAE_TOME,
    JADE_MONOLITH,
    JADE_STATUE,
    KORMUS_BELL,
    NEVINYRRALS_DISK,
    ROD_OF_RUIN,
    SUNGLASSES_OF_URZA,
    UTILITY_ARTIFACTS,
    WEB,
    Card,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import PHANTOM_MONSTER
from beta_magic.card_defs import GRIZZLY_BEARS


class UtilityArtifactAndReachTests(unittest.TestCase):
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
    def put_in_play(player: PlayerState, definition) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def resolve_batch(self) -> None:
        while self.game.stack or self.game.batch_abilities:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_definitions(self) -> None:
        self.assertEqual(
            UTILITY_ARTIFACTS,
            (
                DISRUPTING_SCEPTER,
                ROD_OF_RUIN,
                JAYEMDAE_TOME,
                ICY_MANIPULATOR,
                NEVINYRRALS_DISK,
                JADE_MONOLITH,
                JADE_STATUE,
                HOWLING_MINE,
                KORMUS_BELL,
                GAUNTLET_OF_MIGHT,
                HELM_OF_CHATZUK,
                SUNGLASSES_OF_URZA,
            ),
        )
        self.assertEqual(
            [card.mana_cost.compact for card in UTILITY_ARTIFACTS],
            ["3", "4", "4", "4", "4", "4", "4", "2", "4", "4", "1", "3"],
        )
        self.assertEqual(
            (GIANT_SPIDER.power, GIANT_SPIDER.toughness), (2, 4)
        )

    def test_rod_of_ruin_pays_taps_and_deals_damage_after_priority(self) -> None:
        rod = self.put_in_play(self.alice, ROD_OF_RUIN)
        self.alice.mana_pool.colorless = 3
        self.game.activate_ability(self.alice.id, rod, 0)
        self.game.complete_pending_activation((self.bob,))

        self.assertTrue(rod.tapped)
        self.assertEqual(self.bob.life, 20)
        self.resolve_batch()
        self.assertEqual(self.bob.life, 19)

    def test_jayemdae_tome_draws_after_its_fast_effect_resolves(self) -> None:
        tome = self.put_in_play(self.alice, JAYEMDAE_TOME)
        self.alice.mana_pool.colorless = 4
        starting_hand = len(self.alice.hand)
        self.game.activate_ability(self.alice.id, tome, 0)

        self.assertTrue(tome.tapped)
        self.assertEqual(len(self.alice.hand), starting_hand)
        self.resolve_batch()
        self.assertEqual(len(self.alice.hand), starting_hand + 1)

    def test_icy_manipulator_taps_a_target_after_priority(self) -> None:
        icy = self.put_in_play(self.alice, ICY_MANIPULATOR)
        target = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.alice.mana_pool.colorless = 1
        self.game.activate_ability(self.alice.id, icy, 0)

        self.assertIn(target, self.game.legal_targets_for())
        self.game.complete_pending_activation((target,))
        self.assertFalse(target.tapped)
        self.resolve_batch()
        self.assertTrue(target.tapped)

    def test_giant_spider_and_webbed_creature_can_block_flying(self) -> None:
        flyer = self.put_in_play(self.alice, PHANTOM_MONSTER)
        spider = self.put_in_play(self.bob, GIANT_SPIDER)
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        web = self.put_in_play(self.bob, WEB)
        web.enchanted_card_id = bear.id

        self.assertIn(
            KeywordAbility.CAN_BLOCK_FLYING,
            self.game.creature_abilities(bear),
        )
        self.assertNotIn(
            KeywordAbility.FLYING, self.game.creature_abilities(bear)
        )
        self.assertEqual(self.game.creature_toughness(bear), 4)

        self.game.begin_combat()
        self.game.declare_attackers((flyer,))
        self.game.declare_blockers({spider: flyer})


if __name__ == "__main__":
    unittest.main()
