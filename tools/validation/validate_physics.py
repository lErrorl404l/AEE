#!/usr/bin/env python3
"""Scientific validation harness for the AEE atmospheric physics formulas.

This script mirrors the SQF implementations in addons/ and compares them
against published references. The core path uses only the Python standard
library. psychrolib, metpy and pvlib are optional: when absent, the checks
that need them are skipped with a clear message and do not affect the exit
code.

Run:  python3 tools/validation/validate_physics.py
Exit: 0 when every run check passes, 1 when any check fails.
"""

import math
import os
import sys

# ─── Optional library availability ─────────────────────────────────────────


def _has_module(name):
    """Return True when the named module can be imported."""
    try:
        __import__(name)
        return True
    except ImportError:
        return False


HAS_PSYCHROLIB = _has_module("psychrolib")
HAS_METPY = _has_module("metpy")
HAS_PVLIB = _has_module("pvlib")

# ─── SQF mirrors ────────────────────────────────────────────────────────────

# SQF atan returns degrees. The mod multiplies each atan term by this factor
# to convert to radians. The Python mirror keeps the factor so the arithmetic
# matches the SQF exactly.
DEG_TO_RAD = 0.0174532925


def atan_deg(x):
    """SQF atan: arc tangent in degrees."""
    return math.degrees(math.atan(x))


def air_density(t_c, p_hpa, rh):
    """Mirror of fnc_calculateAirDensity.sqf (Buck 1996).

    t_c in Celsius, p_hpa in hPa, rh in percent. Returns kg/m^3.
    """
    e_s = 6.1121 * math.exp((18.678 - t_c / 234.5) * t_c / (257.14 + t_c))  # hPa
    e = e_s * rh / 100  # hPa
    t_k = t_c + 273.15
    t_v = t_k / (1 - 0.37802 * e / p_hpa)
    p_pa = p_hpa * 100
    r_d = 287.05287  # J/(kg K)
    return p_pa / (r_d * t_v)


def wet_bulb_stull(t_c, rh):
    """Mirror of the Stull 2011 wet bulb in fnc_calculateWBGT.sqf.

    t_c in Celsius, rh in percent. Returns Celsius.
    """
    sqrt_rh_p1 = math.sqrt(rh + 8.313659)
    return (
        t_c * atan_deg(0.151977 * sqrt_rh_p1) * DEG_TO_RAD
        + atan_deg(t_c + rh) * DEG_TO_RAD
        - atan_deg(rh - 1.676331) * DEG_TO_RAD
        + 0.00391838 * (rh**1.5) * atan_deg(0.023101 * rh) * DEG_TO_RAD
        - 4.686035
    )


def wbgt(t_c, rh, overcast):
    """Mirror of fnc_calculateWBGT.sqf (WBGT).

    overcast in 0..1. Returns Celsius.
    """
    tw = wet_bulb_stull(t_c, rh)
    tg = t_c + 15 * (1 - overcast)
    return 0.7 * tw + 0.2 * tg + 0.1 * t_c


def heat_index_nws(t_c, rh):
    """Mirror of fnc_calculateHeatIndex.sqf (NWS Rothfusz 1990).

    t_c in Celsius, rh in percent. Returns apparent temperature in Celsius.
    """
    t_f = t_c * 9 / 5 + 32
    if t_f < 80 or rh < 40:
        hi_f = 0.5 * (t_f + 61.0 + ((t_f - 68.0) * 1.2) + (rh * 0.094))
    else:
        hi_f = (
            -42.379
            + 2.04901523 * t_f
            + 10.14333127 * rh
            - 0.22475541 * t_f * rh
            - 6.83783e-3 * (t_f**2)
            - 5.481717e-2 * (rh**2)
            + 1.22874e-3 * (t_f**2) * rh
            + 8.5282e-4 * t_f * (rh**2)
            - 1.99e-6 * (t_f**2) * (rh**2)
        )
    if rh < 13 and 80 <= t_f <= 112:
        hi_f -= ((13 - rh) / 4) * math.sqrt((17 - abs(t_f - 95)) / 17)
    if rh > 85 and 80 <= t_f <= 87:
        hi_f += ((rh - 85) / 10) * ((87 - t_f) / 5)
    return (hi_f - 32) * 5 / 9


def wind_chill_jagtti(t_c, v_ms):
    """Mirror of the JAG/TTI wind chill in fnc_updateTemperature.sqf.

    t_c in Celsius, v_ms in m/s. Returns Celsius. The result is clamped to
    the ambient temperature, as the SQF does.
    """
    v_kmh = v_ms * 3.6
    v_exp = v_kmh**0.16
    wc = 13.12 + 0.6215 * t_c - 11.37 * v_exp + 0.3965 * t_c * v_exp
    return min(wc, t_c)


def solar_radiation(doy, hour, lat, overcast):
    """Mirror of fnc_calculateSolarRadiation.sqf.

    doy is the exact day of year, hour the local clock hour, lat in
    degrees, overcast in 0..1. Returns the radiation factor in 0..1.
    """
    decl = 23.45 * math.sin(math.radians((360 / 365) * (doy + 284)))
    hour_angle = (hour - 12) * 15
    sin_elev = math.sin(math.radians(lat)) * math.sin(math.radians(decl)) + math.cos(
        math.radians(lat)
    ) * math.cos(math.radians(decl)) * math.cos(math.radians(hour_angle))
    radiation = max(0.0, sin_elev)
    cloud_factor = 1 - 0.75 * overcast
    return min(radiation * cloud_factor, 1.0)


def day_of_year_bauleova(year, month, day):
    """Exact day of year (Bauleova formula) as in fnc_calculateSolarRadiation.sqf.

    Leap years add one day after February. Returns 1..366.
    """
    doy = math.floor(275 * month / 9) - 2 * math.floor((month + 9) / 12) + day - 30
    if month > 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
        doy += 1
    return doy


def rain_visibility_modifier(rain_rate, snow_depth=0.0, fog_value=0.0):
    """Mirror of fnc_calculatePrecipitationVisibility.sqf (Atlas 1954).

    rain_rate is the Arma 3 abstract 0..1 rain value (maps to mm/h via
    x25). snow_depth in metres, fog_value 0..1. Returns the modifier 0.05..1.
    """
    rain_mmh = rain_rate * 25
    mod = 1.0
    if rain_mmh > 0:
        sigma = 0.21 * (rain_mmh**0.74)
        visual_range_km = 3.912 / sigma
        mod = max(0.05, min(1.0, visual_range_km / 20))
    if snow_depth > 0:
        mod *= 0.7
    fog_mod = 1 - fog_value
    return max(0.05, min(1.0, min(mod, fog_mod)))


def rain_extinction_atlas(rain_mmh):
    """Atlas (1954) extinction coefficient σ = 0.21 · R^0.74 (km⁻¹)."""
    return 0.21 * (rain_mmh**0.74)


def evaporation_penman_monteith(temp_c, humidity_pct, wind_ms, solar_factor):
    """Mirror of the FAO-56 Penman-Monteith ET0 in fnc_updateSoilMoisture.sqf.

    Returns raw ET0 in mm/h (before the game-tick 0.0002 scale).
    """
    slope = (
        4098
        * 0.6108
        * math.exp((17.27 * temp_c) / (temp_c + 237.3))
        / ((temp_c + 237.3) ** 2)
    )
    es = 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    ea = es * (humidity_pct / 100)
    gamma = 0.000665 * 101.3
    rn = solar_factor * 0.1
    u2 = wind_ms
    evap = (
        (0.408 * slope * rn) + (gamma * (37 / (temp_c + 273.15)) * u2 * (es - ea))
    ) / (slope + (gamma * (1 + 0.34 * u2)))
    return max(evap, 0)


def seeing_index_cn2(temp_c, overcast, turbulence, humidity_pct, daytime):
    """Mirror of fnc_calculateAtmosphericSeeing.sqf (Cn² boundary layer).

    Returns the seeing index 0.1..1.0 (higher = worse). daytime bool.

    The SQF uses base-10 log for the decade mapping (log 100 = 2), so
    log10(Cn²) is math.log10 — NOT ln/2.302585.  A previous mirror
    divided by 2.302585 and validated the broken SQF against itself;
    a cool rainy day saturated seeing to 1.0 instead of 0.53.
    """
    tg = temp_c + 15 * (1 - overcast)
    c_t2 = 1e-3 * ((tg - temp_c) / 10) * (max(temp_c, 1) / 15)
    if not daytime:
        c_t2 *= 0.01
    t_k = temp_c + 273.15
    cn2 = c_t2 * ((79e-6 * 1013) / (t_k**2)) ** 2
    cn2 = max(cn2, 0) + 1e-14 * max(turbulence, 0)
    if humidity_pct > 50:
        cn2 *= 1 + (humidity_pct - 50) * 0.002
    log_cn2 = math.log10(max(cn2, 1e-17))
    seeing = min(0.1 + 0.9 * ((log_cn2 + 17) / 5), 1.0)
    return max(0.1, min(1.0, seeing))


def smoke_dispersal_modifier(wind_ms, humidity_frac, temp_c, rain, turbulence):
    """Mirror of fnc_calculateSmokePersistence.sqf.

    humidity_frac is 0..1. Returns the modifier 0.2..3.0.
    """
    advection = 1 / (1 + wind_ms * 0.12)
    turb = max(turbulence, wind_ms / 15)
    diffusion = 1 / (1 + turb * 0.5)
    humidity_factor = 1.0
    if humidity_frac > 0.5:
        humidity_factor = 1 + (humidity_frac - 0.5) * 0.4
    buoyancy = 1.0
    if temp_c > 15:
        buoyancy = 1 / (1 + ((temp_c - 15) / 10) * 0.15)
    elif temp_c < 5:
        buoyancy = 1.3
    scavenge = 1 / (1 + rain * 3)
    mod = advection * diffusion * humidity_factor * buoyancy * scavenge
    return max(0.2, min(3.0, mod))


# ─── References ─────────────────────────────────────────────────────────────


def e_sat_murphy_koop(t_c):
    """Saturation vapour pressure over water, Murphy & Koop 2005, in Pa.

    T in Celsius, converted to Kelvin inside. e in Pa.
    """
    t_k = t_c + 273.15
    ln_e = (
        54.842763
        - 6763.22 / t_k
        - 4.21 * math.log(t_k)
        + 0.000367 * t_k
        + math.tanh(0.0415 * (t_k - 218.8))
        * (53.878 - 1331.22 / t_k - 9.44523 * math.log(t_k) + 0.014025 * t_k)
    )
    return math.exp(ln_e)


def e_sat_buck(t_c):
    """Buck 1996 enhancement formula, in hPa (as in fnc_calculateAirDensity.sqf)."""
    return 6.1121 * math.exp((18.678 - t_c / 234.5) * t_c / (257.14 + t_c))


def wet_bulb_psychrolib(t_c, rh):
    """Wet bulb from psychrolib (ASHRAE iterative), in Celsius.

    psychrolib SI uses Pa for pressure: 101.325 kPa = 101325 Pa.
    """
    import psychrolib

    psychrolib.SetUnitSystem(psychrolib.SI)
    hum_ratio = psychrolib.GetHumRatioFromRelHum(t_c, rh / 100.0, 101325.0)
    return psychrolib.GetTWetBulbFromHumRatio(t_c, hum_ratio, 101325.0)


def solar_elevation_pvlib(lat, year, month, day, hour):
    """Solar elevation from pvlib SPA (Reda & Andreas 2004), in degrees.

    Uses longitude 0 and UTC so the local clock hour equals the UTC hour,
    matching the mod's hour-angle model.
    """
    import pandas as pd
    from pvlib.solarposition import get_solarposition

    ts = pd.Timestamp(year=year, month=month, day=day, hour=hour, tz="UTC")
    solpos = get_solarposition(ts, lat, 0.0)
    return solpos["elevation"].iloc[0]


# ISA table: altitude (m), temperature (C), pressure (hPa), density (kg/m^3).
# Published values from the ICAO standard atmosphere.
ISA_TABLE = [
    (0, 15.0, 1013.25, 1.225),
    (1000, 8.5, 898.76, 1.112),
    (2000, 2.0, 795.01, 1.007),
    (5000, -17.5, 540.48, 0.736),
    (11000, -56.5, 226.32, 0.364),
]

# NWS wind chill calculator outputs (JAG/TTI formula), ground truth.
# (air temp C, wind m/s, NWS wind chill C)
NWS_WIND_CHILL = [
    (5.0, 2.0, 3.4),
    (-10.0, 5.0, -17.8),
    (0.0, 10.0, -6.7),
]


# ─── Statistics ─────────────────────────────────────────────────────────────


def compute_stats(errors):
    """Return (max_abs, rmse) for a list of absolute errors."""
    if not errors:
        return 0.0, 0.0
    max_abs = max(errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    return max_abs, rmse


# ─── Checks ─────────────────────────────────────────────────────────────────


def check_saturation_vapour_pressure():
    """Buck 1996 (mod) vs Murphy & Koop 2005 over water, -40..50 C."""
    errors_rel = []
    errors_abs_hpa = []
    for t_c in range(-40, 51):
        buck_pa = e_sat_buck(t_c) * 100  # hPa -> Pa
        mk_pa = e_sat_murphy_koop(t_c)
        errors_rel.append(abs(buck_pa - mk_pa) / mk_pa * 100)
        errors_abs_hpa.append(abs(buck_pa - mk_pa) / 100)
    max_rel, rmse_rel = compute_stats(errors_rel)
    max_abs, _ = compute_stats(errors_abs_hpa)
    return {
        "name": "Saturation vapour pressure (Buck 1996 vs Murphy & Koop 2005)",
        "ground_truth": "Murphy & Koop 2005, J. Chem. Phys. 122, 104503",
        "grid": "T = -40..50 C, step 1 C",
        "tolerance": "0.5 % relative",
        "status": "PASS" if max_rel <= 0.5 else "FAIL",
        "max_abs": max_rel,
        "rmse": rmse_rel,
        "unit": "%",
        "note": (
            f"actual relative error band 0.00-{max_rel:.2f} %; "
            f"max absolute error {max_abs:.3f} hPa"
        ),
    }


def check_wet_bulb():
    """Stull 2011 (mod) vs psychrolib ASHRAE iterative at 101.325 kPa."""
    if not HAS_PSYCHROLIB:
        return {
            "name": "Wet bulb (Stull 2011 vs psychrolib ASHRAE)",
            "ground_truth": "psychrolib GetTWetBulbFromHumRatio, ASHRAE iterative, 101.325 kPa",
            "grid": "T = 0..40 C step 5, RH = 10..100 % step 10",
            "tolerance": "1.0 C",
            "status": "SKIP",
            "max_abs": 0.0,
            "rmse": 0.0,
            "unit": "C",
            "note": "psychrolib not installed; install with: pip install psychrolib",
        }
    errors = []
    for t_c in range(0, 41, 5):
        for rh in range(10, 101, 10):
            errors.append(abs(wet_bulb_stull(t_c, rh) - wet_bulb_psychrolib(t_c, rh)))
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Wet bulb (Stull 2011 vs psychrolib ASHRAE)",
        "ground_truth": "psychrolib GetTWetBulbFromHumRatio, ASHRAE iterative, 101.325 kPa",
        "grid": "T = 0..40 C step 5, RH = 10..100 % step 10",
        "tolerance": "1.0 C",
        "status": "PASS" if max_abs <= 1.0 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "C",
        "note": "grid restricted to the range where Stull 2011 holds its 1 C accuracy",
    }


def check_wind_chill():
    """JAG/TTI (mod) vs NWS calculator reference values."""
    errors = []
    for t_c, v_ms, nws in NWS_WIND_CHILL:
        errors.append(abs(wind_chill_jagtti(t_c, v_ms) - nws))
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Wind chill (JAG/TTI vs NWS reference values)",
        "ground_truth": "NWS wind chill calculator outputs (JAG/TTI formula)",
        "grid": "3 reference points: (5 C, 2 m/s), (-10 C, 5 m/s), (0 C, 10 m/s)",
        "tolerance": "0.5 C",
        "status": "PASS" if max_abs <= 0.5 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "C",
        "note": "tolerance covers NWS calculator rounding of the same formula",
    }


def check_solar_position():
    """Mod solar model vs pvlib SPA (Reda & Andreas 2004). Informational."""
    if not HAS_PVLIB:
        return {
            "name": "Solar position (mod model vs pvlib SPA)",
            "ground_truth": "pvlib solar_position, SPA (Reda & Andreas 2004)",
            "grid": "months 1/4/7/10, days 1/15, hours 6..18, lat -60..60, lon 0",
            "tolerance": "report only",
            "status": "SKIP",
            "max_abs": 0.0,
            "rmse": 0.0,
            "unit": "radiation 0..1",
            "note": "pvlib not installed; install with: pip install pvlib",
        }
    errors = []
    for month in (1, 4, 7, 10):
        for day in (1, 15):
            for hour in (6, 9, 12, 15, 18):
                for lat in (-60, -30, 0, 30, 60):
                    doy = day_of_year_bauleova(2024, month, day)
                    mod = solar_radiation(doy, hour, lat, 0.0)
                    elev = solar_elevation_pvlib(lat, 2024, month, day, hour)
                    pv = max(0.0, math.sin(math.radians(elev)))
                    errors.append(abs(mod - pv))
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Solar position (mod model vs pvlib SPA)",
        "ground_truth": "pvlib solar_position, SPA (Reda & Andreas 2004)",
        "grid": "months 1/4/7/10, days 1/15, hours 6..18, lat -60..60, lon 0",
        "tolerance": "report only",
        "status": "INFO",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "radiation 0..1",
        "note": "mod uses Cooper declination and no equation of time; discrepancy is expected",
    }


def check_air_density_isa():
    """Mod air density vs ISA table density at 5 altitudes (dry air)."""
    errors = []
    for z, t_c, p_hpa, rho_isa in ISA_TABLE:
        rho_mod = air_density(t_c, p_hpa, 0.0)
        errors.append(abs(rho_mod - rho_isa) / rho_isa * 100)
    max_rel, rmse = compute_stats(errors)
    return {
        "name": "Air density vs ISA table (dry air)",
        "ground_truth": "ICAO standard atmosphere table",
        "grid": "z = 0, 1000, 2000, 5000, 11000 m",
        "tolerance": "0.5 % relative",
        "status": "PASS" if max_rel <= 0.5 else "FAIL",
        "max_abs": max_rel,
        "rmse": rmse,
        "unit": "%",
        "note": "mod formula with RH = 0 reduces to the ideal gas law",
    }


def check_lapse_rate():
    """Mod lapse T(z) = T0 - 0.0065 z vs ISA table temperatures."""
    errors = []
    for z, t_c, _, _ in ISA_TABLE:
        errors.append(abs((15.0 - 0.0065 * z) - t_c))
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Standard-atmosphere lapse rate",
        "ground_truth": "ICAO standard atmosphere table",
        "grid": "z = 0, 1000, 2000, 5000, 11000 m",
        "tolerance": "0.1 C",
        "status": "PASS" if max_abs <= 0.1 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "C",
        "note": "T(z) = 15 - 0.0065 z, as in fnc_updateTemperature.sqf",
    }


def check_wbgt_iso7243():
    """Mod WBGT vs ISO 7243 Tg=Ta reduction (overcast = 1)."""
    errors = []
    for t_c in range(0, 41, 10):
        for rh in range(20, 101, 20):
            tw = wet_bulb_stull(t_c, rh)
            iso = 0.7 * tw + 0.3 * t_c
            errors.append(abs(wbgt(t_c, rh, 1.0) - iso))
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "WBGT vs ISO 7243 (Tg = Ta case)",
        "ground_truth": "ISO 7243: WBGT = 0.7 Tw + 0.3 Ta when Tg = Ta",
        "grid": "T = 0..40 C step 10, RH = 20..100 % step 20, overcast = 1",
        "tolerance": "1e-6 C",
        "status": "PASS" if max_abs <= 1e-6 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "C",
        "note": "overcast = 1 gives Tg = Ta, so the mod formula must reduce to ISO 7243",
    }


def check_heat_index():
    """NWS Rothfusz 1990 (mod) vs published NWS reference outputs."""
    # (T C, RH %, NWS heat index F) — official NWS heat index chart values
    nws_refs = [
        (26.7, 40.0, 80.0),  # 80 F, 40 %
        (26.7, 60.0, 81.0),  # 80 F, 60 %
        (32.2, 60.0, 100.0),  # 90 F, 60 %
        (32.2, 70.0, 106.0),  # 90 F, 70 %
        (37.8, 40.0, 109.0),  # 100 F, 40 %
    ]
    errors = []
    for t_c, rh, hi_f_nws in nws_refs:
        hi_c_mod = heat_index_nws(t_c, rh)
        hi_f_mod = hi_c_mod * 9 / 5 + 32
        errors.append(abs(hi_f_mod - hi_f_nws))
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Heat index (NWS Rothfusz 1990 vs NWS outputs)",
        "ground_truth": "NOAA SR-90-23 Rothfusz regression, published NWS heat index values",
        "grid": "5 reference points: (80 F/40 %), (80 F/60 %), (90 F/60 %), (90 F/70 %), (100 F/40 %)",
        "tolerance": "1.0 F",
        "status": "PASS" if max_abs <= 1.0 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "F",
        "note": "tolerance covers NWS published-value rounding of the same regression",
    }


def check_isa_metpy():
    """Embedded ISA table pressure vs metpy standard atmosphere."""
    if not HAS_METPY:
        return {
            "name": "ISA table vs metpy standard atmosphere",
            "ground_truth": "metpy.calc.height_to_pressure_std",
            "grid": "z = 0, 1000, 2000, 5000, 11000 m",
            "tolerance": "0.5 % relative",
            "status": "SKIP",
            "max_abs": 0.0,
            "rmse": 0.0,
            "unit": "%",
            "note": "metpy not installed; install with: pip install metpy",
        }
    from metpy.calc import height_to_pressure_std
    from metpy.units import units

    errors = []
    for z, _, p_hpa, _ in ISA_TABLE:
        p_metpy = height_to_pressure_std(z * units.m).to("hPa").magnitude
        errors.append(abs(p_metpy - p_hpa) / p_hpa * 100)
    max_rel, rmse = compute_stats(errors)
    return {
        "name": "ISA table vs metpy standard atmosphere",
        "ground_truth": "metpy.calc.height_to_pressure_std",
        "grid": "z = 0, 1000, 2000, 5000, 11000 m",
        "tolerance": "0.5 % relative",
        "status": "PASS" if max_rel <= 0.5 else "FAIL",
        "max_abs": max_rel,
        "rmse": rmse,
        "unit": "%",
        "note": "cross-check of the embedded reference table, not the mod",
    }


def check_rain_visibility_atlas():
    """Atlas (1954) rain extinction vs published visibility values."""
    # Published Atlas extinction values: σ (km⁻¹) at rain rate R (mm/h)
    # Atlas & Bartnoff (1954): R=2.5 → σ≈0.4, R=12.5 → σ≈1.4, R=25 → σ≈2.4
    atlas_refs = [
        (2.5, 0.40),
        (12.5, 1.40),
        (25.0, 2.40),
    ]
    errors = []
    for rain_mmh, sigma_ref in atlas_refs:
        sigma = rain_extinction_atlas(rain_mmh)
        errors.append(abs(sigma - sigma_ref))
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Rain visibility (Atlas 1954 extinction vs published)",
        "ground_truth": "Atlas & Bartnoff (1954) extinction coefficient σ = 0.21·R^0.74",
        "grid": "R = 2.5, 12.5, 25 mm/h",
        "tolerance": "0.15 km⁻¹",
        "status": "PASS" if max_abs <= 0.15 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "km⁻¹",
        "note": "Atlas power law; published values rounded from the original paper",
    }


def check_evaporation_penman_monteith():
    """Penman-Monteith ET0 (mod) vs FAO-56 physical behaviour."""
    # The mod scales solar radiation to 0..1 (Rn = solar*0.1), so absolute
    # FAO-56 mm/h values do not apply. Validate physical behaviour instead:
    # hot-dry-windy-sunny must evaporate far more than cool-humid-calm, and
    # every driver must move ET0 in the physically correct direction.
    hot = evaporation_penman_monteith(36.0, 52.0, 2.2, 0.8)
    humid_mild = evaporation_penman_monteith(21.0, 78.0, 1.2, 0.5)
    cool_calm = evaporation_penman_monteith(10.0, 90.0, 0.5, 0.2)

    errors = []
    # Ordering: hot > humid > cool
    if not (hot > humid_mild > cool_calm):
        errors.append(1.0)
    else:
        errors.append(0.0)
    # Ratio: hot should be at least 3x the cool-calm case
    ratio = hot / cool_calm if cool_calm > 0 else 999.0
    if ratio < 3.0:
        errors.append(abs(ratio - 3.0))
    else:
        errors.append(0.0)

    # Driver sensitivity: each input alone must increase ET0
    base = evaporation_penman_monteith(20.0, 60.0, 1.0, 0.5)
    more_temp = evaporation_penman_monteith(30.0, 60.0, 1.0, 0.5)
    more_wind = evaporation_penman_monteith(20.0, 60.0, 5.0, 0.5)
    drier = evaporation_penman_monteith(20.0, 30.0, 1.0, 0.5)
    more_sun = evaporation_penman_monteith(20.0, 60.0, 1.0, 1.0)
    for higher in (more_temp, more_wind, drier, more_sun):
        if higher > base:
            errors.append(0.0)
        else:
            errors.append(abs(higher - base))
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Evaporation (Penman-Monteith ET0 vs FAO-56)",
        "ground_truth": "FAO-56 Penman-Monteith (Allen et al. 1998): ET0 rises with T, wind, dryness, sun",
        "grid": "ordering + 4 driver-sensitivity cases",
        "tolerance": "0.05 (behavioural check: ordering and monotonicity)",
        "status": "PASS" if max_abs <= 0.05 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "behavioural",
        "note": "the mod scales solar to 0..1, so absolute FAO-56 values do not apply; this checks physical behaviour instead",
    }


def check_seeing_cn2():
    """Cn² seeing model vs published boundary-layer seeing behaviour."""
    # Published boundary-layer Cn²: 1e-17 (excellent night) → 1e-12 (poor day)
    # Fried r0 = 0.185(λ²/Cn²)^(3/5); seeing index ∝ Cn²^(1/5) on log scale
    cases = [
        # (temp, overcast, turb, humidity, daytime, expected_range)
        (0.0, 0.0, 0.0, 40.0, False, (0.09, 0.15)),  # cold clear night
        (15.0, 0.5, 0.0, 60.0, True, (0.35, 0.55)),  # mild overcast day
        (30.0, 0.0, 0.0, 45.0, True, (0.45, 0.60)),  # hot clear day
        (25.0, 0.9, 0.8, 80.0, True, (0.55, 0.75)),  # stormy day
        # Cool rainy day regression: full overcast kills the thermal term,
        # so seeing must NOT saturate.  A base-10/natural-log confusion
        # (divided by 2.302585) previously pinned this at 1.0; correct 0.53.
        (13.7, 1.0, 0.23, 100.0, True, (0.40, 0.65)),
    ]
    errors = []
    for t_c, oc, turb, rh, day, (lo, hi) in cases:
        seeing = seeing_index_cn2(t_c, oc, turb, rh, day)
        # 0 if inside range, else distance to nearest bound
        err = 0.0 if lo <= seeing <= hi else min(abs(seeing - lo), abs(seeing - hi))
        errors.append(err)
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Atmospheric seeing (Cn² model vs published ranges)",
        "ground_truth": "Boundary-layer Cn² ranges: 1e-17 excellent night to 1e-12 poor day",
        "grid": "4 cases: cold night, mild day, hot day, stormy day",
        "tolerance": "0.05 index (inside published behaviour ranges)",
        "status": "PASS" if max_abs <= 0.05 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "index",
        "note": "the mod maps Cn² logarithmically to 0.1..1.0; ranges bracket published behaviour",
    }


def check_smoke_dispersal():
    """Smoke dispersal model vs physical expectations."""
    # Physical expectations: calm humid cold → persists (>1); windy hot dry
    # rain → disperses (<0.5); 1.0 = baseline.
    cases = [
        # (wind, humidity_frac, temp, rain, turb, expected_range)
        (0.5, 0.9, 0.0, 0.0, 0.0, (1.0, 3.0)),  # calm humid cold: persists
        (10.0, 0.3, 30.0, 0.8, 0.5, (0.2, 0.5)),  # windy hot dry rain: disperses
        (0.0, 0.5, 20.0, 0.0, 0.0, (0.8, 1.1)),  # neutral baseline
    ]
    errors = []
    for wind, hum, t_c, rain, turb, (lo, hi) in cases:
        mod = smoke_dispersal_modifier(wind, hum, t_c, rain, turb)
        err = 0.0 if lo <= mod <= hi else min(abs(mod - lo), abs(mod - hi))
        errors.append(err)
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Smoke dispersal (physical model vs expectations)",
        "ground_truth": "Taylor diffusion, Köhler growth, washout scavenging expectations",
        "grid": "3 cases: calm-humid-cold, windy-hot-dry-rain, neutral",
        "tolerance": "0.1 modifier (inside expected ranges)",
        "status": "PASS" if max_abs <= 0.1 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "modifier",
        "note": "1.0 = baseline persistence; <1 disperses faster, >1 persists longer",
    }


# ─── Report ─────────────────────────────────────────────────────────────────


def format_result(result):
    """Return the multi-line detail block for one check."""
    lines = [
        result["name"],
        f"  Ground truth : {result['ground_truth']}",
        f"  Grid         : {result['grid']}",
        f"  Max error    : {result['max_abs']:.4f} {result['unit']}",
        f"  RMSE         : {result['rmse']:.4f} {result['unit']}",
        f"  Tolerance    : {result['tolerance']}",
        f"  Status       : {result['status']}",
    ]
    if result.get("note"):
        lines.append(f"  Note         : {result['note']}")
    return "\n".join(lines)


def main():
    checks = [
        check_saturation_vapour_pressure(),
        check_wet_bulb(),
        check_wind_chill(),
        check_solar_position(),
        check_air_density_isa(),
        check_lapse_rate(),
        check_wbgt_iso7243(),
        check_heat_index(),
        check_isa_metpy(),
        check_rain_visibility_atlas(),
        check_evaporation_penman_monteith(),
        check_seeing_cn2(),
        check_smoke_dispersal(),
    ]

    lines = [
        "AEE Atmospheric Physics Validation",
        "=" * 44,
        "",
        "Optional libraries: "
        f"psychrolib={'yes' if HAS_PSYCHROLIB else 'no'}, "
        f"metpy={'yes' if HAS_METPY else 'no'}, "
        f"pvlib={'yes' if HAS_PVLIB else 'no'}",
        "",
    ]
    for result in checks:
        lines.append(format_result(result))
        lines.append("")

    lines.append("Summary")
    lines.append("-" * 44)
    lines.append(f"{'Formula':<46} {'Status':<7} {'Max error':<14} Tolerance")
    for result in checks:
        max_err = f"{result['max_abs']:.3f} {result['unit']}"
        lines.append(
            f"{result['name'][:46]:<46} {result['status']:<7} {max_err:<14} {result['tolerance']}"
        )
    lines.append("")

    failed = [r for r in checks if r["status"] == "FAIL"]
    skipped = [r for r in checks if r["status"] == "SKIP"]
    lines.append(f"Checks run: {len(checks) - len(skipped)} of {len(checks)}")
    lines.append(f"Skipped (missing optional library): {len(skipped)}")
    lines.append(f"Failed: {len(failed)}")
    report = "\n".join(lines)

    print(report)
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.txt")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report + "\n")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
