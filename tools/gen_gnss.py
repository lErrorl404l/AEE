#!/usr/bin/env python3
"""Build the GPS model tables from the GPS SPS Performance Standard and the
FAA SPS Performance Analysis Report.

  * Constellation (data/gnss/gps_constellation.json): the SPS PS 2020 slot
    table, circular orbits a = 26559.8 km, i = 55 deg, nodal regression
    -0.0402 deg/day and the stationary-groundtrack mean motion (two draconic
    revolutions per turn of the Earth relative to the node).  The model is
    checked against every published groundtrack equatorial crossing (GEC).
  * Range error (data/gnss/sps_pan_125.json): the measured 95 % horizontal
    error of 34 sites (FAA PAN #125, Q1 2024) divided by twice the mean HDOP
    this constellation gives each site over the quarter (2DRMS ~ 95 %), so
    UERE_1sigma = H95 / (2 HDOP), tabulated against geomagnetic latitude
    (WMM2025 dipole) and the quarter's smoothed sunspot number.

Writes addons/lib/functions/geo/fnc_gnssTables.sqf.

Run: python3 tools/gen_gnss.py [--check]
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).parents[1]
CONS = REPO / "data/gnss/gps_constellation.json"
PAN = REPO / "data/gnss/sps_pan_125.json"
SW = REPO / "data/space_weather/space_weather.json"
WMM = REPO / "data/magnetism/WMM2025.COF"
OUT = REPO / "addons/lib/functions/geo/fnc_gnssTables.sqf"
EARTH_RATE = 360.98564736629          # deg per solar day (Meeus 12.4)
RE_A, RE_F = 6378.137, 1 / 298.257223563


def mean_motion(c: dict) -> float:
    """deg/day: two draconic revolutions per turn of the Earth relative to the
    node, which makes the groundtracks stationary (SPS PS Table 3.2-3 note 2)."""
    return 2 * (EARTH_RATE - c["nodal_regression_deg_per_day"])


def gec(c: dict, slot: dict) -> float:
    """Groundtrack equatorial crossing longitude implied by the model."""
    n = mean_motion(c)
    t_node = ((360 - slot["arglat"]) % 360) / n
    lon = slot["raan"] - c["greenwich_hour_angle_deg"] - (EARTH_RATE - c["nodal_regression_deg_per_day"]) * t_node
    return lon % 360


def sat_ecef(c: dict, slot: dict, days: float) -> tuple[float, float, float]:
    n = mean_motion(c)
    u = math.radians(slot["arglat"] + n * days)
    raan = math.radians(slot["raan"] + c["nodal_regression_deg_per_day"] * days)
    inc = math.radians(c["inclination_deg"])
    a = c["semi_major_axis_km"]
    x = a * (math.cos(raan) * math.cos(u) - math.sin(raan) * math.sin(u) * math.cos(inc))
    y = a * (math.sin(raan) * math.cos(u) + math.cos(raan) * math.sin(u) * math.cos(inc))
    z = a * math.sin(u) * math.sin(inc)
    th = math.radians(c["greenwich_hour_angle_deg"] + EARTH_RATE * days)
    return (x * math.cos(th) + y * math.sin(th), -x * math.sin(th) + y * math.cos(th), z)


def observer(lat: float, lon: float) -> tuple:
    e2 = RE_F * (2 - RE_F)
    la, lo = math.radians(lat), math.radians(lon)
    nr = RE_A / math.sqrt(1 - e2 * math.sin(la) ** 2)
    p = (nr * math.cos(la) * math.cos(lo), nr * math.cos(la) * math.sin(lo), nr * (1 - e2) * math.sin(la))
    east = (-math.sin(lo), math.cos(lo), 0.0)
    north = (-math.sin(la) * math.cos(lo), -math.sin(la) * math.sin(lo), math.cos(la))
    up = (math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la))
    return p, east, north, up


def dops(c: dict, lat: float, lon: float, days: float) -> tuple[float, float, int] | None:
    p, e, nn, u = observer(lat, lon)
    rows = []
    for s in c["slots"]:
        r = sat_ecef(c, s, days)
        d = [r[i] - p[i] for i in range(3)]
        L = math.sqrt(sum(x * x for x in d))
        d = [x / L for x in d]
        el = math.degrees(math.asin(sum(d[i] * u[i] for i in range(3))))
        if el < c["mask_angle_deg"]:
            continue
        rows.append([sum(d[i] * e[i] for i in range(3)), sum(d[i] * nn[i] for i in range(3)),
                     sum(d[i] * u[i] for i in range(3)), 1.0])
    if len(rows) < 4:
        return None
    m = [[sum(r[i] * r[j] for r in rows) for j in range(4)] for i in range(4)]
    inv = invert4(m)
    return math.sqrt(inv[0][0] + inv[1][1]), math.sqrt(inv[2][2]), len(rows)


def invert4(m: list) -> list:
    a = [row[:] + [1.0 if i == j else 0.0 for j in range(4)] for i, row in enumerate(m)]
    for col in range(4):
        piv = max(range(col, 4), key=lambda r: abs(a[r][col]))
        a[col], a[piv] = a[piv], a[col]
        pv = a[col][col]
        a[col] = [x / pv for x in a[col]]
        for r in range(4):
            if r != col:
                f = a[r][col]
                a[r] = [x - f * y for x, y in zip(a[r], a[col])]
    return [row[4:] for row in a]


def geomagnetic_lat(lat: float, lon: float, year: float) -> float:
    rows = {}
    lines = WMM.read_text().splitlines()
    epoch = float(lines[0].split()[0])
    for line in lines[1:]:
        p = line.split()
        if len(p) < 6:
            break
        rows[int(p[0]), int(p[1])] = [float(x) for x in p[2:6]]
    dt = year - epoch
    g10 = rows[1, 0][0] + rows[1, 0][2] * dt
    g11 = rows[1, 1][0] + rows[1, 1][2] * dt
    h11 = rows[1, 1][1] + rows[1, 1][3] * dt
    b0 = math.sqrt(g10 * g10 + g11 * g11 + h11 * h11)
    plat = 90 - math.degrees(math.acos(-g10 / b0))
    plon = math.degrees(math.atan2(-h11, -g11))
    s = (math.sin(math.radians(lat)) * math.sin(math.radians(plat))
         + math.cos(math.radians(lat)) * math.cos(math.radians(plat)) * math.cos(math.radians(lon - plon)))
    return math.degrees(math.asin(s))


def build() -> dict:
    c = json.loads(CONS.read_text())
    for s in c["baseline_slots"] + c["slots"]:
        # Two revolutions per day: each orbit crosses the equator northbound
        # at two longitudes 180 deg apart; the table quotes the one in 0-180.
        err = (gec(c, s) - s["gec"] + 90) % 180 - 90
        if abs(err) > 0.1:
            raise ValueError(f"slot {s['slot']}: model GEC off by {err:.2f} deg")
    pan = json.loads(PAN.read_text())
    # Quarter: 2024-01-01 .. 2024-03-31 (days since the 2016-12-31 epoch).
    d0 = 8766 - c["epoch_day_number"] - c["epoch_ut_hours"] / 24
    samples = [d0 + k / 12 for k in range(91 * 12)]
    table = []
    for site in pan["sites"]:
        h = [x[0] for x in (dops(c, site["lat"], site["lon"], t) for t in samples) if x]
        hdop = statistics.mean(h)
        uere = site["h95_m"] / (2 * hdop)
        mlat = abs(geomagnetic_lat(site["lat"], site["lon"], 2024.1))
        table.append((round(mlat, 2), round(uere, 3), round(hdop, 3), site["site"]))
    table.sort()
    sw = json.loads(SW.read_text())
    i0 = (2024 - sw["ssn_first_year"]) * 12
    ssn_ref = statistics.mean(sw["ssn_monthly"][i0:i0 + 3])
    # Geomagnetic-latitude profile: the median UERE in 10-degree bands.
    bands = []
    for lo in range(0, 80, 10):
        vals = [u for m, u, _h, _s in table if lo <= m < lo + 10]
        if vals:
            bands.append([lo + 5, round(statistics.median(vals), 3)])
    return {"table": table, "bands": bands, "ssn_ref": round(ssn_ref, 1), "constellation": c}


def render(b: dict) -> str:
    c = b["constellation"]
    slots = ",\n".join(f'    [{s["raan"]:g}, {s["arglat"]:g}]' for s in c["slots"])
    bands = ", ".join(f"[{m:g}, {u:g}]" for m, u in b["bands"])
    return f'''#include "..\\..\\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.  Regenerate: python3 tools/gen_gnss.py

GPS tables:
  constellation  GPS SPS Performance Standard 5th ed. (2020), Tables 3.2-1/2/3:
                 the 30 locations of the fully expanded 24-slot constellation,
                 [RAAN deg, argument of latitude deg] at the epoch
                 2016-12-31 23:59:43 UTC (day {c["epoch_day_number"]}, {c["epoch_ut_hours"]:g} h),
                 GHA {c["greenwich_hour_angle_deg"]:g} deg, a {c["semi_major_axis_km"]:g} km,
                 i {c["inclination_deg"]:g} deg, nodal regression {c["nodal_regression_deg_per_day"]:g} deg/day.
  uereBands      single-frequency user range error, 1 sigma (m), against
                 geomagnetic latitude (deg): FAA SPS PAN #125 (Q1 2024)
                 95 % horizontal errors over 2 x this constellation's HDOP,
                 at the quarter's smoothed sunspot number {b["ssn_ref"]:g}.
Return: HASHMAP
Public: No
*/
createHashMapFromArray [
    ["epochDay", {c["epoch_day_number"]}],
    ["epochHours", {c["epoch_ut_hours"]:g}],
    ["gha0", {c["greenwich_hour_angle_deg"]:g}],
    ["aKm", {c["semi_major_axis_km"]:g}],
    ["incDeg", {c["inclination_deg"]:g}],
    ["nodeRate", {c["nodal_regression_deg_per_day"]:g}],
    ["maskDeg", {c["mask_angle_deg"]:g}],
    ["slots", [
{slots}
    ]],
    ["uereBands", [{bands}]],
    ["ssnRef", {b["ssn_ref"]:g}]
]
'''


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    b = build()
    text = render(b)
    if "--check" in args:
        fresh = OUT.is_file() and OUT.read_text() == text
        print(f"gnss: {'fresh' if fresh else 'STALE'}")
        return 0 if fresh else 1
    OUT.write_text(text)
    for m, u, h, s in b["table"]:
        print(f"  {s:22s} |mlat| {m:5.1f}  HDOP {h:.2f}  UERE {u:.2f} m")
    print("gnss: bands", b["bands"], "ssnRef", b["ssn_ref"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
