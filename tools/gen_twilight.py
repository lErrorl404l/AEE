#!/usr/bin/env python3
"""Twilight illuminance from the held Schlyter table.

Parses section 10 of the held page (data/astronomy/sources/
schlyter_radfaq.html, 'Solar illumination on horizontal surface at various
solar altitudes'), keeps the 0 to -18 deg rows, writes
data/astronomy/twilight_illuminance.json and the runtime kernel
addons/core/functions/fnc_twilightIlluminance.sqf (log-lux interpolation).

Run: python3 tools/gen_twilight.py [--check]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.validation import source_cache  # noqa: E402

HELD = source_cache.capture_path("astronomy", "schlyter_radfaq.html")
DATA = REPO / "data/astronomy/twilight_illuminance.json"
OUT = REPO / "addons/core/functions/fnc_twilightIlluminance.sqf"
ROW = re.compile(r"^\s*(-?\d+\.\d)\s+(-?\d+\.\d\d)\s+([\d.]+)\s*$")


def parse() -> list[tuple[float, float]]:
    text = HELD.read_bytes().decode("latin-1").replace("\r", "")
    start = text.index("Solar illumination on horizontal surface")
    rows = []
    for line in text[start:].splitlines()[:120]:
        m = ROW.match(line)
        if m:
            alt, lg, lux = float(m.group(1)), float(m.group(2)), float(m.group(3))
            if alt <= 0:
                rows.append((alt, lg))
    assert rows[0][0] == 0.0 and rows[-1][0] == -18.0, rows
    return rows


def render(rows) -> str:
    alts = ", ".join(f"{a:g}" for a, _ in rows)
    logs = ", ".join(f"{lg:g}" for _, lg in rows)
    return f"""#include "..\\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.
Regenerate with: python3 tools/gen_twilight.py

Clear-sky horizontal illuminance of twilight (the scattered light of a sun
below the horizon), by true solar altitude, interpolated in log10 lux from
the table of P. Schlyter, "Radiometry and photometry in astronomy", section
10 (held: data/astronomy/sources/schlyter_radfaq.html): 759 lx at 0 deg,
3.41 lx at -6, 0.00806 lx at -12, 0.000645 lx at -18.  Below -18 deg
(astronomical night) the sun contributes nothing.

Arguments: 0: solar altitude, deg
Return: illuminance, lux (0 above the horizon: daylight is not twilight)
Public: No
*/
params [["_alt", -90, [0]]];
if (_alt > 0 || _alt < -18) exitWith {{ 0 }};
private _a = [{alts}];
private _l = [{logs}];
private _i = 0;
for "_k" from 0 to ((count _a) - 2) do {{
    if (_alt <= (_a select _k)) then {{ _i = _k; }};
}};
_i = _i min ((count _a) - 2);
private _w = ((_a select _i) - _alt) / ((_a select _i) - (_a select (_i + 1)));
10 ^ (((_l select _i) * (1 - _w)) + ((_l select (_i + 1)) * _w))
"""


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not HELD.is_file():
        print(
            "schlyter_radfaq.html is not held in {}; the twilight check was "
            "skipped".format(source_cache.cache_root())
        )
        return 0
    rows = parse()
    data = json.loads(DATA.read_text(encoding="utf-8"))
    data["rows"] = [{"altitude": a, "log10_lux": lg} for a, lg in rows]
    data_text = json.dumps(data, indent=1) + "\n"
    sqf = render(rows)
    if "--check" in args:
        ok = DATA.read_text(encoding="utf-8") == data_text and OUT.read_text(encoding="utf-8") == sqf
        print("twilight: " + ("fresh" if ok else "stale, run python3 tools/gen_twilight.py"))
        return 0 if ok else 1
    DATA.write_text(data_text, encoding="utf-8")
    OUT.write_text(sqf, encoding="utf-8")
    print("twilight: wrote data and fnc_twilightIlluminance.sqf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
