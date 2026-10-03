#!/usr/bin/env python3
"""Generate the fusion emissive material ladder (issue #196 family).

The fusion overlay quantises each selection's AGC brightness to one of 256
levels and swaps the matching emissive rvmat onto the selection.  The files
are GENERATED here, not hand-written, so the count is auditable and the set
is reproducible.  An earlier revision shipped 16 hand-written files named by
their grey percent (0, 7, 13, ... 100); that was a texture-count convenience,
not physics, and it made the quantiser fourteen times coarser than the sensor
resolves.  A real thermal display is 8-bit grey, and the modelled detectors
are 320x240 and 640x480, so 256 levels is the defensible scale.

Material form, matched byte-for-byte to the old set:
  - ambient {20,20,20,1}, diffuse {0.005,0.005,0.005,0}, AlwaysInShadow and
    a PURE WHITE Stage1 texture.  The Stage1 must stay white: a grey Stage1
    composited over the green NVG base tints the scene pink (issue #204).
  - emmisive carries the heat, = (band / 255) * 500, four decimal places, so
    band 255 is exactly the A3TI full-white value 500 and band 0 is black.
    The ladder is monotonic in radiance, which is what makes the white-hot
    polarity correct; test_thermal_optics.py asserts it.

Cost note: the band count changes only how many material FILES ship.  The
overlay still calls setObjectMaterial once per selection per tick, so the
per-tick call count is unchanged by this file.

Usage:
  python3 tools/gen_fusion_emissive_materials.py          # write the files
  python3 tools/gen_fusion_emissive_materials.py --check  # verify, no write
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "addons" / "thermal" / "data"
PREFIX = "fusion_emissive_"
SUFFIX = ".rvmat"
MAX_EMISSIVE = 500.0
BANDS = 256

TEMPLATE = """ambient[] = {{20,20,20,1}};
diffuse[] = {{0.005,0.005,0.005,0}};
forcedDiffuse[] = {{0,0,0,0}};
emmisive[] = {{{e},{e},{e},{e}}};
specular[] = {{0,0,0,0}};
specularPower = 1;
renderFlags[] = {{"AlwaysInShadow"}};
PixelShaderID = "Normal";
VertexShaderID = "Basic";
class Stage1
{{
    texture = "#(rgb,8,8,3)color(1,1,1,1)";
    uvSource = "tex";
}};
"""

_NAME = re.compile(rf"^{PREFIX}(\d{{3}}){re.escape(SUFFIX)}$")


def emissive_for(band: int) -> str:
    """Band 0..255 -> the emissive string, grey * 500 at four decimals."""
    return f"{band / (BANDS - 1) * MAX_EMISSIVE:.4f}"


def render(band: int) -> str:
    e = emissive_for(band)
    return TEMPLATE.format(e=e)


def expected() -> dict:
    return {f"{PREFIX}{b:03d}{SUFFIX}": render(b) for b in range(BANDS)}


def stale_names(present: set) -> list:
    """Files matching fusion_emissive_NNN.rvmat that are not in the set.

    The old set used two-digit and three-digit percent names (00, 07, ...,
    100); any of them still on disk is stale dead weight for the PBO.
    """
    names = sorted(n for n in present if n.startswith(PREFIX) and n.endswith(SUFFIX))
    return [n for n in names if not _NAME.match(n)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="verify only, write nothing")
    args = ap.parse_args()

    want = expected()
    present = {p.name for p in DATA_DIR.iterdir() if p.is_file()}
    stale = stale_names(present)

    problems = []
    if args.check:
        for name, text in want.items():
            path = DATA_DIR / name
            if not path.exists():
                problems.append(f"missing {name}")
            elif path.read_text(encoding="utf-8") != text:
                problems.append(f"out of date {name}")
        problems += [f"stale {n}" for n in stale]
    else:
        for name in stale:
            (DATA_DIR / name).unlink()
        for name, text in want.items():
            (DATA_DIR / name).write_text(text, encoding="utf-8")

    total = sum(len(t) for t in want.values())
    print(
        f"fusion emissive ladder: {BANDS} bands, {len(want)} files, {total} bytes total"
    )
    print(f"emissive band 0 = {emissive_for(0)}, band 255 = {emissive_for(255)}")
    if problems:
        for p in problems:
            print(f"FAIL {p}")
        return 1
    print("OK" if args.check else "WROTE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
