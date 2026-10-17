#!/usr/bin/env python3
"""Generate the World Magnetic Model kernel from the NOAA coefficient file.

Reads ``data/magnetism/WMM2025.COF`` (NOAA NCEI / BGS, public domain) and
writes ``addons/magnetism/functions/fnc_wmmField.sqf``: a pure function
[latDeg, lonDeg, altKm, decimalYear] -> [D, I, H, X, Y, Z] (degrees, nT).

The algorithm is the WMM technical report's (Chulliat et al., NOAA
Technical Report): WGS84 geodetic to geocentric coordinates, Schmidt
semi-normalised associated Legendre functions by recursion, the degree-12
spherical-harmonic sum with secular variation, and the rotation back to
the geodetic frame.  Before writing, the generated SQF is EXECUTED by the
test-harness interpreter (tools/tests/sqf_lite.py) on every point of NOAA's
WMM2025_TestValues.txt; the declination and inclination must agree to
0.01 deg and X, Y, Z to 1 nT.

Run:
    python3 tools/gen_wmm.py [--check]
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

COF = REPO / "data" / "magnetism" / "WMM2025.COF"
TESTS = REPO / "data" / "magnetism" / "WMM2025_TestValues.txt"
OUT = REPO / "addons" / "magnetism" / "functions" / "fnc_wmmField.sqf"
DIPOLE_OUT = REPO / "addons" / "magnetism" / "functions" / "fnc_geomagneticLatitude.sqf"
NMAX = 12


def load_cof() -> tuple[float, list[tuple[int, int, float, float, float, float]]]:
    lines = COF.read_text(encoding="utf-8").splitlines()
    epoch = float(lines[0].split()[0])
    rows = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 6:
            break
        rows.append((int(parts[0]), int(parts[1]), *map(float, parts[2:6])))
    return epoch, rows


def render() -> str:
    epoch, rows = load_cof()
    flat = {(n, m): (g, h, gd, hd) for n, m, g, h, gd, hd in rows}
    cols = [[], [], [], []]
    for n in range(1, NMAX + 1):
        for m in range(0, n + 1):
            for i in range(4):
                cols[i].append(flat[n, m][i])

    def arr(values: list[float]) -> str:
        return "[" + ", ".join(f"{v:g}" for v in values) + "]"

    return f"""#include "..\\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.
Regenerate with: python3 tools/gen_wmm.py

World Magnetic Model WMM2025 (NOAA NCEI / BGS, public domain), epoch
{epoch:g}, valid 2025.0-2030.0.  Coefficients from data/magnetism/WMM2025.COF.
The generator executes this kernel on every NOAA test value before writing.

Arguments:
  0: geodetic latitude, deg (positive north)
  1: longitude, deg (positive east)
  2: height above the WGS84 ellipsoid, km
  3: decimal year
Return: [D declination deg (east +), I inclination deg (down +), H, X, Y, Z nT]
At |lat| = 90 exactly (a geographic pole) the frame has no east, so D, H, X
and Y are undefined and are returned as 0, I is +90 (north) or -90 (south)
and Z, the axial component, is exact.
Public: No
*/

params [["_latDeg", 0, [0]], ["_lonDeg", 0, [0]], ["_altKm", 0, [0]], ["_year", {epoch:g}, [0]]];

// Gauss coefficients for n = 1..{NMAX}, m = 0..n, flattened in (n, m) order.
private _coefG = {arr(cols[0])};
private _coefH = {arr(cols[1])};
private _coefGD = {arr(cols[2])};
private _coefHD = {arr(cols[3])};

private _dt = _year - {epoch:g};

// WGS84 geodetic -> geocentric.
private _a = 6378.137;
private _f = 1 / 298.257223563;
private _e2 = _f * (2 - _f);
private _sinLat = sin _latDeg;
private _cosLat = cos _latDeg;
private _Nr = _a / sqrt (1 - _e2 * _sinLat * _sinLat);
private _p = (_Nr + _altKm) * _cosLat;
private _z = (_Nr * (1 - _e2) + _altKm) * _sinLat;
private _r = sqrt (_p * _p + _z * _z);
private _latC = _z atan2 _p;
private _ct = sin _latC;
private _st = cos _latC;
// Geographic poles: cos(latC) is zero, every P(n,m) with m > 0 vanishes with
// it, and the (north, east) frame has no defined orientation there.  The
// division below would then be 0/0, whose float32 value is pure rounding
// noise, so the pole takes the overridden path at the end of the kernel.
private _atPole = (abs _st) < 1e-6;
private _stSafe = [_st, 1] select _atPole;

// Schmidt semi-normalised P(n,m) and dP/dtheta, flat index n(n+1)/2 + m.
private _pnm = [1];
private _dpnm = [0];
for "_n" from 1 to {NMAX} do {{
    for "_m" from 0 to _n do {{
        if (_n == _m) then {{
            private _k = 1;
            if (_n > 1) then {{ _k = sqrt ((2 * _n - 1) / (2 * _n)); }};
            private _iPrev = ((_n - 1) * _n / 2) + _n - 1;
            _pnm pushBack (_k * _st * (_pnm select _iPrev));
            _dpnm pushBack (_k * (_ct * (_pnm select _iPrev) + _st * (_dpnm select _iPrev)));
        }} else {{
            private _a1 = (2 * _n - 1) / sqrt (_n * _n - _m * _m);
            private _i1 = ((_n - 1) * _n / 2) + _m;
            private _pn = _a1 * _ct * (_pnm select _i1);
            private _dpn = _a1 * (_ct * (_dpnm select _i1) - _st * (_pnm select _i1));
            if (_n > 1) then {{
                private _b1 = sqrt ((((_n - 1) * (_n - 1)) - _m * _m) / (_n * _n - _m * _m));
                private _i2 = ((_n - 2) * (_n - 1) / 2) + _m;
                _pn = _pn - _b1 * (_pnm select _i2);
                _dpn = _dpn - _b1 * (_dpnm select _i2);
            }};
            _pnm pushBack _pn;
            _dpnm pushBack _dpn;
        }};
    }};
}};

// Spherical-harmonic sum (geocentric north X', east Y', down Z').
private _bx = 0;
private _by = 0;
private _bz = 0;
private _k = 0;
for "_n" from 1 to {NMAX} do {{
    private _rr = (6371.2 / _r) ^ (_n + 2);
    for "_m" from 0 to _n do {{
        private _g = (_coefG select _k) + (_coefGD select _k) * _dt;
        private _h = (_coefH select _k) + (_coefHD select _k) * _dt;
        private _cm = cos (_m * _lonDeg);
        private _sm = sin (_m * _lonDeg);
        private _ip = (_n * (_n + 1) / 2) + _m;
        _bx = _bx + _rr * (_g * _cm + _h * _sm) * (_dpnm select _ip);
        _by = _by + _rr * _m * (_g * _sm - _h * _cm) * (_pnm select _ip) / _stSafe;
        _bz = _bz - (_n + 1) * _rr * (_g * _cm + _h * _sm) * (_pnm select _ip);
        _k = _k + 1;
    }};
}};

// Rotate to the geodetic frame.
private _d = _latC - _latDeg;
private _Xg = _bx * (cos _d) - _bz * (sin _d);
private _Zg = _bx * (sin _d) + _bz * (cos _d);
if (_atPole) then {{
    // Pole: the declination and the horizontal intensity have no defined value
    // (the frame has no east), so report them as 0.  The axial component Z is
    // exact and is kept: I is then +90 at the north pole and -90 at the south.
    _by = 0;
    _Xg = 0;
}};
private _Hn = sqrt (_Xg * _Xg + _by * _by);
[_by atan2 _Xg, _Zg atan2 _Hn, _Hn, _Xg, _by, _Zg]
"""


def render_dipole() -> str:
    epoch, rows = load_cof()
    flat = {(n, m): (g, h, gd, hd) for n, m, g, h, gd, hd in rows}
    g10, _, g10d, _ = flat[1, 0]
    g11, h11, g11d, h11d = flat[1, 1]
    return f"""#include "..\\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.
Regenerate with: python3 tools/gen_wmm.py

Geomagnetic (centred-dipole) latitude of a point, from the WMM2025 degree-1
Gauss coefficients with their secular variation (data/magnetism/WMM2025.COF).
The north geomagnetic pole is at colatitude acos(-g10 / B0) and longitude
atan2(-h11, -g11), B0 = sqrt(g10^2 + g11^2 + h11^2) (the dipole axis).

Arguments: [latDeg, lonDeg, decimalYear]
Return: [geomagneticLatDeg, poleLatDeg, poleLonDeg]
Public: No
*/

params [["_latDeg", 0, [0]], ["_lonDeg", 0, [0]], ["_year", {epoch:g}, [0]]];
private _dt = _year - {epoch:g};
private _cg10 = {g10:g} + ({g10d:g}) * _dt;
private _cg11 = {g11:g} + ({g11d:g}) * _dt;
private _ch11 = {h11:g} + ({h11d:g}) * _dt;
private _b0 = sqrt (_cg10 * _cg10 + _cg11 * _cg11 + _ch11 * _ch11);
private _poleLat = 90 - acos (-_cg10 / _b0);
private _poleLon = (-_ch11) atan2 (-_cg11);
private _sinM = (sin _latDeg) * (sin _poleLat) + (cos _latDeg) * (cos _poleLat) * (cos (_lonDeg - _poleLon));
[asin ((_sinM max -1) min 1), _poleLat, _poleLon]
"""


def validate(text: str) -> float:
    """Execute the SQF on every NOAA test point; return the worst error."""
    import tempfile

    from tools.tests.sqf_lite import run_sqf

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fnc_wmmField.sqf"
        path.write_text(text, encoding="utf-8")
        worst = 0.0
        for line in TESTS.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            v = [float(x) for x in line.split()]
            year, alt, lat, lon, dec, inc, _h, x, y, z = v[:10]
            got = run_sqf(path, [lat, lon, alt, year], {})
            worst = max(
                worst,
                abs(got[0] - dec) / 0.01,
                abs(got[1] - inc) / 0.01,
                abs(got[3] - x),
                abs(got[4] - y),
                abs(got[5] - z),
            )
    return worst


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    text = render()
    worst = validate(text)
    if worst > 1.0:
        print(
            f"wmm: the SQF kernel fails the NOAA test values (worst {worst:.3f} of tolerance)"
        )
        return 1
    dipole = render_dipole()
    if "--check" in args:
        fresh = OUT.is_file() and OUT.read_text(encoding="utf-8") == text
        fresh = (
            fresh
            and DIPOLE_OUT.is_file()
            and DIPOLE_OUT.read_text(encoding="utf-8") == dipole
        )
        print(f"wmm: {'fresh' if fresh else 'STALE'} (NOAA test values pass)")
        return 0 if fresh else 1
    OUT.write_text(text, encoding="utf-8")
    DIPOLE_OUT.write_text(dipole, encoding="utf-8")
    print(
        f"wmm: wrote {OUT.relative_to(REPO)} (all NOAA test values within tolerance, worst {worst:.3f})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
