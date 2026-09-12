#!/usr/bin/env python3
"""
Visual regression diff tool for AEE.

Compares two directories of PNG screenshots (baseline vs current)
and reports pass/fail with pixel-level diff images.

Usage:
    python3 visual_diff.py <baseline_dir> <current_dir> [--threshold 0.1] [--output diff_dir]

Output:
    - PASS if all images match within threshold
    - FAIL with diff images highlighting changes
    - Summary of matched/mismatched/missing images
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("ERROR: pip install Pillow numpy", file=sys.stderr)
    sys.exit(1)


def load_image(path: Path) -> np.ndarray:
    """Load PNG as RGB numpy array."""
    img = Image.open(path).convert("RGB")
    return np.array(img, dtype=np.float32) / 255.0


def compute_diff(baseline: np.ndarray, current: np.ndarray) -> tuple[float, np.ndarray]:
    """Compute mean absolute difference and per-pixel diff image."""
    if baseline.shape != current.shape:
        # Resize current to match baseline
        current_img = Image.fromarray((current * 255).astype(np.uint8))
        current_img = current_img.resize(
            (baseline.shape[1], baseline.shape[0]), Image.LANCZOS
        )
        current = np.array(current_img, dtype=np.float32) / 255.0

    diff = np.abs(baseline - current)
    mean_diff = float(np.mean(diff))

    # Create visual diff: red channel shows difference intensity
    diff_vis = np.clip(diff * 3.0, 0, 1)  # Amplify for visibility
    return mean_diff, diff_vis


def run_diff(
    baseline_dir: Path,
    current_dir: Path,
    threshold: float,
    output_dir: Path | None,
) -> bool:
    """Run visual diff. Returns True if all pass."""
    baseline_files = sorted(baseline_dir.glob("*.png"))
    current_files = sorted(current_dir.glob("*.png"))

    baseline_names = {f.stem: f for f in baseline_files}
    current_names = {f.stem: f for f in current_files}

    all_names = sorted(set(baseline_names.keys()) | set(current_names.keys()))

    if not all_names:
        print("No images found in either directory.")
        return False

    passed = 0
    failed = 0
    missing = 0

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    for name in all_names:
        base_path = baseline_names.get(name)
        curr_path = current_names.get(name)

        if not base_path:
            print(f"  SKIP  {name}.png — not in baseline")
            missing += 1
            continue
        if not curr_path:
            print(f"  FAIL  {name}.png — not in current")
            failed += 1
            continue

        baseline = load_image(base_path)
        current = load_image(curr_path)
        mean_diff, diff_vis = compute_diff(baseline, current)

        if mean_diff <= threshold:
            print(f"  PASS  {name}.png  (diff={mean_diff:.4f})")
            passed += 1
        else:
            print(f"  FAIL  {name}.png  (diff={mean_diff:.4f}, threshold={threshold})")
            failed += 1

            if output_diff := output_dir / f"{name}_diff.png":
                diff_img = Image.fromarray((diff_vis * 255).astype(np.uint8))
                diff_img.save(output_diff)

    print(f"\n{passed} passed, {failed} failed, {missing} missing")
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="AEE visual regression diff")
    parser.add_argument("baseline", type=Path, help="Baseline screenshots directory")
    parser.add_argument("current", type=Path, help="Current screenshots directory")
    parser.add_argument(
        "--threshold", type=float, default=0.1, help="Max mean diff per pixel (0-1)"
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Diff image output dir"
    )
    args = parser.parse_args()

    if not args.baseline.is_dir():
        print(f"ERROR: baseline dir not found: {args.baseline}", file=sys.stderr)
        sys.exit(1)
    if not args.current.is_dir():
        print(f"ERROR: current dir not found: {args.current}", file=sys.stderr)
        sys.exit(1)

    passed = run_diff(args.baseline, args.current, args.threshold, args.output)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
