"""A testable human-versus-bots booster draft coordinator."""
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Protocol, Sequence

from .bot import DraftBot
from .cards import Card, CardCatalog, default_catalog
from .models import DraftConfig, DraftContext
from .packs import BetaBoosterGenerator, NoBasicLandBetaBoosterGenerator


class _PackGenerator(Protocol):
    def generate_pack(self) -> tuple[Card, ...]: ...


class _Bot(Protocol):
    @property
    def pool(self) -> tuple[str, ...]: ...

    def pick_with_details(
        self, pack: Sequence[str], *, context: DraftContext | None = None
    ): ...


@dataclass(frozen=True)
class DraftCard:
    """One physical card instance moving around the draft table."""

    id: str
    card: Card


class DraftSession:
    """Coordinate one human seat and a configurable number of bot seats."""

    def __init__(
        self,
        *,
        catalog: CardCatalog | None = None,
        generator: _PackGenerator | None = None,
        bots: Sequence[_Bot] | None = None,
        table_size: int = 8,
        rounds: int = 3,
        no_basic_lands: bool = False,
        color_balanced: bool = False,
        seed: int | None = None,
    ) -> None:
        if type(table_size) is not int or table_size < 2:
            raise ValueError("table_size must be an integer of at least two")
        if type(rounds) is not int or rounds < 1:
            raise ValueError("rounds must be a positive integer")
        self.catalog = default_catalog() if catalog is None else catalog
        self.table_size = table_size
        self.rounds = rounds
        self.pack_size = 15
        self.no_basic_lands = no_basic_lands
        self.color_balanced = color_balanced
        if generator is None:
            rng = random.Random(seed)
            generator_type = (
                NoBasicLandBetaBoosterGenerator
                if no_basic_lands
                else BetaBoosterGenerator
            )
            generator = generator_type(
                self.catalog,
                rng=rng,
                color_balanced=color_balanced,
            )
        self.generator = generator
        if bots is None:
            config = DraftConfig(
                total_picks=rounds * self.pack_size,
                pack_size=self.pack_size,
                table_size=table_size,
            )
            bots = tuple(
                DraftBot(config=config, catalog=self.catalog)
                for _ in range(table_size - 1)
            )
        if len(bots) != table_size - 1:
            raise ValueError("one bot is required for every non-human seat")
        self.bots = tuple(bots)
        self.round_number = 1
        self.pick_number = 1
        self.human_pool: list[DraftCard] = []
        self.packs: list[list[DraftCard]] = []
        self.pack_ids: list[str] = []
        self.complete = False
        self._open_round()

    @property
    def current_pack(self) -> tuple[DraftCard, ...]:
        return tuple(self.packs[0]) if self.packs else ()

    @property
    def passing_direction(self) -> str:
        return "left" if self.round_number % 2 else "right"

    def _open_round(self) -> None:
        self.packs = []
        self.pack_ids = []
        for origin in range(self.table_size):
            pack = self.generator.generate_pack()
            if len(pack) != self.pack_size:
                raise ValueError(
                    f"draft generator returned {len(pack)} cards; expected 15"
                )
            self.packs.append(
                [
                    DraftCard(
                        f"r{self.round_number}-o{origin}-s{slot}", card
                    )
                    for slot, card in enumerate(pack)
                ]
            )
            self.pack_ids.append(f"round-{self.round_number}-origin-{origin}")

    def pick(self, card_id: str) -> DraftCard:
        """Commit the human choice, let every bot pick, then pass packs."""

        if self.complete:
            raise RuntimeError("the draft is complete")
        index = next(
            (i for i, offered in enumerate(self.packs[0]) if offered.id == card_id),
            None,
        )
        if index is None:
            raise ValueError("that card is not in the current pack")
        chosen = self.packs[0].pop(index)
        self.human_pool.append(chosen)

        for seat, bot in enumerate(self.bots, start=1):
            pack = self.packs[seat]
            names = [offered.card.name for offered in pack]
            decision = bot.pick_with_details(
                names,
                context=DraftContext(
                    self.round_number,
                    self.pick_number,
                    self.pack_ids[seat],
                ),
            )
            pack.pop(decision.index)

        if self.pick_number == self.pack_size:
            if self.round_number == self.rounds:
                self.complete = True
                self.packs = []
                self.pack_ids = []
                return chosen
            self.round_number += 1
            self.pick_number = 1
            self._open_round()
            return chosen

        direction = 1 if self.round_number % 2 else -1
        passed_packs: list[list[DraftCard] | None] = [None] * self.table_size
        passed_ids: list[str | None] = [None] * self.table_size
        for seat in range(self.table_size):
            recipient = (seat + direction) % self.table_size
            passed_packs[recipient] = self.packs[seat]
            passed_ids[recipient] = self.pack_ids[seat]
        self.packs = [pack for pack in passed_packs if pack is not None]
        self.pack_ids = [pack_id for pack_id in passed_ids if pack_id is not None]
        self.pick_number += 1
        return chosen


__all__ = ["DraftCard", "DraftSession"]
