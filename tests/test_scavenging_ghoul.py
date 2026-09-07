import unittest

from beta_magic import (
    Card,
    DamageIncidentKind,
    DamageResolutionStep,
    GameState,
    PlayerState,
    TurnPhase,
    Zone,
)
from beta_magic.card_defs.black import SCAVENGING_GHOUL
from beta_magic.card_defs.green import GRIZZLY_BEARS
from beta_magic.card_defs.artifacts import SOL_RING


class ScavengingGhoulTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [SOL_RING] * 20)
        self.bob = PlayerState.with_deck("b", "Bob", [SOL_RING] * 20)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)

    @staticmethod
    def permanent(player, definition, *, token=False):
        card = Card(
            definition,
            owner_id=player.id,
            controller_id=player.id,
            base_controller_id=player.id,
            zone=Zone.BATTLEFIELD,
            is_token=token,
        )
        player.battlefield.append(card)
        return card

    def finish_turn(self):
        self.game.current_phase = TurnPhase.END
        self.game.next_turn()

    def test_deaths_are_collected_only_at_end_of_turn(self) -> None:
        ghoul = self.permanent(self.alice, SCAVENGING_GHOUL)
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game._move_card(bear, Zone.GRAVEYARD)
        self.assertEqual(ghoul.counters, {})
        self.finish_turn()
        self.assertEqual(ghoul.counters, {"corpse": 1})

    def test_ghoul_cast_after_death_still_collects_it(self) -> None:
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game._move_card(bear, Zone.GRAVEYARD)
        ghoul = self.permanent(self.alice, SCAVENGING_GHOUL)
        self.finish_turn()
        self.assertEqual(ghoul.counters["corpse"], 1)

    def test_all_ghouls_receive_each_death(self) -> None:
        first = self.permanent(self.alice, SCAVENGING_GHOUL)
        second = self.permanent(self.bob, SCAVENGING_GHOUL)
        self.game._move_card(self.permanent(self.alice, GRIZZLY_BEARS), Zone.GRAVEYARD)
        self.game._move_card(self.permanent(self.bob, GRIZZLY_BEARS), Zone.GRAVEYARD)
        self.finish_turn()
        self.assertEqual(first.counters["corpse"], 2)
        self.assertEqual(second.counters["corpse"], 2)

    def test_ghoul_does_not_count_itself_after_leaving_play(self) -> None:
        ghoul = self.permanent(self.alice, SCAVENGING_GHOUL)
        self.game._move_card(ghoul, Zone.GRAVEYARD)
        self.finish_turn()
        self.assertEqual(ghoul.counters, {})

    def test_creature_token_death_counts(self) -> None:
        ghoul = self.permanent(self.alice, SCAVENGING_GHOUL)
        token = self.permanent(self.bob, GRIZZLY_BEARS, token=True)
        self.game._move_card(token, Zone.GRAVEYARD)
        self.finish_turn()
        self.assertEqual(ghoul.counters["corpse"], 1)

    def test_exiled_creature_does_not_count(self) -> None:
        ghoul = self.permanent(self.alice, SCAVENGING_GHOUL)
        bear = self.permanent(self.bob, GRIZZLY_BEARS)
        self.game._move_card(bear, Zone.EXILE)
        self.finish_turn()
        self.assertEqual(ghoul.counters, {})

    def test_counter_regenerates_and_is_spent(self) -> None:
        ghoul = self.permanent(self.alice, SCAVENGING_GHOUL)
        ghoul.counters["corpse"] = 1
        ghoul.damage = 2
        self.game._begin_damage_incident(DamageIncidentKind.SINGLE_SOURCE)
        # The damage was already marked for this focused regeneration-window test.
        self.game.pending_damage.step = DamageResolutionStep.REGENERATION
        self.game.priority_player_index = 0
        self.game.activate_ability(self.alice.id, ghoul, 0)
        self.assertEqual(ghoul.counters["corpse"], 0)
        self.assertEqual(ghoul.damage, 0)
        self.assertTrue(ghoul.tapped)


if __name__ == "__main__":
    unittest.main()
