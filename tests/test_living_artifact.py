import unittest

from beta_magic import Card, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.artifacts import SOL_RING
from beta_magic.card_defs.green import LIVING_ARTIFACT
from beta_magic.damage import DamageIncidentKind


class LivingArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [SOL_RING] * 20)
        self.bob = PlayerState.with_deck("b", "Bob", [SOL_RING] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def permanent(player, definition, *, attached=None):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            enchanted_card_id=attached.id if attached else None,
        )
        player.battlefield.append(card)
        return card

    def test_definition_targets_artifacts(self) -> None:
        artifact = self.permanent(self.bob, SOL_RING)
        aura = Card(LIVING_ARTIFACT, self.alice.id, zone=Zone.HAND)
        self.alice.hand.append(aura)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0
        self.alice.mana_pool.green = 1
        self.game.begin_cast(aura)
        self.assertIn(artifact, self.game.legal_targets_for())

    def test_actual_life_loss_adds_counters_to_aura_not_artifact(self) -> None:
        artifact = self.permanent(self.bob, SOL_RING)
        aura = self.permanent(self.alice, LIVING_ARTIFACT, attached=artifact)
        self.game._lose_life(self.alice, 3)
        self.assertEqual(aura.counters, {"life": 3})
        self.assertEqual(artifact.counters, {})

    def test_prevented_life_loss_does_not_add_counters(self) -> None:
        artifact = self.permanent(self.bob, SOL_RING)
        aura = self.permanent(self.alice, LIVING_ARTIFACT, attached=artifact)
        self.game.life_loss_prevention[self.alice.id] = 2
        self.game._lose_life(self.alice, 3)
        self.assertEqual(aura.counters, {"life": 1})

    def test_each_aura_keeps_its_own_counters(self) -> None:
        artifact = self.permanent(self.bob, SOL_RING)
        first = self.permanent(self.alice, LIVING_ARTIFACT, attached=artifact)
        second = self.permanent(self.alice, LIVING_ARTIFACT, attached=artifact)
        self.game._lose_life(self.alice, 2)
        self.assertEqual(first.counters["life"], 2)
        self.assertEqual(second.counters["life"], 2)

    def test_aura_controller_gets_counters_on_opponents_artifact(self) -> None:
        artifact = self.permanent(self.bob, SOL_RING)
        aura = self.permanent(self.alice, LIVING_ARTIFACT, attached=artifact)
        self.game._lose_life(self.bob, 2)
        self.assertEqual(aura.counters, {})
        self.game._lose_life(self.alice, 1)
        self.assertEqual(aura.counters["life"], 1)

    def test_controller_may_redeem_one_counter_from_each_copy(self) -> None:
        artifact = self.permanent(self.bob, SOL_RING)
        first = self.permanent(self.alice, LIVING_ARTIFACT, attached=artifact)
        second = self.permanent(self.alice, LIVING_ARTIFACT, attached=artifact)
        first.counters["life"] = 2
        second.counters["life"] = 2
        self.game._enter_phase(TurnPhase.UPKEEP)

        for aura in (first, second):
            self.assertIs(self.game._timed_event_source(self.game.timed_events[0]), aura)
            self.game.priority_player_index = 0
            self.game.choose_upkeep_payment(self.alice.id, pay=True)
            self.game._resolve_timed_event()

        self.assertEqual(self.alice.life, 22)
        self.assertEqual(first.counters["life"], 1)
        self.assertEqual(second.counters["life"], 1)

    def test_removing_aura_removes_its_counters(self) -> None:
        artifact = self.permanent(self.alice, SOL_RING)
        aura = self.permanent(self.alice, LIVING_ARTIFACT, attached=artifact)
        aura.counters["life"] = 4
        self.game._move_card(aura, Zone.GRAVEYARD)
        self.assertEqual(aura.counters, {})


if __name__ == "__main__":
    unittest.main()
