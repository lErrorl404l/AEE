#!/usr/bin/env python3
"""Build data/symbology/nato_catalogue.json from the pulled NATO symbol images.

Reads the three MediaWiki pulls (the Commons gallery, the en.wikipedia article,
the Commons category tree), keeps only genuine APP-6 / MIL-STD-2525 symbols, and
re-derives the affiliation and the battle dimension from the image's frame.

An image is a symbol only when it carries an APP-6 frame or a function glyph.
A war map, a historical unit insignia or an article photograph is not a symbol;
it is dropped and its reason is recorded in data/symbology/dropped.json.

The frame gives the affiliation (rectangle friend, diamond hostile, square
neutral, quatrefoil unknown).  The battle dimension comes from the frame border
where the source carries one (arc on top air, curved bottom subsurface, closed
land); where the source does not, it comes from the function (aviation, naval,
subsurface).  Every entry records its method.

Run:  python3 tools/build_symbology_catalogue.py
      python3 tools/build_symbology_catalogue.py --pull /tmp/opencode/nato-symbols
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
CATALOGUE = ROOT / "data" / "symbology" / "nato_catalogue.json"
DROPPED = ROOT / "data" / "symbology" / "dropped.json"
DEFAULT_PULL = Path("/tmp/opencode/nato-symbols")

# Title patterns that name a genuine APP-6 / MIL-STD-2525 symbol set.  Each is
# the uploader's symbol series, not an article illustration.
SYMBOL_PATTERNS = [
    re.compile(r"^Military Symbol - "),
    re.compile(r"^Military Map Symbol - "),
    re.compile(r"^NATO Map Symbol - "),
    re.compile(r"^Ground Track - "),
    re.compile(r"^APP-6[ a-zA-Z0-9]* "),
    re.compile(r"^(FRD|HOS|NEU|UNK|AFD|XFD|XAF|FD|TZ|XT|MOB) "),
    re.compile(r"^Unit Size - "),
    re.compile(
        r"^Infantry (Battalion|Brigade|Company|Corps|Division|Platoon|Regiment|Section|Squad|squad) Nato"
    ),
    re.compile(r"^Army( group)? Nato"),
]
# Titles that are plainly not a symbol: a war map, a photograph, an insignia, a
# logo, an example sheet or a guide.
NON_SYMBOL_PATTERNS = [
    re.compile(r"war map", re.I),
    re.compile(r"\bmarket garden\b", re.I),
    re.compile(r"organization", re.I),
    re.compile(r"battle map", re.I),
    re.compile(r"\bguide\b", re.I),
    re.compile(r"boundary", re.I),
    re.compile(r"GebJgBtl", re.I),
    re.compile(r"Commons-logo", re.I),
    re.compile(r"question mark", re.I),
    re.compile(r"^File:(A 1-21|0-Inst|MapTeranoevensmaller|Medak)", re.I),
    re.compile(r"Example", re.I),
    re.compile(r"\.(jpg|jpeg|png)$", re.I),
]

# The frame name in a CdnMCG title gives the affiliation.  The dimension is not
# encoded in the CdnMCG frame, so it comes from the function.
FRAME_AFFIL = [
    (re.compile(r"Diamond", re.I), "Hostile"),
    (re.compile(r"Quatrefoil", re.I), "Unknown"),
    (re.compile(r"1\.0[0-9]x1\.0[0-9]|1\.1x1\.1|Solid 1\.1x1\.1", re.I), "Neutral"),
    (re.compile(r"1\.5x1|1\.6x1|Opaque", re.I), "Friend"),
]
FRAME_ID_AFFIL = {
    "Friendly Frame": "Friend",
    "Hostile Frame": "Hostile",
    "Neutral Frame": "Neutral",
    "Unknown Frame": "Unknown",
}
TITLE_AFFIL = [
    (re.compile(r"\bfriendly\b", re.I), "Friend"),
    (re.compile(r"\b(hostile|enemy)\b", re.I), "Hostile"),
    (re.compile(r"\b(neutral|unaligned)\b", re.I), "Neutral"),
    (re.compile(r"\bunknown\b", re.I), "Unknown"),
]
CODE_AFFIL = {
    "FRD": "Friend",
    "AFD": "Friend",
    "HOS": "Hostile",
    "NEU": "Neutral",
    "UNK": "Unknown",
}
# The unit-size indicator files are the APP-6 echelon modifiers, not framed
# symbols.  They are kept as kind = echelon for the cross-product.
ECHELON_PATTERNS = [
    re.compile(r"Unit Size - "),
    re.compile(r"^Unit Size - "),
]


def clean(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", html.unescape(s))).strip()


def lic_class(lic: str | None) -> str:
    value = (lic or "").lower()
    if (
        "public domain" in value
        or value.startswith("cc0")
        or "copyrighted free use" in value
    ):
        return "pd"
    if "by-sa" in value:
        return "ccbysa"
    if value.startswith("cc by") or value.startswith("cc-by"):
        return "ccby"
    return "other"


def is_symbol(title: str, path: Path) -> tuple[bool, str]:
    if not path.exists() or path.stat().st_size == 0:
        return False, "not downloaded"
    name = title.replace("File:", "")
    for rx in NON_SYMBOL_PATTERNS:
        if rx.search(name):
            return False, f"not a symbol ({rx.pattern})"
    for rx in SYMBOL_PATTERNS:
        if rx.match(name):
            return True, ""
    return False, "no APP-6 symbol series and no frame"


def frame_affiliation(title: str, svg: str) -> str:
    name = title.replace("File:", "")
    # The CdnMCG title names the affiliation as a word ("Hostile Unit"), which is
    # the uploader's intent and stronger than the frame name ("1.5x1" -> friend).
    for rx, affil in TITLE_AFFIL:
        if rx.search(name):
            return affil
    for fid, affil in FRAME_ID_AFFIL.items():
        if f'id="{fid}"' in svg:
            return affil
    for code, affil in CODE_AFFIL.items():
        if re.match(rf"^{code} ", name):
            return affil
    for rx, affil in FRAME_AFFIL:
        if rx.search(name):
            return affil
    if "Military Symbol" in name:
        # CdnMCG frames are named in the title; an unread one stays Unspecified.
        return "Unspecified"
    if name.startswith("APP-6"):
        # The PD APP-6 function glyphs carry a rectangle frame (friend).
        return "Friend"
    return "Unspecified"


def frame_dimension(title: str, svg: str) -> str:
    name = title.replace("File:", "")
    # The Urhixidur frame series encodes the dimension in the code.
    m = re.match(r"^File:(?:FRD|HOS|NEU|UNK|AFD|XFD|XAF|FD) ([A-Z+]+)", name)
    if m:
        code = m.group(1)
        if "SUB" in code:
            return "Subsurface"
        if "AIR" in code:
            return "Air/Space"
        if "SRF" in code:
            return "Sea Surface"
        if "INS" in code:
            return "Installation"
        if "EQP" in code:
            return "Equipment"
        return "Land"
    x = name.lower()
    if "sub-surface" in x or "subsurface" in x or "submarine" in x or "sub " in x:
        return "Subsurface"
    if "sea surface" in x or "sea unit" in x or "naval" in x:
        return "Sea Surface"
    if "installation" in x or "facility" in x:
        return "Installation"
    if "equipment" in x or "ground track - equipment" in x:
        return "Equipment"
    if (
        "aviation" in x
        or "air or space" in x
        or "air unit" in x
        or "aerial" in x
        or "airborne" in x
    ):
        return "Air/Space"
    return "Land"


def function_of(title: str) -> str:
    s = title.replace("File:", "")
    s = re.sub(r"^Military Symbol - ", "", s)
    s = re.sub(r"^Military Map Symbol - ", "", s)
    s = re.sub(r"^NATO Map Symbol - ", "", s)
    s = re.sub(r"\([^)]*Frame\)\s*-?\s*", "", s)
    s = re.sub(r"\(NATO APP-6[^)]*\)", "", s)
    s = re.sub(r"\(APP-6[^)]*\)", "", s)
    s = re.sub(r"\.svg$|\.png$|\.jpg$|\.gif$", "", s)
    return s.strip(" -")


def frame_of(title: str) -> str:
    m = re.search(r"\(([^)]*Frame)\)", title)
    return m.group(1) if m else ""


def build(pull: Path) -> int:
    sources = [
        ("commons-gallery", pull / "imageinfo.json"),
        ("en-wiki-article", pull / "wiki_imageinfo.json"),
        ("commons-category", pull / "category_imageinfo.json"),
    ]
    files: dict[str, dict[str, Any]] = {}
    for name, path in sources:
        if not path.exists():
            continue
        for o in json.loads(path.read_text(encoding="utf-8")):
            title = o.get("title")
            if not title:
                continue
            files.setdefault(title, dict(o, srcs=[]))["srcs"].append(name)

    entries, dropped = [], []
    for title, o in files.items():
        d = lic_class(o.get("license"))
        fn = title.replace("File:", "").replace("/", "_")
        p = pull / d / fn
        ok, reason = is_symbol(title, p)
        if not ok:
            dropped.append({"title": title, "reason": reason})
            continue
        svg = ""
        if p.suffix.lower() == ".svg":
            svg = p.read_text(encoding="utf-8", errors="replace")
        name = title.replace("File:", "")
        kind = (
            "echelon" if any(rx.search(name) for rx in ECHELON_PATTERNS) else "symbol"
        )
        affil = "" if kind == "echelon" else frame_affiliation(title, svg)
        if kind == "symbol" and affil == "Unspecified":
            dropped.append(
                {"title": title, "reason": "frame affiliation could not be resolved"}
            )
            continue
        entries.append(
            {
                "file": fn,
                "dir": d,
                "url": (o.get("url") or "").split("?")[0],
                "license": o.get("license"),
                "artist": clean(o.get("artist")),
                "mime": o.get("mime"),
                "kind": kind,
                "affil": affil,
                "dim": "" if kind == "echelon" else frame_dimension(title, svg),
                "func": function_of(title),
                "frame": frame_of(title),
                "src": "+".join(sorted(o["srcs"])),
            }
        )
    entries.sort(key=lambda e: (e["affil"], e["dim"], e["func"]))
    dropped.sort(key=lambda e: e["title"])
    CATALOGUE.write_text(
        json.dumps(
            {
                "source": f"{pull} (Commons gallery + en.wikipedia + category tree)",
                "count": len(entries),
                "dropped": len(dropped),
                "entries": entries,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    DROPPED.write_text(json.dumps(dropped, indent=1), encoding="utf-8")

    import collections

    print(f"kept: {len(entries)}  dropped: {len(dropped)}")
    print("kind:", dict(collections.Counter(e["kind"] for e in entries)))
    print(
        "affiliation:",
        dict(collections.Counter(e["affil"] for e in entries if e["kind"] == "symbol")),
    )
    print(
        "dimension:",
        dict(collections.Counter(e["dim"] for e in entries if e["kind"] == "symbol")),
    )
    return 0


def main(argv: list[str]) -> int:
    pull = DEFAULT_PULL
    if "--pull" in argv:
        pull = Path(argv[argv.index("--pull") + 1])
    return build(pull)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
