#!/usr/bin/env python3
"""Screenshot differential for the visual QA surfaces.

Compares a baseline render against a candidate render of the same pinned scene
and reports how much, and where, the two differ. The engine draws the surface,
so a config value that is set but never drawn shows up here as a near-zero
delta. That is the "config valid, render wrong" fault a config assertion cannot
see.

Client only. A dedicated server renders nothing, so the images are captured by
hand with the dev harness DevScreenshot keybind (fnc_devScreenshot). This tool
never runs in the gate. It reads images a person captured.

Usage:
    compare_screens.py --label map --baseline vanilla_map.png \
        --candidate aee_map.png [--grid 8] [--threshold 8] \
        [--expect-change 0.02] [--crop X,Y,W,H] [--top-colours 5]

Exit codes:
    0  the report was produced, and any --expect-change floor was met
    1  the images differ in size, or the delta missed --expect-change
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError as exc:  # pragma: no cover - environment guard
    sys.stderr.write(f"compare_screens needs Pillow and numpy: {exc}\n")
    raise SystemExit(2)


def load_rgb(path: Path, crop: tuple[int, int, int, int] | None):
    image = Image.open(path).convert("RGB")
    if crop is not None:
        x, y, w, h = crop
        image = image.crop((x, y, x + w, y + h))
    return np.asarray(image, dtype=np.int16)


def dominant_colours(arr, count: int):
    """The most common colours after 5-bit-per-channel quantisation."""
    quant = (arr >> 3).astype(np.int32)
    packed = (quant[:, :, 0] << 10) | (quant[:, :, 1] << 5) | quant[:, :, 2]
    values, counts = np.unique(packed, return_counts=True)
    order = np.argsort(counts)[::-1][:count]
    total = arr.shape[0] * arr.shape[1]
    rows = []
    for index in order:
        value = int(values[index])
        rgb = (((value >> 10) & 31) << 3, ((value >> 5) & 31) << 3, (value & 31) << 3)
        rows.append((rgb, counts[index] / total))
    return rows


def change_grid(changed, size: int):
    height, width = changed.shape
    rows = []
    for row in range(size):
        line = []
        for column in range(size):
            y0 = row * height // size
            y1 = (row + 1) * height // size
            x0 = column * width // size
            x1 = (column + 1) * width // size
            cell = changed[y0:y1, x0:x1]
            share = float(cell.mean()) if cell.size else 0.0
            line.append(min(9, int(share * 10)))
        rows.append(line)
    return rows


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Screenshot differential.")
    parser.add_argument("--label", required=True, help="surface name, for the report")
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--grid", type=int, default=8)
    parser.add_argument(
        "--threshold",
        type=int,
        default=8,
        help="per-channel delta that counts a pixel as changed (0-255)",
    )
    parser.add_argument(
        "--expect-change",
        type=float,
        default=None,
        help="fail when the changed fraction is below this floor",
    )
    parser.add_argument(
        "--crop",
        default=None,
        help="region to compare, as X,Y,W,H",
    )
    parser.add_argument("--top-colours", type=int, default=5)
    args = parser.parse_args(argv)

    crop = None
    if args.crop:
        parts = [int(p) for p in args.crop.split(",")]
        if len(parts) != 4:
            parser.error("--crop needs X,Y,W,H")
        crop = tuple(parts)

    baseline = load_rgb(args.baseline, crop)
    candidate = load_rgb(args.candidate, crop)
    if baseline.shape != candidate.shape:
        sys.stderr.write(
            f"[{args.label}] size mismatch: baseline {baseline.shape} "
            f"candidate {candidate.shape}\n"
        )
        return 1

    delta = np.abs(baseline - candidate)
    changed = delta.max(axis=2) > args.threshold
    mean_abs = float(delta.mean())
    changed_share = float(changed.mean())

    print(
        f"[{args.label}] baseline={args.baseline.name} candidate={args.candidate.name}"
    )
    print(f"[{args.label}] size={baseline.shape[1]}x{baseline.shape[0]} crop={crop}")
    print(f"[{args.label}] mean abs delta={mean_abs:.2f}/255")
    print(
        f"[{args.label}] changed fraction={changed_share:.4f} (threshold {args.threshold})"
    )
    print(
        f"[{args.label}] change grid ({args.grid}x{args.grid}, 0-9 = tenths changed):"
    )
    for line in change_grid(changed, args.grid):
        print(f"[{args.label}]   " + "".join(str(d) for d in line))

    if args.top_colours > 0:
        for name, arr in (("baseline", baseline), ("candidate", candidate)):
            top = dominant_colours(arr, args.top_colours)
            rendered = " ".join(
                f"#{r:02x}{g:02x}{b:02x}:{share:.2f}" for (r, g, b), share in top
            )
            print(f"[{args.label}] {name} top colours: {rendered}")

    if args.expect_change is not None and changed_share < args.expect_change:
        print(
            f"[{args.label}] [FAIL] changed fraction {changed_share:.4f} is below "
            f"the floor {args.expect_change}: the engine did not draw the change"
        )
        return 1

    print(f"[{args.label}] [OK] report produced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
