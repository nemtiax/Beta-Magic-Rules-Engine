import unittest

from beta_magic import (
    DISRUPTING_SCEPTER,
    GRIZZLY_BEARS,
    HYPNOTIC_SPECTER,
    JADE_MONOLITH,
    MIND_TWIST,
    VETERAN_BODYGUARD,
    Card,
    DamageIncidentKind,
    DamageResolutionStep,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)


class DiscardEffectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("alice", "Alice", [GRIZZLY_BEARS] * 20)
        self.bob = PlayerState.with_deck("bob", "Bob", [GRIZZLY_BEARS] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.random.seed(7)
        self.game.start(opening_hand_size=0, shuffle=False)
        while self.game.current_phase is not TurnPhase.MAIN:
            self.game.advance_phase()

    def card(self, definition, player, zone):
        card = Card(definition, player.id, controller_id=player.id, zone=zone)
        player.cards_in(zone).append(card)
        return card

    def resolve_priority(self):
        while self.game.priority_player_index is not None:
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
            if self.game.pending_discard_choices:
                break

    def test_mind_twist_discards_x_random_cards_from_opponent(self) -> None:
        spell = self.card(MIND_TWIST, self.alice, Zone.HAND)
        victims = [self.card(GRIZZLY_BEARS, self.bob, Zone.HAND) for _ in range(4)]
        self.alice.mana_pool.black = 1
        self.alice.mana_pool.colorless = 2

        self.game.begin_cast(spell, x_value=2)
        self.assertEqual(self.game.legal_player_targets_for(), [self.bob])
        self.game.complete_pending_cast((self.bob,))
        self.resolve_priority()

        self.assertEqual(len(self.bob.hand), 2)
        self.assertEqual(len(self.bob.graveyard), 2)
        self.assertTrue(
            {card.id for card in self.bob.graveyard}.issubset(
                {card.id for card in victims}
            )
        )

    def test_disrupting_scepter_opponent_chooses_after_batch(self) -> None:
        scepter = self.card(DISRUPTING_SCEPTER, self.alice, Zone.BATTLEFIELD)
        chosen = self.card(GRIZZLY_BEARS, self.bob, Zone.HAND)
        self.card(GRIZZLY_BEARS, self.bob, Zone.HAND)
        self.alice.mana_pool.colorless = 3

        self.game.activate_ability(self.alice.id, scepter, 0)
        self.game.complete_pending_activation((self.bob,))
        self.resolve_priority()

        self.assertTrue(scepter.tapped)
        self.assertEqual(self.game.pending_discard_choices[0].player_id, self.bob.id)
        with self.assertRaises(ValueError):
            self.game.choose_discard(self.alice.id, (chosen,))
        self.game.choose_discard(self.bob.id, (chosen,))
        self.assertIn(chosen, self.bob.graveyard)

    def test_hypnotic_specter_triggers_only_after_player_damage(self) -> None:
        specter = self.card(HYPNOTIC_SPECTER, self.alice, Zone.BATTLEFIELD)
        self.card(GRIZZLY_BEARS, self.bob, Zone.HAND)

        self.game._deal_damage(
            self.bob, 2, specter.name, source_card=specter,
            source_controller_id=self.alice.id, combat=True,
        )
        self.resolve_priority()

        self.assertEqual(self.bob.life, 18)
        self.assertFalse(self.bob.hand)
        self.assertEqual(len(self.bob.graveyard), 1)

    def test_prevented_specter_damage_does_not_cause_discard(self) -> None:
        specter = self.card(HYPNOTIC_SPECTER, self.alice, Zone.BATTLEFIELD)
        victim = self.card(GRIZZLY_BEARS, self.bob, Zone.HAND)
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(
            self.bob, 2, specter.name, source_card=specter,
            source_controller_id=self.alice.id, combat=True,
        )
        self.game.pending_damage.packets[0].prevented = 2
        self.game._resolve_damage_incident()

        self.assertEqual(self.bob.life, 20)
        self.assertEqual(self.bob.hand, [victim])
        self.assertFalse(self.game.event_opportunities)

    def test_specter_damage_redirected_away_from_player_does_not_discard(self) -> None:
        specter = self.card(HYPNOTIC_SPECTER, self.alice, Zone.BATTLEFIELD)
        bodyguard = self.card(VETERAN_BODYGUARD, self.bob, Zone.BATTLEFIELD)
        victim = self.card(GRIZZLY_BEARS, self.bob, Zone.HAND)

        self.game._deal_damage(
            self.bob, 2, specter.name, source_card=specter,
            source_controller_id=self.alice.id, combat=True, trample=False,
        )

        self.assertEqual(self.bob.life, 20)
        self.assertEqual(bodyguard.damage, 2)
        self.assertEqual(self.bob.hand, [victim])
        self.assertFalse(self.game.event_opportunities)

    def test_specter_damage_redirected_to_opponent_causes_discard(self) -> None:
        self.game.pause_for_damage_windows = True
        specter = self.card(HYPNOTIC_SPECTER, self.alice, Zone.BATTLEFIELD)
        bear = self.card(GRIZZLY_BEARS, self.bob, Zone.BATTLEFIELD)
        monolith = self.card(JADE_MONOLITH, self.bob, Zone.BATTLEFIELD)
        self.card(GRIZZLY_BEARS, self.bob, Zone.HAND)
        self.bob.mana_pool.colorless = 1

        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        self.game._deal_damage(
            bear, 2, specter.name, source_card=specter,
            source_controller_id=self.alice.id, combat=True,
        )
        self.game._resolve_damage_incident()
        for _ in range(2):
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)
        self.assertIs(
            self.game.pending_damage.step, DamageResolutionStep.REDIRECTION
        )
        self.game.pass_priority(self.alice.id)
        self.game.activate_ability(self.bob.id, monolith, 0)
        packet = self.game.pending_damage.packets[0]
        self.game.redirect_damage(self.bob.id, packet.id)

        for _ in range(20):
            if self.game.priority_player_index is None:
                break
            player = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(player.id)

        self.assertEqual(self.bob.life, 18)
        self.assertFalse(self.bob.hand)
        self.assertEqual(len(self.bob.graveyard), 1)


if __name__ == "__main__":
    unittest.main()
