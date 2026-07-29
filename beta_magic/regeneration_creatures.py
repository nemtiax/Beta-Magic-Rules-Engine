"""Straightforward Beta creatures with paid regeneration abilities."""

from .cards import ActivatedRegenerationAbility, CardDefinition
from .mana import ManaCost
from .types import CardType, Color, KeywordAbility


def _regeneration(cost: str) -> tuple[ActivatedRegenerationAbility, ...]:
    return (ActivatedRegenerationAbility(ManaCost.parse(cost)),)


DRUDGE_SKELETONS = CardDefinition(
    name="Drudge Skeletons",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{1}{B}"),
    rules_text="{B}: Regenerate Drudge Skeletons.",
    colors=frozenset({Color.BLACK}),
    subtypes=("Skeletons",),
    power=1,
    toughness=1,
    activated_abilities=_regeneration("{B}"),
)

UTHDEN_TROLL = CardDefinition(
    name="Uthden Troll",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{R}"),
    rules_text="{R}: Regenerate Uthden Troll.",
    colors=frozenset({Color.RED}),
    subtypes=("Troll",),
    power=2,
    toughness=2,
    activated_abilities=_regeneration("{R}"),
)

WILL_O_THE_WISP = CardDefinition(
    name="Will-o'-the-Wisp",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{B}"),
    rules_text="Flying. {B}: Regenerate Will-o'-the-Wisp.",
    colors=frozenset({Color.BLACK}),
    subtypes=("Will-O'-The-Wisp",),
    power=0,
    toughness=1,
    abilities=frozenset({KeywordAbility.FLYING}),
    activated_abilities=_regeneration("{B}"),
)

WALL_OF_BONE = CardDefinition(
    name="Wall of Bone",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{B}"),
    rules_text="{B}: Regenerate Wall of Bone.",
    colors=frozenset({Color.BLACK}),
    subtypes=("Wall",),
    power=1,
    toughness=4,
    activated_abilities=_regeneration("{B}"),
)

WALL_OF_BRAMBLES = CardDefinition(
    name="Wall of Brambles",
    card_types=frozenset({CardType.CREATURE}),
    mana_cost=ManaCost.parse("{2}{G}"),
    rules_text="{G}: Regenerate Wall of Brambles.",
    colors=frozenset({Color.GREEN}),
    subtypes=("Wall",),
    power=2,
    toughness=3,
    activated_abilities=_regeneration("{G}"),
)

REGENERATION_CREATURES = (
    DRUDGE_SKELETONS,
    UTHDEN_TROLL,
    WILL_O_THE_WISP,
    WALL_OF_BONE,
    WALL_OF_BRAMBLES,
)
