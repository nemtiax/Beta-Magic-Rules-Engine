"""The five Limited Edition Beta Circles of Protection."""

from .cards import ActivatedPreventDamageAbility, CardDefinition
from .mana import ManaCost
from .types import CardType, Color


def _circle(color: Color) -> CardDefinition:
    color_name = color.name.title()
    return CardDefinition(
        name=f"Circle of Protection: {color_name}",
        card_types=frozenset({CardType.ENCHANTMENT}),
        mana_cost=ManaCost.parse("{1}{W}"),
        rules_text=(
            f"{{1}}: Prevents all damage against you from one "
            f"{color_name.lower()} source."
        ),
        colors=frozenset({Color.WHITE}),
        activated_abilities=(
            ActivatedPreventDamageAbility(
                amount=None,
                mana_cost=ManaCost.parse("{1}"),
                tap_cost=False,
                source_color=color,
                controller_only=True,
            ),
        ),
    )


CIRCLE_OF_PROTECTION_BLACK = _circle(Color.BLACK)
CIRCLE_OF_PROTECTION_BLUE = _circle(Color.BLUE)
CIRCLE_OF_PROTECTION_GREEN = _circle(Color.GREEN)
CIRCLE_OF_PROTECTION_RED = _circle(Color.RED)
CIRCLE_OF_PROTECTION_WHITE = _circle(Color.WHITE)

CIRCLES_OF_PROTECTION = (
    CIRCLE_OF_PROTECTION_BLACK,
    CIRCLE_OF_PROTECTION_BLUE,
    CIRCLE_OF_PROTECTION_GREEN,
    CIRCLE_OF_PROTECTION_RED,
    CIRCLE_OF_PROTECTION_WHITE,
)
