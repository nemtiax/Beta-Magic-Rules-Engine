"""Optional local card-image manifest shared by the gameplay presentation."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path


IMAGE_ROOT = Path(__file__).resolve().parents[1] / "card_images"
IMAGE_MANIFEST = IMAGE_ROOT / "manifest.json"


@lru_cache(maxsize=1)
def card_image_urls() -> dict[str, dict[str, str]]:
    """Return safe local file URLs, or an empty mapping when images are absent."""

    if not IMAGE_MANIFEST.is_file():
        return {}
    try:
        payload = json.loads(IMAGE_MANIFEST.read_text(encoding="utf-8"))
        entries = payload["cards"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(entries, dict):
        return {}

    root = IMAGE_ROOT.resolve()
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


def image_urls_for(card_name: str) -> dict[str, str]:
    """Return optional art-crop and full-card URLs for a canonical card name."""

    return card_image_urls().get(card_name, {})
