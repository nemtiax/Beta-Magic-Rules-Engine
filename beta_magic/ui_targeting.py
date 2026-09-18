"""Human-readable descriptions of pending UI target choices."""

from __future__ import annotations

from collections.abc import Iterable

from .abilities import TargetRequirement
from .types import CardType, Color, Zone


_TYPE_ORDER = {
    CardType.ARTIFACT: 0,
    CardType.CREATURE: 1,
    CardType.ENCHANTMENT: 2,
    CardType.LAND: 3,
    CardType.INSTANT: 4,
    CardType.INTERRUPT: 5,
    CardType.SORCERY: 6,
}

_ZONE_ORDER = {
    Zone.BATTLEFIELD: 0,
    Zone.STACK: 1,
    Zone.GRAVEYARD: 2,
    Zone.HAND: 3,
    Zone.LIBRARY: 4,
    Zone.EXILE: 5,
    Zone.ANTE: 6,
}


def _join_options(options: Iterable[str]) -> str:
    values = tuple(options)
    if len(values) < 2:
        return values[0] if values else ""
    if len(values) == 2:
        return f"{values[0]} or {values[1]}"
    return f"{', '.join(values[:-1])}, or {values[-1]}"


def _pluralize(noun: str) -> str:
    if noun.endswith("y") and not noun.endswith(("ay", "ey", "iy", "oy", "uy")):
        return f"{noun[:-1]}ies"
    if noun.endswith(("s", "x", "z", "ch", "sh")):
        return f"{noun}es"
    return f"{noun}s"


def _type_description(
    requirement: TargetRequirement,
    *,
    zone: Zone,
    plural: bool,
) -> str:
    types = tuple(
        sorted(
            requirement.any_card_types or requirement.card_types,
            key=lambda card_type: _TYPE_ORDER[card_type],
        )
    )
    type_names = [card_type.value.lower() for card_type in types]

    if requirement.any_card_types:
        noun = _join_options(
            _pluralize(name) if plural else name for name in type_names
        )
    elif type_names:
        if plural:
            type_names[-1] = _pluralize(type_names[-1])
        noun = " ".join(type_names)
    elif zone is Zone.BATTLEFIELD:
        noun = "permanents" if plural else "permanent"
    elif zone is Zone.STACK:
        noun = "spells" if plural else "spell"
    else:
        noun = "cards" if plural else "card"

    if zone is Zone.STACK and "spell" not in noun:
        noun = f"{noun} {'spells' if plural else 'spell'}"
    elif zone not in {Zone.BATTLEFIELD, Zone.STACK} and types:
        noun = f"{noun} {'cards' if plural else 'card'}"

    prefixes: list[str] = []
    if requirement.blocking_only:
        prefixes.append("blocking")
    if requirement.tapped_only:
        prefixes.append("tapped")
    elif requirement.untapped_only:
        prefixes.append("untapped")
    if requirement.color is not None:
        prefixes.append(requirement.color.name.lower())
    prefixes.extend(
        f"non{color.name.lower()}"
        for color in sorted(requirement.excluded_colors, key=lambda item: item.value)
        if color is not Color.COLORLESS
    )
    prefixes.extend(
        f"non{card_type.value.lower()}"
        for card_type in sorted(
            requirement.excluded_card_types,
            key=lambda card_type: _TYPE_ORDER[card_type],
        )
    )
    if requirement.subtypes:
        prefixes.extend(sorted(requirement.subtypes))
    prefixes.extend(
        f"non-{subtype}" for subtype in sorted(requirement.excluded_subtypes)
    )
    if prefixes:
        noun = f"{' '.join(prefixes)} {noun}"
    if requirement.maximum_power is not None:
        noun = f"{noun} with power {requirement.maximum_power} or less"
    return noun


def _location_description(
    requirement: TargetRequirement,
    zone: Zone,
) -> str:
    if zone is Zone.BATTLEFIELD:
        if requirement.controller_only:
            return " you control"
        if requirement.owner_only:
            return " you own in play"
        if requirement.defending_player_only:
            return " controlled by the defending player"
        if requirement.active_player_only:
            return " controlled by the active player"
        return " in play"
    if zone is Zone.STACK:
        return " being cast"
    if zone is Zone.GRAVEYARD:
        return " in your graveyard" if requirement.owner_only else " in a graveyard"
    if zone is Zone.HAND:
        return " in your hand" if requirement.owner_only else " in a hand"
    if zone is Zone.LIBRARY:
        return " in your library" if requirement.owner_only else " in a library"
    if zone is Zone.EXILE:
        return " set aside"
    if zone is Zone.ANTE:
        return " in ante"
    return f" in {zone.value}"


def _card_target_phrase(
    requirement: TargetRequirement,
    zone: Zone,
    *,
    plural: bool,
) -> str:
    noun = _type_description(requirement, zone=zone, plural=plural)
    article = "" if plural else "a "
    return f"{article}target {noun}{_location_description(requirement, zone)}"


def _player_target_phrase(requirement: TargetRequirement, *, plural: bool) -> str:
    if requirement.opponent_only:
        return "opponents" if plural else "your opponent"
    if requirement.defending_player_only:
        return "defending players" if plural else "the defending player"
    if requirement.active_player_only:
        return "active players" if plural else "the active player"
    return "target players" if plural else "a target player"


def target_choice_prompt(
    requirement: TargetRequirement,
    source_name: str,
    *,
    target_zones: frozenset[Zone] | None = None,
    target_count: int | None = None,
    detail: str | None = None,
) -> str:
    """Describe the legal kind and location of a pending target choice."""

    zones = target_zones
    if zones is None:
        zones = requirement.additional_zones | (
            frozenset({requirement.zone})
            if requirement.zone is not None
            else frozenset()
        )
    count = (
        target_count
        if requirement.count_equals_x and target_count is not None
        else requirement.count
    )
    plural = requirement.any_number or count != 1
    phrases = [
        _card_target_phrase(requirement, zone, plural=plural)
        for zone in sorted(zones, key=lambda zone: _ZONE_ORDER[zone])
    ]
    if requirement.players:
        phrases.append(_player_target_phrase(requirement, plural=plural))

    choices = _join_options(phrases)
    if requirement.any_number:
        choices = f"one or more {choices.removeprefix('target ')}"
    elif count != 1:
        choices = f"{count} {choices.removeprefix('target ')}"
    suffix = f" ({detail})" if detail else ""
    return f"Choose {choices} for {source_name}{suffix}."
