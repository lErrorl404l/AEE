"""The machine-local store for retrieved third-party captures.

The repository publishes the extracted data and its citations. It never
publishes the captured pages, drawings or manuals, because they belong to
their publishers. The bytes are held outside the working tree in a local
cache and are not redistributed.

Layout: one directory per data domain, mirroring the path under
``data/<domain>/sources/``::

    <root>/vehicle/achzarit.wiki
    <root>/ballistics/cip/datasheets/5-56-x-45-en.pdf
    <root>/symbology/svg/ccbysa/<file>.svg
    <root>/symbology/render/<marker>.png

The root is ``$AEE_SOURCE_CACHE`` when set, else
``$XDG_DATA_HOME/aee/source-cache``, else ``~/.local/share/aee/source-cache``.

A record's ``sha256`` identifies the bytes that were retrieved. It does not
mean the bytes ship in the repository. A reader that needs the bytes asks
this module. A reader that only needs the citation never does.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def cache_root() -> Path:
    """Return the cache root from the environment or the XDG default."""
    override = os.environ.get("AEE_SOURCE_CACHE")
    if override:
        return Path(override).expanduser()
    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base).expanduser() / "aee" / "source-cache"
    return Path.home() / ".local" / "share" / "aee" / "source-cache"


def cache_dir(domain: str) -> Path:
    """Return the cache directory that holds one data domain's captures."""
    return cache_root() / domain


def capture_path(domain: str, relative: str | Path) -> Path:
    """Return the cache path for one capture, named as under sources/."""
    return cache_dir(domain) / relative


def repo_sources_dir(domain: str) -> Path:
    """Return the in-tree sources directory, which holds JSON records only."""
    return REPO / "data" / domain / "sources"


def held_dir(domain: str, data_dir: Path) -> Path:
    """Return where a corpus reads its held bytes.

    The shipped corpus reads the cache. A temporary fixture tree keeps its
    bytes beside its records, so the CLI self-checks stay self-contained.
    """
    if data_dir.resolve() == (REPO / "data" / domain).resolve():
        return cache_dir(domain)
    return data_dir / "sources"


def resolve(domain: str, relative: str | Path) -> Path | None:
    """Return the capture path when the bytes are held, else None.

    The cache is the store. An in-tree copy is still accepted so a machine
    that has not migrated yet keeps working, but nothing writes there.
    """
    cached = capture_path(domain, relative)
    if cached.is_file():
        return cached
    legacy = repo_sources_dir(domain) / relative
    if legacy.is_file():
        return legacy
    return None


def require(domain: str, relative: str | Path) -> Path:
    """Return the capture path or stop with the command that fills it."""
    found = resolve(domain, relative)
    if found is None:
        raise SystemExit(
            f"source cache: {domain}/{relative} is not held. "
            f"The bytes live in {cache_root()} and are not in the repository."
        )
    return found


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of the held bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stored_digest(domain: str, relative: str | Path) -> str | None:
    """Return the digest of the held bytes, or None when they are absent."""
    found = resolve(domain, relative)
    if found is None:
        return None
    return sha256_file(found)
