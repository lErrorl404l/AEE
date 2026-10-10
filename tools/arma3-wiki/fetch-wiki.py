#!/usr/bin/env python3
"""Read an Arma 3 community wiki (BIKI) page for offline reference.

The live wiki sits behind a bot filter that refuses a plain fetch. The Wayback
Machine holds a copy of every command page without that filter, so each page is
read from there and reduced to its readable text.

Usage:
    python3 fetch-wiki.py <page> [<page> ...]
    python3 fetch-wiki.py setWantedRPMRTD enginesRpmRTD
    python3 fetch-wiki.py setWantedRPMRTD --output-dir ./cache
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

WAYBACK = "https://web.archive.org/web/2024/https://community.bistudio.com/wiki/"
HEADERS = {"User-Agent": "Mozilla/5.0 (AEE reference reader)"}
BLOCKS = re.compile(r"(?is)<(script|style)\b.*?</\1>")
TAGS = re.compile(r"<[^>]+>")
BLANKS = re.compile(r"\n{3,}")
STOPS = ('id="catlinks"', "## Navigation menu", "Navigation menu")


def fetch(page: str) -> str:
    """Read one wiki page through the Wayback Machine."""
    request = urllib.request.Request(WAYBACK + page, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read().decode("utf-8", "replace")


def readable(source: str) -> str:
    """Reduce a wiki page to its readable text."""
    body = source.split('class="mw-parser-output"', 1)[-1]
    for stop in STOPS:
        body = body.split(stop, 1)[0]
    body = BLOCKS.sub("", body)
    body = html.unescape(TAGS.sub("", body))
    lines = [line.strip() for line in body.splitlines()]
    return BLANKS.sub("\n\n", "\n".join(line for line in lines if line)).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Read Arma 3 wiki pages")
    parser.add_argument("pages", nargs="+", help="Command or function names")
    parser.add_argument("--output-dir", "-o", help="Write each page to a file")
    args = parser.parse_args()

    out = Path(args.output_dir) if args.output_dir else None
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)

    status = 0
    for page in args.pages:
        try:
            text = readable(fetch(page))
        except (urllib.error.URLError, TimeoutError) as error:
            print(f"{page}: fetch failed: {error}", file=sys.stderr)
            status = 1
            continue
        if out is not None:
            path = out / f"{page}.txt"
            path.write_text(text, encoding="utf-8")
            print(f"{page}: {len(text)} chars -> {path}")
        else:
            print(f"===== {page} =====")
            print(text)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
