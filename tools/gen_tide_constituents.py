#!/usr/bin/env python3
"""Generate the runtime tide-constituent table from the maritime corpus.

The corpus is ``data/maritime/tide_constituents.json``: TICON-4 tide-gauge
harmonic constants (Hart-Davis, Dettmering & Seitz 2025, DOI
10.17882/109129, CC BY 4.0) for the gauges the vanilla worlds bind to, and
the Doodson equilibrium ratios for an unbound world.  The generator writes
``addons/maritime/functions/fnc_getTideConstituents.sqf``.

The prediction formula is checked here against NOAA's official prediction
for San Francisco (9414290) before anything is written, so a wrong
astronomical argument cannot reach the runtime.

Run:
    python3 tools/gen_tide_constituents.py [--check]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).parents[1]
DATA = REPO / "data" / "maritime" / "tide_constituents.json"
OUT = REPO / "addons" / "maritime" / "functions" / "fnc_getTideConstituents.sqf"
CONS = ["M2", "S2", "N2", "K2", "K1", "O1", "P1", "Q1"]
NOAA_RMS_LIMIT_M = 0.06


def julian_day(y: int, m: int, d: int, ut_h: float) -> float:
    """Meeus (1998) ch. 7, Gregorian calendar."""
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5 + ut_h / 24


def arguments(jd: float) -> dict[str, tuple[float, float, float]]:
    """[V (deg), f, u (deg)] per constituent at Greenwich.

    V: Schureman (1958) US C&GS SP 98, Table 2, with T the Greenwich mean
    solar hour angle (15 UT + 180).  Mean longitudes s, h, p and the node N:
    Meeus (1998) eq. 47.1-47.7 and 25.2.  Nodal factors f, u: Pugh (1987),
    Tides, Surges and Mean Sea-Level, Table 4.3.
    """
    t = (jd - 2451545.0) / 36525
    s = (218.3164477 + 481267.88123421 * t) % 360
    h = (280.46646 + 36000.76983 * t) % 360
    p = (83.3532465 + 4069.0137287 * t) % 360
    n = (125.04452 - 1934.136261 * t) % 360
    tau = 15 * (((jd + 0.5) % 1) * 24) + 180
    c = lambda x: math.cos(math.radians(x))  # noqa: E731
    sn = lambda x: math.sin(math.radians(x))  # noqa: E731
    f_m2 = 1.0004 - 0.0373 * c(n) + 0.0002 * c(2 * n)
    u_m2 = -2.14 * sn(n)
    f_k1 = 1.0060 + 0.1150 * c(n) - 0.0088 * c(2 * n) + 0.0006 * c(3 * n)
    u_k1 = -8.86 * sn(n) + 0.68 * sn(2 * n) - 0.07 * sn(3 * n)
    f_o1 = 1.0089 + 0.1871 * c(n) - 0.0147 * c(2 * n) + 0.0014 * c(3 * n)
    u_o1 = 10.80 * sn(n) - 1.34 * sn(2 * n) + 0.19 * sn(3 * n)
    f_k2 = 1.0241 + 0.2863 * c(n) + 0.0083 * c(2 * n) - 0.0015 * c(3 * n)
    u_k2 = -17.74 * sn(n) + 0.68 * sn(2 * n) - 0.04 * sn(3 * n)
    return {
        "M2": (2 * tau - 2 * s + 2 * h, f_m2, u_m2),
        "S2": (2 * tau, 1.0, 0.0),
        "N2": (2 * tau - 3 * s + 2 * h + p, f_m2, u_m2),
        "K2": (2 * tau + 2 * h, f_k2, u_k2),
        "K1": (tau + h - 90, f_k1, u_k1),
        "O1": (tau - 2 * s + h + 90, f_o1, u_o1),
        "P1": (tau - h + 90, 1.0, 0.0),
        "Q1": (tau - 3 * s + h + p + 90, f_o1, u_o1),
    }


def height(jd: float, cons: dict[str, tuple[float, float]]) -> float:
    args = arguments(jd)
    return sum(a * args[k][1] * math.cos(math.radians(args[k][0] + args[k][2] - g)) for k, (a, g) in cons.items())


def noaa_rms() -> float:
    base = DATA.parent
    harcon = json.loads((base / "validation" / "noaa_9414290_harcon.json").read_text(encoding="utf-8"))
    pred = json.loads((base / "validation" / "noaa_9414290_predictions_20240115.json").read_text(encoding="utf-8"))
    cons = {
        x["name"]: (x["amplitude"], x["phase_GMT"])
        for x in harcon["HarmonicConstituents"]
        if x["name"] in CONS
    }
    errs = []
    for row in pred["predictions"]:
        day, clock = row["t"].split()
        y, m, d = map(int, day.split("-"))
        errs.append(height(julian_day(y, m, d, int(clock[:2])), cons) - float(row["v"]))
    return (sum(e * e for e in errs) / len(errs)) ** 0.5


def load() -> dict:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    rms = noaa_rms()
    if rms > NOAA_RMS_LIMIT_M:
        raise ValueError(f"tide formula fails the NOAA 9414290 check: {rms:.3f} m RMS")
    for gid, g in data["gauges"].items():
        if sorted(g["constituents"]) != sorted(CONS):
            raise ValueError(f"{gid}: must hold {CONS}")
    for world, b in data["world_bindings"].items():
        if b["gauge"] and b["gauge"] not in data["gauges"]:
            raise ValueError(f"{world}: unknown gauge {b['gauge']}")
    return data


def render(data: dict) -> str:
    def row(cons: dict[str, dict]) -> str:
        return "[" + ", ".join(f"[{cons[k]['amp_m']:g}, {cons[k]['phase_deg']:g}]" for k in CONS) + "]"

    ratios = data["equilibrium_ratios"]
    lines = [
        '#include "..\\script_component.hpp"',
        "/*",
        "GENERATED FILE. Do not edit by hand.",
        "Regenerate with: python3 tools/gen_tide_constituents.py",
        "",
        "Tide-gauge harmonic constants for the current world, from TICON-4",
        f"({data['source']['authors']}, {data['source']['year']}, DOI {data['source']['doi']},",
        f"{data['source']['licence']}).  Constituent order: {' '.join(CONS)}.",
        "Each entry is [amplitude m, Greenwich phase lag deg].",
    ]
    for gid, g in data["gauges"].items():
        lines.append(f"  {gid}: {g['gauge']} ({g['country']}, {g['years_of_obs']:g} yr, {g['record_quality']})")
    lines += [
        "",
        "Return: [constituents, bound] - bound is false for a world with no",
        "gauge, whose constituents are the Doodson equilibrium ratios scaled by",
        "the M2 amplitude setting with zero phase lag; [] for a world with no",
        "ocean tide (Livonia).",
        "Public: No",
        "*/",
        "",
        "private _GAUGES = createHashMapFromArray [",
        ",\n".join(f'    ["{gid}", {row(g["constituents"])}]' for gid, g in data["gauges"].items()),
        "];",
        "private _WORLDS = createHashMapFromArray [",
        ",\n".join(f'    ["{w.lower()}", "{b["gauge"]}"]' for w, b in sorted(data["world_bindings"].items())),
        "];",
        "",
        "private _gid = _WORLDS getOrDefault [toLower worldName, \"-\"];",
        'if (_gid == "") exitWith { [] };',
        'if (_gid != "-") exitWith { [_GAUGES get _gid, true] };',
        "private _m2 = missionNamespace getVariable [QGVAR(tideAmplitude), 1.0];",
        "if !(_m2 isEqualType 0) then { _m2 = 1.0; };",
        "[[" + ", ".join(f"[_m2 * {ratios[k]:g}, 0]" for k in CONS) + "], false]",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    text = render(load())
    if "--check" in args:
        fresh = OUT.is_file() and OUT.read_text(encoding="utf-8") == text
        print(f"tide constituents: {'fresh' if fresh else 'STALE'}")
        return 0 if fresh else 1
    OUT.write_text(text, encoding="utf-8")
    print(f"tide constituents: wrote {OUT.relative_to(REPO)} (NOAA check {noaa_rms():.3f} m RMS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
