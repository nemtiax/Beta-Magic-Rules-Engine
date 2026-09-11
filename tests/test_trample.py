import unittest

from beta_magic import (
    GameState,
    KeywordAbility,
    PlayerState,
    TRAMPLE_CREATURES,
    TurnPhase,
    UTHDEN_TROLL,
    WAR_MAMMOTH,
    Zone,
)
from beta_magic.card_defs import (
    CIRCLE_OF_PROTECTION_GREEN,
    GREEN_WARD,
    GRIZZLY_BEARS,
    MONSS_GOBLIN_RAIDERS,
    SAMITE_HEALER,
)
from beta_magic.damage import DamageIncidentKind


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

    def test_protection_prevents_damage_before_trample_redirects(self) -> None:
        mammoth = self.put_in_play(self.alice, WAR_MAMMOTH)
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        ward = self.put_in_play(self.bob, GREEN_WARD)
        ward.enchanted_card_id = bear.id
        self.reach_damage(mammoth, [bear])

        self.game.deal_combat_damage()

        self.assertEqual(self.bob.life, 20)
        self.assertEqual(bear.damage, 0)
        self.assertIn(bear, self.bob.battlefield)

    def test_blocker_prevention_reduces_excess_trample_damage(self) -> None:
        mammoth = self.put_in_play(self.alice, WAR_MAMMOTH)
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        healer = self.put_in_play(self.bob, SAMITE_HEALER)
        self.game.pause_for_damage_windows = True
        self.reach_damage(mammoth, [bear])
        self.game.deal_combat_damage()

        self.game.pass_priority(self.alice.id)
        self.game.activate_ability(self.bob.id, healer, 0)
        packet = next(
            packet
            for packet in self.game.pending_damage.packets
            if packet.recipient_id == bear.id
        )
        self.game.prevent_damage(self.bob.id, packet.id)
        while self.game.pending_damage is not None:
            priority = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(priority.id)

        self.assertEqual(self.bob.life, 20)
        self.assertIn(bear, self.bob.graveyard)

    def test_redirected_trample_damage_gets_a_new_prevention_window(self) -> None:
        mammoth = self.put_in_play(self.alice, WAR_MAMMOTH)
        goblin = self.put_in_play(self.bob, MONSS_GOBLIN_RAIDERS)
        circle = self.put_in_play(self.bob, CIRCLE_OF_PROTECTION_GREEN)
        self.game.pause_for_damage_windows = True
        self.reach_damage(mammoth, [goblin])
        self.bob.mana_pool.colorless = 1
        self.game.deal_combat_damage()

        while not any(
            packet.recipient_id == self.bob.id
            for packet in self.game.pending_damage.packets
        ):
            priority = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(priority.id)
        self.game.pass_priority(self.alice.id)
        self.game.activate_ability(self.bob.id, circle, 0)
        packet = self.game.pending_damage.packets[0]
        self.game.prevent_damage(self.bob.id, packet.id)
        while self.game.pending_damage is not None:
            priority = self.game.players[self.game.priority_player_index]
            self.game.pass_priority(priority.id)

        self.assertEqual(self.bob.life, 20)

    def test_nontrample_damage_is_applied_before_trample_damage(self) -> None:
        mammoth = self.put_in_play(self.alice, WAR_MAMMOTH)
        goblin = self.put_in_play(self.alice, MONSS_GOBLIN_RAIDERS)
        bear = self.put_in_play(self.bob, GRIZZLY_BEARS)
        self.game._begin_damage_incident(DamageIncidentKind.COMBAT)
        self.game._deal_damage(
            bear, 1, goblin.name, source_card=goblin, combat=True
        )
        self.game._deal_damage(
            bear,
            3,
            mammoth.name,
            source_card=mammoth,
            combat=True,
            trample=True,
            trample_defender_id=self.bob.id,
        )

        self.game._resolve_damage_incident()

        self.assertEqual(self.bob.life, 18)
        self.assertIn(bear, self.bob.graveyard)

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

    def test_regenerated_blocker_stays_in_combat_and_stops_trample(self) -> None:
        mammoth = self.put_in_play(self.alice, WAR_MAMMOTH)
        troll = self.put_in_play(self.bob, UTHDEN_TROLL)
        self.reach_damage(mammoth, [troll])
        self.game.combat.regenerated_card_ids.add(troll.id)

        self.game.deal_combat_damage()

        self.assertEqual(self.bob.life, 20)
        self.assertEqual(troll.damage, 0)
        self.assertEqual(mammoth.damage, 0)
        self.assertIn(troll, self.bob.battlefield)

    def test_trample_uses_other_blockers_when_one_regenerated(self) -> None:
        mammoth = self.put_in_play(self.alice, WAR_MAMMOTH)
        troll = self.put_in_play(self.bob, UTHDEN_TROLL)
        goblin = self.put_in_play(self.bob, MONSS_GOBLIN_RAIDERS)
        self.reach_damage(mammoth, [troll, goblin])
        self.game.combat.regenerated_card_ids.add(troll.id)

        self.game.deal_combat_damage()

        self.assertEqual(self.bob.life, 18)
        self.assertEqual(troll.damage, 0)
        self.assertIn(troll, self.bob.battlefield)
        self.assertIn(goblin, self.bob.graveyard)


if __name__ == "__main__":
    unittest.main()
