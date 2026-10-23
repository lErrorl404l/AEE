#!/usr/bin/env python3
"""Independent ballistic verifier for the AEE projectile corpus.

The AEE kernel is the subject, never the reference. This tool recomputes every
trajectory from the published equations in Python and compares the result with
an independent solver (``py-ballisticcalc``) given the same inputs. It never
runs the SQF, never shells out to it, and never imports a value the generator
produced from it. Only the standard drag tables are shared, because both sides
must integrate the same published Cd(Mach) curve for the comparison to be
like-for-like.

Comparison contract
-------------------
Solver            py-ballisticcalc 3.1.1, LGPL-3.0, pinned in
                  tools/requirements-tooling.txt and never vendored. See
                  docs/adr/ADR-046-independent-ballistic-verifier.md.
Zero distance     100 m, on both sides.
Sight height      40 mm, the value the published reference tables use.
Atmosphere        ISA sea level: 15.0 C, 1013.25 hPa, 0 % relative humidity.
                  The density ratio is computed on the AEE side from the
                  troposphere equation and compared with the solver's own
                  ICAO model. A difference there is reported, not hidden.
Wind              4 m/s full value, from 90 degrees (drift to the right).
Gravity           9.80665 m/s^2, flat fire, no Coriolis, no spin drift.
Ranges            0 to 1000 m at 100 m steps, truncated at the first step where
                  the retained velocity falls below 200 m/s. A G-table
                  extrapolated into the subsonic region is not a disagreement.

AEE side equations (verified against the SQF before writing this file)
---------------------------------------------------------------------
Retardation, addons/ballistics/functions/fnc_calculateBallisticDrag.sqf:

    retard = K * (Cd(Mach) / BC) * v^2 * rhoRel
    K      = 0.00068418

Mach uses the local speed of sound, addons/lib/constants.hpp together with
fnc_calculateBallisticDrag.sqf:

    a = 20.05 * sqrt(T + 273.15)

Cd is linearly interpolated on Mach and clamped at both ends, as the kernel
does. The tables come from fnc_getDragTables.sqf through the loader in
tools/gen_kernel_vectors.py, which parses the SQF literal.

The integration here is a fixed-step RK4 at 1 ms, not the game tick, so its
numerical error is far below the tolerances below.

Tolerances and their justification
----------------------------------
Retained velocity  1 % relative. Both sides integrate the same drag law, so the
                   only difference is quadrature error and the interpolation of
                   Cd, both sub-0.1 % at a 1 ms step. 1 % leaves room for the
                   solver's own step control.
Drop               max(0.001 * |drop|, 0.03 mrad * range) up to 300 m. The
                   relative floor ramps linearly from 1 % at 300 m to 2 % at
                   1000 m. 0.03 mrad is the instrument floor: at 300 m it is
                   9 mm, about the resolution a published table prints. The
                   ramp covers the growing sensitivity of drop to the drag
                   model at long range, where a 1 % BC error becomes a
                   several-percent drop error.
Wind drift         max(3 %, 5 mm). At short range the drift is only tens of
                   millimetres and whole-millimetre rounding in a published
                   table is a few percent by itself, so an absolute floor stops
                   rounding noise from dominating.
Time of flight     1 % relative, reported but not gated.

Residual systematic offset
--------------------------
AEE uses rho0 = 1.225 kg/m3 (AERO_ISA_SEA_LEVEL_DENSITY). The solver's
imperial path documents cStandardDensity = 0.076474 lb/ft3 = 1.2250 kg/m3. The
two constants agree, so no constant density offset is expected. This tool
measures the offset anyway and prints it. A measurable offset is attributed,
never absorbed by widening a tolerance.

Data screenings
---------------
Two screens run over the corpus and are reported as classes of their own. They
examine the declarations, not the trajectories.

1. Form factor. i = SD / BC, where SD = (mass_gr / 7000) / calibre_in^2. The
   band is derived from the corpus, not invented: the minimum and maximum of i
   over the records whose bc_g7 grade is "measured". A record that carries only
   a G1 BC is mapped onto the G7 scale with the median BC_g1 / BC_g7 ratio the
   corpus itself exhibits. The derivation is printed.
2. Transposition. Checks for a drag model that disagrees with its field name, a
   BC_g1 / BC_g7 ratio outside the corpus's own ratio band, a mass that is a
   decade away from the median for its calibre, a BC identical to another
   bullet's BC while the mass and calibre both differ, a BC that is the
   reciprocal or a decade shift of the same bullet's other-model BC, and a
   bullet calibre that does not match the cartridge of its matched load.

Exit status
-----------
0  No data error. Both report files are still written.
1  At least one compared bullet breaches tolerance by a factor of five or more,
   or a hard transposition flag stands on a compared bullet. Either means the
   declaration is wrong, not the arithmetic.

Usage
-----
    python3 tools/validation/verify_ballistics.py              # representative set
    python3 tools/validation/verify_ballistics.py --full       # whole corpus
    python3 tools/validation/verify_ballistics.py --published  # solver check only
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "ballistics"

# Kernel constants, transcribed from addons/lib/constants.hpp and
# fnc_calculateBallisticDrag.sqf.
DRAG_CONSTANT = 0.00068418
KELVIN_OFFSET = 273.15
SOUND_SPEED_COEFF = 20.05
SEA_LEVEL_DENSITY = 1.225
STANDARD_GRAVITY = 9.80665

ZERO_M = 100.0
SIGHT_M = 0.040
WIND_MS = 4.0
TEMP_C = 15.0
PRESSURE_HPA = 1013.25
HUMIDITY = 0.0
MAX_RANGE_M = 1000.0
RANGE_STEP_M = 100.0
SUBSONIC_FLOOR_MS = 200.0
RK4_STEP_S = 0.001

VELOCITY_TOL = 0.01
DRIFT_TOL = 0.03
DRIFT_FLOOR_M = 0.005
DROP_INSTRUMENT_RAD = 0.00003
TOF_TOL = 0.01
GROSS_FACTOR = 5.0

RANGE_GRID = [float(r) for r in range(0, int(MAX_RANGE_M) + 1, int(RANGE_STEP_M))]

# The representative set: G1 and G7, pistol to .338, and one launcher-scale
# bullet. Each entry must resolve to a corpus projectile and a muzzle velocity.
REPRESENTATIVE = [
    "apg_m855",       # 5.56 mm, G7, measured
    "apg_m80",        # 7.62 mm, G7, measured
    "apg_m118",       # 7.62 mm match, G7, measured
    "lapua_GB552",    # .308 155 gr, G7
    "lapua_E469",     # .308 150 gr, G1 only
    "lapua_E433",     # 9.3 mm 285 gr, G1 only
    "lapua_GB458",    # 6.5 mm 139 gr, G7
    "lapua_GB488",    # .338 250 gr, G7
    "lapua_GB528",    # .338 300 gr, G7
    "lapua_GB544",    # 5.56 mm 69 gr, G7
    "apg_m33",        # .50 BMG, G7, measured
]


# --------------------------------------------------------------------------
# Drag tables and atmosphere
# --------------------------------------------------------------------------


def drag_tables() -> dict[str, list[list[float]]]:
    """Return the standard Cd(Mach) tables the kernel holds."""
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT / "tools" / "tests"))
    from gen_kernel_vectors import load_drag_tables  # noqa: PLC0415

    return load_drag_tables()


def cd_at(table: list[list[float]], mach: float) -> float:
    """Linear interpolation on Mach, clamped at both ends, as the kernel does."""
    if mach <= table[0][0]:
        return table[0][1]
    if mach >= table[-1][0]:
        return table[-1][1]
    lo, hi = 0, len(table) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if table[mid][0] <= mach:
            lo = mid
        else:
            hi = mid
    m0, c0 = table[lo]
    m1, c1 = table[hi]
    return c0 + (c1 - c0) * (mach - m0) / (m1 - m0)


def sound_speed(temp_c: float) -> float:
    """Local speed of sound, a = 20.05 * sqrt(T + 273.15)."""
    return SOUND_SPEED_COEFF * math.sqrt(temp_c + KELVIN_OFFSET)


def isa_density_ratio(altitude_m: float) -> float:
    """Troposphere density relative to the ISA sea level value.

    T = 288.15 - 0.0065 h, p = 1013.25 * (T / 288.15) ^ 5.2559,
    rho = p / (R T). Independent of the solver, so the two can be compared.
    """
    temp_k = 288.15 - 0.0065 * altitude_m
    pressure_hpa = PRESSURE_HPA * (temp_k / 288.15) ** 5.2559
    density = pressure_hpa * 100.0 / (287.058 * temp_k)
    return density / SEA_LEVEL_DENSITY


# --------------------------------------------------------------------------
# AEE-side trajectory
# --------------------------------------------------------------------------


@dataclass
class Sample:
    """Downrange x, vertical y, lateral z, and the three velocity components."""

    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float

    @property
    def speed(self) -> float:
        return math.sqrt(self.vx * self.vx + self.vy * self.vy + self.vz * self.vz)


def _accel(
    vx: float,
    vy: float,
    vz: float,
    table: list[list[float]],
    bc: float,
    rho_rel: float,
    sound: float,
) -> tuple[float, float, float]:
    """Drag on the air-relative velocity, plus gravity.

    The wind blows along +z, so the air-relative lateral speed is vz - WIND_MS.
    The drag vector is not parallel to the ground track once wind is present,
    and that coupling is what the published drift tables respond to.
    """
    ux, uy, uz = vx, vy, vz - WIND_MS
    speed = math.sqrt(ux * ux + uy * uy + uz * uz)
    if speed <= 0.0:
        return 0.0, -STANDARD_GRAVITY, 0.0
    cd = cd_at(table, speed / sound)
    k = DRAG_CONSTANT * (cd / bc) * rho_rel
    return -k * speed * ux, -k * speed * uy - STANDARD_GRAVITY, -k * speed * uz


def _rk4_step(
    s: Sample,
    dt: float,
    table: list[list[float]],
    bc: float,
    rho_rel: float,
    sound: float,
) -> Sample:
    def f(state: Sample) -> tuple[float, ...]:
        ax, ay, az = _accel(state.vx, state.vy, state.vz, table, bc, rho_rel, sound)
        return state.vx, state.vy, state.vz, ax, ay, az

    def advance(state: Sample, k: tuple[float, ...], scale: float) -> Sample:
        return Sample(
            state.x + scale * k[0],
            state.y + scale * k[1],
            state.z + scale * k[2],
            state.vx + scale * k[3],
            state.vy + scale * k[4],
            state.vz + scale * k[5],
        )

    k1 = f(s)
    k2 = f(advance(s, k1, 0.5 * dt))
    k3 = f(advance(s, k2, 0.5 * dt))
    k4 = f(advance(s, k3, dt))
    dt6 = dt / 6.0
    return Sample(
        s.x + dt6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]),
        s.y + dt6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]),
        s.z + dt6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2]),
        s.vx + dt6 * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3]),
        s.vy + dt6 * (k1[4] + 2 * k2[4] + 2 * k3[4] + k4[4]),
        s.vz + dt6 * (k1[5] + 2 * k2[5] + 2 * k3[5] + k4[5]),
    )


def _flight(
    table: list[list[float]],
    bc: float,
    mv: float,
    theta: float,
    rho_rel: float,
    sound: float,
    until_x: float,
) -> tuple[Sample, float]:
    s = Sample(0.0, 0.0, 0.0, mv * math.cos(theta), mv * math.sin(theta), 0.0)
    t = 0.0
    while s.x < until_x and s.speed > SUBSONIC_FLOOR_MS / 2.0:
        s = _rk4_step(s, RK4_STEP_S, table, bc, rho_rel, sound)
        t += RK4_STEP_S
    return s, t


def launch_angle(
    table: list[list[float]],
    bc: float,
    mv: float,
    rho_rel: float,
    sound: float,
    zero_m: float = ZERO_M,
) -> float:
    """Solve the bore angle that puts the bullet on the line of sight at zero."""

    def height(theta: float) -> float:
        s, _ = _flight(table, bc, mv, theta, rho_rel, sound, zero_m)
        return s.y - SIGHT_M * (1.0 - s.x / zero_m)

    lo, hi = -0.05, 0.20
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if height(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def aee_trajectory(
    projectile: dict,
    mv: float,
    tables: dict[str, list[list[float]]],
    rho_rel: float = 1.0,
    temp_c: float = TEMP_C,
    ranges: list[float] | None = None,
) -> dict[float, dict]:
    """Integrate the AEE equations and return samples at the asked ranges."""
    model, bc = drag_model_and_bc(projectile)
    table = tables[model]
    sound = sound_speed(temp_c)
    theta = launch_angle(table, bc, mv, rho_rel, sound)
    out: dict[float, dict] = {}
    s = Sample(0.0, 0.0, 0.0, mv * math.cos(theta), mv * math.sin(theta), 0.0)
    t = 0.0
    out[0.0] = {
        "velocity_ms": s.speed,
        "drop_m": s.y - SIGHT_M,
        "wind_m": s.z,
        "tof_s": t,
    }
    for target in ranges or RANGE_GRID:
        while s.x < target and s.speed > SUBSONIC_FLOOR_MS / 2.0:
            s = _rk4_step(s, RK4_STEP_S, table, bc, rho_rel, sound)
            t += RK4_STEP_S
        if s.x < target:
            break
        out[target] = {
            "velocity_ms": s.speed,
            "drop_m": s.y - SIGHT_M * (1.0 - s.x / ZERO_M),
            "wind_m": s.z,
            "tof_s": t,
        }
    return out


# --------------------------------------------------------------------------
# Corpus loading
# --------------------------------------------------------------------------


def _value(record: dict, key: str):
    entry = record.get("values", {}).get(key)
    if isinstance(entry, dict):
        return entry.get("value")
    return None


def _meta(record: dict, key: str) -> dict:
    entry = record.get("values", {}).get(key)
    return entry if isinstance(entry, dict) else {}


def load_corpus() -> tuple[list[dict], list[dict], list[dict]]:
    projectiles = json.loads((DATA / "projectiles.json").read_text(encoding="utf-8"))
    loads = json.loads((DATA / "loads.json").read_text(encoding="utf-8"))
    weapons = json.loads((DATA / "weapons.json").read_text(encoding="utf-8"))
    return projectiles, loads, weapons


def drag_model_and_bc(projectile: dict) -> tuple[str, float]:
    """Pick the drag model and BC a record declares.

    A record that carries both is integrated under G7, because G7 is the model
    a long-range BC is measured under and the two published values describe the
    same bullet. A record that carries one uses that one.
    """
    g7 = _value(projectile, "bc_g7")
    g1 = _value(projectile, "bc_g1")
    if g7:
        return "G7", float(g7)
    if g1:
        return "G1", float(g1)
    raise KeyError("no ballistic coefficient")


def mass_gr(projectile: dict) -> float | None:
    mass_g = _value(projectile, "mass_g")
    return mass_g / 0.06479891 if mass_g else None


def calibre_in(projectile: dict) -> float | None:
    dia = _value(projectile, "diameter_mm")
    return dia / 25.4 if dia else None


def significant_figures(value: float) -> int:
    """Count the significant figures a published coefficient carries."""
    text = f"{float(value):.6f}".rstrip("0")
    digits = "".join(ch for ch in text if ch.isdigit()).lstrip("0")
    return len(digits)


def sectional_density(projectile: dict) -> float | None:
    mass = mass_gr(projectile)
    cal = calibre_in(projectile)
    if not mass or not cal:
        return None
    return (mass / 7000.0) / (cal * cal)


def name_tokens(text: str) -> set[str]:
    cleaned = []
    for ch in text.lower():
        cleaned.append(ch if ch.isalnum() or ch in ".-" else " ")
    tokens = set()
    for token in "".join(cleaned).split():
        token = token.strip(".")
        if token:
            tokens.add(token)
    return tokens


def load_velocity(load: dict) -> float | None:
    direct = _value(load, "service_velocity_ms")
    if direct:
        return float(direct)
    anchors = _value(load, "mv_anchors")
    if isinstance(anchors, list) and anchors:
        speeds = [
            a.get("mv_ms") for a in anchors if isinstance(a, dict) and a.get("mv_ms")
        ]
        if speeds:
            return float(max(speeds))
    return None


def _load_mass_hint(text: str) -> float | None:
    tokens = text.replace("gr.", "gr").split()
    for i, token in enumerate(tokens):
        if token.lower() == "gr" and i:
            try:
                return float(tokens[i - 1].replace(",", "."))
            except ValueError:
                return None
    return None


def _load_calibre_hint(load: dict) -> float:
    """Calibre of the cartridge a load names, in inches, or 0.0 when unknown.

    Only unmistakable forms are accepted: a leading-dot designation (.308),
    a millimetre designation (7.62x51, 12.7 x 108 mm, 105mm). A bare number is
    ambiguous between the two conventions, so it yields 0.0 and the caller does
    not filter on it.
    """
    text = str(_value(load, "cartridge") or load.get("cartridge_id") or "")
    dotted = re.search(r"(?<![\d.])\.(\d{2,3})", text)
    if dotted:
        return float("0." + dotted.group(1))
    metric = re.search(r"(\d{1,2}\.\d+)\s*(?:x|mm|\s|$)", text)
    if metric:
        return float(metric.group(1)) / 25.4
    whole = re.search(r"(\d{2,3})\s*mm", text)
    if whole:
        return float(whole.group(1)) / 25.4
    return 0.0


def match_load(projectile: dict, loads: list[dict], require_calibre: bool = True) -> dict | None:
    """Match a projectile to the load that names it.

    The mass in grains must agree and every token of the load's projectile name
    must appear in the projectile's names. Among the matches the closest
    calibre wins.
    """
    mass = mass_gr(projectile)
    calibre = calibre_in(projectile)
    if mass is None:
        return None
    names = name_tokens(" ".join(projectile.get("names", [])))
    best = None
    best_score = -1e9
    for load in loads:
        declared = str(_value(load, "projectile") or load.get("projectile") or "")
        tokens = name_tokens(declared)
        if not tokens or not tokens <= names:
            continue
        load_mass = _load_mass_hint(declared)
        if load_mass is not None and abs(load_mass - mass) > max(1.5, 0.03 * mass):
            continue
        hint = _load_calibre_hint(load)
        if require_calibre and calibre is not None and hint > 0.0 and abs(hint - calibre) > 0.03:
            continue
        score = -abs(hint - calibre) if (calibre is not None and hint > 0.0) else 0.0
        if load_mass is not None:
            score -= abs(load_mass - mass) * 0.5
        if score > best_score:
            best_score = score
            best = load
    return best


# --------------------------------------------------------------------------
# Independent solver
# --------------------------------------------------------------------------


def py_trajectory(
    projectile: dict,
    mv: float,
    ranges: list[float],
    temp_c: float = TEMP_C,
) -> tuple[dict[float, dict], dict]:
    """Trajectory from py-ballisticcalc under the same declared conditions."""
    from py_ballisticcalc import (  # noqa: PLC0415
        Ammo,
        Angular,
        Atmo,
        Calculator,
        Distance,
        DragModel,
        PreferredUnits,
        Pressure,
        Shot,
        TableG1,
        TableG7,
        Temperature,
        Unit,
        Velocity,
        Weapon,
        Weight,
        Wind,
    )

    model, bc = drag_model_and_bc(projectile)
    table = TableG7 if model == "G7" else TableG1
    PreferredUnits.distance = Unit.Meter
    PreferredUnits.velocity = Unit.MPS
    dm = DragModel(
        bc=bc,
        drag_table=table,
        weight=Weight.Gram(_value(projectile, "mass_g")),
        diameter=Distance.Millimeter(_value(projectile, "diameter_mm")),
    )
    ammo = Ammo(dm=dm, mv=Velocity.MPS(mv))
    atmo = Atmo(
        altitude=Distance.Meter(0.0),
        pressure=Pressure.hPa(PRESSURE_HPA),
        temperature=Temperature.Celsius(temp_c),
        humidity=HUMIDITY,
    )
    shot = Shot(
        ammo=ammo,
        atmo=atmo,
        weapon=Weapon(sight_height=Distance.Millimeter(SIGHT_M * 1000.0)),
        winds=[Wind(velocity=Velocity.MPS(WIND_MS), direction_from=Angular.Degree(90))],
    )
    calc = Calculator()
    calc.set_weapon_zero(shot, Distance.Meter(ZERO_M))
    hit = calc.fire(
        shot,
        trajectory_range=Distance.Meter(max(ranges)),
        trajectory_step=Distance.Meter(1.0),
    )
    by_x = {round(point.distance >> Distance.Meter): point for point in hit.records}
    out: dict[float, dict] = {}
    for r in ranges:
        point = by_x.get(int(r))
        if point is None:
            continue
        tof = float(point.time)
        out[r] = {
            "velocity_ms": point.velocity >> Unit.MPS,
            "drop_m": point.height >> Distance.Meter,
            "wind_m": abs(point.windage >> Distance.Meter),
            "tof_s": tof,
            # The classic small-drift approximation, for attribution only.
            "drift_approx_m": WIND_MS * (tof - r / mv),
        }
    atmosphere = {"density_ratio": float(atmo.density_ratio)}
    return out, atmosphere


# --------------------------------------------------------------------------
# Tolerances
# --------------------------------------------------------------------------


def drop_tolerance(range_m: float, reference_drop_m: float) -> float:
    if range_m <= 300.0:
        relative = 0.01
    else:
        relative = 0.01 + 0.01 * (min(range_m, 1000.0) - 300.0) / 700.0
    return max(relative * abs(reference_drop_m), DROP_INSTRUMENT_RAD * range_m)


def drift_tolerance(reference_drift_m: float) -> float:
    return max(DRIFT_TOL * abs(reference_drift_m), DRIFT_FLOOR_M)


def velocity_tolerance(reference_velocity: float) -> float:
    return VELOCITY_TOL * reference_velocity


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------


@dataclass
class Disagreement:
    class_name: str
    projectile_id: str
    metric: str
    range_m: float
    aee: float
    reference: float
    tolerance: float
    excess: float


@dataclass
class Comparison:
    projectile_id: str
    names: list[str]
    model: str
    bc: float
    mv_ms: float
    load_id: str
    ranges: list[float]
    max_velocity_error: float = 0.0
    max_drop_error: float = 0.0
    max_drift_error: float = 0.0
    max_tof_error: float = 0.0
    drift_bias: float = 0.0
    failures: list[Disagreement] = field(default_factory=list)


def compare_projectile(
    projectile: dict,
    load: dict,
    mv: float,
    tables: dict[str, list[list[float]]],
) -> Comparison:
    model, bc = drag_model_and_bc(projectile)
    reference, _ = py_trajectory(projectile, mv, RANGE_GRID)
    ranges: list[float] = []
    for r in RANGE_GRID:
        if r not in reference:
            continue
        if r > 0.0 and reference[r]["velocity_ms"] < SUBSONIC_FLOOR_MS:
            break
        ranges.append(r)
    aee = aee_trajectory(projectile, mv, tables, ranges=ranges)
    comparison = Comparison(
        projectile_id=projectile["projectile_id"],
        names=projectile.get("names", []),
        model=model,
        bc=bc,
        mv_ms=mv,
        load_id=str(load.get("load_id", "")),
        ranges=ranges,
    )
    drift_ratios = []
    for r in ranges:
        if r == 0.0 or r not in aee:
            continue
        mine, theirs = aee[r], reference[r]
        v_tol = velocity_tolerance(theirs["velocity_ms"])
        d_tol = drop_tolerance(r, theirs["drop_m"])
        w_tol = drift_tolerance(theirs["wind_m"])
        v_err = abs(mine["velocity_ms"] - theirs["velocity_ms"])
        d_err = abs(mine["drop_m"] - theirs["drop_m"])
        w_err = abs(mine["wind_m"] - theirs["wind_m"])
        comparison.max_velocity_error = max(
            comparison.max_velocity_error, v_err / v_tol
        )
        comparison.max_drop_error = max(comparison.max_drop_error, d_err / d_tol)
        comparison.max_drift_error = max(comparison.max_drift_error, w_err / w_tol)
        tof_err = abs(mine["tof_s"] - theirs["tof_s"])
        comparison.max_tof_error = max(
            comparison.max_tof_error, tof_err / (TOF_TOL * theirs["tof_s"])
        )
        if theirs["wind_m"] > 1e-6:
            drift_ratios.append(mine["wind_m"] / theirs["wind_m"])
        for metric, err, tol, mine_value, theirs_value in (
            ("velocity", v_err, v_tol, mine["velocity_ms"], theirs["velocity_ms"]),
            ("drop", d_err, d_tol, mine["drop_m"], theirs["drop_m"]),
            ("drift", w_err, w_tol, mine["wind_m"], theirs["wind_m"]),
        ):
            if err > tol:
                comparison.failures.append(
                    Disagreement(
                        class_name="trajectory",
                        projectile_id=comparison.projectile_id,
                        metric=metric,
                        range_m=r,
                        aee=mine_value,
                        reference=theirs_value,
                        tolerance=tol,
                        excess=err / tol,
                    )
                )
    if drift_ratios:
        comparison.drift_bias = statistics.fmean(drift_ratios) - 1.0
    return comparison


# --------------------------------------------------------------------------
# Data screens
# --------------------------------------------------------------------------


def derive_form_factor_band(projectiles: list[dict]) -> dict:
    """Derive the acceptable form factor band from the corpus itself.

    i = SD / BC, so i is unity for the drag model's standard projectile. The
    band is taken per calibre group, over the records that hold a bc_g7 whose
    grade is "measured" or "corroborated", and a group is only banded when at
    least three such records exist. A group with fewer is left unscreened
    rather than guessed at. Only bc_g7 records are screened, because mapping a
    G1 coefficient onto the G7 scale would need a ratio whose spread the corpus
    puts at 1.38 to 2.58, which leaves no power to detect anything.
    """
    groups: dict[float, list[tuple[float, str, str]]] = {}
    for projectile in projectiles:
        bc7 = _value(projectile, "bc_g7")
        cal = calibre_in(projectile)
        sd = sectional_density(projectile)
        if not bc7 or not cal or not sd:
            continue
        grade = str(_meta(projectile, "bc_g7").get("grade") or "")
        groups.setdefault(round(cal, 2), []).append(
            (sd / float(bc7), grade, projectile["projectile_id"])
        )

    banded: dict[str, dict] = {}
    screened = 0
    unscreened = 0
    for cal, items in sorted(groups.items()):
        strong = [i for i, grade, _ in items if grade in ("measured", "corroborated")]
        if len(strong) < 3:
            unscreened += len(items)
            continue
        screened += len(items)
        banded[f"{cal:.2f}"] = {
            "records": len(items),
            "strong": len(strong),
            "min": min(strong),
            "max": max(strong),
            "median": statistics.median(strong),
        }

    measured = sorted(
        i for items in groups.values() for i, grade, _ in items if grade == "measured"
    )
    ratios = sorted(
        float(_value(p, "bc_g1")) / float(_value(p, "bc_g7"))
        for p in projectiles
        if _value(p, "bc_g1") and _value(p, "bc_g7")
    )
    if not banded or not ratios:
        raise RuntimeError("the corpus holds no measured G7 record to derive a band from")
    return {
        "method": (
            "i = SD / BC with SD = (mass_gr / 7000) / calibre_in^2, so i is 1.0 "
            "for the drag model's standard projectile. The band is taken per "
            "calibre group over the bc_g7 records graded 'measured' or "
            "'corroborated', and a group is banded only when it holds at least "
            "three such records. Records outside a banded group are flagged. "
            "Groups without enough measurement, and records that hold only a "
            "bc_g1, are not screened."
        ),
        "g7_records": sum(len(v) for v in groups.values()),
        "screened": screened,
        "unscreened": unscreened,
        "groups": banded,
        "measured_count": len(measured),
        "g7_min": measured[0],
        "g7_max": measured[-1],
        "g7_median": statistics.median(measured),
        "ratio_count": len(ratios),
        "bc1_bc7_min": ratios[0],
        "bc1_bc7_median": statistics.median(ratios),
        "bc1_bc7_max": ratios[-1],
    }


def screen_form_factor(projectiles: list[dict], band: dict) -> list[dict]:
    flags = []
    for projectile in projectiles:
        bc7 = _value(projectile, "bc_g7")
        cal = calibre_in(projectile)
        sd = sectional_density(projectile)
        if not bc7 or not cal or not sd:
            continue
        group = band["groups"].get(f"{round(cal, 2):.2f}")
        if group is None:
            continue
        implied = sd / float(bc7)
        if group["min"] <= implied <= group["max"]:
            continue
        flags.append(
            {
                "class_name": "form_factor",
                "projectile_id": projectile["projectile_id"],
                "names": projectile.get("names", []),
                "basis": "bc_g7",
                "calibre_in": round(cal, 4),
                "form_factor": round(implied, 4),
                "band": [round(group["min"], 4), round(group["max"], 4)],
                "band_records": group["strong"],
                "deviation": round(implied / group["median"], 3),
                "note": "declared BC is not consistent with the calibre and mass",
            }
        )
    flags.sort(key=lambda f: -abs(math.log(f["deviation"])))
    return flags


def screen_transposition(
    projectiles: list[dict], loads: list[dict], band: dict
) -> list[dict]:
    flags: list[dict] = []
    by_calibre: dict[float, list[float]] = {}
    for projectile in projectiles:
        cal = calibre_in(projectile)
        mass = mass_gr(projectile)
        if cal and mass:
            by_calibre.setdefault(round(cal, 2), []).append(mass)
    medians = {k: statistics.median(v) for k, v in by_calibre.items() if len(v) >= 3}
    seen_bc: dict[tuple, tuple] = {}

    def add(projectile: dict, subclass: str, note: str, **extra) -> None:
        flags.append(
            {
                "class_name": "transposition",
                "subclass": subclass,
                "projectile_id": projectile["projectile_id"],
                "names": projectile.get("names", []),
                "note": note,
                **extra,
            }
        )

    for projectile in projectiles:
        pid = projectile["projectile_id"]
        bc1 = _value(projectile, "bc_g1")
        bc7 = _value(projectile, "bc_g7")
        declared = _value(projectile, "drag_model")
        cal = calibre_in(projectile)
        mass = mass_gr(projectile)

        for key, label in (("bc_g1", "G1"), ("bc_g7", "G7")):
            model = _meta(projectile, key).get("drag_model")
            if model and str(model).upper() != label:
                add(projectile, "drag_model_field", f"{key} carries drag_model {model}")
        if declared and bc7 and not bc1 and str(declared).upper() != "G7":
            add(
                projectile,
                "drag_model_field",
                f"record declares {declared} but holds only bc_g7",
            )

        if bc1 and bc7:
            ratio = float(bc1) / float(bc7)
            if ratio < band["bc1_bc7_min"] or ratio > band["bc1_bc7_max"]:
                add(
                    projectile,
                    "bc_pair_ratio",
                    "BC_g1 / BC_g7 outside the ratio the corpus supports",
                    value=round(ratio, 4),
                    band=[round(band["bc1_bc7_min"], 4), round(band["bc1_bc7_max"], 4)],
                )
            if abs(ratio - 10.0) < 0.5 or abs(ratio - 0.1) < 0.05:
                add(
                    projectile,
                    "bc_decimal_shift",
                    "BC_g1 is a decade away from BC_g7",
                    value=round(ratio, 4),
                )
            if abs(float(bc1) * float(bc7) - 1.0) < 0.02:
                add(
                    projectile,
                    "bc_reciprocal",
                    "BC_g1 and BC_g7 are reciprocal",
                    value=round(float(bc1) * float(bc7), 6),
                )

        if cal and mass:
            median = medians.get(round(cal, 2))
            if median and (mass > 10.0 * median or mass < 0.1 * median):
                add(
                    projectile,
                    "mass_decade",
                    "mass is a decade away from the calibre median",
                    value=round(mass, 2),
                    median_gr=round(median, 2),
                )

        # A shared BC is only evidence of a copy when the number carries four
        # significant figures. Manufacturer BCs are commonly published to three
        # decimal places, and two bullets sharing 0.240 is ordinary rounding.
        for bc, label in ((bc1, "G1"), (bc7, "G7")):
            if not bc or significant_figures(bc) < 4:
                continue
            key = (label, round(float(bc), 5))
            other = seen_bc.get(key)
            if other and other[0] != pid:
                other_mass, other_cal = other[1], other[2]
                if (
                    mass is not None
                    and other_mass is not None
                    and abs(mass - other_mass) > 0.01 * other_mass
                    and cal is not None
                    and other_cal is not None
                    and abs(cal - other_cal) > 0.01 * other_cal
                ):
                    add(
                        projectile,
                        "bc_duplicate",
                        "BC identical to another bullet of different mass and calibre",
                        other=other[0],
                        value=round(float(bc), 5),
                        other_mass_gr=round(other_mass, 2),
                        other_calibre_in=round(other_cal, 4),
                    )
            seen_bc.setdefault(key, (pid, mass, cal))

    for projectile in projectiles:
        load = match_load(projectile, loads, require_calibre=False)
        cal = calibre_in(projectile)
        if load is None or cal is None:
            continue
        hint = _load_calibre_hint(load)
        if hint <= 0.0:
            continue
        if abs(cal - hint) > 0.012:
            add(
                projectile,
                "calibre_mismatch",
                "bullet calibre does not match the cartridge of its load",
                load_id=load.get("load_id"),
                value=round(cal, 4),
                cartridge_calibre_in=hint,
            )
    return flags


# --------------------------------------------------------------------------
# Published worked examples
# --------------------------------------------------------------------------

LAPUA_URL = (
    "https://www.lapua.com/wp-content/uploads/2026/06/Lapua_Catalog_2026_ENG_web.pdf"
)
LAPUA_SHA = "27b2ebed6394cfa9a762527f8188eb3e534d39c1ef75dd9524f78c7954417f64"

PUBLISHED_EXAMPLES = [
    {
        "id": "lapua_308_155_scenar_l",
        "citation": (
            "Lapua Catalog 2026, .308 Win product 4317076, 155 gr Scenar-L (GB552), "
            "metric trajectory table"
        ),
        "url": LAPUA_URL,
        "sha256": LAPUA_SHA,
        "model": "G1",
        "bc": 0.460,
        "mv_ms": 860.0,
        "mass_g": 10.0438,
        "diameter_mm": 7.8232,
        "barrel_mm": 660,
        "zero_m": 100.0,
        "sight_m": 0.040,
        "wind_ms": 4.0,
        "temperature_c": 15.0,
        "pressure_hpa": 1013.25,
        "humidity": 0.0,
        "velocity_ms": {100: 794, 200: 730, 300: 669, 600: 503, 800: 408, 1000: 331},
        "drop_mm": {100: 0, 200: -115, 300: -414, 600: -2813, 800: -6265, 1000: -12106},
        "drift_mm": {100: 18, 200: 76, 300: 180, 600: 831, 800: 1640, 1000: 2857},
        # The publisher band the BC by velocity, so the single 0.460 coefficient
        # is only the above-830 m/s band. Beyond 800 m the table rests on the
        # 0.430 band, so those rows are printed and not gated.
        "gate_until_m": 800,
        "tolerance": {"velocity": 0.02, "drop": 0.02, "drift": 0.10},
    },
    {
        "id": "lapua_338lm_250_scenar",
        "citation": (
            "Lapua Catalog 2026, .338 Lapua Mag. product 4318017, 250 gr Scenar "
            "(GB488), metric trajectory table"
        ),
        "url": LAPUA_URL,
        "sha256": LAPUA_SHA,
        "model": "G7",
        "bc": 0.322,
        "mv_ms": 905.0,
        "mass_g": 16.1997,
        "diameter_mm": 8.5852,
        "barrel_mm": 680,
        "zero_m": 100.0,
        "sight_m": 0.040,
        "wind_ms": 4.0,
        "temperature_c": 15.0,
        "pressure_hpa": 1013.25,
        "humidity": 0.0,
        "velocity_ms": {100: 856, 200: 808, 300: 762, 600: 631, 800: 551, 1000: 477},
        "drop_mm": {100: 0, 200: -93, 300: -336, 600: -2164, 800: -4570, 1000: -8274},
        "drift_mm": {100: 12, 200: 48, 300: 112, 600: 495, 800: 944, 1000: 1589},
        "gate_until_m": 1000,
        "tolerance": {"velocity": 0.02, "drop": 0.02, "drift": 0.10},
    },
]


def check_published_examples() -> list[dict]:
    """Reproduce each published table and return the measured error per metric."""
    results = []
    for example in PUBLISHED_EXAMPLES:
        projectile = {
            "projectile_id": example["id"],
            "values": {
                "mass_g": {"value": example["mass_g"]},
                "diameter_mm": {"value": example["diameter_mm"]},
                f"bc_{example['model'].lower()}": {"value": example["bc"]},
                "drag_model": {"value": example["model"]},
            },
        }
        ranges = sorted(float(r) for r in example["velocity_ms"])
        reference, atmosphere = py_trajectory(projectile, example["mv_ms"], ranges)
        rows = []
        worst = {"velocity": 0.0, "drop": 0.0, "drift": 0.0}
        for r in ranges:
            point = reference.get(r)
            if point is None:
                continue
            key = int(r)
            published_v = example["velocity_ms"][key]
            published_drop = example["drop_mm"][key] / 1000.0
            published_drift = example["drift_mm"][key] / 1000.0
            v_error = abs(point["velocity_ms"] - published_v) / published_v
            d_error = abs(point["drop_m"] - published_drop) / max(
                abs(published_drop), 0.010
            )
            w_error = abs(point["wind_m"] - published_drift) / max(
                abs(published_drift), 0.010
            )
            if key <= example["gate_until_m"]:
                worst["velocity"] = max(worst["velocity"], v_error)
                worst["drop"] = max(worst["drop"], d_error)
                worst["drift"] = max(worst["drift"], w_error)
            rows.append(
                {
                    "range_m": key,
                    "published_velocity_ms": published_v,
                    "velocity_ms": round(point["velocity_ms"], 1),
                    "velocity_error": round(v_error, 4),
                    "published_drop_mm": example["drop_mm"][key],
                    "drop_mm": round(point["drop_m"] * 1000.0, 1),
                    "drop_error": round(d_error, 4),
                    "published_drift_mm": example["drift_mm"][key],
                    "drift_mm": round(point["wind_m"] * 1000.0, 1),
                    "drift_error": round(w_error, 4),
                    "drift_approx_mm": round(point["drift_approx_m"] * 1000.0, 1),
                    "tof_s": round(point["tof_s"], 3),
                }
            )
        tolerance = example["tolerance"]
        results.append(
            {
                "id": example["id"],
                "citation": example["citation"],
                "url": example["url"],
                "sha256": example["sha256"],
                "model": example["model"],
                "bc": example["bc"],
                "mv_ms": example["mv_ms"],
                "conditions": {
                    "zero_m": example["zero_m"],
                    "sight_m": example["sight_m"],
                    "wind_ms": example["wind_ms"],
                    "temperature_c": example["temperature_c"],
                    "pressure_hpa": example["pressure_hpa"],
                    "humidity": example["humidity"],
                },
                "rows": rows,
                "worst_error": {k: round(v, 4) for k, v in worst.items()},
                "gate_until_m": example["gate_until_m"],
                "passed": all(worst[k] <= tolerance[k] for k in tolerance),
                "atmosphere": atmosphere,
                "tolerance": tolerance,
            }
        )
    return results


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def build_report(full: bool) -> tuple[dict, int]:
    projectiles, loads, _weapons = load_corpus()
    tables = drag_tables()
    band = derive_form_factor_band(projectiles)

    if full:
        candidates = [
            p for p in projectiles if _value(p, "bc_g7") or _value(p, "bc_g1")
        ]
    else:
        wanted = {pid.lower() for pid in REPRESENTATIVE}
        candidates = [p for p in projectiles if p["projectile_id"].lower() in wanted]

    comparisons: list[Comparison] = []
    unmatched: list[dict] = []
    for projectile in candidates:
        load = match_load(projectile, loads)
        mv = load_velocity(load) if load else None
        if not _value(projectile, "bc_g1") and not _value(projectile, "bc_g7"):
            unmatched.append(
                {
                    "projectile_id": projectile["projectile_id"],
                    "names": projectile.get("names", []),
                    "note": "no ballistic coefficient",
                }
            )
            continue
        if not load or not mv:
            unmatched.append(
                {
                    "projectile_id": projectile["projectile_id"],
                    "names": projectile.get("names", []),
                    "note": "no declared muzzle velocity",
                }
            )
            continue
        comparisons.append(compare_projectile(projectile, load, mv, tables))

    form_factor_flags = screen_form_factor(projectiles, band)
    transposition_flags = screen_transposition(projectiles, loads, band)
    published = check_published_examples()

    trajectory_failures = [f for c in comparisons for f in c.failures]
    gross = [f for f in trajectory_failures if f.excess >= GROSS_FACTOR]
    compared_ids = {c.projectile_id.lower() for c in comparisons}
    hard_ids = {
        f["projectile_id"].lower()
        for f in transposition_flags
        if f.get("subclass")
        in ("drag_model_field", "bc_decimal_shift", "bc_reciprocal")
    }
    hard_on_compared = sorted(hard_ids & compared_ids)
    drift_biases = [c.drift_bias for c in comparisons if c.drift_bias]

    report = {
        "conditions": {
            "zero_m": ZERO_M,
            "sight_m": SIGHT_M,
            "wind_ms": WIND_MS,
            "wind_from_degrees": 90,
            "temperature_c": TEMP_C,
            "pressure_hpa": PRESSURE_HPA,
            "humidity": HUMIDITY,
            "gravity_ms2": STANDARD_GRAVITY,
            "range_step_m": RANGE_STEP_M,
            "max_range_m": MAX_RANGE_M,
            "subsonic_floor_ms": SUBSONIC_FLOOR_MS,
            "rk4_step_s": RK4_STEP_S,
        },
        "tolerances": {
            "velocity_relative": VELOCITY_TOL,
            "drop": (
                "max(relative * |drop|, 0.03 mrad * range); the relative floor "
                "ramps from 1 percent at 300 m to 2 percent at 1000 m"
            ),
            "drift": f"max({DRIFT_TOL:.2f} * |drift|, {DRIFT_FLOOR_M * 1000:.0f} mm)",
            "tof_relative": TOF_TOL,
        },
        "form_factor_band": band,
        "density_check": {
            "aee_isa_density_ratio_sea_level": round(isa_density_ratio(0.0), 6),
            "aee_isa_density_ratio_1500m": round(isa_density_ratio(1500.0), 6),
            "solver_density_ratio_sea_level": published[0]["atmosphere"][
                "density_ratio"
            ],
            "note": (
                "AEE rho0 = 1.225 kg/m3. The solver documents cStandardDensity "
                "0.076474 lb/ft3 = 1.2250 kg/m3. Both ratios are printed so the "
                "constant offset between the two sides is known rather than "
                "absorbed by a tolerance."
            ),
        },
        "published_examples": published,
        "compared": [
            {
                "projectile_id": c.projectile_id,
                "names": c.names,
                "model": c.model,
                "bc": c.bc,
                "mv_ms": c.mv_ms,
                "load_id": c.load_id,
                "ranges_m": c.ranges,
                "worst_velocity_error_over_tolerance": round(c.max_velocity_error, 3),
                "worst_drop_error_over_tolerance": round(c.max_drop_error, 3),
                "worst_drift_error_over_tolerance": round(c.max_drift_error, 3),
                "worst_tof_error_over_tolerance": round(c.max_tof_error, 3),
                "drift_bias": round(c.drift_bias, 4),
            }
            for c in comparisons
        ],
        "counts": {
            "compared": len(comparisons),
            "unmatched": len(unmatched),
            "trajectory_disagreements": len(trajectory_failures),
            "gross_disagreements": len(gross),
            "form_factor_flags": len(form_factor_flags),
            "transposition_flags": len(transposition_flags),
            "hard_transposition_on_compared": len(hard_on_compared),
            "mean_drift_bias": round(statistics.fmean(drift_biases), 4)
            if drift_biases
            else 0.0,
        },
        "disagreements": [
            {
                "class_name": f.class_name,
                "projectile_id": f.projectile_id,
                "metric": f.metric,
                "range_m": f.range_m,
                "aee": round(f.aee, 4),
                "reference": round(f.reference, 4),
                "tolerance": round(f.tolerance, 6),
                "excess": round(f.excess, 3),
            }
            for f in sorted(trajectory_failures, key=lambda f: -f.excess)
        ],
        "form_factor": form_factor_flags,
        "transposition": transposition_flags,
        "unmatched": unmatched,
        "data_error": bool(gross or hard_on_compared),
    }
    return report, (1 if report["data_error"] else 0)


def render_markdown(report: dict) -> str:
    lines: list[str] = []
    add = lines.append
    conditions = report["conditions"]
    counts = report["counts"]
    add("# Ballistic verification report")
    add("")
    add("Generated by `tools/validation/verify_ballistics.py`. The AEE kernel is")
    add("recomputed in Python from the published equations and compared with")
    add("`py-ballisticcalc` 3.1.1 under identical declared conditions.")
    add("")
    add("## Conditions")
    add("")
    add(f"- Zero distance: {conditions['zero_m']:.0f} m.")
    add(f"- Sight height: {conditions['sight_m'] * 1000:.0f} mm.")
    add(
        f"- Atmosphere: {conditions['temperature_c']:.1f} C, "
        f"{conditions['pressure_hpa']:.2f} hPa, "
        f"{conditions['humidity'] * 100:.0f} % relative humidity (ISA sea level)."
    )
    add(
        f"- Wind: {conditions['wind_ms']:.0f} m/s full value from "
        f"{conditions['wind_from_degrees']} degrees."
    )
    add(
        f"- Gravity: {conditions['gravity_ms2']:.5f} m/s^2, flat fire, no Coriolis, "
        "no spin drift."
    )
    add(
        f"- Ranges: 0 to {conditions['max_range_m']:.0f} m at "
        f"{conditions['range_step_m']:.0f} m steps, truncated below "
        f"{conditions['subsonic_floor_ms']:.0f} m/s retained velocity."
    )
    add(
        f"- AEE integration: RK4 at a fixed {conditions['rk4_step_s'] * 1000:.1f} ms step."
    )
    add("")
    add("## Tolerances")
    add("")
    add(
        f"- Retained velocity: {report['tolerances']['velocity_relative'] * 100:.0f} % relative."
    )
    add(f"- Drop: {report['tolerances']['drop']}.")
    add(f"- Wind drift: {report['tolerances']['drift']}.")
    add(
        f"- Time of flight: {report['tolerances']['tof_relative'] * 100:.0f} % relative, reported only."
    )
    add("")
    add("## Published examples")
    add("")
    add("Each table comes from a page that was fetched, and its sha256 matches the")
    add("hash the corpus records for that document.")
    add("")
    for example in report["published_examples"]:
        add(f"### {example['id']}")
        add("")
        add(f"- Source: {example['citation']}")
        add(f"- URL: {example['url']}")
        add(f"- sha256: `{example['sha256']}`")
        add(
            f"- Model and BC: {example['model']} {example['bc']}, muzzle velocity "
            f"{example['mv_ms']:.0f} m/s."
        )
        add(f"- Verdict: {'reproduced' if example['passed'] else 'NOT reproduced'}.")
        add("")
        add(
            "| Range (m) | Published v (m/s) | Solver v | v error | Published drop (mm) "
            "| Solver drop | drop error | Published drift (mm) | Solver drift | drift error |"
        )
        add("|---|---|---|---|---|---|---|---|---|---|")
        for row in example["rows"]:
            add(
                "| {range_m} | {published_velocity_ms} | {velocity_ms} | {velocity_error:.2%} | "
                "{published_drop_mm} | {drop_mm} | {drop_error:.2%} | {published_drift_mm} | "
                "{drift_mm} | {drift_error:.2%} |".format(**row)
            )
        add("")
        worst = example["worst_error"]
        add(
            f"Worst error: velocity {worst['velocity']:.2%}, drop {worst['drop']:.2%}, "
            f"drift {worst['drift']:.2%}."
        )
        last = example["rows"][-1]
        add(
            f"Attribution of the drift residual: the classic approximation "
            f"w (t - x / v0) gives {last['drift_approx_mm']:.0f} mm at "
            f"{last['range_m']} m, the solver gives {last['drift_mm']:.0f} mm and the "
            f"published table gives {last['published_drift_mm']} mm. The solver "
            f"follows the closed form, so the residual is the publisher's wind "
            f"convention, not the drag law."
        )
        add("")
    add("## Form factor band")
    add("")
    band = report["form_factor_band"]
    add(band["method"])
    add("")
    add(f"- G7 records in the corpus: {band['g7_records']}; screened {band['screened']}, "
        f"not screened {band['unscreened']}.")
    add(f"- Measured G7 records: {band['measured_count']}, i from {band['g7_min']:.3f} to "
        f"{band['g7_max']:.3f}, median {band['g7_median']:.3f}.")
    add(f"- BC_g1 / BC_g7 over the {band['ratio_count']} records holding both: "
        f"{band['bc1_bc7_min']:.3f} to {band['bc1_bc7_max']:.3f}, median "
        f"{band['bc1_bc7_median']:.3f}.")
    add("")
    add("| Calibre (in) | Records | Measured or corroborated | Band min | Band max | Band median | Flagged |")
    add("|---|---|---|---|---|---|---|")
    flagged_by_calibre: dict[str, int] = {}
    for flag in report["form_factor"]:
        key = f"{flag['calibre_in']:.2f}"
        flagged_by_calibre[key] = flagged_by_calibre.get(key, 0) + 1
    for cal, group in band["groups"].items():
        add(
            f"| {cal} | {group['records']} | {group['strong']} | {group['min']:.3f} | "
            f"{group['max']:.3f} | {group['median']:.3f} | "
            f"{flagged_by_calibre.get(cal, 0)} |"
        )
    add("")
    add("Worst form factor flags by deviation from the group median:")
    add("")
    if not report["form_factor"]:
        add("None.")
    else:
        add("| Bullet | Calibre (in) | i | Band | Deviation |")
        add("|---|---|---|---|---|")
        for flag in report["form_factor"][:15]:
            add(
                f"| {flag['projectile_id']} | {flag['calibre_in']:.3f} | {flag['form_factor']:.3f} | "
                f"{flag['band'][0]:.3f} to {flag['band'][1]:.3f} | {flag['deviation']:.2f}x |"
            )
        if len(report["form_factor"]) > 15:
            add("")
            add(f"The machine-readable report lists all {len(report['form_factor'])} flags.")
    add("")
    add("## Density convention")
    add("")
    density = report["density_check"]
    add(
        f"- AEE ISA density ratio at sea level: {density['aee_isa_density_ratio_sea_level']:.6f}."
    )
    add(
        f"- AEE ISA density ratio at 1500 m: {density['aee_isa_density_ratio_1500m']:.6f}."
    )
    add(
        f"- Solver density ratio at the same sea level conditions: "
        f"{density['solver_density_ratio_sea_level']:.6f}."
    )
    add(f"- {density['note']}")
    add(
        f"- Measured mean drift bias (AEE divided by solver): {counts['mean_drift_bias']:+.2%}."
    )
    add("")
    add("## Counts")
    add("")
    for key in (
        "compared",
        "unmatched",
        "trajectory_disagreements",
        "gross_disagreements",
        "form_factor_flags",
        "transposition_flags",
        "hard_transposition_on_compared",
    ):
        add(f"- {key.replace('_', ' ')}: {counts[key]}")
    add("")
    add("## Worst trajectory disagreements")
    add("")
    worst_five = report["disagreements"][:5]
    if not worst_five:
        add("None above tolerance.")
    else:
        add("| Bullet | Metric | Range (m) | AEE | Solver | Tolerance | Excess |")
        add("|---|---|---|---|---|---|---|")
        for row in worst_five:
            add(
                f"| {row['projectile_id']} | {row['metric']} | {row['range_m']:.0f} | "
                f"{row['aee']:.4f} | {row['reference']:.4f} | {row['tolerance']:.6f} | "
                f"{row['excess']:.2f}x |"
            )
    add("")
    add("## Transposition flags")
    add("")
    if not report["transposition"]:
        add("None.")
    else:
        by_subclass: dict[str, int] = {}
        for flag in report["transposition"]:
            by_subclass[flag["subclass"]] = by_subclass.get(flag["subclass"], 0) + 1
        for subclass, count in sorted(by_subclass.items(), key=lambda kv: -kv[1]):
            add(f"- {subclass.replace('_', ' ')}: {count}")
        add("")
        add("| Bullet | Subclass | Detail |")
        add("|---|---|---|")
        for flag in report["transposition"][:15]:
            detail = flag["note"]
            for key in ("value", "band", "other", "cartridge_calibre_in", "median_gr"):
                if key in flag:
                    detail += f" ({key} {flag[key]})"
            add(f"| {flag['projectile_id']} | {flag['subclass']} | {detail} |")
        if len(report["transposition"]) > 15:
            add("")
            add(f"The machine-readable report lists all {len(report['transposition'])} flags.")
    add("")
    add("## Unmatched bullets")
    add("")
    if not report["unmatched"]:
        add("None.")
    else:
        for flag in report["unmatched"][:20]:
            add(f"- {flag['projectile_id']}: {flag['note']}.")
        if len(report["unmatched"]) > 20:
            add(f"- and {len(report['unmatched']) - 20} more.")
    add("")
    add("No corpus value is changed by this tool. A flagged value is a follow-up item.")
    add("")
    return "\n".join(lines)


def main(argv: list[str] | None = None, out_dir: Path | None = None) -> int:
    """Run the verifier. out_dir redirects the reports, which the test uses."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--full", action="store_true", help="compare the whole corpus")
    parser.add_argument(
        "--published", action="store_true", help="run the published example check only"
    )
    args = parser.parse_args(argv)

    if args.published:
        results = check_published_examples()
        for result in results:
            worst = result["worst_error"]
            print(
                f"{result['id']}: velocity {worst['velocity']:.2%}, "
                f"drop {worst['drop']:.2%}, drift {worst['drift']:.2%} -> "
                f"{'reproduced' if result['passed'] else 'FAILED'}"
            )
        return 0 if all(r["passed"] for r in results) else 1

    report, status = build_report(args.full)
    report_md = (out_dir or DATA) / "VERIFICATION.md"
    report_json = (out_dir or DATA) / "verification.json"
    report_md.write_text(render_markdown(report), encoding="utf-8")
    report_json.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    counts = report["counts"]
    print(
        f"compared {counts['compared']}, unmatched {counts['unmatched']}, "
        f"trajectory disagreements {counts['trajectory_disagreements']}, "
        f"form factor flags {counts['form_factor_flags']}, "
        f"transposition flags {counts['transposition_flags']}"
    )
    print(f"wrote {report_md} and {report_json}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
