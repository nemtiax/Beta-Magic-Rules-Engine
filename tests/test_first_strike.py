import unittest

from beta_magic import (
    ELVISH_ARCHERS,
    FIRST_STRIKE_CREATURES,
    GameState,
    KeywordAbility,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import (
    GRIZZLY_BEARS,
    HILL_GIANT,
    MONSS_GOBLIN_RAIDERS,
)


def player(player_id: str) -> PlayerState:
    return PlayerState.with_deck(player_id, player_id.title(), [GRIZZLY_BEARS] * 12)


class FirstStrikeTests(unittest.TestCase):
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

    def fight(self, attacker_definition, blocker_definition, assignments=None):
        attacker = self.put_in_play(self.alice, attacker_definition)
        blocker = self.put_in_play(self.bob, blocker_definition)
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        self.game.declare_blockers({blocker: attacker})
        self.game.advance_combat()
        self.game.deal_combat_damage(assignments)
        return attacker, blocker

    def test_elvish_archers_definition(self) -> None:
        self.assertEqual(FIRST_STRIKE_CREATURES, (ELVISH_ARCHERS,))
        self.assertEqual(ELVISH_ARCHERS.mana_cost.compact, "1G")
        self.assertEqual((ELVISH_ARCHERS.power, ELVISH_ARCHERS.toughness), (2, 1))
        self.assertEqual(
            ELVISH_ARCHERS.abilities, frozenset({KeywordAbility.FIRST_STRIKE})
        )

    def test_first_strike_attacker_kills_blocker_before_return_damage(self) -> None:
        archer, bear = self.fight(ELVISH_ARCHERS, GRIZZLY_BEARS)
        self.assertIn(archer, self.alice.battlefield)
        self.assertEqual(archer.damage, 0)
        self.assertIn(bear, self.bob.graveyard)

    def test_first_strike_blocker_kills_attacker_before_regular_damage(self) -> None:
        bear, archer = self.fight(GRIZZLY_BEARS, ELVISH_ARCHERS)
        self.assertIn(bear, self.alice.graveyard)
        self.assertIn(archer, self.bob.battlefield)
        self.assertEqual(archer.damage, 0)

    def test_two_first_strikers_damage_each_other_simultaneously(self) -> None:
        attacker, blocker = self.fight(ELVISH_ARCHERS, ELVISH_ARCHERS)
        self.assertIn(attacker, self.alice.graveyard)
        self.assertIn(blocker, self.bob.graveyard)

    def test_mixed_first_strike_and_regular_blockers(self) -> None:
        giant = self.put_in_play(self.alice, HILL_GIANT)
        archer = self.put_in_play(self.bob, ELVISH_ARCHERS)
        goblin = self.put_in_play(self.bob, MONSS_GOBLIN_RAIDERS)
        self.game.begin_combat()
        self.game.declare_attackers([giant])
        self.game.declare_blockers({archer: giant, goblin: giant})
        self.game.advance_combat()
        self.game.deal_combat_damage({giant: {archer: 2, goblin: 1}})
        self.assertIn(giant, self.alice.graveyard)
        self.assertIn(archer, self.bob.graveyard)
        self.assertIn(goblin, self.bob.graveyard)


if __name__ == "__main__":
    unittest.main()
