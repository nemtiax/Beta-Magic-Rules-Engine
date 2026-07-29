import unittest

from beta_magic import (
    LIGHTNING_BOLT,
    PSIONIC_BLAST,
    TARGETED_DAMAGE_SPELLS,
    CardType,
    DamageEvent,
    GameState,
    PlayerState,
    SpellCastEvent,
    TurnPhase,
    Zone,
)
from beta_magic.vanilla_creatures import GRIZZLY_BEARS, HILL_GIANT


class TargetedDamageSpellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 20
        )
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.advance_phase()

    @staticmethod
    def put_in_play(player: PlayerState, definition=GRIZZLY_BEARS):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        player.battlefield.append(card)
        return card

    @staticmethod
    def put_in_hand(player: PlayerState, definition):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.HAND
        player.hand.append(card)
        return card

    def resolve_stack(self) -> None:
        while self.game.stack:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

    def test_card_definitions(self) -> None:
        self.assertEqual(
            TARGETED_DAMAGE_SPELLS, (LIGHTNING_BOLT, PSIONIC_BLAST)
        )
        self.assertEqual(LIGHTNING_BOLT.mana_cost.compact, "R")
        self.assertEqual(PSIONIC_BLAST.mana_cost.compact, "2U")
        self.assertTrue(
            all(
                CardType.INSTANT in definition.card_types
                and definition.target_requirement is not None
                and definition.target_requirement.players
                for definition in TARGETED_DAMAGE_SPELLS
            )
        )

    def test_lightning_bolt_can_target_player_and_goes_to_graveyard(self) -> None:
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        self.alice.mana_pool.red = 1
        self.game.begin_cast(bolt)
        self.assertEqual(self.game.legal_player_targets_for(), self.game.players)

        self.game.complete_pending_cast((self.bob,))
        self.resolve_stack()

        self.assertEqual(self.bob.life, 17)
        self.assertIn(bolt, self.alice.graveyard)
        self.assertFalse(self.game.stack)
        self.assertEqual(self.alice.mana_pool.total, 0)
        cast = next(
            event
            for event in self.game.events
            if isinstance(event, SpellCastEvent)
            and event.card_id == bolt.id
        )
        self.assertEqual(cast.target_player_ids, ("bob",))

    def test_lightning_bolt_can_deal_lethal_damage_to_creature(self) -> None:
        bear = self.put_in_play(self.bob)
        bolt = self.put_in_hand(self.alice, LIGHTNING_BOLT)
        self.alice.mana_pool.red = 1

        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((bear,))
        self.resolve_stack()

        self.assertIn(bear, self.bob.graveyard)
        self.assertIn(bolt, self.alice.graveyard)
        self.assertTrue(
            any(
                isinstance(event, DamageEvent)
                and event.card_id == bear.id
                and event.amount == 3
                for event in self.game.events
            )
        )

    def test_psionic_blast_damages_target_and_caster(self) -> None:
        blast = self.put_in_hand(self.alice, PSIONIC_BLAST)
        self.alice.mana_pool.blue = 1
        self.alice.mana_pool.colorless = 2

        self.game.begin_cast(blast)
        self.game.complete_pending_cast((self.bob,))
        self.resolve_stack()

        self.assertEqual(self.bob.life, 16)
        self.assertEqual(self.alice.life, 18)
        self.assertIn(blast, self.alice.graveyard)

    def test_nonactive_player_can_cast_instant_during_upkeep(self) -> None:
        bolt = self.put_in_hand(self.bob, LIGHTNING_BOLT)
        self.bob.mana_pool.red = 1

        self.game.begin_cast(bolt)
        self.game.complete_pending_cast((self.alice,))
        self.resolve_stack()

        self.assertEqual(self.alice.life, 17)
        self.assertIn(bolt, self.bob.graveyard)

    def test_instant_cannot_be_cast_during_untap_or_combat_damage(self) -> None:
        game = GameState(
            [
                PlayerState.with_deck("a", "A", [HILL_GIANT] * 20),
                PlayerState.with_deck("b", "B", [GRIZZLY_BEARS] * 20),
            ]
        )
        game.start(opening_hand_size=0, shuffle=False)
        bolt = self.put_in_hand(game.players[0], LIGHTNING_BOLT)
        game.players[0].mana_pool.red = 1
        with self.assertRaisesRegex(RuntimeError, "Untap"):
            game.begin_cast(bolt)

        while game.current_phase is not TurnPhase.MAIN:
            game.advance_phase()
        attacker = game.players[0].library.pop()
        attacker.zone = Zone.BATTLEFIELD
        game.players[0].battlefield.append(attacker)
        game.begin_combat()
        game.declare_attackers([attacker])
        game.declare_blockers({})
        game.advance_combat()
        with self.assertRaisesRegex(RuntimeError, "combat damage"):
            game.begin_cast(bolt)


if __name__ == "__main__":
    unittest.main()
