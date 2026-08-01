"""Small definition builders shared across printed-color modules."""

from ..abilities import TargetRequirement
from ..cards import CardDefinition
from ..effects import ChangeTargetColorEffect
from ..mana import ManaCost
from ..types import CardType, Color, Zone


def lace(name: str, color: Color) -> CardDefinition:
    """Build one member of Limited Edition Beta's five-card Lace cycle."""

    return CardDefinition(
        name=name,
        card_types=frozenset({CardType.INTERRUPT}),
        mana_cost=ManaCost.parse(f"{{{color.value}}}"),
        rules_text=(
            f"Change one card being played or already in play to "
            f"{color.name.lower()}. Its costs remain unchanged."
        ),
        colors=frozenset({color}),
        target_requirement=TargetRequirement(
            zone=Zone.BATTLEFIELD,
            additional_zones=frozenset({Zone.STACK}),
        ),
        spell_effects=(ChangeTargetColorEffect(color),),
    )


__all__ = ["lace"]
