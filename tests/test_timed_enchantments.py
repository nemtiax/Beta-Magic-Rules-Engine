import unittest

from beta_magic import (
    BAD_MOON,
    CURSED_LAND,
    FEEDBACK,
    TIMED_ENCHANTMENTS,
    WANDERLUST,
    WARP_ARTIFACT,
    LIGHTNING_BOLT,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
    SOL_RING,
)
from beta_magic.basic_lands import PLAINS
from beta_magic.vanilla_creatures import GRIZZLY_BEARS


class TimedEnchantmentTests(unittest.TestCase):
    def make_game(self):
        alice = PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 30)
        bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 30)
        game = GameState([alice, bob])
        game.start(opening_hand_size=0, shuffle=False)
        return game, alice, bob

    @staticmethod
    def put_in_play(player, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        card.controller_id = player.id
        player.battlefield.append(card)
        return card

    def test_definitions(self) -> None:
        self.assertEqual(
            TIMED_ENCHANTMENTS,
            (CURSED_LAND, FEEDBACK, WANDERLUST, WARP_ARTIFACT),
        )
        self.assertEqual(
            tuple(card.mana_cost.compact for card in TIMED_ENCHANTMENTS),
            ("2BB", "2U", "2G", "BB"),
        )

    def test_each_aura_targets_the_right_permanent_type(self) -> None:
        game, alice, bob = self.make_game()
        targets = {
            CURSED_LAND: self.put_in_play(alice, PLAINS),
            FEEDBACK: self.put_in_play(alice, BAD_MOON),
            WANDERLUST: self.put_in_play(alice, GRIZZLY_BEARS),
            WARP_ARTIFACT: self.put_in_play(alice, SOL_RING),
        }
        for aura_definition, expected in targets.items():
            with self.subTest(aura_definition.name):
                aura = bob.library.pop()
                aura.definition = aura_definition
                aura.zone = Zone.HAND
                bob.hand.append(aura)
                legal = game.legal_targets_for(aura)
                self.assertIn(expected, legal)
                self.assertEqual(len(legal), 1)
                bob.hand.remove(aura)
                aura.zone = Zone.LIBRARY
                bob.library.append(aura)

    def test_auras_damage_enchanted_permanents_controller_during_their_upkeep(
        self,
    ) -> None:
        cases = (
            (CURSED_LAND, PLAINS),
            (FEEDBACK, BAD_MOON),
            (WANDERLUST, GRIZZLY_BEARS),
            (WARP_ARTIFACT, SOL_RING),
        )
        for aura_definition, target_definition in cases:
            with self.subTest(aura_definition.name):
                game, alice, bob = self.make_game()
                target = self.put_in_play(alice, target_definition)
                aura = self.put_in_play(bob, aura_definition)
                aura.enchanted_card_id = target.id

                game.advance_phase()

                self.assertIs(game.current_phase, TurnPhase.UPKEEP)
                self.assertEqual(len(game.timed_events), 1)
                self.assertEqual(
                    game.timed_events[0].affected_player_id, alice.id
                )
                for _ in range(2):
                    player = game.players[game.priority_player_index]
                    game.pass_priority(player.id)
                self.assertEqual(alice.life, 19)
                self.assertEqual(bob.life, 20)

    def test_aura_does_not_fire_during_other_players_upkeep(self) -> None:
        game, alice, bob = self.make_game()
        target = self.put_in_play(bob, GRIZZLY_BEARS)
        aura = self.put_in_play(alice, WANDERLUST)
        aura.enchanted_card_id = target.id

        game.advance_phase()

        self.assertEqual(game.timed_events, [])
        self.assertEqual((alice.life, bob.life), (20, 20))

    def test_response_can_remove_enchanted_permanent_before_event(self) -> None:
        game, alice, bob = self.make_game()
        creature = self.put_in_play(alice, GRIZZLY_BEARS)
        aura = self.put_in_play(bob, WANDERLUST)
        aura.enchanted_card_id = creature.id
        bolt = alice.library.pop()
        bolt.definition = LIGHTNING_BOLT
        bolt.zone = Zone.HAND
        alice.hand.append(bolt)
        game.advance_phase()
        alice.mana_pool.red = 1

        game.begin_cast(bolt)
        game.complete_pending_cast((creature,))
        for _ in range(2):
            player = game.players[game.priority_player_index]
            game.pass_priority(player.id)
        self.assertIn(creature, alice.graveyard)
        self.assertIn(aura, bob.graveyard)

        for _ in range(2):
            player = game.players[game.priority_player_index]
            game.pass_priority(player.id)
        self.assertEqual(alice.life, 20)


if __name__ == "__main__":
    unittest.main()
