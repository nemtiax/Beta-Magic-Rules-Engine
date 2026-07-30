import unittest

from beta_magic import (
    ANCESTRAL_RECALL,
    BLUE_UTILITY_SPELLS,
    CASTLE,
    JUMP,
    SERRA_ANGEL,
    UNSUMMON,
    Card,
    GameState,
    KeywordAbility,
    PlayerState,
    PRODIGAL_SORCERER,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import HOLY_STRENGTH
from beta_magic.card_defs import GRIZZLY_BEARS


class EasyCardTests(unittest.TestCase):
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

    @staticmethod
    def put_in_hand(player: PlayerState, definition) -> Card:
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        player.hand.append(card)
        return card

    def cast(self, definition, target) -> Card:
        spell = self.put_in_hand(self.alice, definition)
        self.alice.mana_pool.blue = 10
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((target,))
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        return spell

    def test_definitions(self) -> None:
        self.assertEqual(
            BLUE_UTILITY_SPELLS, (ANCESTRAL_RECALL, JUMP, UNSUMMON)
        )
        self.assertEqual(CASTLE.mana_cost.compact, "3W")
        self.assertEqual(SERRA_ANGEL.mana_cost.compact, "3WW")
        self.assertEqual(
            (SERRA_ANGEL.power, SERRA_ANGEL.toughness), (4, 4)
        )

    def test_castle_only_buffs_controllers_untapped_nonattackers(self) -> None:
        self.put_in_play(self.alice, CASTLE)
        angel = self.put_in_play(self.alice, SERRA_ANGEL)
        opposing_bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.assertEqual(self.game.creature_toughness(angel), 6)
        self.assertEqual(self.game.creature_toughness(opposing_bear), 2)

        angel.tapped = True
        self.assertEqual(self.game.creature_toughness(angel), 4)
        angel.tapped = False
        self.game.begin_combat()
        self.game.declare_attackers((angel,))

        self.assertFalse(angel.tapped)
        self.assertEqual(self.game.creature_toughness(angel), 4)

    def test_tapping_immediately_removes_castles_toughness_bonus(self) -> None:
        self.put_in_play(self.alice, CASTLE)
        sorcerer = self.put_in_play(self.alice, PRODIGAL_SORCERER)
        sorcerer.damage = 1

        self.game.activate_ability(self.alice.id, sorcerer, 0)
        self.game.complete_pending_activation((self.bob,))

        self.assertIn(sorcerer, self.alice.graveyard)

    def test_serra_angel_still_has_summoning_sickness(self) -> None:
        angel = self.put_in_play(self.alice, SERRA_ANGEL)
        angel.entered_battlefield_turn = self.game.turn_number
        self.game.begin_combat()
        with self.assertRaisesRegex(ValueError, "did not begin"):
            self.game.declare_attackers((angel,))

    def test_ancestral_recall_draws_three_for_either_player(self) -> None:
        self.cast(ANCESTRAL_RECALL, self.bob)
        self.assertEqual(len(self.bob.hand), 3)

    def test_jump_grants_flying_until_end_of_turn(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.cast(JUMP, bear)
        self.assertIn(
            KeywordAbility.FLYING, self.game.creature_abilities(bear)
        )
        self.game.temporary_creature_effects.clear()
        self.assertNotIn(
            KeywordAbility.FLYING, self.game.creature_abilities(bear)
        )

    def test_unsummon_returns_creature_and_discards_its_auras(self) -> None:
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        aura = self.put_in_play(self.alice, HOLY_STRENGTH)
        aura.enchanted_card_id = bear.id

        self.cast(UNSUMMON, bear)

        self.assertIn(bear, self.bob.hand)
        self.assertIn(aura, self.alice.graveyard)
        self.assertEqual(bear.damage, 0)
        self.assertFalse(bear.tapped)


if __name__ == "__main__":
    unittest.main()
