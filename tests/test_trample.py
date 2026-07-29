import unittest

from beta_magic import (
    GameState,
    KeywordAbility,
    PlayerState,
    TRAMPLE_CREATURES,
    TurnPhase,
    WAR_MAMMOTH,
    Zone,
)
from beta_magic.vanilla_creatures import (
    GRIZZLY_BEARS,
    MONSS_GOBLIN_RAIDERS,
)


def player(player_id: str) -> PlayerState:
    return PlayerState.with_deck(player_id, player_id.title(), [GRIZZLY_BEARS] * 12)


class TrampleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = player("alice")
        self.bob = player("bob")
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    @staticmethod
    def put_in_play(owner: PlayerState, definition):
        card = owner.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        owner.battlefield.append(card)
        return card

    def reach_damage(self, attacker, blockers):
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        self.game.declare_blockers({blocker: attacker for blocker in blockers})
        self.game.advance_combat()

    def test_war_mammoth_definition(self) -> None:
        self.assertEqual(TRAMPLE_CREATURES, (WAR_MAMMOTH,))
        self.assertEqual(WAR_MAMMOTH.mana_cost.compact, "3G")
        self.assertEqual((WAR_MAMMOTH.power, WAR_MAMMOTH.toughness), (3, 3))
        self.assertEqual(
            WAR_MAMMOTH.abilities, frozenset({KeywordAbility.TRAMPLE})
        )

    def test_excess_damage_tramples_over_single_blocker(self) -> None:
        mammoth = self.put_in_play(self.alice, WAR_MAMMOTH)
        goblin = self.put_in_play(self.bob, MONSS_GOBLIN_RAIDERS)
        self.reach_damage(mammoth, [goblin])
        self.game.deal_combat_damage()
        self.assertIn(goblin, self.bob.graveyard)
        self.assertEqual(self.bob.life, 18)
        self.assertEqual(mammoth.damage, 1)

    def test_only_damage_beyond_remaining_toughness_tramples(self) -> None:
        mammoth = self.put_in_play(self.alice, WAR_MAMMOTH)
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        bear.damage = 1
        self.reach_damage(mammoth, [bear])
        self.game.deal_combat_damage()
        self.assertIn(bear, self.bob.graveyard)
        self.assertEqual(self.bob.life, 18)

    def test_attacker_can_pile_damage_on_one_of_multiple_blockers(self) -> None:
        mammoth = self.put_in_play(self.alice, WAR_MAMMOTH)
        goblin = self.put_in_play(self.bob, MONSS_GOBLIN_RAIDERS)
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.reach_damage(mammoth, [goblin, bear])
        self.game.deal_combat_damage({mammoth: {goblin: 3, bear: 0}})
        self.assertIn(goblin, self.bob.graveyard)
        self.assertIn(bear, self.bob.battlefield)
        self.assertEqual(self.bob.life, 18)
        self.assertIn(mammoth, self.alice.graveyard)

    def test_all_damage_tramples_past_a_removed_blocker(self) -> None:
        mammoth = self.put_in_play(self.alice, WAR_MAMMOTH)
        goblin = self.put_in_play(self.bob, MONSS_GOBLIN_RAIDERS)
        self.reach_damage(mammoth, [goblin])
        self.bob.battlefield.remove(goblin)
        goblin.zone = Zone.GRAVEYARD
        self.bob.graveyard.append(goblin)
        self.game.deal_combat_damage()
        self.assertEqual(self.bob.life, 17)


if __name__ == "__main__":
    unittest.main()
