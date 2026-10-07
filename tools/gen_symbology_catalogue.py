#!/usr/bin/env python3
"""Generate the complete AEE APP-6 marker set from the pulled catalogue.

The catalogue (data/symbology/nato_catalogue.json) records every NATO / APP-6
map symbol image pulled from the three operator sources, with its affiliation,
battle dimension, function, frame, licence, author and source URL.

For each catalogue symbol this generator:

  * rasterises the real image (rsvg-convert for SVG, Pillow for PNG/JPEG) into a
    64 px white-on-transparent mask, so the engine marker colour tints it the
    way it tints the vanilla NATO markers,
  * converts the mask to a .paa with `hemtt utils paa convert`,
  * emits one CfgMarkers child into addons/optics/config_markers.hpp, and
  * emits addons/optics/data/markers/ATTRIBUTION.md with the per-file source
    URL, licence and author.

The real image is used wherever it exists; nothing is hand-drawn here.  The
set is registered under the AEE_Symbology marker class, so the complete APP-6
grammar is selectable in Eden and drawn by the engine marker layer.

Run:  python3 tools/gen_symbology_catalogue.py
      python3 tools/gen_symbology_catalogue.py --check
      python3 tools/gen_symbology_catalogue.py --table
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
CATALOGUE = ROOT / "data" / "symbology" / "nato_catalogue.json"
SOURCE_ROOT = Path("/tmp/opencode/nato-symbols")
MARKERS_OUT = ROOT / "addons" / "optics" / "data" / "markers"
CONFIG_OUT = ROOT / "addons" / "optics" / "config_markers.hpp"
ATTRIB_OUT = MARKERS_OUT / "ATTRIBUTION.md"
ADDON_PREFIX = "\\z\\aee\\addons\\optics\\data\\markers"

SIZE = 64
ART = 58  # the art box inside the 64 px marker, leaving a small margin

AFFIL_LETTER = {
    "Friend": "F",
    "Hostile": "H",
    "Neutral": "N",
    "Unknown": "U",
    "Unspecified": "V",
}
AFFIL_SIDE = {"Friend": 1, "Hostile": 0, "Neutral": 2, "Unknown": 2, "Unspecified": 2}
DIM_LETTER = {"Land": "L", "Air/Space": "A", "Sea Surface": "S"}


def load() -> list[dict[str, Any]]:
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    return list(data["entries"])


def _slug(text: str, limit: int = 32) -> str:
    out: list[str] = []
    prev_us = False
    for ch in text:
        if ch.isalnum():
            out.append(ch)
            prev_us = False
        elif not prev_us:
            out.append("_")
            prev_us = True
    slug = "".join(out).strip("_")
    return slug[:limit].rstrip("_") or "Symbol"


def marker_name(entry: dict[str, Any], seen: set[str]) -> str:
    fam = AFFIL_LETTER.get(entry.get("affil", ""), "V")
    dim = DIM_LETTER.get(entry.get("dim", ""), "L")
    base = f"AEE_{fam}{dim}_{_slug(str(entry.get('func', '')))}"
    name = base
    n = 2
    while name in seen:
        name = f"{base}_{n}"
        n += 1
    seen.add(name)
    return name


def _source_path(entry: dict[str, Any]) -> Path:
    return SOURCE_ROOT / str(entry["dir"]) / str(entry["file"])


def _rasterise(src: Path) -> Any:
    """Rasterise a source image into a 64 px white-on-transparent mask."""
    from PIL import Image, ImageChops

    if src.suffix.lower() == ".svg":
        rsvg = shutil.which("rsvg-convert")
        if rsvg is None:
            raise SystemExit("gen_symbology_catalogue: rsvg-convert not found")
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "art.png"
            result = subprocess.run(
                [
                    rsvg,
                    "-w",
                    str(ART),
                    "-h",
                    str(ART),
                    "--keep-aspect-ratio",
                    str(src),
                    "-o",
                    str(png),
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise SystemExit(f"rsvg-convert failed for {src.name}\n{result.stderr}")
            art = Image.open(png).convert("RGBA")
    else:
        art = Image.open(src).convert("RGBA")
        art.thumbnail((ART, ART), Image.LANCZOS)

    # Ink mask: dark strokes become opaque white, light background becomes
    # transparent.  Source alpha is respected so a transparent-background file
    # keeps its transparency.
    lum = art.convert("L")
    ink = ImageChops.invert(lum)
    alpha = ImageChops.multiply(ink, art.getchannel("A"))

    canvas = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    white = Image.new("RGBA", art.size, (255, 255, 255, 0))
    white.putalpha(alpha)
    canvas.alpha_composite(white, ((SIZE - art.width) // 2, (SIZE - art.height) // 2))
    return canvas


def convert(tga: Path, paa: Path) -> None:
    hemtt = shutil.which("hemtt")
    if hemtt is None:
        raise SystemExit("gen_symbology_catalogue: hemtt not found on PATH")
    paa.unlink(missing_ok=True)
    result = subprocess.run(
        [hemtt, "utils", "paa", "convert", str(tga), str(paa)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"paa convert failed for {paa.name}\n{result.stderr}")


def entries() -> list[tuple[str, dict[str, Any]]]:
    seen: set[str] = set()
    out: list[tuple[str, dict[str, Any]]] = []
    for entry in load():
        out.append((marker_name(entry, seen), entry))
    return out


def build() -> int:
    MARKERS_OUT.mkdir(parents=True, exist_ok=True)
    pairs = entries()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for name, entry in pairs:
            tga = tmp_dir / f"{name}.tga"
            _rasterise(_source_path(entry)).save(tga)
            convert(tga, MARKERS_OUT / f"{name}.paa")
    write_config(pairs)
    write_attribution(pairs)
    print(f"symbology catalogue: {len(pairs)} markers written")
    return 0


def render_config(pairs: list[tuple[str, dict[str, Any]]]) -> str:
    lines = [
        "// Generated by tools/gen_symbology_catalogue.py.  Do not edit by hand.",
        "// The complete AEE APP-6 marker set, composed from the pulled catalogue",
        "// images.  Each icon is a real .paa under data/markers.  markerClass and",
        "// size/shadow come from AEE_MarkerBase in config.cpp.",
        "",
    ]
    for name, entry in pairs:
        affil = str(entry.get("affil", "Unspecified"))
        side = AFFIL_SIDE.get(affil, 2)
        display = f"AEE {affil} {entry.get('dim', '')} {entry.get('func', '')}".strip()
        icon = f"{ADDON_PREFIX}\\{name}.paa"
        lines += [
            f"    class {name}: AEE_MarkerBase {{",
            f'        name = "{display}";',
            f'        icon = "{icon}";',
            f'        texture = "{icon}";',
            f"        side = {side};",
            "        scope = 2;",
            "    };",
        ]
    return "\n".join(lines) + "\n"


def write_config(pairs: list[tuple[str, dict[str, Any]]]) -> None:
    CONFIG_OUT.write_text(
        render_config(pairs) + "\n" + render_engine_overrides(pairs), encoding="utf-8"
    )


# The engine's own NATO marker families.  AEE overwrites the icon of each so the
# base Arma marker renders the AEE symbol.  Arma merges addon configs and the
# later-loaded mod value wins, so re-declaring the class overrides the engine
# field (BIKI Addon configuration).  Family letter -> the APP-6 affiliation.
ENGINE_FAMILY_AFFIL = {
    "b": "Friend",
    "o": "Hostile",
    "n": "Neutral",
    "c": "Unspecified",
}
ENGINE_GLYPH_KEYWORD = {
    "unknown": "Unknown",
    "inf": "Infantry",
    "motor_inf": "Motor",
    "mech_inf": "Mechanized Infantry",
    "armor": "Armour",
    "recon": "Reconnaissance",
    "air": "Army Aviation",
    "plane": "Air Force",
    "uav": "Unmanned",
    "naval": "Navy",
    "med": "Medical",
    "art": "Artillery",
    "mortar": "Mortar",
    "hq": "Headquarters",
    "support": "Combat Service Support",
    "maint": "Maintenance",
    "service": "Supply",
    "installation": "Installation",
    "antiair": "Air Defence",
}
# The engine families and their glyphs (Addons/ui_f CfgMarkers NATO block).
ENGINE_FAMILIES = {
    "b": list(ENGINE_GLYPH_KEYWORD),
    "o": list(ENGINE_GLYPH_KEYWORD),
    "n": list(ENGINE_GLYPH_KEYWORD),
    "c": ["air", "car", "plane", "ship", "unknown"],
}


def _find_asset(
    pairs: list[tuple[str, dict[str, Any]]], affil: str, keyword: str
) -> str | None:
    for name, entry in pairs:
        if (
            entry.get("affil") == affil
            and keyword.lower() in str(entry.get("func", "")).lower()
        ):
            return name
    return None


def render_engine_overrides(pairs: list[tuple[str, dict[str, Any]]]) -> str:
    lines = [
        "",
        "// Overwrite the engine's own NATO marker families, so the base Arma",
        "// marker renders the AEE symbol and no engine mark shows beside it.",
        "// A mod may re-declare an engine class; Arma merges the configs and the",
        "// later-loaded value wins (BIKI Addon configuration).",
    ]
    for fam, glyphs in ENGINE_FAMILIES.items():
        affil = ENGINE_FAMILY_AFFIL[fam]
        for glyph in glyphs:
            keyword = ENGINE_GLYPH_KEYWORD.get(glyph)
            if not keyword:
                continue
            asset = _find_asset(pairs, affil, keyword)
            if asset is None:
                continue
            icon = f"{ADDON_PREFIX}\\{asset}.paa"
            lines.append(
                f'    class {fam}_{glyph} {{ icon = "{icon}"; texture = "{icon}"; }};'
            )
    return "\n".join(lines) + "\n"


def render_attribution(pairs: list[tuple[str, dict[str, Any]]]) -> str:
    lines = [
        "# AEE APP-6 marker texture attribution",
        "",
        "The AEE map markers are real `.paa` textures composed from the NATO / APP-6",
        "symbol images pulled from Wikimedia Commons and en.wikipedia.  The symbol",
        "designs are a standard (MIL-STD-2525, a US Government work, and NATO APP-6);",
        "the licence below is the uploader's licence on their own SVG trace.  Each",
        "converted `.paa` of a CC BY-SA file remains CC BY-SA 4.0.  AEE is",
        "GPL-2.0-or-later, and CC BY-SA 4.0 is one-way compatible with GPLv3, so the",
        "combined distribution is GPLv3 by the 'or later' route.",
        "",
        "| AEE asset | Source file | Licence | Author | Source URL |",
        "|---|---|---|---|---|",
    ]
    for name, entry in pairs:
        file = str(entry.get("file", "")).replace("|", "\\|")
        lic = str(entry.get("license", "")).replace("|", "\\|")
        artist = str(entry.get("artist", "")).replace("|", "\\|")
        url = str(entry.get("url", ""))
        lines.append(f"| {name} | {file} | {lic} | {artist} | {url} |")
    return "\n".join(lines) + "\n"


def write_attribution(pairs: list[tuple[str, dict[str, Any]]]) -> None:
    ATTRIB_OUT.write_text(render_attribution(pairs), encoding="utf-8")


def check() -> int:
    pairs = entries()
    stale: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for name, entry in pairs:
            committed = MARKERS_OUT / f"{name}.paa"
            if not committed.is_file():
                stale.append(f"{name}.paa is missing")
                continue
            tga = tmp_dir / f"{name}.tga"
            _rasterise(_source_path(entry)).save(tga)
            fresh = tmp_dir / f"{name}.paa"
            convert(tga, fresh)
            if committed.read_bytes() != fresh.read_bytes():
                stale.append(f"{name}.paa is stale")
    if CONFIG_OUT.read_text(encoding="utf-8") != (
        render_config(pairs) + "\n" + render_engine_overrides(pairs)
    ):
        stale.append("config_markers.hpp is stale")
    if ATTRIB_OUT.read_text(encoding="utf-8") != render_attribution(pairs):
        stale.append("ATTRIBUTION.md is stale")
    if stale:
        print(f"symbology catalogue: FAIL ({len(stale)})")
        for line in stale:
            print(f"  {line}")
        return 1
    print(f"symbology catalogue: {len(pairs)} markers fresh")
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check()
    if "--table" in argv:
        for name, entry in entries():
            print(
                f"{name}\t{entry.get('affil')}\t{entry.get('dim')}\t"
                f"{entry.get('license')}\t{entry.get('artist')}"
            )
        return 0
    return build()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
