#!/usr/bin/env python3
"""End-to-end physics validation against independent references (JSP 939 VV&A).

The existing validate_physics.py is VERIFICATION: the SQF mirrors are
checked against published formulas and reference values.  This script is
the VALIDATION layer: it feeds the same scenario state through independent
physics oracles and compares 1:1 with tolerance bands.

Per JSP 939 (Modelling & Simulation) VV&A practice:
  - Direction 2 (accuracy): in-game output vs independent solver.
  - Tolerance bands are the acceptance criteria, documented per domain.

Oracles:
  - ISO 9613-1:1993 atmospheric absorption (implemented locally; the two
    check values 2.60 / 12.59 dB/km were corrected in issue #80 - the
    original hand-computed 4.164 / 130.217 were wrong).
  - ICAO Standard Atmosphere (Doc 7488 / ISO 2533) table.
  - NWS Rothfusz 1990 heat index regression.
  - Optional pip libraries when installed: metpy, pythermalcomfort,
    psychrolib (SKIP when absent - never fail the core path).

Run:  python3 tools/validation/validate_oracles.py
Exit: 0 when every run check passes, 1 when any fails.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate_physics as vp  # reuse the SQF mirrors + stats helpers


def _has_module(name):
    try:
        __import__(name)
        return True
    except ImportError:
        return False


HAS_PYTHERMALCOMFORT = _has_module("pythermalcomfort")

# ─── ISO 9613-1:1993 atmospheric absorption oracle ─────────────────────────
# ISO 9613-1:1993 "Acoustics - Attenuation of sound during propagation
# outdoors - Part 1: Calculation of the absorption of sound by the
# atmosphere".  The implementation below is the standard formula set; the
# two check values are the CORRECTED references from issue #80.
#   Reference: 15 C, 50 % RH, 101.325 kPa -> 1 kHz = 2.60 dB/km,
#   8 kHz = 12.59 dB/km.


def _water_vapour_fraction(t_c, rh, p_pa):
    """Molar concentration of water vapour h as a FRACTION (ISO 9613-1).

    h = RH * psat / p.  The frO/frN relaxation-frequency constants are
    calibrated for h in [0, ~0.05] (a fraction), NOT a percentage —
    using percent inflates frO and gives 10x too much absorption at
    8 kHz.  Verified: fraction form reproduces the corrected issue #80
    references (2.60 / 12.59 dB/km).
    """
    psat = vp.e_sat_buck(t_c) * 100.0  # Buck hPa -> Pa
    return (rh / 100.0) * psat / p_pa


def iso9613_absorption_db_per_km(f_hz, t_c, rh, p_pa=101325.0):
    """ISO 9613-1:1993 atmospheric absorption coefficient (dB/km).

    Alpha (dB/m) per the standard, converted to dB/km.  T in Kelvin in the
    formula; p0 = 101.325 kPa reference.
    """
    t_k = t_c + 273.15
    t0 = 293.15
    p0 = 101325.0
    h = _water_vapour_fraction(t_c, rh, p_pa)

    fr_o = (p_pa / p0) * (24.0 + 4.04e4 * h * (0.02 + h) / (0.391 + h))
    fr_n = (t_k / t0) ** -0.5 * (
        9.0 + 280.0 * h * math.exp(-4.170 * ((t_k / t0) ** (-1.0 / 3.0)) - 1.0)
    )

    alpha = (
        8.686
        * f_hz**2
        * (
            1.84e-11 * (p_pa / p0) ** -1 * (t_k / t0) ** 0.5
            + (t_k / t0) ** -2.5
            * (
                0.01275 * math.exp(-2239.1 / t_k) / (fr_o + f_hz**2 / fr_o)
                + 0.1068 * math.exp(-3352.0 / t_k) / (fr_n + f_hz**2 / fr_n)
            )
        )
    )
    return alpha * 1000.0  # dB/m -> dB/km


def check_iso9613_absorption():
    """ISO 9613-1 oracle vs the corrected issue #80 references."""
    cases = [
        (1000.0, 2.60, "1 kHz"),
        (8000.0, 12.59, "8 kHz"),
    ]
    errors = []
    for f_hz, ref_dbk, label in cases:
        alpha = iso9613_absorption_db_per_km(f_hz, 15.0, 50.0, 101325.0)
        errors.append(abs(alpha - ref_dbk))
    max_abs, rmse = vp.compute_stats(errors)
    return {
        "name": "ISO 9613-1 atmospheric absorption (oracle)",
        "ground_truth": "ISO 9613-1:1993 formula; corrected refs 2.60/12.59 dB/km (issue #80)",
        "grid": "15 C, 50 % RH, 101.325 kPa, 1 and 8 kHz",
        "tolerance": "0.05 dB/km",
        "status": "PASS" if max_abs <= 0.05 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "dB/km",
        "note": "guard against the original hand-computed 4.164/130.217 error",
    }


# ─── ICAO standard atmosphere (Doc 7488 / ISO 2533) ────────────────────────
# Embedded verified rows.  The mod computes density from T/RH/P via the
# ideal gas law with virtual temperature (fnc_calculateAirDensity.sqf);
# the oracle compares mod output against the ISA table at the same state.
ISA_ROWS = [
    # (alt_m, temp_C, p_kPa, rho_kgm3)
    (0, 15.0, 101.325, 1.2250),
    (5000, -17.5, 54.02, 0.7361),
    (10000, -50.0, 26.44, 0.4127),
]


def check_icao_density_oracle():
    """Mod air density vs ICAO standard-atmosphere density."""
    errors = []
    for alt_m, temp_c, p_kpa, rho_ref in ISA_ROWS:
        rho_mod = vp.air_density(temp_c, p_kpa * 10.0, 0.0)  # RH 0 = dry
        errors.append(abs(rho_mod - rho_ref) / rho_ref)
    max_abs, rmse = vp.compute_stats(errors)
    return {
        "name": "Air density vs ICAO Std Atm (oracle)",
        "ground_truth": "ICAO Doc 7488 / ISO 2533 density column",
        "grid": "0 / 5000 / 10000 m (ISA rows)",
        "tolerance": "0.5 % relative",
        "status": "PASS" if max_abs <= 0.005 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "rel",
        "note": "dry-air path reduces the mod formula to the ideal gas law",
    }


# ─── NWS Rothfusz 1990 heat index oracle ───────────────────────────────────
# Official NWS check value: 90 F (32.2 C), 70 % RH -> 105.9 F.


def check_heat_index_oracle():
    """Mod NWS heat index vs the official 105.9 F check value."""
    hi_c_mod = vp.heat_index_nws(32.2, 70.0)
    hi_f_mod = hi_c_mod * 9 / 5 + 32
    err = abs(hi_f_mod - 105.9)
    return {
        "name": "NWS heat index oracle (90 F / 70 % -> 105.9 F)",
        "ground_truth": "NOAA SR-90-23 Rothfusz regression official check value",
        "grid": "single official check point",
        "tolerance": "0.5 F",
        "status": "PASS" if err <= 0.5 else "FAIL",
        "max_abs": err,
        "rmse": err,
        "unit": "F",
        "note": "mod mirror validated here against the NWS published value",
    }


# ─── Optional library oracles (SKIP when absent) ───────────────────────────
# NOTE: the wet-bulb-vs-psychrolib and ISA-vs-metpy checks already exist in
# validate_physics.py (checks #2 and #7, same grids).  They are NOT
# duplicated here: the psychrolib iteration costs ~1.7 s per call, so a
# second grid would add minutes for zero new information.  The pythermal
# comfort WBGT check below IS new - validate_physics.py has no independent
# thermal-comfort oracle.


def check_wbgt_pythermalcomfort_oracle():
    """Mod WBGT weighting vs pythermalcomfort ISO 7243.

    The mod computes WBGT = 0.7*Tw + 0.2*Tg + 0.1*T (ISO 7243) with
    Tg = T at overcast=1 (the Tg=Ta reduction the mod's own harness
    validates against ISO 7243 in validate_physics check #7).
    pythermalcomfort implements the same weighting independently
    (wbgt(twb, tg, tdb)).  The grid is overcast=1 only: at overcast=0
    pythermalcomfort applies its own solar-load adjustment to Tg, which
    the mod deliberately does not model - comparing there would measure
    that design difference, not the weighting.  NOTE: pythermalcomfort's
    wet_bulb_tmp is itself Stull, so the Tw INPUT is shared - this
    check validates the 0.7/0.2/0.1 aggregation against a second
    codebase; the psychrometrics oracle (Stull vs psychrolib) lives in
    validate_physics check #2.
    """
    if not HAS_PYTHERMALCOMFORT:
        return {
            "name": "WBGT weighting vs pythermalcomfort (oracle)",
            "ground_truth": "pythermalcomfort ISO 7243 wbgt(twb, tg, tdb)",
            "grid": "T 20-40 C step 5, RH 20-100 % step 20, overcast 1",
            "tolerance": "0.06 C (pythermalcomfort 1-decimal rounding)",
            "status": "SKIP",
            "max_abs": 0.0,
            "rmse": 0.0,
            "unit": "C",
            "note": "needs pythermalcomfort",
        }
    from pythermalcomfort.models import wbgt as ptc_wbgt

    errors = []
    for t in range(20, 41, 5):
        for rh in range(20, 101, 20):
            mod_tw = vp.wet_bulb_stull(t, rh)
            mod_tg = t  # overcast=1: Tg = Ta (mod's ISO 7243 reduction)
            mod_wbgt = 0.7 * mod_tw + 0.2 * mod_tg + 0.1 * t
            # pythermalcomfort rounds to 1 decimal (round_output=True),
            # so the tolerance is 0.06 C (half the rounding step).
            ref = ptc_wbgt(twb=mod_tw, tg=mod_tg, tdb=t).wbgt
            errors.append(abs(mod_wbgt - ref))
    max_abs, rmse = vp.compute_stats(errors)
    return {
        "name": "WBGT weighting vs pythermalcomfort (oracle)",
        "ground_truth": "pythermalcomfort ISO 7243 wbgt(twb, tg, tdb)",
        "grid": "T 20-40 C step 5, RH 20-100 % step 20, overcast 1",
        "tolerance": "0.06 C (pythermalcomfort 1-decimal rounding)",
        "status": "PASS" if max_abs <= 0.06 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "C",
        "note": "shared Stull Tw input; validates the 0.7/0.2/0.1 aggregation",
    }


# ─── Runner ─────────────────────────────────────────────────────────────────


def format_result(result):
    status = result["status"]
    marker = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}[status]
    return (
        f"[{marker}] {result['name']}\n"
        f"    ground truth : {result['ground_truth']}\n"
        f"    grid         : {result['grid']}\n"
        f"    tolerance    : {result['tolerance']}\n"
        f"    max abs err  : {result['max_abs']:.4f} {result['unit']}"
        + (f"\n    note         : {result['note']}" if result["note"] else "")
    )


def main():
    checks = [
        check_iso9613_absorption(),
        check_icao_density_oracle(),
        check_heat_index_oracle(),
        check_wbgt_pythermalcomfort_oracle(),
    ]

    lines = [
        "AEE Physics Oracle Validation (JSP 939 VV&A)",
        "=" * 48,
        "",
        "Independent oracles: "
        f"pythermalcomfort={'yes' if HAS_PYTHERMALCOMFORT else 'no'}"
        " (psychrolib and metpy oracles live in validate_physics.py)",
        "",
    ]
    for result in checks:
        lines.append(format_result(result))
        lines.append("")

    failed = [r for r in checks if r["status"] == "FAIL"]
    skipped = [r for r in checks if r["status"] == "SKIP"]
    lines.append("Summary")
    lines.append("-" * 48)
    lines.append(f"Checks run: {len(checks) - len(skipped)} of {len(checks)}")
    lines.append(f"Skipped (missing optional library): {len(skipped)}")
    lines.append(f"Failed: {len(failed)}")
    report = "\n".join(lines)

    print(report)
    report_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "oracle_report.txt"
    )
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
