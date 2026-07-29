"""Beta creatures with repeatable, self-targeted pump abilities."""

from .cards import ActivatedPumpAbility, CardDefinition
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility


SHIVAN_DRAGON = CardDefinition(
    name="Shivan Dragon",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{4}{R}{R}"),
    rules_text="Flying. {R}: +1/+0 until end of turn.",
    colors=frozenset({Color.RED}),
    subtypes=("Dragon",),
    power=5,
    toughness=5,
    abilities=frozenset({KeywordAbility.FLYING}),
    activated_abilities=(
        ActivatedPumpAbility(ManaCost.parse("{R}"), power=1),
    ),
)

FROZEN_SHADE = CardDefinition(
    name="Frozen Shade",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{B}"),
    rules_text="{B}: +1/+1 until end of turn.",
    colors=frozenset({Color.BLACK}),
    subtypes=("Shade",),
    power=0,
    toughness=1,
    activated_abilities=(
        ActivatedPumpAbility(ManaCost.parse("{B}"), power=1, toughness=1),
    ),
)

GRANITE_GARGOYLE = CardDefinition(
    name="Granite Gargoyle",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{R}"),
    rules_text="Flying. {R}: +0/+1 until end of turn.",
    colors=frozenset({Color.RED}),
    subtypes=("Gargoyle",),
    power=2,
    toughness=2,
    abilities=frozenset({KeywordAbility.FLYING}),
    activated_abilities=(
        ActivatedPumpAbility(ManaCost.parse("{R}"), toughness=1),
    ),
)

DRAGON_WHELP = CardDefinition(
    name="Dragon Whelp",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{R}{R}"),
    rules_text=(
        "Flying. {R}: +1/+0 until end of turn. If more than {R}{R}{R} "
        "is spent this way in a turn, destroy Dragon Whelp at end of turn."
    ),
    colors=frozenset({Color.RED}),
    subtypes=("Dragon",),
    power=2,
    toughness=3,
    abilities=frozenset({KeywordAbility.FLYING}),
    activated_abilities=(
        ActivatedPumpAbility(
            ManaCost.parse("{R}"),
            power=1,
            safe_activations_per_turn=3,
        ),
    ),
)

PUMP_CREATURES = (
    SHIVAN_DRAGON,
    FROZEN_SHADE,
    GRANITE_GARGOYLE,
    DRAGON_WHELP,
)
