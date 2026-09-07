"""PySide6/QML desktop client for drafting against the local bots."""
from __future__ import annotations

import argparse
from functools import lru_cache
import json
from pathlib import Path
import re
import sys
from typing import Sequence

from .bot import DraftBot
from .cards import Card
from .models import DraftConfig, DraftContext, PickEvaluation
from .session import DraftCard, DraftSession

try:
    from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtQml import QQmlApplicationEngine
except ModuleNotFoundError:  # Keep the bot's non-UI API dependency-free.
    QObject = object  # type: ignore[assignment,misc]
    Property = Signal = Slot = None  # type: ignore[assignment]
    QQuickStyle = None  # type: ignore[assignment,misc]


_COLOR_ORDER = {"W": 0, "U": 1, "B": 2, "R": 3, "G": 4}
_COLOR_NAMES = {
    "W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"
}
_REPOSITORY_IMAGE_ROOT = Path(__file__).resolve().parents[2] / "card_images"
_LEGACY_IMAGE_ROOT = Path(__file__).resolve().parents[1] / "card_images"
_IMAGE_ROOT = (
    _REPOSITORY_IMAGE_ROOT
    if (_REPOSITORY_IMAGE_ROOT / "manifest.json").is_file()
    else _LEGACY_IMAGE_ROOT
)
_IMAGE_MANIFEST = _IMAGE_ROOT / "manifest.json"
_POOL_GROUPS = (
    ("White", "#eee8c8"),
    ("Blue", "#76b5d6"),
    ("Black", "#8b8098"),
    ("Red", "#d96d50"),
    ("Green", "#78a970"),
    ("Multicolor", "#c7aa63"),
    ("Colorless", "#aaa7a1"),
    ("Lands", "#c9bea5"),
)


def _clean_text(value: str) -> str:
    return value.replace("â€”", "—").replace("�", "—")


def _compact_mana_cost(value: str) -> str:
    return re.sub(r"[{}]", "", value)


def _pool_group_index(card: Card) -> int:
    if card.is_land:
        return 7
    if len(card.colors) > 1:
        return 5
    if len(card.colors) == 1:
        return _COLOR_ORDER.get(card.colors[0], 6)
    return 6


def _pool_sort_key(offered: DraftCard) -> tuple:
    card = offered.card
    return (_pool_group_index(card), card.mana_value, card.name, offered.id)


def _card_colors(card: Card) -> tuple[str, str, str]:
    if card.is_land:
        return "#c9bea5", "#201d18", "#756b58"
    if len(card.colors) > 1:
        return "#c7aa63", "#211b10", "#745f32"
    color = card.colors[0] if card.colors else "C"
    return {
        "W": ("#eee8c8", "#242116", "#827b5d"),
        "U": ("#76b5d6", "#14242d", "#376f8b"),
        "B": ("#665d70", "#f3eff6", "#3d3547"),
        "R": ("#d96d50", "#281712", "#893c29"),
        "G": ("#78a970", "#172318", "#416b3d"),
        "C": ("#aaa7a1", "#242321", "#66635e"),
    }[color]


def _color_label(card: Card) -> str:
    if card.is_land:
        return "Land"
    if len(card.colors) > 1:
        return "Multicolor"
    if not card.colors:
        return "Colorless"
    return _COLOR_NAMES.get(card.colors[0], "Colorless")


@lru_cache(maxsize=1)
def _card_image_urls() -> dict[str, dict[str, str]]:
    """Load installed image paths without making card images a requirement."""

    if not _IMAGE_MANIFEST.is_file():
        return {}
    try:
        payload = json.loads(_IMAGE_MANIFEST.read_text(encoding="utf-8"))
        entries = payload["cards"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(entries, dict):
        return {}
    root = _IMAGE_ROOT.resolve()
    result: dict[str, dict[str, str]] = {}
    for name, entry in entries.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            continue
        urls: dict[str, str] = {}
        for key in ("art_crop", "full_card"):
            relative = entry.get(key)
            if not isinstance(relative, str):
                continue
            try:
                candidate = (root / relative).resolve()
                candidate.relative_to(root)
                if candidate.is_file() and candidate.stat().st_size:
                    urls[key] = candidate.as_uri()
            except (OSError, RuntimeError, ValueError):
                continue
        if urls:
            result[name] = urls
    return result


def _present_card(offered: DraftCard) -> dict:
    card = offered.card
    image_urls = _card_image_urls().get(card.name, {})
    background, foreground, border = _card_colors(card)
    stats = ""
    if card.power is not None and card.toughness is not None:
        stats = f"{card.power}/{card.toughness}"
    rules_text = card.rules_text
    if not rules_text and card.keywords:
        rules_text = ", ".join(card.keywords)
    return {
        "id": offered.id,
        "name": card.name,
        "manaCost": _compact_mana_cost(card.mana_cost),
        "manaValue": card.mana_value,
        "typeLine": _clean_text(card.type_line),
        "rulesText": _clean_text(rules_text),
        "rarity": card.rarity.title(),
        "stats": stats,
        "colorLabel": _color_label(card),
        "artCropUrl": image_urls.get("art_crop", ""),
        "fullCardUrl": image_urls.get("full_card", ""),
        "background": background,
        "foreground": foreground,
        "border": border,
    }


if Signal is not None:
    class DraftViewModel(QObject):
        """Small QML-facing adapter; all draft progression remains in DraftSession."""

        stateChanged = Signal()

        def __init__(
            self,
            *,
            session: DraftSession | None = None,
            no_basic_lands: bool = False,
            seed: int | None = None,
            table_size: int = 8,
            rounds: int = 3,
            color_balanced: bool = False,
            advisor_enabled: bool = False,
            score_display_enabled: bool = False,
            color_plan_display_enabled: bool = False,
            advisor: DraftBot | None = None,
        ) -> None:
            super().__init__()
            if session is not None:
                table_size = session.table_size
                rounds = session.rounds
                no_basic_lands = session.no_basic_lands
                color_balanced = session.color_balanced
            self._seed = seed
            self._table_size = table_size
            self._rounds = rounds
            self._no_basic_lands = no_basic_lands
            self._color_balanced = color_balanced
            self._session = session or self._make_session()
            self._advisor_enabled = advisor_enabled
            self._score_display_enabled = score_display_enabled
            self._color_plan_display_enabled = color_plan_display_enabled
            self._advisor = advisor or self._make_advisor()
            self._inspected_id = (
                self._session.current_pack[0].id
                if self._session.current_pack else ""
            )
            self._message = "Double-click a card in the pack to draft it."

        def _make_session(self) -> DraftSession:
            return DraftSession(
                table_size=self._table_size,
                rounds=self._rounds,
                no_basic_lands=self._no_basic_lands,
                color_balanced=self._color_balanced,
                seed=self._seed,
            )

        def _make_advisor(self) -> DraftBot:
            return DraftBot(
                config=DraftConfig(
                    total_picks=self._rounds * 15,
                    pack_size=15,
                    table_size=self._table_size,
                ),
                catalog=self._session.catalog,
            )

        def _draft_context(self) -> DraftContext:
            return DraftContext(
                self._session.round_number,
                self._session.pick_number,
                self._session.pack_ids[0],
            )

        def _advisor_rankings(self) -> tuple[PickEvaluation, ...]:
            if (
                not (
                    self._advisor_enabled
                    or self._score_display_enabled
                    or self._color_plan_display_enabled
                )
                or not self._session.current_pack
            ):
                return ()
            return self._advisor.rank(
                [card.card.name for card in self._session.current_pack],
                context=self._draft_context(),
            )

        def _find_card(self, card_id: str) -> DraftCard | None:
            for offered in (*self._session.current_pack, *self._session.human_pool):
                if offered.id == card_id:
                    return offered
            return None

        def _preview(self) -> dict:
            offered = self._find_card(self._inspected_id)
            if offered is None and self._session.current_pack:
                offered = self._session.current_pack[0]
            if offered is None and self._session.human_pool:
                offered = self._session.human_pool[-1]
            return _present_card(offered) if offered is not None else {}

        @Property("QVariantMap", notify=stateChanged)
        def state(self) -> dict:
            session = self._session
            rankings = self._advisor_rankings()
            evaluations = {evaluation.index: evaluation for evaluation in rankings}
            recommendation = rankings[0] if rankings else None
            color_plans = ()
            if self._color_plan_display_enabled:
                pack_names = [card.card.name for card in session.current_pack]
                color_plans = self._advisor.color_plans(
                    context=self._draft_context() if pack_names else None,
                    pack=pack_names if pack_names else None,
                )
            highest_plan_weight = color_plans[0].weight if color_plans else 1.0
            advisor_pick_index = (
                recommendation.index
                if recommendation is not None and self._advisor_enabled
                else None
            )
            advisor_pick_name = (
                session.current_pack[advisor_pick_index].card.name
                if advisor_pick_index is not None else ""
            )
            pack = []
            for index, card in enumerate(session.current_pack):
                presented = _present_card(card)
                evaluation = evaluations.get(index)
                presented["botRecommended"] = index == advisor_pick_index
                presented["botScore"] = (
                    evaluation.score
                    if evaluation is not None and self._score_display_enabled
                    else None
                )
                presented["botScoreText"] = (
                    f"{evaluation.score:.2f}"
                    if evaluation is not None and self._score_display_enabled
                    else ""
                )
                pack.append(presented)
            pool = [
                _present_card(card)
                for card in sorted(session.human_pool, key=_pool_sort_key)
            ]
            grouped_cards: list[list[dict]] = [[] for _ in _POOL_GROUPS]
            for offered in sorted(session.human_pool, key=_pool_sort_key):
                grouped_cards[_pool_group_index(offered.card)].append(
                    _present_card(offered)
                )
            pool_groups = [
                {
                    "label": label,
                    "accent": accent,
                    "cards": grouped_cards[index],
                    "count": len(grouped_cards[index]),
                }
                for index, (label, accent) in enumerate(_POOL_GROUPS)
            ]
            if session.complete:
                heading = "Draft complete"
                subheading = f"Your pool contains {len(pool)} cards."
            else:
                heading = f"Round {session.round_number} · Pick {session.pick_number}"
                subheading = (
                    f"{len(pack)} cards · passing {session.passing_direction}"
                )
            return {
                "heading": heading,
                "subheading": subheading,
                "message": self._message,
                "complete": session.complete,
                "pack": pack,
                "pool": pool,
                "poolGroups": pool_groups,
                "poolCount": len(pool),
                "preview": self._preview(),
                "noBasicLands": session.no_basic_lands,
                "packStyle": (
                    "No-basic boosters" if session.no_basic_lands
                    else "Historical Beta boosters"
                ) + (" · balanced commons" if session.color_balanced else "")
                + f" · {session.table_size} players · {session.rounds} rounds",
                "colorBalanced": session.color_balanced,
                "tableSize": session.table_size,
                "rounds": session.rounds,
                "advisorEnabled": self._advisor_enabled,
                "advisorPickName": advisor_pick_name,
                "scoreDisplayEnabled": self._score_display_enabled,
                "colorPlanDisplayEnabled": self._color_plan_display_enabled,
                "colorPlans": [
                    {
                        "label": "/".join(plan.colors),
                        "weight": plan.weight,
                        "weightText": f"{plan.weight:.1%}",
                        "relativeWeight": plan.weight / highest_plan_weight,
                    }
                    for plan in color_plans
                ],
            }

        @Slot(str)
        def inspectCard(self, card_id: str) -> None:
            if card_id != self._inspected_id and self._find_card(card_id) is not None:
                self._inspected_id = card_id
                self.stateChanged.emit()

        @Slot(str)
        def draftCard(self, card_id: str) -> None:
            pack_names = [card.card.name for card in self._session.current_pack]
            context = self._draft_context() if pack_names else None
            try:
                chosen = self._session.pick(card_id)
            except (RuntimeError, ValueError) as error:
                self._message = str(error).capitalize() + "."
                self.stateChanged.emit()
                return
            self._advisor.record_pick(
                pack_names,
                chosen.card.name,
                context=context,
            )
            self._inspected_id = chosen.id
            if self._session.complete:
                self._message = f"Drafted {chosen.card.name}. The draft is complete."
            else:
                self._message = f"Drafted {chosen.card.name}. The next pack has arrived."
            self.stateChanged.emit()

        @Slot(bool)
        def setAdvisorEnabled(self, enabled: bool) -> None:
            if self._advisor_enabled == enabled:
                return
            self._advisor_enabled = enabled
            self._message = (
                "Bot advisor enabled; its preferred card is highlighted."
                if enabled else "Bot advisor hidden."
            )
            self.stateChanged.emit()

        @Slot(bool)
        def setScoreDisplayEnabled(self, enabled: bool) -> None:
            if self._score_display_enabled == enabled:
                return
            self._score_display_enabled = enabled
            self._message = (
                "Bot scores shown for every card in the pack."
                if enabled else "Bot scores hidden."
            )
            self.stateChanged.emit()

        @Slot(bool, bool, int, int)
        def startNewDraft(
            self,
            no_basic_lands: bool,
            color_balanced: bool,
            table_size: int,
            rounds: int,
        ) -> None:
            if table_size < 2 or rounds < 1:
                self._message = (
                    "A draft needs at least two players and one booster round."
                )
                self.stateChanged.emit()
                return
            self._no_basic_lands = no_basic_lands
            self._color_balanced = color_balanced
            self._table_size = table_size
            self._rounds = rounds
            self._session = self._make_session()
            self._advisor = self._make_advisor()
            self._inspected_id = self._session.current_pack[0].id
            self._message = "Started a new draft. Double-click a card to pick it."
            self.stateChanged.emit()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Draft Limited Edition Beta against seven local bots."
    )
    parser.add_argument(
        "--no-basic-lands",
        action="store_true",
        help="generate modernized boosters in which basics do not occupy slots",
    )
    parser.add_argument("--seed", type=int, help="seed for reproducible booster contents")
    parser.add_argument(
        "--players", type=int, default=8,
        help="number of seats including the human (default: 8)",
    )
    parser.add_argument(
        "--rounds", type=int, default=3,
        help="number of 15-card booster rounds (default: 3)",
    )
    parser.add_argument(
        "--bot-advisor",
        action="store_true",
        help="highlight the card a shadow bot would choose from each pack",
    )
    parser.add_argument(
        "--bot-scores",
        action="store_true",
        help="show the shadow bot's numeric score for every card in each pack",
    )
    parser.add_argument(
        "--bot-color-plans",
        action="store_true",
        help="show the shadow bot's current mono- and two-color plan weights",
    )
    parser.add_argument(
        "--color-balanced",
        action="store_true",
        help="ensure the common portion of each booster represents every color",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if Signal is None:
        print(
            "The draft UI requires PySide6. Install with: "
            "python -m pip install -e .[ui]",
            file=sys.stderr,
        )
        return 2
    if args.players < 2:
        _parser().error("--players must be at least 2")
    if args.rounds < 1:
        _parser().error("--rounds must be at least 1")

    # Main.qml supplies its own dark control delegates. Native platform styles
    # do not permit those internals to be customized and emit warnings (as well
    # as occasionally painting native hover decorations over our controls).
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv[:1])
    app.setApplicationName("Beta Draft")
    engine = QQmlApplicationEngine()
    bridge = DraftViewModel(
        no_basic_lands=args.no_basic_lands,
        seed=args.seed,
        table_size=args.players,
        rounds=args.rounds,
        color_balanced=args.color_balanced,
        advisor_enabled=args.bot_advisor,
        score_display_enabled=args.bot_scores,
        color_plan_display_enabled=args.bot_color_plans,
    )
    bridge.setParent(engine)
    engine.rootContext().setContextProperty("draftBridge", bridge)
    qml_path = Path(__file__).with_name("qml") / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["DraftViewModel", "main"] if Signal is not None else ["main"]
