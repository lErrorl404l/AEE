#!/usr/bin/env python3
"""Validate that every AEE terrain symbol texture is a transparent mask.

The engine tints a map icon through the class colour, so every terrain symbol
texture must be a white symbol on a TRANSPARENT ground.  A texture with no
alpha channel, a fully opaque alpha, or an opaque background renders as a
solid box behind the symbol and fails this check.

Each committed .paa is converted back to a PNG with `hemtt utils paa convert`
and its alpha channel is inspected.

Run: python3 tools/validation/validate_terrain_alpha.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[2]
SOURCE_JSON = ROOT / "data" / "symbology" / "terrain_symbols.json"
TERRAIN_DIR = ROOT / "addons" / "optics" / "data" / "terrain"

# A background pixel must be no more than this opaque (0..255).
BACKGROUND_MAX = 40
# At least this fraction of pixels must be transparent for a transparent ground.
MIN_TRANSPARENT_FRACTION = 0.10


def referenced(doc: dict) -> list[str]:
    out: list[str] = []
    for section in ("locations", "objects"):
        for row in doc.get(section, []):
            symbol = row.get("symbol")
            if symbol and symbol not in out:
                out.append(symbol)
    return out


def main() -> int:
    from PIL import Image

    if not SOURCE_JSON.exists():
        print("validate_terrain_alpha: terrain_symbols.json missing")
        return 1
    hemtt = shutil.which("hemtt")
    if hemtt is None:
        print("validate_terrain_alpha: hemtt not found on PATH")
        return 1

    symbols = referenced(json.loads(SOURCE_JSON.read_text(encoding="utf-8")))
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for symbol in symbols:
            paa = TERRAIN_DIR / f"{symbol}.paa"
            if not paa.is_file():
                errors.append(f"{symbol}: texture missing")
                continue
            out = tmp_dir / f"{symbol}.png"
            result = subprocess.run(
                [hemtt, "utils", "paa", "convert", str(paa), str(out)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0 or not out.is_file():
                errors.append(f"{symbol}: paa convert failed")
                continue
            image = Image.open(out).convert("RGBA")
            alpha = image.getchannel("A")
            low, high = alpha.getextrema()
            if high < 100:
                errors.append(f"{symbol}: no visible symbol (alpha max {high})")
            if low > 0:
                errors.append(f"{symbol}: no transparent background (alpha min {low})")
            transparent = sum(1 for v in alpha.getdata() if v <= BACKGROUND_MAX)
            fraction = transparent / (image.width * image.height)
            if fraction < MIN_TRANSPARENT_FRACTION:
                errors.append(
                    f"{symbol}: background is not transparent "
                    f"({fraction:.1%} transparent)"
                )

    if errors:
        print(f"validate_terrain_alpha: FAIL ({len(errors)})")
        for line in errors[:40]:
            print(f"  {line}")
        return 1
    print(f"validate_terrain_alpha: PASS ({len(symbols)} transparent masks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
