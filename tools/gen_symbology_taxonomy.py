#!/usr/bin/env python3
"""Generate the missing MIL-STD-2525 function glyphs from the standard taxonomy.

The pulled Commons catalogue holds the drawn APP-6 gallery.  It does not hold
the standard's full function-glyph taxonomy (the Military Intelligence, Signal
Unit, Administrative, Equipment and Installation subtrees, and the Air, Sea
Surface, Subsurface and Space branches).  This generator fills that gap.

The source is /tmp/opencode/symbol_army_rows.tsv: the full MIL-STD-2525C
enumeration (877 rows, name + SIDC + hierarchy).  Each row's SIDC names one
function.  The geometry is rendered by milsymbol (MIT), an open-source
implementation of MIL-STD-2525 / APP-6, in monochrome so the engine marker
colour tints the texture.  The symbol designs are the standard's own geometry
(public domain); the milsymbol renderer is credited in ATTRIBUTION.md.

A row whose function is already covered by the pulled catalogue is skipped, so
the real pulled image wins and this layer holds only the gap.

Run:  python3 tools/gen_symbology_taxonomy.py
      python3 tools/gen_symbology_taxonomy.py --check
      python3 tools/gen_symbology_taxonomy.py --table
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
TSV = Path("/tmp/opencode/symbol_army_rows.tsv")
CATALOGUE = ROOT / "data" / "symbology" / "nato_catalogue.json"
MARKERS_OUT = ROOT / "addons" / "optics" / "data" / "markers"
CONFIG_OUT = ROOT / "addons" / "optics" / "config_taxonomy.hpp"
TAXONOMY_OUT = ROOT / "data" / "symbology" / "app6_taxonomy.json"
RENDERER = ROOT / "tools" / "milsymbol_render.mjs"
ADDON_PREFIX = "\\z\\aee\\addons\\optics\\data\\markers"
MILSYMBOL_ENTRY = os.environ.get(
    "MILSYMBOL_ENTRY", "/tmp/opencode/milsym/node_modules/milsymbol/index.js"
)

SIZE = 64
RENDER = 256  # milsymbol renders the SVG at this size; it is rasterised to SIZE

AFFIL_LETTER = {"Friend": "F", "Hostile": "H", "Neutral": "N", "Unknown": "U"}
AFFIL_SIDE = {"Friend": 1, "Hostile": 0, "Neutral": 2, "Unknown": 2}
AFFIL_CHAR = {"Friend": "F", "Hostile": "H", "Neutral": "N", "Unknown": "U"}
AFFIL_ORDER = ["Friend", "Hostile", "Neutral", "Unknown"]
DIM_LETTER = {
    "Land": "L",
    "Air/Space": "A",
    "Space": "P",
    "Sea Surface": "S",
    "Subsurface": "U",
    "Installation": "I",
    "Equipment": "E",
}


def _slug(text: str, limit: int = 30) -> str:
    out: list[str] = []
    prev_us = False
    for ch in text:
        if ch.isalnum():
            out.append(ch)
            prev_us = False
        elif not prev_us:
            out.append("_")
            prev_us = True
    return "".join(out).strip("_")[:limit].rstrip("_") or "Symbol"


def _tokens(text: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9]+", text.lower()))


def normalise_sidc(code: str) -> str:
    s = code.replace("\\*", "*").replace("\u2014", "-").replace("\u2013", "-")
    s = re.sub(r"[^A-Za-z0-9-]", "-", s.replace("*", "-"))
    return s.ljust(15, "-")[:15]


def dimension_of(hierarchy: str) -> str:
    parts = [p.strip() for p in hierarchy.split("/") if p.strip()]
    if "Installation" in parts:
        return "Installation"
    if "Equipment" in parts:
        return "Equipment"
    if "Space" in parts:
        return "Space"
    if "Air" in parts:
        return "Air/Space"
    if "Sea Surface Track" in parts or "Sea Surface" in parts:
        return "Sea Surface"
    if "Subsurface Track" in parts or "Subsurface" in parts:
        return "Subsurface"
    return "Land"


def read_rows() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in TSV.read_text(encoding="utf-8").splitlines():
        cols = line.split("\t")
        if len(cols) != 3:
            continue
        name, sidc, hierarchy = cols[0].strip(), cols[1].strip(), cols[2].strip()
        if name and sidc:
            rows.append((name, normalise_sidc(sidc), hierarchy))
    return rows


def catalogue_tokens() -> list[frozenset[str]]:
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    out: list[frozenset[str]] = []
    for e in data["entries"]:
        if e.get("kind", "symbol") == "symbol":
            out.append(_tokens(str(e.get("func", ""))))
    return out


def is_covered(name: str, cat: list[frozenset[str]]) -> bool:
    want = _tokens(name)
    if not want:
        return True
    return any(want <= tokens for tokens in cat)


def plan() -> list[dict[str, Any]]:
    """One entry per (distinct SIDC, affiliation) that needs a marker."""
    cat = catalogue_tokens()
    seen_sidc: set[str] = set()
    seen_name: set[str] = set()
    out: list[dict[str, Any]] = []
    for name, sidc, hierarchy in read_rows():
        if sidc in seen_sidc or is_covered(name, cat):
            continue
        seen_sidc.add(sidc)
        dim = dimension_of(hierarchy)
        for affil in AFFIL_ORDER:
            variant = sidc[:1] + AFFIL_CHAR[affil] + sidc[2:]
            base = f"AEE_{AFFIL_LETTER[affil]}{DIM_LETTER[dim]}_{_slug(name)}"
            marker = base
            n = 2
            while marker in seen_name:
                marker = f"{base}_{n}"
                n += 1
            seen_name.add(marker)
            out.append(
                {
                    "marker": marker,
                    "func": name,
                    "affil": affil,
                    "dim": dim,
                    "sidc": variant,
                    "hierarchy": hierarchy,
                }
            )
    return out


def _rasterise(svg: Path) -> Any:
    from PIL import Image

    rsvg = shutil.which("rsvg-convert")
    if rsvg is None:
        raise SystemExit("gen_symbology_taxonomy: rsvg-convert not found")
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "art.png"
        r = subprocess.run(
            [rsvg, "-w", str(SIZE), "-h", str(SIZE), str(svg), "-o", str(png)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            raise SystemExit(f"rsvg-convert failed for {svg.name}\n{r.stderr}")
        art = Image.open(png).convert("RGBA")
    white = Image.new("RGBA", art.size, (255, 255, 255, 0))
    white.putalpha(art.getchannel("A"))
    return white


def convert(tga: Path, paa: Path) -> None:
    hemtt = shutil.which("hemtt")
    if hemtt is None:
        raise SystemExit("gen_symbology_taxonomy: hemtt not found")
    paa.unlink(missing_ok=True)
    r = subprocess.run(
        [hemtt, "utils", "paa", "convert", str(tga), str(paa)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise SystemExit(f"paa convert failed for {paa.name}\n{r.stderr}")


def render_svgs(items: list[dict[str, Any]], out_dir: Path) -> None:
    node = shutil.which("node")
    if node is None:
        raise SystemExit("gen_symbology_taxonomy: node not found (milsymbol renderer)")
    manifest = [
        {
            "sidc": it["sidc"],
            "out": str(out_dir / f"{it['marker']}.svg"),
            "size": RENDER,
        }
        for it in items
    ]
    mpath = out_dir / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    env = dict(os.environ, MILSYMBOL_ENTRY=MILSYMBOL_ENTRY)
    r = subprocess.run(
        [node, str(RENDERER), str(mpath)], capture_output=True, text=True, env=env
    )
    if r.returncode != 0:
        raise SystemExit(f"milsymbol render failed\n{r.stdout}\n{r.stderr}")


def build() -> int:
    items = plan()
    MARKERS_OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        render_svgs(items, tmp_dir)

        def one(it: dict[str, Any]) -> None:
            svg = tmp_dir / f"{it['marker']}.svg"
            tga = tmp_dir / f"{it['marker']}.tga"
            _rasterise(svg).save(tga)
            convert(tga, MARKERS_OUT / f"{it['marker']}.paa")

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(one, items))
    write_config(items)
    write_taxonomy(items)
    print(f"taxonomy: {len(items)} markers written")
    return 0


def render_config(items: list[dict[str, Any]]) -> str:
    lines = [
        "// Generated by tools/gen_symbology_taxonomy.py.  Do not edit by hand.",
        "// The MIL-STD-2525 function glyphs the pulled catalogue does not hold,",
        "// rendered from the standard taxonomy by milsymbol (MIT).  The symbol",
        "// designs are the standard's own geometry (public domain).",
        "",
    ]
    for it in items:
        icon = f"{ADDON_PREFIX}\\{it['marker']}.paa"
        display = f"AEE {it['affil']} {it['dim']} {it['func']}"
        lines += [
            f"    class {it['marker']}: AEE_MarkerBase {{",
            f'        name = "{display}";',
            f'        icon = "{icon}";',
            f'        texture = "{icon}";',
            f"        side = {AFFIL_SIDE[it['affil']]};",
            "        scope = 2;",
            "    };",
        ]
    return "\n".join(lines) + "\n"


def write_config(items: list[dict[str, Any]]) -> None:
    CONFIG_OUT.write_text(render_config(items), encoding="utf-8")


def write_taxonomy(items: list[dict[str, Any]]) -> None:
    entries = [
        {
            "marker": it["marker"],
            "func": it["func"],
            "affil": it["affil"],
            "dim": it["dim"],
            "sidc": it["sidc"],
            "hierarchy": it["hierarchy"],
            "source": "MIL-STD-2525 taxonomy (symbol.army 2525C enumeration)",
            "renderer": "milsymbol (MIT)",
            "licence": "MIT renderer; standard geometry is public domain",
        }
        for it in items
    ]
    TAXONOMY_OUT.write_text(
        json.dumps(
            {
                "source": str(TSV),
                "count": len(entries),
                "entries": entries,
            },
            indent=1,
        ),
        encoding="utf-8",
    )


def check() -> int:
    items = plan()
    stale: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        render_svgs(items, tmp_dir)
        for it in items:
            committed = MARKERS_OUT / f"{it['marker']}.paa"
            if not committed.is_file():
                stale.append(f"{it['marker']}.paa is missing")
                continue
            tga = tmp_dir / f"{it['marker']}.tga"
            _rasterise(tmp_dir / f"{it['marker']}.svg").save(tga)
            fresh = tmp_dir / f"{it['marker']}.paa"
            convert(tga, fresh)
            if committed.read_bytes() != fresh.read_bytes():
                stale.append(f"{it['marker']}.paa is stale")
    if CONFIG_OUT.read_text(encoding="utf-8") != render_config(items):
        stale.append("config_taxonomy.hpp is stale")
    if stale:
        print(f"taxonomy: FAIL ({len(stale)})")
        for line in stale:
            print(f"  {line}")
        return 1
    print(f"taxonomy: {len(items)} markers fresh")
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check()
    if "--table" in argv:
        for it in plan():
            print(
                f"{it['marker']}\t{it['affil']}\t{it['dim']}\t{it['sidc']}\t{it['func']}"
            )
        return 0
    return build()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
