"""Download Beta art crops and full-card images from Scryfall.

Run from the repository root with:

    python tools/download_card_images.py

Downloads are resumable: existing nonempty files are skipped unless --force is
used. The shared generated card_images directory is intentionally ignored by
Git and is consumed by both the gameplay and draft UIs.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Sequence
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCRYFALL_SEARCH_URL = (
    "https://api.scryfall.com/cards/search?"
    "q=e%3Aleb&unique=cards&order=name"
)
USER_AGENT = "BetaMagicDraftImageDownloader/1.0"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CARD_DATA = PROJECT_ROOT / "cards" / "LEB.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "card_images"
MINIMUM_DELAY = 0.05


@dataclass(frozen=True)
class ImageDownload:
    card_name: str
    kind: str
    url: str
    destination: Path


class ScryfallClient:
    """Small polite HTTP client with spacing and bounded transient retries."""

    def __init__(self, *, delay: float = 0.1, retries: int = 3) -> None:
        if delay < MINIMUM_DELAY:
            raise ValueError(
                f"request delay must be at least {MINIMUM_DELAY:.2f} seconds"
            )
        self.delay = delay
        self.retries = retries
        self._last_request = 0.0

    def _wait(self) -> None:
        remaining = self.delay - (time.monotonic() - self._last_request)
        if remaining > 0:
            time.sleep(remaining)
        self._last_request = time.monotonic()

    def get(self, url: str, *, accept: str) -> tuple[bytes, str]:
        for attempt in range(self.retries + 1):
            self._wait()
            request = Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": accept},
            )
            try:
                with urlopen(request, timeout=45) as response:
                    return response.read(), response.headers.get_content_type()
            except HTTPError as error:
                retryable = error.code == 429 or 500 <= error.code < 600
                if not retryable or attempt == self.retries:
                    raise
                retry_after = error.headers.get("Retry-After")
                pause = float(retry_after) if retry_after else 2 ** attempt
                time.sleep(max(self.delay, pause))
            except (TimeoutError, URLError):
                if attempt == self.retries:
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError("unreachable request retry state")

    def get_json(self, url: str) -> dict[str, Any]:
        payload, content_type = self.get(url, accept="application/json")
        if content_type != "application/json":
            raise ValueError(
                f"expected JSON from {url}, received {content_type!r}"
            )
        value = json.loads(payload.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"expected a JSON object from {url}")
        return value


def card_filename(name: str) -> str:
    """Return the stable, filesystem-safe stem used by both image folders."""

    ascii_name = (
        unicodedata.normalize("NFKD", name).replace("'", "").replace("’", "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    result = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    if not result:
        raise ValueError(f"card name cannot form a filename: {name!r}")
    return result


def load_expected_names(path: Path = CARD_DATA) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cards = payload.get("cards")
    if cards is None:
        cards = payload.get("data", {}).get("cards")
    if not isinstance(cards, list):
        raise ValueError(f"card catalog at {path} has no card list")
    names = {
        card.get("name")
        for card in cards
        if isinstance(card, dict) and isinstance(card.get("name"), str)
    }
    if not names:
        raise ValueError(f"card catalog at {path} has no named cards")
    return names


def fetch_beta_cards(client: ScryfallClient) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    url: str | None = SCRYFALL_SEARCH_URL
    while url:
        page = client.get_json(url)
        page_cards = page.get("data")
        if not isinstance(page_cards, list):
            raise ValueError("Scryfall search response has no card data list")
        cards.extend(page_cards)
        url = page.get("next_page") if page.get("has_more") else None
    return cards


def validate_remote_catalog(
    cards: Sequence[dict[str, Any]], expected_names: set[str]
) -> None:
    names = [card.get("name") for card in cards]
    remote_names = {name for name in names if isinstance(name, str)}
    duplicates = sorted(
        name for name in remote_names if names.count(name) > 1
    )
    missing = sorted(expected_names - remote_names)
    extra = sorted(remote_names - expected_names)
    if duplicates or missing or extra or len(cards) != len(expected_names):
        raise ValueError(
            "Scryfall Beta results differ from the local catalog: "
            f"duplicates={duplicates}, missing={missing}, extra={extra}"
        )


def image_uris(card: dict[str, Any]) -> dict[str, str]:
    uris = card.get("image_uris")
    if not isinstance(uris, dict):
        faces = card.get("card_faces") or []
        uris = faces[0].get("image_uris") if faces else None
    if not isinstance(uris, dict):
        raise ValueError(f"{card.get('name', 'card')} has no Scryfall image URIs")
    return uris


def build_downloads(
    cards: Sequence[dict[str, Any]],
    output: Path,
    *,
    full_size: str = "large",
) -> tuple[list[ImageDownload], dict[str, dict[str, str]]]:
    extension = ".png" if full_size == "png" else ".jpg"
    downloads: list[ImageDownload] = []
    manifest: dict[str, dict[str, str]] = {}
    used_stems: dict[str, str] = {}
    for card in sorted(cards, key=lambda item: item["name"]):
        name = card["name"]
        stem = card_filename(name)
        if stem in used_stems and used_stems[stem] != name:
            raise ValueError(
                f"filename collision between {used_stems[stem]!r} and {name!r}"
            )
        used_stems[stem] = name
        uris = image_uris(card)
        if "art_crop" not in uris or full_size not in uris:
            raise ValueError(
                f"{name} does not provide art_crop and {full_size} images"
            )
        art_path = output / "art_crops" / f"{stem}.jpg"
        full_path = output / "full_cards" / f"{stem}{extension}"
        downloads.extend(
            (
                ImageDownload(name, "art crop", uris["art_crop"], art_path),
                ImageDownload(name, "full card", uris[full_size], full_path),
            )
        )
        manifest[name] = {
            "scryfall_id": str(card.get("id", "")),
            "art_crop": art_path.relative_to(output).as_posix(),
            "full_card": full_path.relative_to(output).as_posix(),
        }
    return downloads, manifest


def download_image(
    item: ImageDownload,
    client: ScryfallClient,
    *,
    force: bool = False,
) -> str:
    if not force and item.destination.is_file() and item.destination.stat().st_size:
        return "skipped"
    item.destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = item.destination.with_suffix(item.destination.suffix + ".part")
    try:
        payload, content_type = client.get(item.url, accept="image/*")
        if not content_type.startswith("image/"):
            raise ValueError(
                f"expected an image for {item.card_name}, received {content_type!r}"
            )
        temporary.write_bytes(payload)
        os.replace(temporary, item.destination)
    finally:
        temporary.unlink(missing_ok=True)
    return "downloaded"


def write_manifest(
    output: Path,
    manifest: dict[str, dict[str, str]],
    *,
    full_size: str,
) -> None:
    payload = {
        "set": "leb",
        "source": SCRYFALL_SEARCH_URL,
        "full_card_size": full_size,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cards": manifest,
    }
    destination = output / "manifest.json"
    temporary = output / "manifest.json.part"
    output.mkdir(parents=True, exist_ok=True)
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download Beta card art and full-card images from Scryfall."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"destination root (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--full-size",
        choices=("small", "normal", "large", "png", "border_crop"),
        default="large",
        help="Scryfall image version for full_cards (default: large)",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.1,
        help="minimum delay between HTTP requests in seconds (default: 0.1)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="redownload files that already exist",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.request_delay < MINIMUM_DELAY:
        _parser().error(
            f"--request-delay must be at least {MINIMUM_DELAY:.2f} seconds"
        )
    output = args.output_dir.resolve()
    client = ScryfallClient(delay=args.request_delay)
    print("Fetching Limited Edition Beta card records from Scryfall...")
    cards = fetch_beta_cards(client)
    expected_names = load_expected_names()
    validate_remote_catalog(cards, expected_names)
    downloads, manifest = build_downloads(
        cards, output, full_size=args.full_size
    )
    downloaded = 0
    skipped = 0
    for index, item in enumerate(downloads, start=1):
        result = download_image(item, client, force=args.force)
        downloaded += result == "downloaded"
        skipped += result == "skipped"
        print(
            f"[{index:>3}/{len(downloads)}] {item.card_name} "
            f"({item.kind}): {result}"
        )
    write_manifest(output, manifest, full_size=args.full_size)
    print(
        f"Finished: {downloaded} downloaded, {skipped} skipped; "
        f"manifest written to {output / 'manifest.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
