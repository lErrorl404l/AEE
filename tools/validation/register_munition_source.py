#!/usr/bin/env python3
"""Hold one published source that names a munition in its body text.

tools/ingest_wikipedia_munition.py reads an article's infobox. Not every
munition is documented that way: a maker's product page, a non-English
encyclopaedia article or a reference page states the designation in body
text and states no infobox figure. Those sources are published all the
same, and the corpus still has to name the item they name.

This tool fetches one URL, holds its bytes in the machine-local source cache
(tools/validation/source_cache.py, domain "munition"),
registers them in data/munition/sources.json with their SHA-256, and writes
an IDENTITY-ONLY catalogue entry. The entry names the munition and holds no
figure at all, which states what the source gives and is never an estimate.
A designation the source does not state is never written: the aliases on the
command line are the designations that source publishes.

--verify re-hashes every held source against the registry, so a corpus can
never cite bytes it no longer holds. A machine that does not hold the cache
reports the absent bytes and passes, because the repository never ships them.

Run:
  python3 tools/validation/register_munition_source.py --url URL --id ID \\
      --type cannon --name "QJK-99" --alias "QJK-99" --tier 5 \\
      --title "12.7x108mm" --licence "CC BY-SA 4.0"
  python3 tools/validation/register_munition_source.py --verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

_REPO = Path(__file__).parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.validation import source_cache  # noqa: E402

_DATA = _REPO / "data" / "munition"
_CATALOGUE = _DATA / "catalogue"
_HELD = source_cache.cache_dir("munition")
_REGISTRY = _DATA / "sources.json"
_UA = "AEE-research/1.0 (munition catalogue capture)"

# What a munition IS, in the words the game and the sources both use.
TYPES = ("missile", "bomb", "rocket", "cannon", "grenade", "mortar", "shell")
_EXTENSION = (".html", ".htm", ".pdf", ".txt")


def _suffix(url: str) -> str:
    """The held file's extension, from the URL path when it has one."""
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return suffix if suffix in _EXTENSION else ".html"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(request, timeout=90) as handle:
        return handle.read()


def register(
    url: str,
    cid: str,
    munition_type: str,
    name: str,
    aliases: list[str],
    tier: int,
    title: str,
    licence: str,
    locator: str,
    note: str,
    source_id: str = "",
    force: bool = False,
) -> int:
    entry_path = _CATALOGUE / f"{cid}.json"
    if entry_path.exists() and not force:
        print(f"{cid}: a catalogue entry is already held, not overwritten")
        return 1

    source_id = source_id or cid
    registry = (
        json.loads(_REGISTRY.read_text(encoding="utf-8")) if _REGISTRY.exists() else []
    )
    known = {source["source_id"] for source in registry}
    held = _HELD / f"{source_id}{_suffix(url)}"
    if source_id in known and held.exists() and not force:
        # The source is already held: two entries may cite one document
        # (the HMP250 and the HMP400 are on one maker page), and a page
        # that serves different bytes on a second fetch must not silently
        # replace the bytes the registry pinned.
        raw = held.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
    else:
        raw = fetch(url)
        digest = hashlib.sha256(raw).hexdigest()
        _HELD.mkdir(parents=True, exist_ok=True)
        held.write_bytes(raw)
    if source_id not in known:
        registry.append(
            {
                "source_id": source_id,
                "tier": tier,
                "type": "manufacturer" if tier == 4 else "compilation",
                "title": title,
                "edition": "",
                "identifier": source_id,
                "locator": locator,
                "published": "",
                "retrieved": date.today().isoformat(),
                "url": url,
                "licence": licence,
                "primary_held": True,
                "note": note,
                "sha256": digest,
            }
        )
        _REGISTRY.write_text(json.dumps(registry, indent=1) + "\n", encoding="utf-8")

    entry_path.write_text(
        json.dumps(
            {
                "retrieved": date.today().isoformat(),
                "note": (
                    f"IDENTITY ONLY. The held tier-{tier} source '{source_id}' "
                    f"publishes {name} in its body text. It states no figure this "
                    f"corpus can hold. The entry names the item and holds a "
                    f"labelled zero for every field. {note}"
                ).strip(),
                "sources": [],
                "entries": [
                    {
                        "catalogue_id": cid,
                        "canonical_name": name,
                        "munition_type": munition_type,
                        "aliases": sorted({a.strip() for a in aliases if a.strip()}),
                        "keywords": [],
                        "values": {},
                    }
                ],
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{cid}: held {len(raw)} bytes, sha256 {digest[:16]}")
    return 0


def verify() -> int:
    """Re-hash every held munition source against the registry.

    The bytes live in the local cache and are not redistributed. When the
    cache is absent the byte check cannot run, and a clean clone must not
    fail for it: the run reports the absent store and passes.
    """
    registry = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    if not _HELD.is_dir():
        print(
            f"munition sources: {len(registry)} registered; the bytes are not "
            f"held in {source_cache.cache_root()}, byte check skipped"
        )
        return 0
    bad = 0
    for source in registry:
        path = _HELD / f"{source['source_id']}{_suffix(source['url'])}"
        if not path.exists():
            print(f"{source['source_id']}: held bytes MISSING")
            bad += 1
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != source["sha256"]:
            print(f"{source['source_id']}: digest MISMATCH")
            bad += 1
    print(f"munition sources: {len(registry)} registered, {bad} bad")
    return 0 if bad == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--id")
    ap.add_argument("--type", choices=TYPES, default=None)
    ap.add_argument("--name")
    ap.add_argument("--alias", action="append", default=[])
    ap.add_argument("--source-id", default="")
    ap.add_argument("--tier", type=int, default=5)
    ap.add_argument("--title", default="")
    ap.add_argument("--licence", default="")
    ap.add_argument("--locator", default="Body text")
    ap.add_argument("--note", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    if args.verify:
        return verify()
    missing = [
        flag
        for flag, value in (
            ("--url", args.url),
            ("--id", args.id),
            ("--type", args.type),
            ("--name", args.name),
            ("--title", args.title),
            ("--licence", args.licence),
        )
        if not value
    ]
    if missing:
        ap.error("required: " + " ".join(missing))
    return register(
        args.url,
        args.id,
        args.type,
        args.name,
        args.alias,
        args.tier,
        args.title,
        args.licence,
        args.locator,
        args.note,
        args.source_id,
        args.force,
    )


if __name__ == "__main__":
    sys.exit(main())
