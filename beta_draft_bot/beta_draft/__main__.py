"""One JSON request per line on stdin; one JSON response per line on stdout."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import DraftBot, DraftConfig, DraftContext


def handle_request(bot: DraftBot, request) -> tuple[DraftBot, dict, bool]:
    if isinstance(request, list):
        request = {"op": "pick", "pack": request}
    if not isinstance(request, dict):
        raise ValueError("Request must be a pack array or an object")
    operation = request.get("op", "pick")
    if not isinstance(operation, str):
        raise ValueError("op must be a string")
    if operation == "state":
        return bot, {"state": bot.to_dict()}, False
    if operation == "reset":
        config = request.get("config", {})
        if not isinstance(config, dict):
            raise ValueError("config must be an object")
        bot = DraftBot(config=DraftConfig(**config))
        return bot, {"state": bot.to_dict()}, True
    if operation == "restore":
        bot = DraftBot.from_dict(request.get("state"))
        return bot, {"state": bot.to_dict()}, True
    if operation not in {"pick", "rank", "record"}:
        raise ValueError(f"Unknown operation: {operation!r}")
    raw_context = request.get("context")
    if raw_context is not None and not isinstance(raw_context, dict):
        raise ValueError("context must be an object or null")
    context = DraftContext(**raw_context) if raw_context is not None else None
    pack = request.get("pack")
    if operation == "rank":
        return bot, {"rankings": [e.to_dict() for e in bot.rank(pack, context=context)],
                     "pool_size": len(bot.pool)}, False
    if operation == "record":
        choice = bot.record_pick(pack, request.get("card"), context=context)
    else:
        choice = bot.pick_with_details(pack, context=context)
    result = choice.to_dict()
    result["pool_size"] = len(bot.pool)
    result["pool"] = list(bot.pool)
    return bot, result, True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, help="Load and automatically save a JSON checkpoint")
    args = parser.parse_args(argv)
    try:
        bot = DraftBot.load(args.state) if args.state is not None and args.state.exists() else DraftBot()
    except (ValueError, TypeError, OSError) as error:
        parser.error(str(error))
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            # A failed request or failed checkpoint write must not consume a pick.
            working = DraftBot.from_dict(bot.to_dict())
            working, response, changed = handle_request(working, request)
            if changed and args.state is not None:
                working.save(args.state)
            bot = working
        except (ValueError, TypeError, OSError) as error:
            response = {"error": {"type": type(error).__name__, "message": str(error)}}
        print(json.dumps(response, ensure_ascii=False, allow_nan=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
