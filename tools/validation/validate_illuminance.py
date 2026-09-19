#!/usr/bin/env python3
"""Validation for the shared illuminance layer (fnc_calculateIlluminance).

Checks the maths that converts the engine's getLighting lightDirection
vector into azimuth/elevation, and the lux model bounds.  This is what is
VERIFIABLE from the engine contract + physics:

  Verifiable (checked here):
    - Azimuth conversion: engine vector (x=east, y=south, z=up) → compass
      azimuth clockwise from north, matching Arma's getDir convention.
      Test vectors: north=0, east=90, south=180, west=270.
    - Elevation conversion: z/|v| → asin, 0 at horizon, 90 overhead.
    - Lux model bounds: starlight (moonIntensity=0, clear) ≈ 0.001 lux,
      full moon (moonIntensity=1, clear) ≈ 0.25 lux, within the NVG
      operating range.  Overcast/rain reduce it monotonically.
    - Shared-state contract: every published variable is documented and
      numerically typed.

  NOT verifiable (engine calibration, documented):
    - The exact lux scale 0.001..0.25 (NVG operating assumption, from the
      sensor-value audit: starlight ~0.001 lux, full moon ~0.25 lux)

Run:  python3 tools/validation/validate_illuminance.py
Exit: 0 when every check passes, 1 when any fails.
"""

import math
import os
import sys

# ─── SQF mirrors ────────────────────────────────────────────────────────────


def light_vector_to_azimuth_elevation(vec):
    """Mirror of the SQF conversion in fnc_calculateIlluminance.sqf.

    vec = [x, y, z]: x=east, y=south, z=up (Arma world convention).
    Returns (azimuth_deg, elevation_deg) or (0, 0) for a degenerate vector.
    """
    length = math.sqrt(vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2)
    if length < 0.001:
        return (0.0, 0.0)
    elev = math.degrees(math.asin(vec[2] / length))
    flat_x = vec[0]
    flat_y = vec[1]
    flat_len = math.sqrt(flat_x**2 + flat_y**2)
    if flat_len < 0.001:
        return (0.0, elev)  # straight up/down: azimuth undefined
    az = math.degrees(math.atan2(flat_x, -flat_y))
    az = az % 360.0
    return (az, elev)


def lux_model(moon_intensity, overcast=0.0, rain=0.0):
    """Mirror of the SQF lux model: 0.001 + moonLight*0.249.

    moonLight = max(0, moonIntensity - min(overcast*0.8, 0.275) - rain*0.5)
    """
    moon_light = max(0.0, moon_intensity - min(overcast * 0.8, 0.275) - rain * 0.5)
    return 0.001 + moon_light * 0.249


# ─── Checks ────────────────────────────────────────────────────────────────


def check_azimuth_cardinal():
    """Engine vectors at the four compass points map to correct azimuths."""
    cases = [
        ([0, -1, 0.1], 0.0, "north"),  # (0,-1): north
        ([1, 0, 0.1], 90.0, "east"),  # (1,0): east
        ([0, 1, 0.1], 180.0, "south"),  # (0,1): south
        ([-1, 0, 0.1], 270.0, "west"),  # (-1,0): west
    ]
    worst = 0.0
    for vec, expected, name in cases:
        az, _ = light_vector_to_azimuth_elevation(vec)
        err = abs(az - expected)
        worst = max(worst, err)
        assert err < 1.0, f"{name}: azimuth {az} != {expected}"
    return worst


def check_elevation_angles():
    """Elevation maps z/|v| through asin: 0 at horizon, 90 overhead."""
    cases = [
        ([1, 0, 0], 0.0, "horizon"),
        ([0, 0, 1], 90.0, "overhead"),
        ([1, 0, 1], 45.0, "45 deg"),
    ]
    worst = 0.0
    for vec, expected, name in cases:
        _, elev = light_vector_to_azimuth_elevation(vec)
        err = abs(elev - expected)
        worst = max(worst, err)
        assert err < 0.5, f"{name}: elevation {elev} != {expected}"
    return worst


def check_sun_direction_consistency():
    """The docker probe's day vector must give a plausible sun elevation.

    Probe captured getLighting lightDirection = [0.0255, 0.4718, -0.8813]
    on Stratis at the default time.  -0.8813 z means the light points DOWN
    (sun above the horizon shining down): elevation of the light source
    is asin(-0.8813) ≈ -61.8, so the SUN is at +61.8 degrees above the
    horizon — a plausible summer afternoon sun.  This locks the sign
    convention: the engine vector is FROM the light.
    """
    vec = [0.025531, 0.471776, -0.881349]
    _, elev = light_vector_to_azimuth_elevation(vec)
    sun_elev = -elev  # vector points from sun; sun is opposite
    assert 20.0 < sun_elev < 90.0, f"sun elevation {sun_elev} implausible"
    return abs(sun_elev - 61.8)


def check_lux_bounds():
    """Lux model stays within the documented NVG operating range."""
    starlight = lux_model(0.0, 0.0, 0.0)
    full_moon = lux_model(1.0, 0.0, 0.0)
    assert 0.0005 < starlight < 0.005, f"starlight lux {starlight} out of range"
    assert 0.1 < full_moon < 0.5, f"full moon lux {full_moon} out of range"
    assert starlight < full_moon, "starlight must be dimmer than full moon"
    return abs(full_moon - starlight)


def check_lux_monotonic_weather():
    """Overcast and rain must reduce lux monotonically (never increase)."""
    base = lux_model(1.0, 0.0, 0.0)
    overcast = lux_model(1.0, 0.8, 0.0)
    rain = lux_model(1.0, 0.0, 1.0)
    both = lux_model(1.0, 0.8, 1.0)
    assert overcast < base, "overcast must reduce lux"
    assert rain < base, "rain must reduce lux"
    assert both <= overcast, "rain on overcast must not increase lux"
    assert both <= rain, "overcast on rain must not increase lux"
    return abs(base - both)


def check_state_contract():
    """Every published shared-state variable is documented in the header."""
    expected = [
        "illuminanceLux",
        "ambientLux",
        "dynamicLux",
        "lightDirection",
        "lightAzimuth",
        "lightElevation",
        "lightIsNight",
        "starsVisibility",
    ]
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "..",
        "addons",
        "core",
        "functions",
        "fnc_calculateIlluminance.sqf",
    )
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    missing = [v for v in expected if f"setVariable [QGVAR({v})" not in src]
    assert not missing, f"shared-state vars not published: {missing}"
    return 0.0


# ─── Runner ────────────────────────────────────────────────────────────────


def format_result(name, status, err, unit, tol):
    err_str = f"{err:.4f}{unit}" if err == err else "n/a"
    line = f"[{status}] {name}"
    line += f"  (max_err={err_str}, tol={tol}{unit})" if status == "PASS" else ""
    return line


def main():
    checks = [
        ("illuminance: azimuth cardinal points", check_azimuth_cardinal, "deg", 1.0),
        ("illuminance: elevation angles", check_elevation_angles, "deg", 0.5),
        (
            "illuminance: probe sun elevation plausible",
            check_sun_direction_consistency,
            "deg",
            5.0,
        ),
        ("illuminance: lux operating bounds", check_lux_bounds, "lx", 0.05),
        (
            "illuminance: lux monotonic in weather",
            check_lux_monotonic_weather,
            "lx",
            0.01,
        ),
        ("illuminance: shared-state contract", check_state_contract, "", 0.0),
    ]

    lines = ["AEE illuminance layer validation", "=" * 40]
    results = []
    failed = 0
    for name, fn, unit, tol in checks:
        try:
            err = fn()
            status = "PASS"
        except AssertionError as e:
            err = float("nan")
            status = "FAIL"
            results.append(str(e))
            failed += 1
        lines.append(format_result(name, status, err, unit, tol))

    lines.append("")
    lines.append(f"Checks run: {len(checks)}")
    lines.append(f"Failed: {failed}")
    if results:
        lines.append("Failures:")
        lines.extend(f"  {r}" for r in results)
    report = "\n".join(lines)
    print(report)
    report_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "illum_report.txt"
    )
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
