#!/usr/bin/env python3
"""Clear-sky daylight chromaticity from a solar spectral model.

The spectrum of the direct beam and of the diffuse sky on a horizontal plane
is the Bird & Riordan (1986) SPCTRAL2 model (NREL spectrl2_2.c form):
Rayleigh, Angstrom aerosol, water vapour, ozone and mixed-gas transmittances
over the 122-band extraterrestrial spectrum (data/daylight/
spectrl2_coefficients.json).  Each spectrum is integrated against the CIE 1931
2 deg colour-matching functions (CIE 018:2019, data/daylight/
CIE_xyz_1931_2deg.csv) to tristimulus XYZ.

The runtime table holds, on a grid of apparent solar elevation x aerosol
optical depth at 500 nm x surface pressure, the luminance-scaled tristimulus
values of the beam (on the horizontal) and of the sky, so the runtime can mix
them linearly (light adds in XYZ) with the cloud cover.

Writes addons/vision/functions/perception/fnc_daylightTable.sqf.

Run: python3 tools/gen_daylight.py [--check]
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).parents[1]
COEF = REPO / "data/daylight/spectrl2_coefficients.json"
CMF = REPO / "data/daylight/CIE_xyz_1931_2deg.csv"
SCOT = REPO / "data/daylight/CIE_sle_scotopic.csv"
OUT = REPO / "addons/vision/functions/perception/fnc_daylightTable.sqf"

ELEVATIONS = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 23, 26, 30, 35, 40, 45, 50, 60, 70, 80, 90]
AODS = [0.02, 0.035, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8, 1.1, 1.5]
PRESSURES = [1013.25, 850.0, 700.0]          # hPa (sea level, ~1.5 km, ~3 km)
# Fixed inputs: column ozone 0.30 atm-cm (global mean ~300 DU, WMO GAW),
# precipitable water 1.5 cm (its absorption bands lie mostly beyond 690 nm,
# where the CMFs are near zero; see test_daylight), ground albedo 0.2
# (Bird & Riordan default), Earth-Sun distance 1 AU.
OZONE = 0.30
WATER = 1.5
ALBEDO = 0.2


def load():
    c = json.loads(COEF.read_text(encoding="utf-8"))
    cmf = []
    with CMF.open(encoding="utf-8") as f:
        for row in csv.reader(f):
            cmf.append([float(v) if v.strip().lower() != "nan" else 0.0 for v in row])
    return c, cmf


def kasten_young(elev: float) -> float:
    """Relative optical air mass, Kasten & Young 1989 (apparent elevation)."""
    return 1 / (math.sin(math.radians(elev)) + 0.50572 * (elev + 6.07995) ** -1.6364)


def spectrl2(c: dict, elev: float, aod500: float, p_hpa: float,
             water: float = WATER, ozone: float = OZONE, albedo: float = ALBEDO):
    """Direct-normal and diffuse-horizontal spectral irradiance (W m-2 nm-1).

    Bird & Riordan 1986 eqs. 2-1 to 3-17, with the spectrl2_2.c constants
    (1.3366 Rayleigh, 118.3 mixed gas, Tu' in eq. 3-8)."""
    d = c["defaults"]
    zen = 90 - elev
    cosz = math.cos(math.radians(zen))
    m = kasten_young(elev)
    p = p_hpa * 100

    def trans(mass):
        out = []
        for i, wl in enumerate(c["wavelength"]):
            um = wl / 1000
            mp = mass * p / 101300
            tr = math.exp(-mp / (um ** 4 * (115.6406 - 1.3366 / um ** 2)))
            tau = aod500 * (wl / 500) ** -d["alpha"]
            ta = math.exp(-tau * mass)
            aw = c["water_vapor_absorption"][i] * water * mass
            tw = math.exp(-0.2385 * aw / (1 + 20.07 * aw) ** 0.45)
            h0 = d["ozone_max_height_km"] / 6370
            mo = (1 + h0) / math.sqrt(cosz ** 2 + 2 * h0)
            to = math.exp(-c["ozone_absorption"][i] * ozone * mo)
            am = c["mixed_absorption"][i] * mp
            tu = math.exp(-1.41 * am / (1 + 118.3 * am) ** 0.45)
            omega = d["scattering_albedo_400nm"] * math.exp(
                -d["wavelength_variation_factor"] * math.log(wl / 400) ** 2)
            tas = math.exp(-omega * tau * mass)
            taa = math.exp(-(1 - omega) * tau * mass)
            out.append((tr, ta, tw, to, tu, tas, taa))
        return out

    t = trans(m)
    tp = trans(1.8)
    alg = math.log(1 - d["aerosol_asymmetry_factor"])
    bfs = alg * (0.0783 + alg * (-0.3824 - alg * 0.5874))
    afs = alg * (1.459 + alg * (0.1595 + alg * 0.4129))
    fs = 1 - 0.5 * math.exp((afs + bfs * cosz) * cosz)
    fsp = 1 - 0.5 * math.exp((afs + bfs / 1.8) / 1.8)
    dni, dhi = [], []
    for i, wl in enumerate(c["wavelength"]):
        h = c["spectral_irradiance_et"][i]
        tr, ta, tw, to, tu, tas, taa = t[i]
        trp, _tap, twp, _top, tup, tasp, taap = tp[i]
        idn = h * tr * ta * tw * to * tu
        cs = ((wl + 550) / 1000) ** 1.8 if wl <= 450 else 1.0
        rs = tup * twp * taap * (0.5 * (1 - trp) + (1 - fsp) * trp * (1 - tasp))
        common = h * cosz * to * tu * tw * taa
        ir = common * (1 - tr ** 0.95) * 0.5
        ia = common * tr ** 1.5 * (1 - tas) * fs
        ig = (idn * cosz + ir + ia) * rs * albedo / (1 - rs * albedo)
        dni.append(idn)
        dhi.append((ir + ia + ig) * cs)
    return dni, dhi


def load_scotopic() -> list:
    """CIE 1951 scotopic V'(lambda) (CIE 018:2019), [[nm, V'], ...]."""
    with SCOT.open(encoding="utf-8") as f:
        return [[float(a), float(b)] for a, b in csv.reader(f)]


def scotopic(c: dict, vp: list, spectrum: list) -> float:
    """The V'-weighted integral on the CMF scale: S/P = 1699 S / (683 Y)."""
    wl = c["wavelength"]
    S = 0.0
    j = 0
    for lam, v in vp:
        while j < len(wl) - 2 and wl[j + 1] < lam:
            j += 1
        f = (lam - wl[j]) / (wl[j + 1] - wl[j])
        S += (spectrum[j] * (1 - f) + spectrum[j + 1] * f) * v
    return S * 1699 / 683


def tristimulus(c: dict, cmf: list, spectrum: list) -> tuple[float, float, float]:
    """XYZ of a spectrum (linear interpolation onto the 1 nm CMF grid)."""
    wl = c["wavelength"]
    X = Y = Z = 0.0
    j = 0
    for lam, xb, yb, zb in cmf:
        while j < len(wl) - 2 and wl[j + 1] < lam:
            j += 1
        f = (lam - wl[j]) / (wl[j + 1] - wl[j])
        s = spectrum[j] * (1 - f) + spectrum[j + 1] * f
        X += s * xb
        Y += s * yb
        Z += s * zb
    return X, Y, Z


def planck_xy(cmf: list, T: float) -> tuple[float, float]:
    c2 = 1.4388e-2  # m K (CIE 15:2018, ITS-90)
    X = Y = Z = 0.0
    for lam, xb, yb, zb in cmf:
        L = lam * 1e-9
        b = 1 / (L ** 5 * (math.exp(c2 / (L * T)) - 1))
        X += b * xb
        Y += b * yb
        Z += b * zb
    s = X + Y + Z
    return X / s, Y / s


def uv(x: float, y: float) -> tuple[float, float]:
    d = -2 * x + 12 * y + 3
    return 4 * x / d, 6 * y / d          # CIE 1960 UCS


def cct(cmf: list, x: float, y: float) -> float:
    """CCT by definition (CIE 15:2018 s.9.5): the Planckian temperature
    nearest in the CIE 1960 (u, v) diagram; golden-section on 1/T."""
    u0, v0 = uv(x, y)

    def dist(mired):
        u, v = uv(*planck_xy(cmf, 1e6 / mired))
        return (u - u0) ** 2 + (v - v0) ** 2

    a, b = 1.0, 1000.0
    g = (math.sqrt(5) - 1) / 2
    for _ in range(60):
        c1, c2 = b - g * (b - a), a + g * (b - a)
        if dist(c1) < dist(c2):
            b = c2
        else:
            a = c1
    return 1e6 / ((a + b) / 2)


def build() -> dict:
    c, cmf = load()
    vp = load_scotopic()
    rows = []
    for p in PRESSURES:
        for aod in AODS:
            for e in ELEVATIONS:
                dni, dhi = spectrl2(c, e, aod, p)
                cosz = math.sin(math.radians(e))
                bX, bY, bZ = tristimulus(c, cmf, [v * cosz for v in dni])
                sX, sY, sZ = tristimulus(c, cmf, dhi)
                beam = [v * cosz for v in dni]
                rows.append([bX, bY, bZ, sX, sY, sZ, scotopic(c, vp, beam), scotopic(c, vp, dhi)])
    return {"elev": ELEVATIONS, "aod": AODS, "pres": PRESSURES, "rows": rows}


def render(b: dict) -> str:
    def fmt(v):
        return f"{v:.6g}"

    rows = ",\n    ".join("[" + ", ".join(fmt(v) for v in r) + "]" for r in b["rows"])
    return f"""#include "..\\..\\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.
Regenerate with: python3 tools/gen_daylight.py

Clear-sky tristimulus values (CIE 1931 2 deg, unnormalised photometric scale)
of the direct beam on the horizontal and of the diffuse sky, from the Bird &
Riordan 1986 SPCTRAL2 spectral model (data/daylight/spectrl2_coefficients.json)
and the CIE 018:2019 colour-matching functions (data/daylight/
CIE_xyz_1931_2deg.csv and CIE_sle_scotopic.csv, CC BY-SA 4.0).  Ozone {OZONE} atm-cm, precipitable
water {WATER} cm, ground albedo {ALBEDO}.

rows: index (iPressure * nAod + iAod) * nElev + iElev, each
      [Xbeam, Ybeam, Zbeam, Xsky, Ysky, Zsky, Sbeam, Ssky]; S is the CIE
      1951 scotopic integral on the Y scale (S/Y is the S/P ratio).

Return: HashMap with keys elev (deg), aod (500 nm), pres (hPa), rows.
*/
createHashMapFromArray [
  ["elev", {json.dumps(b["elev"])}],
  ["aod", {json.dumps(b["aod"])}],
  ["pres", {json.dumps(b["pres"])}],
  ["rows", [
    {rows}
  ]]
]
"""


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    text = render(build())
    if "--check" in args:
        if OUT.read_text(encoding="utf-8") != text:
            print("daylight: stale, run python3 tools/gen_daylight.py")
            return 1
        print("daylight: fresh")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"daylight: wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
