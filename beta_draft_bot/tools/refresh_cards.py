"""Explicit, optional metadata refresh. Runtime drafting never needs the network.

Run from the project root: python tools/refresh_cards.py
Review card-data and rules changes before accepting an updated snapshot.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
import time
from urllib.request import Request, urlopen

URL = "https://api.scryfall.com/cards/search?q=e%3Aleb&unique=cards&order=name"


def metadata(raw):
    return {
        "name": raw["name"], "mana_cost": raw.get("mana_cost", ""),
        "mana_value": raw["cmc"], "colors": raw["colors"],
        "type_line": raw["type_line"], "power": raw.get("power"),
        "toughness": raw.get("toughness"), "keywords": raw["keywords"],
        "produced_mana": raw.get("produced_mana", []),
        "rules_text": raw.get("printed_text") or raw.get("oracle_text", ""),
        "rarity": raw["rarity"],
        "source": raw["scryfall_uri"].split("?")[0],
    }


def main():
    cards = []
    url = URL
    while url:
        request = Request(url, headers={"User-Agent": "BetaDraftBot/1.0", "Accept": "application/json"})
        with urlopen(request, timeout=30) as response:
            page = json.load(response)
        cards.extend(page["data"])
        url = page.get("next_page") if page.get("has_more") else None
        if url:
            time.sleep(0.15)
    if len(cards) != 292 or len({c["name"] for c in cards}) != 292 or any(c["set"] != "leb" for c in cards):
        raise ValueError("Unexpected Beta catalog; existing snapshot was not modified")
    destination = Path(__file__).resolve().parents[1] / "beta_draft/data/cards.json"
    expected = {line.split("|", 1)[0] for line in destination.with_name("ratings.tsv").read_text().splitlines()
                if line and not line.startswith("#")}
    if expected != {c["name"] for c in cards}:
        raise ValueError("Card names and curated evaluations differ; review before refreshing")
    payload = {"set": "leb", "source": URL, "retrieved_at": datetime.now(timezone.utc).date().isoformat(),
               "cards": [metadata(c) for c in cards]}
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(cards)} card records to {destination}")


if __name__ == "__main__":
    main()
