import unittest

from beta_magic import (
    BAD_MOON,
    DWARVEN_DEMOLITION_TEAM,
    GOBLIN_BALLOON_BRIGADE,
    NORTHERN_PALADIN,
    ROYAL_ASSASSIN,
    SWAMP,
    Card,
    GameState,
    KeywordAbility,
    PlayerState,
    Zone,
)
from beta_magic.vanilla_creatures import GRIZZLY_BEARS, SCATHE_ZOMBIES
from beta_magic.vanilla_walls import WALL_OF_WOOD


class UtilityAbilityCreatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = GameState(
            [
                PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 10),
                PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 10),
            ]
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

    def resolve_batch(self) -> None:
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)

    def activate_at(self, source, target) -> None:
        self.game.activate_ability(self.alice.id, source, 0)
        self.game.complete_pending_activation((target,))

    def test_demolition_team_only_targets_walls(self) -> None:
        team = self.put_in_play(self.alice, DWARVEN_DEMOLITION_TEAM)
        wall = self.put_in_play(self.bob, WALL_OF_WOOD)
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)

        self.game.activate_ability(self.alice.id, team, 0)
        self.assertEqual(self.game.legal_targets_for(), [wall])
        self.game.complete_pending_activation((wall,))
        self.resolve_batch()

        self.assertIn(wall, self.bob.graveyard)
        self.assertIn(bear, self.bob.battlefield)

    def test_balloon_brigade_buys_flying_until_end_of_turn(self) -> None:
        brigade = self.put_in_play(self.alice, GOBLIN_BALLOON_BRIGADE)
        self.alice.mana_pool.red = 2

        self.game.activate_ability(self.alice.id, brigade, 0)
        self.game.activate_ability(self.alice.id, brigade, 0)

        self.assertEqual(self.alice.mana_pool.red, 0)
        self.assertIn(KeywordAbility.FLYING, self.game.creature_abilities(brigade))
        self.game.temporary_creature_effects.clear()
        self.assertNotIn(
            KeywordAbility.FLYING, self.game.creature_abilities(brigade)
        )

    def test_royal_assassin_can_target_either_players_tapped_creature(self) -> None:
        assassin = self.put_in_play(self.alice, ROYAL_ASSASSIN)
        own_bear = self.put_in_play(self.alice, GRIZZLY_BEARS)
        opposing_bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        own_bear.tapped = opposing_bear.tapped = True

        self.game.activate_ability(self.alice.id, assassin, 0)

        self.assertEqual(
            set(self.game.legal_targets_for()), {own_bear, opposing_bear}
        )

    def test_assassin_target_still_dies_if_untapped_during_responses(self) -> None:
        assassin = self.put_in_play(self.alice, ROYAL_ASSASSIN)
        target = self.put_in_play(self.bob, GRIZZLY_BEARS)
        target.tapped = True
        self.activate_at(assassin, target)

        target.tapped = False
        self.resolve_batch()

        self.assertIn(target, self.bob.graveyard)

    def test_northern_paladin_targets_any_black_permanent_and_pays_ww(self) -> None:
        paladin = self.put_in_play(self.alice, NORTHERN_PALADIN)
        zombie = self.put_in_play(self.bob, SCATHE_ZOMBIES)
        bad_moon = self.put_in_play(self.bob, BAD_MOON)
        swamp = self.put_in_play(self.bob, SWAMP)
        self.alice.mana_pool.white = 2

        self.game.activate_ability(self.alice.id, paladin, 0)
        self.assertEqual(
            set(self.game.legal_targets_for()), {zombie, bad_moon}
        )
        self.game.complete_pending_activation((bad_moon,))
        self.assertEqual(self.alice.mana_pool.white, 0)
        self.assertTrue(paladin.tapped)
        self.resolve_batch()

        self.assertIn(bad_moon, self.bob.graveyard)
        self.assertIn(swamp, self.bob.battlefield)


if __name__ == "__main__":
    unittest.main()
