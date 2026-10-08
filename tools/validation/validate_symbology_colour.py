#!/usr/bin/env python3
"""Validate that the AEE APP-6 marker textures keep their own colours.

The colour IS the information.  Every AEE marker texture carries its own
colour: the affiliation frame (friend blue, hostile red, neutral green,
unknown yellow), the black glyph and the standard fills.  The engine tint is
neutral (ColorAEE), so the texture is drawn as rendered.  A texture flattened
to a monochrome white mask loses the colour and fails this check.

Each sampled committed .paa is converted back to a PNG with
`hemtt utils paa convert` and inspected:

  * it must show a visible symbol (the alpha is not empty);
  * it must NOT be a monochrome white mask: the opaque content must contain a
    dark or a coloured pixel, not white only;
  * on the composed layers (cross-product, taxonomy) the dominant non-grey
    colour must match the affiliation the marker name encodes.

The sample is deterministic: every affiliation across the catalogue, the
cross-product, the taxonomy and the modifiers.  Pass --all to sweep every
registered texture (slower; the .paa decode spawns hemtt per file).

Run: python3 tools/validation/validate_symbology_colour.py
     python3 tools/validation/validate_symbology_colour.py --all
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[2]
MARKERS = ROOT / "addons" / "optics" / "data" / "markers"

# The registered marker layers.  The composed layers draw a filled affiliation
# frame, so they always carry the affiliation colour.
LAYERS = {
    "catalogue": ROOT / "addons" / "optics" / "config_markers.hpp",
    "crossproduct": ROOT / "addons" / "optics" / "config_crossproduct.hpp",
    "taxonomy": ROOT / "addons" / "optics" / "config_taxonomy.hpp",
    "modifier": ROOT / "addons" / "optics" / "config_modifiers.hpp",
}
COMPOSED_LAYERS = ("crossproduct", "taxonomy")

# A pixel counts as grey when its channel spread is at or below this.
GREY_SPREAD = 24
# A symbol is visible when its alpha reaches at least this.
MIN_ALPHA = 100
# An opaque pixel at or above this in every channel is white.
WHITE_MIN = 200
# A pixel at or below this in every channel is black.
BLACK_MAX = 60

AFFIL_HUE = {"F": "blue", "H": "red", "N": "green", "U": "yellow"}


def classify(rgb: tuple[int, int, int]) -> str:
    """The hue class of a pixel: grey, red, green, blue or yellow."""
    r, g, b = rgb
    if max(r, g, b) - min(r, g, b) <= GREY_SPREAD:
        return "grey"
    if r >= g and r >= b:
        return "yellow" if g > b + 30 else "red"
    if g >= r and g >= b:
        return "green"
    return "blue"


def marker_names(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return re.findall(
        r"^\s*class (AEE_\w+): AEE_MarkerBase", path.read_text(encoding="utf-8"), re.M
    )


def affiliation_of(name: str) -> str | None:
    """The affiliation letter a marker name encodes, or None for an overlay."""
    parts = name.split("_")
    if len(parts) < 2:
        return None
    token = parts[1]
    if token.startswith("X"):
        token = token[1:]
    return token[0] if token and token[0] in AFFIL_HUE else None


def sample() -> list[tuple[str, str]]:
    """A deterministic (layer, marker) sample covering every affiliation."""
    out: list[tuple[str, str]] = []
    for layer, path in LAYERS.items():
        names = marker_names(path)
        if layer == "modifier":
            out += [(layer, name) for name in names[:2]]
            continue
        for aff in AFFIL_HUE:
            match = next((n for n in names if affiliation_of(n) == aff), None)
            if match:
                out.append((layer, match))
    return out


def all_markers() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for layer, path in LAYERS.items():
        out += [(layer, name) for name in marker_names(path)]
    return out


def check(pairs: list[tuple[str, str]]) -> tuple[list[str], dict[str, int]]:
    from PIL import Image

    hemtt = shutil.which("hemtt")
    if hemtt is None:
        raise SystemExit("validate_symbology_colour: hemtt not found on PATH")

    errors: list[str] = []
    stats = {
        "sampled": len(pairs),
        "coloured": 0,
        "monochrome_white": 0,
        "transparent": 0,
        "fully_opaque": 0,
    }
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        for layer, name in pairs:
            paa = MARKERS / f"{name}.paa"
            if not paa.is_file():
                errors.append(f"{name}: texture missing")
                continue
            png = tdir / f"{name}.png"
            result = subprocess.run(
                [hemtt, "utils", "paa", "convert", str(paa), str(png)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0 or not png.is_file():
                errors.append(f"{name}: paa convert failed")
                continue
            image = Image.open(png).convert("RGBA")
            alpha = image.getchannel("A")
            if alpha.getextrema()[1] < MIN_ALPHA:
                errors.append(
                    f"{name}: no visible symbol (alpha max {alpha.getextrema()[1]})"
                )
                continue
            opaque = [px[:3] for px in image.getdata() if px[3] >= 128]
            if not opaque:
                errors.append(f"{name}: no opaque pixels")
                continue
            hues: dict[str, int] = {}
            for px in opaque:
                hue = classify(px)
                hues[hue] = hues.get(hue, 0) + 1
            # The white-mask defect: every opaque pixel is white.
            if all(min(px) >= WHITE_MIN for px in opaque):
                errors.append(f"{name}: MONOCHROME WHITE MASK (the colour is lost)")
                stats["monochrome_white"] += 1
                continue
            coloured = sum(v for k, v in hues.items() if k != "grey")
            if coloured:
                stats["coloured"] += 1
            transparent = sum(1 for v in alpha.getdata() if v <= 40)
            if transparent / (image.width * image.height) < 0.10:
                stats["fully_opaque"] += 1
            else:
                stats["transparent"] += 1
            aff = affiliation_of(name)
            if aff and layer in COMPOSED_LAYERS:
                non_grey = {k: v for k, v in hues.items() if k != "grey"}
                if not non_grey:
                    errors.append(f"{name}: no affiliation colour on a composed layer")
                    continue
                dominant = max(non_grey.items(), key=lambda kv: kv[1])[0]
                if dominant != AFFIL_HUE[aff]:
                    errors.append(
                        f"{name}: dominant {dominant} does not match "
                        f"{AFFIL_HUE[aff]} affiliation"
                    )
    return errors, stats


def main(argv: list[str]) -> int:
    pairs = all_markers() if "--all" in argv else sample()
    # The four affiliations must each be represented in the catalogue.
    catalogue = marker_names(LAYERS["catalogue"])
    for aff in AFFIL_HUE:
        if not any(affiliation_of(n) == aff for n in catalogue):
            print(f"validate_symbology_colour: no catalogue marker for {aff}")
            return 1
    errors, stats = check(pairs)
    if errors:
        print(f"validate_symbology_colour: FAIL ({len(errors)})")
        for line in errors[:40]:
            print(f"  {line}")
        return 1
    print(
        "validate_symbology_colour: PASS "
        f"({stats['sampled']} sampled, {stats['coloured']} coloured, "
        f"{stats['transparent']} transparent, {stats['fully_opaque']} fully opaque, "
        f"{stats['monochrome_white']} monochrome)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
