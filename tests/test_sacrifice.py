import unittest

from beta_magic import Card, CardType, GameState, PlayerState, TurnPhase, Zone
from beta_magic.card_defs.artifacts import SOL_RING
from beta_magic.card_defs.black import SACRIFICE
from beta_magic.card_defs.green import LIVING_LANDS
from beta_magic.card_defs.lands import FOREST
from beta_magic.card_defs.red import HILL_GIANT
from beta_magic.card_defs.white import HOLY_STRENGTH
from beta_magic.card_defs.blue import ANIMATE_ARTIFACT


class SacrificeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alice = PlayerState.with_deck("a", "Alice", [FOREST] * 10)
        self.bob = PlayerState.with_deck("b", "Bob", [FOREST] * 10)
        self.game = GameState([self.alice, self.bob])
        self.game.start(opening_hand_size=0, shuffle=False)
        self.game.current_phase = TurnPhase.MAIN
        self.game.priority_player_index = 0

    @staticmethod
    def add_card(player, definition, zone=Zone.BATTLEFIELD) -> Card:
        card = Card(
            definition,
            player.id,
            controller_id=player.id if zone is Zone.BATTLEFIELD else None,
            base_controller_id=player.id if zone is Zone.BATTLEFIELD else None,
            zone=zone,
        )
        player.cards_in(zone).append(card)
        return card

    def cast_and_resolve(self, creature: Card) -> Card:
        spell = self.add_card(self.alice, SACRIFICE, Zone.HAND)
        self.alice.mana_pool.black = 1
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((creature,))
        self.game.pass_priority(self.bob.id)
        self.game.pass_priority(self.alice.id)
        return spell

    def test_sacrifices_creature_without_regeneration_and_adds_cost_in_black(self):
        giant = self.add_card(self.alice, HILL_GIANT)
        spell = self.cast_and_resolve(giant)
        self.assertEqual(giant.zone, Zone.GRAVEYARD)
        self.assertEqual(spell.zone, Zone.GRAVEYARD)
        self.assertEqual(self.alice.mana_pool.black, 4)
        self.assertIsNone(self.game.pending_destruction)

    def test_only_controlled_creatures_are_legal(self):
        own = self.add_card(self.alice, HILL_GIANT)
        opposing = self.add_card(self.bob, HILL_GIANT)
        artifact = self.add_card(self.alice, SOL_RING)
        spell = self.add_card(self.alice, SACRIFICE, Zone.HAND)
        self.alice.mana_pool.black = 1
        self.game.begin_cast(spell)
        self.assertIn(own, self.game.legal_targets_for())
        self.assertNotIn(opposing, self.game.legal_targets_for())
        self.assertNotIn(artifact, self.game.legal_targets_for())

    def test_creature_with_lethal_damage_is_not_legal(self):
        giant = self.add_card(self.alice, HILL_GIANT)
        giant.damage = self.game.creature_toughness(giant)
        spell = self.add_card(self.alice, SACRIFICE, Zone.HAND)
        self.alice.mana_pool.black = 1
        with self.assertRaisesRegex(RuntimeError, "no legal targets"):
            self.game.begin_cast(spell)

    def test_animated_artifact_uses_printed_artifact_cost(self):
        ring = self.add_card(self.alice, SOL_RING)
        aura = self.add_card(self.alice, ANIMATE_ARTIFACT)
        aura.enchanted_card_id = ring.id
        self.assertIn(CardType.CREATURE, self.game.card_types(ring))
        self.cast_and_resolve(ring)
        self.assertEqual(self.alice.mana_pool.black, 1)

    def test_animated_land_and_tokens_have_zero_casting_cost(self):
        self.add_card(self.alice, LIVING_LANDS)
        forest = self.add_card(self.alice, FOREST)
        self.assertIn(CardType.CREATURE, self.game.card_types(forest))
        self.cast_and_resolve(forest)
        self.assertEqual(self.alice.mana_pool.black, 0)

    def test_attached_enchantment_does_not_increase_mana(self):
        giant = self.add_card(self.alice, HILL_GIANT)
        aura = self.add_card(self.alice, HOLY_STRENGTH)
        aura.enchanted_card_id = giant.id
        self.cast_and_resolve(giant)
        self.assertEqual(self.alice.mana_pool.black, 4)

    def test_can_be_cast_as_standalone_interrupt(self):
        giant = self.add_card(self.alice, HILL_GIANT)
        spell = self.add_card(self.alice, SACRIFICE, Zone.HAND)
        self.alice.mana_pool.black = 1
        self.game.begin_cast(spell)
        self.game.complete_pending_cast((giant,))
        self.assertEqual(spell.zone, Zone.STACK)
        self.assertEqual(self.game.interruptible_spell_id, spell.id)


if __name__ == "__main__":
    unittest.main()
