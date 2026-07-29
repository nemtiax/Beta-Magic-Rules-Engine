"""The straightforward activated-mana artifacts in Limited Edition Beta."""

from .cards import ActivatedManaAbility, CardDefinition
from .mana import ManaCost
from .types import CardType, Color


def _mox(name: str, color: Color) -> CardDefinition:
    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.ARTIFACT}),
        mana_cost=ManaCost.parse("{0}"),
        rules_text=(
            f"Tap to add {{{color.value}}} to your mana pool. "
            "This ability can be played as an interrupt."
        ),
        activated_abilities=(ActivatedManaAbility(color),),
    )


MOX_PEARL = _mox("Mox Pearl", Color.WHITE)
MOX_SAPPHIRE = _mox("Mox Sapphire", Color.BLUE)
MOX_JET = _mox("Mox Jet", Color.BLACK)
MOX_RUBY = _mox("Mox Ruby", Color.RED)
MOX_EMERALD = _mox("Mox Emerald", Color.GREEN)

SOL_RING = CardDefinition(
    name="Sol Ring",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{1}"),
    rules_text=(
        "Tap to add {C}{C} to your mana pool. "
        "This ability can be played as an interrupt."
    ),
    activated_abilities=(
        ActivatedManaAbility(Color.COLORLESS, amount=2),
    ),
)

BLACK_LOTUS = CardDefinition(
    name="Black Lotus",
    card_types=frozenset({CardType.ARTIFACT}),
    mana_cost=ManaCost.parse("{0}"),
    rules_text=(
        "Tap to add three mana of any single color to your mana pool, "
        "then destroy Black Lotus. This ability can be played as an interrupt."
    ),
    activated_abilities=tuple(
        ActivatedManaAbility(
            color,
            amount=3,
            sacrifice_source=True,
        )
        for color in (
            Color.WHITE,
            Color.BLUE,
            Color.BLACK,
            Color.RED,
            Color.GREEN,
        )
    ),
)

MOXEN = (MOX_PEARL, MOX_SAPPHIRE, MOX_JET, MOX_RUBY, MOX_EMERALD)
MANA_ARTIFACTS = MOXEN + (SOL_RING, BLACK_LOTUS)
