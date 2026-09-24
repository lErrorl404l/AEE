#!/usr/bin/env python3
"""Hold the vehicle source documents and verify their digests.

The vehicle corpus carries one registry at `data/vehicle/sources.json`. One
entry names one real document. The held bytes live under
`data/vehicle/sources/`.

The tool holds one named source or every source, and it verifies the
registry. A source is held (`primary_held: true`) only when the bytes on
disk exist and their SHA-256 equals the recorded `sha256`. The recorded
`sha256` is pinned in the registry before the fetch. The tool never trusts
the first fetched digest. A failed fetch, a missing pinned digest and a
mismatched digest write no held file.

Run:
  python3 tools/validation/fetch_vehicle_sources.py <source_id>
  python3 tools/validation/fetch_vehicle_sources.py --all
  python3 tools/validation/fetch_vehicle_sources.py --verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).parents[2]
DEFAULT_DATA_DIR = REPO / "data" / "vehicle"
REGISTRY_NAME = "sources.json"
SOURCES_DIRNAME = "sources"
USER_AGENT = "Mozilla/5.0"

Fetch = Callable[[str], bytes]
_EXTENSION = re.compile(r"\.[A-Za-z0-9]{1,8}")


def held_filename(source: Mapping[str, object]) -> str:
    """Return the held file name for one source entry."""
    source_id = str(source.get("source_id", "source"))
    url = str(source.get("url") or "")
    suffix = Path(urlparse(url).path).suffix.lower()
    if not _EXTENSION.fullmatch(suffix):
        suffix = ".bin"
    return f"{source_id}{suffix}"


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 digest of the bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of the file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write the bytes through a temporary file, then rename it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.part")
    try:
        with tmp.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def fetch_url(url: str) -> bytes:
    """Fetch a URL and return its bytes. The read is read-only."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def hold_source(
    source: Mapping[str, object],
    dest_dir: Path,
    fetch: Fetch = fetch_url,
    today: str | None = None,
) -> tuple[dict[str, object], str | None]:
    """Hold one source. Return the updated entry and an error or None.

    On success the entry carries `primary_held: true` and the digest of the
    held bytes. On any failure the entry is unchanged and no file is
    written. An entry with no pinned `sha256` is rejected, so the tool
    never trusts the first fetched digest.
    """
    entry = dict(source)
    url = source.get("url")
    if not isinstance(url, str) or not url:
        return entry, "no url in the source entry"
    try:
        data = fetch(url)
    except Exception as exc:  # noqa: BLE001 - report the failure, write nothing
        return entry, f"fetch failed: {exc}"
    if not data:
        return entry, "fetch returned no bytes"
    expected = source.get("sha256")
    if not isinstance(expected, str) or not expected:
        return (
            entry,
            "no pinned sha256 in the source entry; a fetched digest is not accepted",
        )
    digest = sha256_bytes(data)
    if expected != digest:
        return entry, f"digest mismatch: expected {expected}, got {digest}"
    atomic_write_bytes(dest_dir / held_filename(entry), data)
    entry["sha256"] = digest
    entry["primary_held"] = True
    if today:
        entry["retrieved"] = today
    return entry, None


def verify_sources(sources: Sequence[object], dest_dir: Path) -> list[str]:
    """Return one error for each held source that fails verification."""
    errors: list[str] = []
    for raw in sources:
        if not isinstance(raw, Mapping) or raw.get("primary_held") is not True:
            continue
        source_id = str(raw.get("source_id", "?"))
        digest = raw.get("sha256")
        if not isinstance(digest, str) or not digest:
            errors.append(f"{source_id}: primary_held is true but sha256 is empty")
            continue
        path = dest_dir / held_filename(raw)
        if not path.exists():
            errors.append(f"{source_id}: held file missing: {path.name}")
            continue
        actual = sha256_file(path)
        if actual != digest:
            errors.append(
                f"{source_id}: digest mismatch: recorded {digest}, on disk {actual}"
            )
    return errors


def load_registry(path: Path) -> list[dict[str, object]]:
    """Read the source registry. Return an empty list when absent."""
    if not path.exists():
        return []
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"{path}: registry must be a top-level array")
    return [dict(item) for item in loaded if isinstance(item, Mapping)]


def save_registry(path: Path, sources: Sequence[Mapping[str, object]]) -> None:
    """Write the source registry, deterministically and atomically."""
    body = json.dumps(list(sources), indent=2) + "\n"
    atomic_write_bytes(path, body.encode("utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool. Return 0 on success and 1 on any error."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_id", nargs="?", help="one source id to hold")
    parser.add_argument(
        "--all", action="store_true", help="hold every source with a url"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="re-check every held source against its bytes",
    )
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir)
    registry_path = data_dir / REGISTRY_NAME
    sources_dir = data_dir / SOURCES_DIRNAME

    try:
        sources = load_registry(registry_path)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 1

    if args.verify:
        errors = verify_sources(sources, sources_dir)
        for error in errors:
            print(f"error: {error}")
        held = sum(1 for item in sources if item.get("primary_held") is True)
        if errors:
            print(f"verify failed: {len(errors)} held source(s) are invalid")
            return 1
        print(f"verify passed: {held} held source(s) match their digest")
        return 0

    if not args.source_id and not args.all:
        parser.print_usage()
        print("error: name a source_id, or use --all, or use --verify")
        return 1

    if args.all:
        targets = [item for item in sources if item.get("url")]
    else:
        targets = [item for item in sources if item.get("source_id") == args.source_id]
        if not targets:
            print(f"error: unknown source_id: {args.source_id}")
            return 1

    by_id = {item.get("source_id"): item for item in sources}
    today = date.today().isoformat()
    failures = 0
    for source in targets:
        entry, error = hold_source(source, sources_dir, fetch=fetch_url, today=today)
        by_id[entry.get("source_id")] = entry
        if error:
            failures += 1
            print(f"source {entry.get('source_id')}: FAILED: {error}")
        else:
            print(
                f"source {entry.get('source_id')}: held, sha256 {entry.get('sha256')}"
            )
    save_registry(registry_path, list(by_id.values()))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
