"""Shared helpers that drive tests through the public rules-engine workflow."""

from collections.abc import Iterable

from beta_magic import (
    Card,
    CombatStep,
    GameState,
    PlayerState,
)


def cast_and_resolve(
    game: GameState,
    card: Card,
    targets: Iterable[Card | PlayerState] = (),
) -> None:
    """Cast a card, make any required target choice, and pass to resolution."""

    pending = game.begin_cast(card)
    if pending is not None:
        game.complete_pending_cast(tuple(targets))
    while game.stack or game.batch_abilities:
        player = game.players[game.priority_player_index]
        game.pass_priority(player.id)


def _close_combat_response_window(
    game: GameState, expected_step: CombatStep
) -> None:
    """Have both players pass a combat response window through public APIs."""

    while game.combat is not None and game.combat.step is expected_step:
        if game.priority_player_index is None:
            raise AssertionError("combat response window has no priority player")
        player = game.players[game.priority_player_index]
        game.pass_priority(player.id)


def declare_attackers(
    game: GameState,
    attackers: Iterable[Card],
    bands: Iterable[Iterable[Card]] = (),
) -> CombatStep:
    """Close pre-attack responses, then declare through the strict API."""

    _close_combat_response_window(game, CombatStep.ATTACK_RESPONSE)
    return game.declare_attackers(attackers, bands=bands)


def declare_blockers(
    game: GameState,
    assignments: dict[Card, Card | Iterable[Card]],
) -> CombatStep:
    """Close pre-block responses, then declare through the strict API."""

    _close_combat_response_window(game, CombatStep.ATTACKER_RESPONSE)
    return game.declare_blockers(assignments)
