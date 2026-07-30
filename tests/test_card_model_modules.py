import unittest

from beta_magic.abilities import (
    ActivatedDamageAbility,
    ActivatedManaAbility,
    TargetRequirement,
)
from beta_magic.cards import (
    ActivatedDamageAbility as CompatibleDamageAbility,
    ActivatedManaAbility as CompatibleManaAbility,
    ContinuousEffect as CompatibleContinuousEffect,
    DamageEffect as CompatibleDamageEffect,
    TargetRequirement as CompatibleTargetRequirement,
)
from beta_magic.effects import ContinuousEffect, DamageEffect


class CardModelModuleTests(unittest.TestCase):
    def test_cards_module_reexports_identical_ability_types(self) -> None:
        self.assertIs(CompatibleDamageAbility, ActivatedDamageAbility)
        self.assertIs(CompatibleManaAbility, ActivatedManaAbility)
        self.assertIs(CompatibleTargetRequirement, TargetRequirement)

    def test_cards_module_reexports_identical_effect_types(self) -> None:
        self.assertIs(CompatibleContinuousEffect, ContinuousEffect)
        self.assertIs(CompatibleDamageEffect, DamageEffect)


if __name__ == "__main__":
    unittest.main()
