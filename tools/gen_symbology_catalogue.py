#!/usr/bin/env python3
"""Generate the complete AEE APP-6 marker set from the committed catalogue.

The catalogue (data/symbology/nato_catalogue.json) records every NATO / APP-6
map symbol image, with its affiliation, battle dimension, function, frame,
licence, author and source URL.

The catalogue images are COMMITTED under data/symbology/sources:

  * sources/svg/<dir>/<file>.svg  -- the 1092 source drawings, exactly as
    pulled, for provenance (Wikimedia Commons CC BY-SA 4.0 / CC BY / public
    domain; see sources/README.md).
  * sources/render/<marker>.png   -- the 903 rendered 64 px RGBA canvases, the
    exact input to `hemtt utils paa convert`.

Why the renders are committed.  The render is not reproducible across
machines.  librsvg encodes the same pixels into different PNG bytes, and 166
of the source drawings carry `<text>` with a `font-family`, so the glyph
depends on the installed font: the local render resolves `sans-serif` to Noto
Sans, a bare runner resolves it to DejaVu Sans, and 162 of 903 markers then
differ.  No distribution ships librsvg 2.62.4 (the version that cut the
shipped .paa) and the font stack cannot be pinned exactly, so the render
OUTPUT is pinned instead of the renderer.  The committed 64 px canvas is the
source of truth for the texture, and CI reproduces each .paa from it byte for
byte with no renderer dependency.  The SVG -> render step is proved
structurally by --verify-svg.

For each catalogue symbol this generator:

  * cuts the committed 64 px render to a .paa with `hemtt utils paa convert`,
  * emits one CfgMarkers child into addons/optics/config_markers.hpp, and
  * emits addons/optics/data/markers/ATTRIBUTION.md with the per-file source
    URL, licence and author.

The real image is used wherever it exists; nothing is hand-drawn here.  The
set is registered under the AEE_Symbology marker class, so the complete APP-6
grammar is selectable in Eden and drawn by the engine marker layer.

Run:  python3 tools/gen_symbology_catalogue.py
      python3 tools/gen_symbology_catalogue.py --check
      python3 tools/gen_symbology_catalogue.py --verify-svg
      python3 tools/gen_symbology_catalogue.py --render   (re-cut the renders)
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
SOURCES = ROOT / "data" / "symbology" / "sources"
SVG_ROOT = SOURCES / "svg"
RENDER_ROOT = SOURCES / "render"
MARKERS_OUT = ROOT / "addons" / "optics" / "data" / "markers"
CONFIG_OUT = ROOT / "addons" / "optics" / "config_markers.hpp"
ATTRIB_OUT = MARKERS_OUT / "ATTRIBUTION.md"
ADDON_PREFIX = "\\z\\aee\\addons\\optics\\data\\markers"

SIZE = 64
ART = 58  # the art box inside the 64 px marker, leaving a small margin
RENDER = 256  # the SVG is rasterised at this size, then reduced to ART

# The SVG -> render compare in --verify-svg is structural, not byte-for-byte,
# because the render depends on the librsvg version and on the installed font.
# The tolerance is calibrated on the observed drift: with the pinned font
# (fonts-noto-core) 894/903 renders are pixel identical and the 9 that differ
# are a font-variant glyph (ink IoU 1.0); without the pinned font the worst
# case is ink IoU 0.647.  A wrong glyph, a re-colour, a plate crop or a
# missing render still fails.
MAX_CHANGED_FRACTION = 0.15  # antialiasing and a font variant move a few percent
NOISE_DELTA = 8  # per-channel differences at or below this are noise
MIN_INK_IOU = 0.60  # the painted (alpha) region must overlap the SVG render

AFFIL_LETTER = {
    "Friend": "F",
    "Hostile": "H",
    "Neutral": "N",
    "Unknown": "U",
    "Unspecified": "V",
}
AFFIL_SIDE = {"Friend": 1, "Hostile": 0, "Neutral": 2, "Unknown": 2, "Unspecified": 2}
DIM_LETTER = {
    "Land": "L",
    "Air/Space": "A",
    "Sea Surface": "S",
    "Subsurface": "U",
    "Installation": "I",
    "Equipment": "E",
}


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


def _source_svg(entry: dict[str, Any]) -> Path:
    return SVG_ROOT / str(entry["dir"]) / str(entry["file"])


def _render_path(name: str) -> Path:
    return RENDER_ROOT / f"{name}.png"


def _load_render(name: str) -> Any:
    """The committed 64 px canvas, the pinned input to `hemtt utils paa convert`."""
    from PIL import Image

    path = _render_path(name)
    if not path.is_file():
        raise SystemExit(f"gen_symbology_catalogue: render {path} not found")
    return Image.open(path).convert("RGBA")


def _rasterise(src: Path) -> Any:
    """Rasterise a source image to a 64 px canvas, keeping its own colours.

    The source drawing is the record.  It is rendered on a transparent
    background with its colours preserved: the frame keeps the affiliation
    colour the standard gives it and the glyph stays black.  The texture is not
    reduced to a white mask, because the engine tint is neutral and the colour
    must live in the texture.
    """
    from PIL import Image

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
                    str(RENDER),
                    "-h",
                    str(RENDER),
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
    canvas = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    canvas.alpha_composite(art, ((SIZE - art.width) // 2, (SIZE - art.height) // 2))
    return canvas


def render_mismatch(committed: Path, fresh: Path) -> str | None:
    """Return why the committed render is not the SVG render, or None when it is.

    A byte compare cannot cross a librsvg version or a font, so this compares
    structure: the size, a real alpha channel, the fraction of changed pixels
    and the painted (alpha) geometry, each within a tolerance.
    """
    from PIL import Image, ImageChops

    with Image.open(committed) as c_img, Image.open(fresh) as f_img:
        if c_img.size != f_img.size:
            return f"size {c_img.size} != SVG render {f_img.size}"
        committed_has_alpha = "A" in c_img.getbands()
        committed_rgba = c_img.convert("RGBA")
        fresh_rgba = f_img.convert("RGBA")

    # A point or line symbol renders on a transparent ground.  A source that
    # dropped the alpha channel is a flat plate crop, not that render.
    render_transparent = fresh_rgba.getchannel("A").getextrema()[0] < 255
    if render_transparent and not committed_has_alpha:
        return "render has no alpha channel (a flat crop, not the SVG render)"

    diff = ImageChops.difference(committed_rgba, fresh_rgba)

    def above_noise(band):
        return band.point(lambda value: 255 if value > NOISE_DELTA else 0)

    marked = above_noise(diff.getchannel("R"))
    for channel in ("G", "B", "A"):
        marked = ImageChops.lighter(marked, above_noise(diff.getchannel(channel)))
    changed = marked.histogram()[255]
    total = committed_rgba.width * committed_rgba.height
    if changed > MAX_CHANGED_FRACTION * total:
        return f"{changed} of {total} pixels differ from the SVG render"

    committed_ink = committed_rgba.getchannel("A").point(
        lambda v: 255 if v > 127 else 0
    )
    fresh_ink = fresh_rgba.getchannel("A").point(lambda v: 255 if v > 127 else 0)
    union = ImageChops.lighter(committed_ink, fresh_ink).histogram()[255]
    if union:
        overlap = ImageChops.multiply(committed_ink, fresh_ink).histogram()[255]
        iou = overlap / union
        if iou < MIN_INK_IOU:
            return f"painted geometry differs from the SVG render (IoU {iou:.3f})"
    return None


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


def symbol_entries() -> list[dict[str, Any]]:
    return [e for e in load() if e.get("kind", "symbol") == "symbol"]


def entries() -> list[tuple[str, dict[str, Any]]]:
    seen: set[str] = set()
    out: list[tuple[str, dict[str, Any]]] = []
    for entry in symbol_entries():
        out.append((marker_name(entry, seen), entry))
    return out


def build() -> int:
    MARKERS_OUT.mkdir(parents=True, exist_ok=True)
    pairs = entries()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for name, entry in pairs:
            tga = tmp_dir / f"{name}.tga"
            _load_render(name).save(tga)
            convert(tga, MARKERS_OUT / f"{name}.paa")
    write_config(pairs)
    write_attribution(pairs)
    print(f"symbology catalogue: {len(pairs)} markers written")
    return 0


def render_all() -> int:
    """Re-cut the committed 64 px renders from the committed source SVGs.

    This is the only step that needs rsvg-convert and the render font, so it
    runs on the machine that cut the textures, not in CI.  See the module
    docstring for why the renders are committed.
    """
    RENDER_ROOT.mkdir(parents=True, exist_ok=True)
    pairs = entries()
    for name, entry in pairs:
        _rasterise(_source_svg(entry)).save(_render_path(name))
    print(f"symbology catalogue: {len(pairs)} renders written to {RENDER_ROOT}")
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
# field (BIKI Addon configuration).
#
# The engine class is pinned to the EXACT APP-6 function it means.  A loose
# keyword match is not used: "armour" is a substring of "armoured", so a keyword
# lookup once pinned b_armor to the anti-tank glyph and b_plane to an engineer
# glyph.  The family letter gives the affiliation; the stem is the catalogue
# function without the affiliation prefix.
ENGINE_FAMILY_AFFIL = {"b": "Friendly", "o": "Hostile", "n": "Neutral"}
ENGINE_GLYPH_STEM = {
    "inf": "Unit Infantry",
    "motor_inf": "Unit Infantry - Motorized",
    "armor": "Unit Armour",
    "recon": "Unit Reconnaissance",
    "plane": "Unit Aviation - Fixed Wing",
    "uav": "Unit Unmanned Aerial Vehicles",
    "med": "Unit Medical",
    "art": "Unit Artillery",
    "mortar": "Unit Mortars",
    "hq": "Unit Headquarters Unit",
    "support": "Unit CSS - Combat Service Support",
    "maint": "Unit CSS - Maintenance",
    "service": "Unit CSS - Supply",
    "antiair": "Unit Air Defence",
}
# The engine families and the glyphs AEE overwrites (Addons/ui_f CfgMarkers).
# The engine also ships b_/o_/n_ air, mech_inf, naval, installation and unknown
# plus c_ car, ship and unknown; those are not overwritten here and are recorded
# as a gap in the register.
ENGINE_FAMILIES = {
    "b": list(ENGINE_GLYPH_STEM),
    "o": list(ENGINE_GLYPH_STEM),
    "n": [glyph for glyph in ENGINE_GLYPH_STEM if glyph != "plane"],
}
# The c_ family is the engine's own civil/unknown set.  AEE pins the two classes
# it has an exact symbol for.
ENGINE_C_EXACT = {"c_air": "APP-6 Army Aviation", "c_plane": "APP-6 Air Force"}
# Where the catalogue holds no single-image symbol for an engine class, the
# interim exact symbol is named here and the deviation is recorded.  The
# composed cross-product supplies the true symbol.
ENGINE_FALLBACK = {"n_motor_inf": "Neutral Unit Infantry"}


def _find_exact(pairs: list[tuple[str, dict[str, Any]]], func: str) -> str | None:
    for name, entry in pairs:
        if entry.get("func") == func:
            return name
    return None


def engine_overrides(
    pairs: list[tuple[str, dict[str, Any]]],
) -> list[tuple[str, str | None, str, bool]]:
    """Resolve each engine class to its exact catalogue marker.

    Returns (engine class, marker name or None, exact function, deviated).
    """
    out: list[tuple[str, str | None, str, bool]] = []
    for fam, glyphs in ENGINE_FAMILIES.items():
        affil = ENGINE_FAMILY_AFFIL[fam]
        for glyph in glyphs:
            cls = f"{fam}_{glyph}"
            func = f"{affil} {ENGINE_GLYPH_STEM[glyph]}"
            name = _find_exact(pairs, func)
            deviated = False
            if name is None:
                fallback = ENGINE_FALLBACK.get(cls)
                name = _find_exact(pairs, fallback) if fallback else None
                deviated = name is not None
            out.append((cls, name, func, deviated))
    for cls, func in ENGINE_C_EXACT.items():
        out.append((cls, _find_exact(pairs, func), func, False))
    return out


def render_engine_overrides(pairs: list[tuple[str, dict[str, Any]]]) -> str:
    lines = [
        "",
        "// Overwrite the engine's own NATO marker families, so the base Arma",
        "// marker renders the AEE symbol and no engine mark shows beside it.",
        "// A mod may re-declare an engine class; Arma merges the configs and the",
        "// later-loaded value wins (BIKI Addon configuration).  Each class is",
        "// pinned to its exact APP-6 symbol by tools/gen_symbology_catalogue.py.",
    ]
    for cls, name, func, deviated in engine_overrides(pairs):
        if name is None:
            lines.append(f"    // {cls}: no exact catalogue symbol for {func!r}")
            continue
        if deviated:
            lines.append(
                f"    // {cls}: catalogue lacks {func!r}; using {name} "
                "(composed cross-product supplies the exact symbol)"
            )
        icon = f"{ADDON_PREFIX}\\{name}.paa"
        lines.append(f'    class {cls} {{ icon = "{icon}"; texture = "{icon}"; }};')
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
    """Reproduce each committed .paa from its committed render, byte for byte.

    The committed 64 px render is the pinned texture input, so this needs no
    renderer and runs in CI.  A stale .paa, a missing render, or a stale
    config or attribution file fails.
    """
    pairs = entries()
    stale: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for name, entry in pairs:
            committed = MARKERS_OUT / f"{name}.paa"
            if not committed.is_file():
                stale.append(f"{name}.paa is missing")
                continue
            if not _render_path(name).is_file():
                stale.append(f"{name}.png render is missing")
                continue
            tga = tmp_dir / f"{name}.tga"
            _load_render(name).save(tga)
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
    print(
        f"symbology catalogue: {len(pairs)} .paa reproduce their committed "
        f"renders; config and attribution fresh"
    )
    return 0


def verify_svg() -> int:
    """Prove every committed render is the render of its committed source SVG.

    The compare is structural, not byte-for-byte, so it holds across the
    librsvg version and the render font.  See render_mismatch.
    """
    bad: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for name, entry in entries():
            committed = _render_path(name)
            if not committed.is_file():
                bad.append(f"{name}: render is missing")
                continue
            svg = _source_svg(entry)
            if not svg.is_file():
                bad.append(f"{name}: source SVG {svg.name} is missing")
                continue
            fresh = tmp_dir / f"{name}.png"
            _rasterise(svg).save(fresh)
            mismatch = render_mismatch(committed, fresh)
            if mismatch:
                bad.append(f"{name}: render is not the SVG render ({mismatch})")
    if bad:
        print(f"symbology catalogue: SVG provenance FAIL ({len(bad)})")
        for line in bad:
            print(f"  {line}")
        return 1
    print(
        f"symbology catalogue: {len(entries())} committed renders match their "
        f"source SVGs"
    )
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check()
    if "--verify-svg" in argv:
        return verify_svg()
    if "--render" in argv:
        return render_all()
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
