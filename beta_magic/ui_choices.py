"""Transient dialog and picker state for the Qt hotseat UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from .cards import Card


@dataclass
class TransientChoiceState:
    """Own view-only choices which have not yet been submitted to the engine."""

    x_card_id: UUID | None = None
    x_value: int = 0
    x_maximum: int = 0
    x_minimum: int = 0
    x_ability_index: int | None = None
    land_type_card_id: UUID | None = None
    mode_card_id: UUID | None = None
    damage_source_card_id: UUID | None = None
    redirection_packet_id: UUID | None = None
    redirection_amount: int = 1
    redirection_maximum: int = 1
    library_search_filter: str = ""
    library_search_selected_id: UUID | None = None
    fireball_card_id: UUID | None = None
    fireball_x_value: int = 0
    fireball_x_maximum: int = 0
    fireball_target_keys: list[str] = field(default_factory=list)
    fork_original_spell_id: UUID | None = None
    fork_target_keys: list[str] = field(default_factory=list)
    fork_x_value: int = 0
    fork_generic_budget: int = 0

    def reset(self) -> None:
        self.x_card_id = None
        self.x_value = 0
        self.x_maximum = 0
        self.x_minimum = 0
        self.x_ability_index = None
        self.land_type_card_id = None
        self.mode_card_id = None
        self.damage_source_card_id = None
        self.redirection_packet_id = None
        self.redirection_amount = 1
        self.redirection_maximum = 1
        self.clear_library_search()
        self.clear_fireball()
        self.clear_fork()

    def begin_x(self, card: Card, maximum: int) -> None:
        self.x_card_id = card.id
        self.x_maximum = maximum
        self.x_value = maximum
        self.x_minimum = 0
        self.x_ability_index = None

    def begin_x_ability(
        self, card: Card, ability_index: int, maximum: int
    ) -> None:
        self.x_card_id = card.id
        self.x_ability_index = ability_index
        self.x_minimum = 1
        self.x_maximum = maximum
        self.x_value = maximum

    def adjust_x(self, delta: int) -> None:
        self.x_value = max(
            self.x_minimum,
            min(self.x_maximum, self.x_value + delta),
        )

    def clear_x(self) -> None:
        self.x_card_id = None
        self.x_value = 0
        self.x_maximum = 0
        self.x_minimum = 0
        self.x_ability_index = None

    def begin_redirection_amount(self, packet_id: UUID, maximum: int) -> None:
        self.redirection_packet_id = packet_id
        self.redirection_maximum = maximum
        self.redirection_amount = maximum

    def adjust_redirection(self, delta: int) -> None:
        self.redirection_amount = max(
            1,
            min(self.redirection_maximum, self.redirection_amount + delta),
        )

    def clear_redirection_amount(self) -> None:
        self.redirection_packet_id = None

    def clear_library_search(self) -> None:
        self.library_search_filter = ""
        self.library_search_selected_id = None

    def begin_fireball(self, card: Card, maximum: int) -> None:
        self.fireball_card_id = card.id
        self.fireball_x_value = maximum
        self.fireball_x_maximum = maximum
        self.fireball_target_keys.clear()

    def clear_fireball(self) -> None:
        self.fireball_card_id = None
        self.fireball_x_value = 0
        self.fireball_x_maximum = 0
        self.fireball_target_keys.clear()

    def begin_fork(
        self,
        original: Card,
        target_keys: list[str],
        x_value: int,
        generic_budget: int,
    ) -> None:
        self.fork_original_spell_id = original.id
        self.fork_target_keys = target_keys
        self.fork_x_value = x_value
        self.fork_generic_budget = generic_budget

    def clear_fork(self) -> None:
        self.fork_original_spell_id = None
        self.fork_target_keys.clear()
        self.fork_x_value = 0
        self.fork_generic_budget = 0
