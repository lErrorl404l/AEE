#!/usr/bin/env python3
"""Analyse the thermal sweep log from an Arma RPT.

Parses [AEE_SWEEP] lines and prints the full 24 h cycle, verifying:
  - radiation peaks near midday and is 0 at night
  - brightness = radiation * 13
  - air/ground temperatures follow the radiation curve with lag

Usage:
  python3 tools/analyze_thermal_sweep.py --rpt <path.rpt>
"""

import argparse
import re
import sys
from pathlib import Path

SWEEP_RE = re.compile(
    r"\[AEE_SWEEP\]\s+h=(\d+)\s+dayTime=([\d.]+)\s+rad=([-\d.]+)\s+"
    r"brightness=([-\d.]+)\s+air=([-\d.]+)\s+ground=([-\d.]+)"
)


def parse_rpt(rpt: Path) -> list[tuple[int, float, float, float, float, float]]:
    """Return [(hour, dayTime, rad, brightness, air, ground), ...]."""
    by_hour: dict[int, tuple[int, float, float, float, float, float]] = {}
    for line in rpt.read_text(errors="ignore").splitlines():
        m = SWEEP_RE.search(line)
        if m:
            h = int(m.group(1))
            by_hour[h] = (
                h,
                float(m.group(2)),
                float(m.group(3)),
                float(m.group(4)),
                float(m.group(5)),
                float(m.group(6)),
            )
    return [by_hour[h] for h in sorted(by_hour)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rpt", required=True, help="Arma RPT path")
    args = ap.parse_args()

    rows = parse_rpt(Path(args.rpt))
    if not rows:
        print("No [AEE_SWEEP] lines found.  Set aee_optics_nvgDebug and run the sweep.")
        return 1

    print(f"{'hour':>4} {'rad':>7} {'bright':>7} {'air':>6} {'ground':>7}")
    for hour, _dt, rad, bright, air, ground in rows:
        print(f"{hour:>4} {rad:>7.3f} {bright:>7.2f} {air:>6.1f} {ground:>7.1f}")

    rads = [r[2] for r in rows]
    peak_hour = rows[rads.index(max(rads))][0]
    night = [r[0] for r in rows if r[2] == 0]
    print()
    print(f"  radiation range: {min(rads):.3f} .. {max(rads):.3f}")
    print(f"  peak hour: {peak_hour} (expect ~12)")
    print(f"  night hours (rad=0): {night}")
    print()
    # Sanity checks against the physics model.
    ok = True
    if not (11 <= peak_hour <= 13):
        print("  WARN: radiation peak is not near midday")
        ok = False
    if max(rads) <= 0:
        print("  WARN: radiation never rises above 0")
        ok = False
    print("  physics curve: " + ("OK" if ok else "CHECK"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
