import unittest

from beta_magic import (
    HOLY_STRENGTH,
    CardMovedEvent,
    DamageEvent,
    GameState,
    ManaBurnEvent,
    PlayerState,
    SpellCastEvent,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs import GRIZZLY_BEARS, HILL_GIANT


class EngineEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck(
            "alice", "Alice", [GRIZZLY_BEARS] * 16
        )
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 16)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    def put_in_play(self, player: PlayerState, definition=GRIZZLY_BEARS):
        card = player.library.pop()
        card.definition = definition
        card.zone = Zone.BATTLEFIELD
        player.battlefield.append(card)
        return card

    def test_cast_emits_movement_and_targeted_spell_events(self) -> None:
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        target = self.put_in_play(self.bob)
        aura = self.alice.library.pop()
        aura.definition = HOLY_STRENGTH
        aura.zone = Zone.HAND
        self.alice.hand.append(aura)
        self.alice.mana_pool.white = 1
        checkpoint = len(self.game.events)

        self.game.cast_enchantment(aura, target)

        events = self.game.events[checkpoint:]
        movement = next(event for event in events if isinstance(event, CardMovedEvent))
        cast = next(event for event in events if isinstance(event, SpellCastEvent))
        self.assertEqual((movement.source, movement.destination), (Zone.HAND, Zone.BATTLEFIELD))
        self.assertEqual(cast.target_ids, (target.id,))
        self.assertEqual(cast.target_names, (target.name,))

    def test_combat_damage_and_mana_burn_have_distinct_events(self) -> None:
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()
        attacker = self.put_in_play(self.alice, HILL_GIANT)
        self.game.begin_combat()
        self.game.declare_attackers([attacker])
        self.game.declare_blockers({})
        self.game.advance_combat()
        self.bob.mana_pool.green = 1
        checkpoint = len(self.game.events)

        self.game.deal_combat_damage()

        events = self.game.events[checkpoint:]
        damage = [event for event in events if isinstance(event, DamageEvent)]
        burns = [event for event in events if isinstance(event, ManaBurnEvent)]
        self.assertEqual(
            [(event.player_id, event.amount, event.source) for event in damage],
            [("bob", 3, "combat")],
        )
        self.assertEqual(
            [(event.player_id, event.amount) for event in burns],
            [("bob", 1)],
        )


if __name__ == "__main__":
    unittest.main()
