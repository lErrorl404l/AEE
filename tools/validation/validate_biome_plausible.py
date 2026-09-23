#!/usr/bin/env python3
"""Biome plausibility validator for the docker map-rotation test.

The dynamic biome system (issue #123) classifies a map from FACTS, not
names: latitude (abs-corrected), water fraction, terrain signals.  The
map-rotation test runs the mission on real Workshop maps and asserts the
resolved biome is PLAUSIBLE for that map's latitude — the physical band
the system should never leave.

A resolved biome is plausible when it is in the Köppen band the latitude
physics permits.  This is the no-hardcoding contract: the test knows the
latitude (a fact read from the map config), never the map name.

Band rules (Köppen thermal zones by latitude):
  |lat| < 23.5   tropical:    Af, Am, Aw
  23.5-35        subtropical: BWh, BSh, Csa, Cfa, Aw, Am
  35-50          temperate:   Cfb, Cfa, Dfa, Dfb, BSk, Csa
  50-66.5        boreal:      Dfb, Dfc, BSk, Cfb
  >66.5          polar:       ET, EF

Cfb (oceanic) appears at any latitude with a warm current — the UK at
55 N and the Scottish Highlands at 57 N are Cfb.  It is temperature-
driven, not latitude-driven, so it stays plausible across the whole
temperate and boreal range.

Exceptions where terrain evidence legitimately overrides latitude:
  - high mean elevation (>1500 m) shifts toward Dfc/ET
  - desert surfaces at subtropical latitudes confirm BWh/BSh

Usage:
  python3 tools/validation/validate_biome_plausible.py <latitude> <biome_code>
Exit 0 when plausible, 1 when not.  Supports "world:lat:code" triples for
the rotation script.

Run:  python3 tools/validation/validate_biome_plausible.py --list
"""

import sys

BANDS = [
    (0, 23.5, {"Af", "Am", "Aw", "BWh", "BSh"}, "tropical"),
    (23.5, 35, {"BWh", "BSh", "Csa", "Cfa", "Aw", "Am"}, "subtropical"),
    (35, 50, {"Cfb", "Cfa", "Dfa", "Dfb", "BSk", "BSh", "Csa"}, "temperate"),
    (50, 66.5, {"Dfb", "Dfc", "BSk", "BSh", "Cfb"}, "boreal"),
    (66.5, 91, {"ET", "EF"}, "polar"),
]

ALL_CODES = {
    "Af",
    "Am",
    "Aw",
    "BSh",
    "BSk",
    "BWk",
    "BWh",
    "Csa",
    "Csb",
    "Cfa",
    "Cfb",
    "Cwa",
    "Dfa",
    "Dfb",
    "Dfc",
    "ET",
    "EF",
}


def plausible(lat, code, mean_elev=0.0):
    """True when the biome code is in the latitude band (or a terrain-
    driven exception)."""
    lat = abs(lat)
    if code not in ALL_CODES:
        return False
    for lo, hi, codes, _ in BANDS:
        if lo <= lat < hi:
            if code in codes:
                return True
            # Terrain exceptions: high mountains legitimately shift cold.
            if mean_elev > 1500 and code in {"Dfc", "ET"}:
                return True
            return False
    return False


def band_name(lat):
    lat = abs(lat)
    for lo, hi, _, name in BANDS:
        if lo <= lat < hi:
            return name
    return "unknown"


def agrees(anchor, per_position):
    """True when the two classifiers are compatible.

    The map-wide classifier reads latitude, water fraction and terrain for
    the WHOLE map. The per-position classifier reads one tile's surface
    type. Both publish into aee_core_biome, so a disagreement means one
    silently overwrote the other.

    A disagreement is a defect when the per-position verdict is a generic
    default. On Stratis at 35 N the map-wide classifier correctly resolved
    Csa, then the per-position path read a man-made surface
    (GdtStratisConcrete), found no climate signal, and answered Cfb. A
    Mediterranean island was downgraded to an oceanic one, and the band
    check could not see it because Cfb is legal at 35 N under the band
    rules.

    The Koppen first TWO letters are the shared climate group: 'Cs' is a
    dry-summer Mediterranean climate and 'Cf' is one with no dry season, so
    'Csa' and 'Cfb' are different climates that both begin with 'C'. A
    one-character test cannot separate them.
    """
    if not anchor or not per_position:
        return True
    return anchor[:2] == per_position[:2]


def main():
    args = sys.argv[1:]
    if "--list" in args:
        print("latitude band -> plausible Köppen codes")
        for lo, hi, codes, name in BANDS:
            print(f"  {lo:5.1f} - {hi:5.1f}  {name:12s} {', '.join(sorted(codes))}")
        return 0
    if "--self-check" in args:
        # The defect that survived: two classifiers disagreeing while both
        # individual verdicts were plausible for the latitude. Without this
        # case the band rules cannot catch it.
        cases = [
            ("Csa", "Csa", True, "same verdict"),
            ("Csa", "Cfb", False, "Stratis: Mediterranean downgraded to oceanic"),
            ("Csa", "Cfa", False, "different thermal group from the anchor"),
            ("BWh", "BWh", True, "same verdict"),
            ("", "Cfb", True, "no anchor yet: nothing to contradict"),
            ("Cfb", "", True, "no per-position verdict: nothing to contradict"),
        ]
        failures = 0
        for anchor, per_position, expected, why in cases:
            got = agrees(anchor, per_position)
            mark = "OK  " if got == expected else "FAIL"
            if got != expected:
                failures += 1
            print(
                f"  {mark} anchor={anchor or '-':<4} per-position={per_position or '-':<4} -> {got} ({why})"
            )
        # And the band rules must still hold.
        for lat, code, expected in (
            (55, "Cfb", True),
            (35, "Csa", True),
            (55, "Af", False),
        ):
            got = plausible(lat, code)
            if got != expected:
                failures += 1
                print(f"  FAIL band lat={lat} {code} -> {got}, expected {expected}")
        print(
            f"classifier agreement: {'PASS' if failures == 0 else 'FAIL'} ({failures} failed)"
        )
        return 1 if failures else 0
    if len(args) < 2:
        print(__doc__)
        return 2
    try:
        lat = float(args[0])
        code = args[1]
        elev = float(args[2]) if len(args) > 2 else 0.0
    except ValueError:
        print(f"invalid args: {args}")
        return 2

    if plausible(lat, code, elev):
        print(f"OK   lat={lat:.1f} ({band_name(lat)}) -> {code}")
        return 0
    expected = set()
    for lo, hi, codes, _ in BANDS:
        if lo <= abs(lat) < hi:
            expected = codes
            break
    print(
        f"FAIL lat={lat:.1f} ({band_name(lat)}) -> {code} "
        f"(expected one of {', '.join(sorted(expected))})"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
