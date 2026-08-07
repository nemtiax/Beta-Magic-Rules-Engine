"""Per-player notification state for the hotseat UI."""

from __future__ import annotations

from collections.abc import Iterable


class UiMessageStore:
    """Keep each player's latest UI message independently."""

    def __init__(self, player_ids: Iterable[str], initial: str = "") -> None:
        self._messages = {player_id: initial for player_id in player_ids}

    def reset(self, player_ids: Iterable[str], initial: str = "") -> None:
        self._messages = {player_id: initial for player_id in player_ids}

    def message_for(self, player_id: str) -> str:
        return self._messages.get(player_id, "")

    def broadcast(self, message: str) -> None:
        for player_id in self._messages:
            self._messages[player_id] = message

    def tell(self, player_id: str, message: str) -> None:
        if player_id not in self._messages:
            raise KeyError(f"player {player_id!r} has no UI message channel")
        self._messages[player_id] = message

    def prompt(
        self,
        player_id: str,
        message: str,
        *,
        observer_message: str | None = None,
    ) -> None:
        """Publish a prompt to one player and a companion message to others."""

        for recipient_id in self._messages:
            self._messages[recipient_id] = (
                message
                if recipient_id == player_id
                else observer_message if observer_message is not None else message
            )
