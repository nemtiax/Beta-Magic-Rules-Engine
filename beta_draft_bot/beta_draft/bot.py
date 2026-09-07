"""Stateful public interface: submit a pack, receive a card, repeat."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import tempfile

from .cards import Card, CardCatalog, COLORS, default_catalog
from .models import ColorPlan, DraftConfig, DraftContext, PickEvaluation
from .strategy import color_plans, eligible, rank_cards

SCHEMA_VERSION = 1


class DraftBot:
    """One instance per drafter. Calls that change state are not thread-safe.

    pick(pack) -> canonical card name, and remembers the pick.
    rank(pack) -> scored choices, without changing any state.
    pick_with_details(pack) -> scored choice, and remembers the pick.
    record_pick(pack, card) -> record a caller-selected override.

    The caller owns pack passing, collation, card instances and draft termination.
    A nonempty all-excluded pack still produces a forced pick with eligible=False.
    """

    def __init__(self, *, config: DraftConfig | None = None,
                 pool: Sequence[str] = (), catalog: CardCatalog | None = None):
        self.config = config if config is not None else DraftConfig()
        if not isinstance(self.config, DraftConfig):
            raise TypeError("config must be a DraftConfig")
        self.catalog = catalog if catalog is not None else default_catalog()
        for name in self.config.banned_cards:
            self.catalog.get(name)
        self._pool = list(self._cards(pool, allow_empty=True))
        self._observations: dict[tuple[int, str], dict[str, float]] = {}
        self._last_context: DraftContext | None = None

    @property
    def pool(self) -> tuple[str, ...]:
        """Read-only ordered picks, including duplicates and forced dead picks."""
        return tuple(c.name for c in self._pool)

    def _cards(self, names: Sequence[str], *, allow_empty: bool = False) -> tuple[Card, ...]:
        if isinstance(names, (str, bytes)) or not isinstance(names, Sequence):
            raise TypeError("A pack or pool must be a sequence of card-name strings")
        cards = tuple(self.catalog.get(name) for name in names)
        if not cards and not allow_empty:
            raise ValueError("Cannot pick from an empty pack")
        return cards

    def _context(self, context: DraftContext | None) -> DraftContext:
        if context is not None:
            if not isinstance(context, DraftContext):
                raise TypeError("context must be a DraftContext")
            result = context
        elif self._last_context is not None:
            last = self._last_context
            if last.pick_number == self.config.pack_size:
                result = DraftContext(last.pack_number + 1, 1)
            else:
                result = DraftContext(last.pack_number, last.pick_number + 1)
        else:
            number = len(self._pool)
            result = DraftContext(number // self.config.pack_size + 1,
                                  number % self.config.pack_size + 1)
        if result.pick_number > self.config.pack_size:
            raise ValueError("context.pick_number exceeds configured pack_size")
        return result

    def _observe(self, pack: tuple[Card, ...], context: DraftContext):
        # A pack seen on the wheel is correlated evidence, not a new pack.
        # Explicit IDs are best; the seat approximation assumes an ordinary table.
        origin = ("id:" + context.pack_id if context.pack_id is not None else
                  "seat:" + str((context.pick_number - 1) % self.config.table_size))
        key = (context.pack_number, origin)
        observations = {k: dict(v) for k, v in self._observations.items()}
        evidence = {c: 0.0 for c in COLORS}
        if context.pick_number > 1:
            lateness = (context.pick_number - 1) / max(1, self.config.pack_size - 1)
            for card in pack:
                if (card.colors and eligible(card, self.config)
                        and not card.has("sideboard")):
                    color = card.colors[0]
                    evidence[color] = max(evidence[color], max(0, card.rating - 2.8) * lateness)
        previous = observations.get(key, {c: 0.0 for c in COLORS})
        observations[key] = {c: max(previous[c], evidence[c]) for c in COLORS}
        return observations

    def _signals(self, observations, context: DraftContext) -> dict[str, float]:
        signals = {c: 0.0 for c in COLORS}
        for (round_number, _), evidence in observations.items():
            age = context.pack_number - round_number
            if age < 0 or age % 2:
                continue  # the opposite passing direction is a different signal
            decay = 0.35 ** (age // 2)
            for color in COLORS:
                signals[color] += decay * evidence[color]
        return {c: min(3.0, value) for c, value in signals.items()}

    def _prepare(self, pack: Sequence[str], context: DraftContext | None):
        cards = self._cards(pack)
        current = self._context(context)
        observations = self._observe(cards, current)
        rankings, _ = rank_cards(tuple(self._pool), cards, self.config,
                                 self._signals(observations, current), len(self._pool))
        return rankings, current, observations

    def rank(self, pack: Sequence[str], *, context: DraftContext | None = None) -> tuple[PickEvaluation, ...]:
        """Preview every candidate, including duplicate indices, without learning or picking."""
        return self._prepare(pack, context)[0]

    def _commit(self, choice: PickEvaluation, context: DraftContext, observations) -> None:
        self._pool.append(self.catalog.get(choice.card))
        self._observations = observations
        self._last_context = context

    def pick_with_details(self, pack: Sequence[str], *, context: DraftContext | None = None) -> PickEvaluation:
        rankings, current, observations = self._prepare(pack, context)
        choice = rankings[0]
        self._commit(choice, current, observations)
        return choice

    def pick(self, pack: Sequence[str], *, context: DraftContext | None = None) -> str:
        return self.pick_with_details(pack, context=context).card

    def record_pick(self, pack: Sequence[str], card: str, *, context: DraftContext | None = None) -> PickEvaluation:
        """Record a human/external override; the chosen card must actually be in this pack."""
        name = self.catalog.get(card).name
        rankings, current, observations = self._prepare(pack, context)
        matches = [e for e in rankings if e.card == name]
        if not matches:
            raise ValueError(f"Chosen card {name!r} is not in the pack")
        choice = min(matches, key=lambda e: e.index)
        self._commit(choice, current, observations)
        return choice

    def color_plans(
        self,
        *,
        context: DraftContext | None = None,
        pack: Sequence[str] | None = None,
    ) -> tuple[ColorPlan, ...]:
        """Diagnostic hypothesis weights, not a deck or calibrated probabilities.

        Supplying ``pack`` includes the same current-pack availability evidence
        used by :meth:`rank`, without recording an observation or changing the
        bot's state.
        """
        current = self._context(context)
        observations = self._observations
        if pack is not None:
            observations = self._observe(self._cards(pack, allow_empty=True), current)
        pool = tuple(c for c in self._pool if eligible(c, self.config) and not c.has("basic"))
        progress = min(1.0, len(self._pool) / max(1, self.config.total_picks - 1))
        return tuple(sorted(color_plans(pool, self._signals(observations, current), progress),
                            key=lambda p: -p.weight))

    def to_dict(self) -> dict:
        """A detached, versioned JSON-safe checkpoint."""
        return {
            "schema_version": SCHEMA_VERSION,
            "config": asdict(self.config),
            "pool": list(self.pool),
            "last_context": asdict(self._last_context) if self._last_context else None,
            "observations": [
                {"pack_number": number, "origin": origin, "evidence": dict(evidence)}
                for (number, origin), evidence in sorted(self._observations.items())
            ],
        }

    @classmethod
    def from_dict(cls, state: dict) -> DraftBot:
        if not isinstance(state, dict):
            raise ValueError("Draft state must be an object")
        if type(state.get("schema_version")) is not int or state["schema_version"] != SCHEMA_VERSION:
            raise ValueError("Unsupported draft-state schema version")
        required = {"schema_version", "config", "pool", "last_context", "observations"}
        if set(state) != required:
            raise ValueError("Draft state has missing or unknown fields")
        if not isinstance(state["config"], dict):
            raise ValueError("State config must be an object")
        bot = cls(config=DraftConfig(**state["config"]), pool=state["pool"])
        raw_context = state["last_context"]
        if raw_context is not None:
            if not isinstance(raw_context, dict):
                raise ValueError("last_context must be an object or null")
            bot._last_context = bot._context(DraftContext(**raw_context))
        if not isinstance(state["observations"], list):
            raise ValueError("observations must be an array")
        for entry in state["observations"]:
            if not isinstance(entry, dict) or set(entry) != {"pack_number", "origin", "evidence"}:
                raise ValueError("Malformed signal observation")
            number, origin, evidence = entry["pack_number"], entry["origin"], entry["evidence"]
            if type(number) is not int or number < 1 or not isinstance(origin, str) or not origin:
                raise ValueError("Invalid signal observation identity")
            if not isinstance(evidence, dict) or set(evidence) != set(COLORS):
                raise ValueError("Signal evidence must contain W, U, B, R and G")
            if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 5
                   for v in evidence.values()):
                raise ValueError("Signal evidence must be finite and between 0 and 5")
            if (number, origin) in bot._observations:
                raise ValueError("Duplicate signal observation identity")
            bot._observations[number, origin] = dict(evidence)
        return bot

    def save(self, path: str | Path) -> None:
        """Atomically replace a JSON checkpoint; its parent directory must exist."""
        destination = Path(path)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".beta-draft-",
                                             suffix=".json", dir=destination.parent, delete=False) as file:
                temporary = Path(file.name)
                json.dump(self.to_dict(), file, ensure_ascii=False, indent=2, allow_nan=False)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    @classmethod
    def load(cls, path: str | Path) -> DraftBot:
        with Path(path).open(encoding="utf-8") as file:
            return cls.from_dict(json.load(file))
