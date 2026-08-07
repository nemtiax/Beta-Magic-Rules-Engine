import unittest

from beta_magic import (
    BAYOU,
    EVIL_PRESENCE,
    GRIZZLY_BEARS,
    KARMA,
    PLAINS,
    SWAMP,
    Card,
    CardType,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class KarmaTests(unittest.TestCase):
    def setUp(self):
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck(
            "bob", "Bob", [GRIZZLY_BEARS] * 20
        )
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def permanent(player, definition, *, owner_id=None):
        card = Card(
            definition,
            owner_id=owner_id or player.id,
            controller_id=player.id,
            zone=Zone.BATTLEFIELD,
        )
        player.battlefield.append(card)
        return card

    def resolve_timed_events(self):
        while self.game.timed_events:
            for _ in range(2):
                player = self.game.players[self.game.priority_player_index]
                self.game.pass_priority(player.id)

    def test_definition(self):
        self.assertEqual(KARMA.mana_cost.compact, "2WW")
        self.assertEqual(KARMA.card_types, frozenset({CardType.ENCHANTMENT}))
        effect = KARMA.upkeep_effects[0]
        self.assertEqual(effect.amount, 1)
        self.assertEqual(
            effect.counted_active_player_owned_land_subtype,
            "Swamp",
        )

    def test_damages_active_player_for_each_swamp_they_own(self):
        self.permanent(self.bob, KARMA)
        self.permanent(self.alice, SWAMP)
        self.permanent(self.alice, BAYOU)
        converted = self.permanent(self.alice, PLAINS)
        evil_presence = self.permanent(self.bob, EVIL_PRESENCE)
        evil_presence.enchanted_card_id = converted.id
        # Ownership, rather than control, determines who Karma damages.
        self.permanent(self.bob, SWAMP, owner_id=self.alice.id)
        self.permanent(self.bob, SWAMP)

        self.game.advance_phase()

        self.assertIs(self.game.current_phase, TurnPhase.UPKEEP)
        self.assertEqual(len(self.game.timed_events), 1)
        self.assertEqual(self.game.timed_events[0].effect.amount, 4)
        self.resolve_timed_events()
        self.assertEqual((self.alice.life, self.bob.life), (16, 20))

    def test_does_not_open_an_event_when_active_player_owns_no_swamps(self):
        self.permanent(self.bob, KARMA)
        self.permanent(self.alice, PLAINS)
        self.permanent(self.bob, SWAMP)

        self.game.advance_phase()

        self.assertEqual(self.game.timed_events, [])
        self.assertEqual((self.alice.life, self.bob.life), (20, 20))


if __name__ == "__main__":
    unittest.main()
