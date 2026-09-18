import unittest

import beta_magic
import beta_magic.card_defs as card_defs
import beta_magic.cards as cards
from beta_magic.cards import Card, CardDefinition


class CardModelModuleTests(unittest.TestCase):
    def test_cards_module_public_api_contains_only_card_models(self) -> None:
        self.assertEqual(cards.__all__, ["Card", "CardDefinition"])
        self.assertIs(cards.Card, Card)
        self.assertIs(cards.CardDefinition, CardDefinition)

    def test_cards_module_does_not_reexport_abilities_or_effects(self) -> None:
        self.assertFalse(hasattr(cards, "ActivatedManaAbility"))
        self.assertFalse(hasattr(cards, "TargetRequirement"))
        self.assertFalse(hasattr(cards, "ContinuousEffect"))
        self.assertFalse(hasattr(cards, "DamageEffect"))

    def test_card_defs_package_exposes_only_catalog_access(self) -> None:
        self.assertEqual(
            card_defs.__all__, ["ALL_CARDS", "CARDS_BY_NAME", "card_named"]
        )
        self.assertFalse(hasattr(card_defs, "LIGHTNING_BOLT"))
        self.assertFalse(hasattr(card_defs, "TARGETED_DAMAGE_SPELLS"))

    def test_root_package_does_not_mirror_card_authoring_modules(self) -> None:
        self.assertFalse(hasattr(beta_magic, "LIGHTNING_BOLT"))
        self.assertFalse(hasattr(beta_magic, "ActivatedManaAbility"))
        self.assertFalse(hasattr(beta_magic, "DamageEffect"))


if __name__ == "__main__":
    unittest.main()
