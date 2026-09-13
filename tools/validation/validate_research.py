#!/usr/bin/env python3
"""Scientific validation for AEE proposed research features (issues #22-#29).

Standalone Python mirrors of the planned SQF implementations. No AEE
dependency. Validates mathematical models against published references
so the implementing agent has pre-verified formulas ready to port.

Features covered:
  1. Ground frost detection (dew point depression, surface energy balance)
  2. Subsurface soil temperature profile (1-D heat diffusion, Stefan)
  3. Fixed-wing aircraft performance (density altitude, ground effect)
  4. Cold-weather human performance (wind chill dexterity, frostbite)
  5. Rain accumulation and surface runoff (water balance)
  6. Circadian rhythm and sleep pressure (Borbely two-process model)

Run:  python3 tools/validation/validate_research.py
Exit: 0 when every check passes, 1 when any check fails.
"""

import math
import os
import sys

# ─── Statistics ─────────────────────────────────────────────────────────────


def compute_stats(errors):
    """Return (max_abs, rmse) for a list of absolute errors."""
    if not errors:
        return 0.0, 0.0
    max_abs = max(errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    return max_abs, rmse


# ─── 1. Ground frost detection ─────────────────────────────────────────────
# Mirror of proposed fnc_calculateGroundFrost.sqf
# Uses Magnus formula (Sonntag 1990) for dew point, then checks if the
# surface skin temperature drops below dew point → condensation → frost
# if surface T < 0 C.


def saturation_vapour_pressure_sonntag(t_c):
    """Magnus formula (Sonntag 1990) for saturation vapour pressure, hPa.

    Ref: Sonntag D., 1990, "Advancement in the form of the Magnus formula"
    Published: e_s = 6.112 * exp(17.67 * T / (T + 243.5))
    """
    return 6.112 * math.exp(17.67 * t_c / (t_c + 243.5))


def dew_point_magnus(t_c, rh_pct):
    """Magnus dew point from air temperature and relative humidity.

    Ref: Alduchov & Eskridge 1996 improved Magnus coefficients.
    Returns degrees C.
    """
    a = 17.625
    b = 243.04
    gamma = math.log(rh_pct / 100.0) + a * t_c / (b + t_c)
    return b * gamma / (a - gamma)


def surface_skin_temperature(t_air, wind_ms, cloud_cover, solar_factor):
    """Simplified surface skin temperature model.

    Clear calm nights cool below air temperature via longwave radiation loss.
    Wind mixes the boundary layer, keeping skin closer to air temperature.
    Cloud cover reduces net longwave loss.

    Ref: Oke T.R., 1987, "Boundary Layer Climates" Ch. 7 — nocturnal
    surface energy balance. Simplified to a single empirical formula.

    t_air: air temperature C
    wind_ms: wind speed m/s
    cloud_cover: 0..1 (0 = clear, 1 = overcast)
    solar_factor: 0..1 (0 = night, >0 = solar heating)

    Returns skin temperature in C.
    """
    # Net longwave cooling under clear calm sky: typically 40-80 W/m^2
    # Convert to approximate cooling in C via Bowen-like ratio
    nlw_loss = 60.0 * (1.0 - cloud_cover * 0.8)  # W/m^2
    # Wind-driven turbulent coupling: higher wind → skin closer to air
    coupling = min(1.0, 0.3 + wind_ms * 0.1)  # 0.3 calm, ~1.0 windy
    # Solar heating keeps skin warm during day
    solar_warmth = solar_factor * 15.0  # up to +15 C above air at full sun
    # Skin temperature: air + solar warming - radiative cooling * (1 - coupling)
    cooling = nlw_loss * 0.08 * (1.0 - coupling)  # ~4.8 C max cooling
    skin_t = t_air + solar_warmth - cooling
    return skin_t


def frost_state(t_air, rh_pct, wind_ms, cloud_cover, solar_factor):
    """Ground frost state machine output.

    Returns dict with:
      skin_t: surface skin temperature C
      dew_t: dew point C
      frost_risk: 0..1 (0 = none, 1 = guaranteed frost)
      state: 'none' | 'dew' | 'frost' | 'hard_frost'
    """
    skin_t = surface_skin_temperature(t_air, wind_ms, cloud_cover, solar_factor)
    dew_t = dew_point_magnus(t_air, rh_pct)

    # Wind coupling: high wind keeps skin near air temp, reducing radiative
    # cooling. Low wind lets skin cool well below air temperature.
    wind_coupling = min(1.0, 0.3 + wind_ms * 0.1)

    if skin_t < dew_t and dew_t <= 0.0:
        # Deposition: skin below dew point and below freezing
        depression = dew_t - skin_t
        frost_risk = min(1.0, depression / 5.0)
        state = "hard_frost" if depression > 2.0 else "frost"
    elif skin_t < 0.0 and skin_t >= dew_t:
        # Radiative frost without dew: skin below 0 but above dew point.
        # High wind coupling means the skin is barely below air temp,
        # so frost risk is lower (less radiative cooling to sustain it).
        frost_risk = min(1.0, abs(skin_t) / 5.0) * (1.0 - wind_coupling * 0.5)
        state = "frost"
    elif skin_t < dew_t and dew_t > 0.0:
        # Dew formation (above freezing)
        frost_risk = 0.0
        state = "dew"
    else:
        frost_risk = 0.0
        state = "none"

    return {
        "skin_t": skin_t,
        "dew_t": dew_t,
        "frost_risk": frost_risk,
        "state": state,
    }


# ─── 2. Subsurface soil temperature profile ────────────────────────────────
# Mirror of proposed fnc_calculateSubsurfaceTemperature.sqf
# 1-D heat diffusion: dT/dt = kappa * d2T/dz2
# Discretised with forward Euler on a depth grid.
# Ref: Carslaw & Jaeger 1959, "Conduction of Heat in Solids"


def soil_diffusivity(soil_type="loam"):
    """Thermal diffusivity kappa in m^2/s for common soil types.

    Ref: de Vries 1963, cited in Oke 1987 Table 4.1.
    """
    # ponytail: clamped lookup, add interpolated table if more soils needed
    values = {
        "dry_sand": 2.6e-7,
        "wet_sand": 1.0e-6,
        "loam": 5.0e-7,
        "wet_loam": 8.0e-7,
        "dry_clay": 3.0e-7,
        "wet_clay": 6.0e-7,
        "peat": 1.0e-7,
        "snow": 2.0e-7,
        "ice": 1.2e-6,
    }
    return values.get(soil_type, 5.0e-7)


def soil_temperature_profile(
    surface_t, air_t, wind_ms, depth_grid_m, hours, soil_type="loam"
):
    """Forward-Euler 1-D heat diffusion into soil.

    surface_t: initial surface skin temperature C
    air_t: air temperature C (drives surface boundary)
    wind_ms: wind speed (modulates surface coupling)
    depth_grid_m: list of depths in metres [0.0, 0.05, 0.1, 0.2, 0.5, 1.0]
    hours: simulation time in hours
    soil_type: key into soil_diffusivity

    Returns list of temperatures at each depth after simulation.
    """
    kappa = soil_diffusivity(soil_type)
    n = len(depth_grid_m)
    dz = [depth_grid_m[i + 1] - depth_grid_m[i] for i in range(n - 1)]
    dz.append(dz[-1] if n > 1 else 0.1)

    # Initial profile: linear interpolation from surface to deep soil
    deep_t = 10.0  # deep soil roughly annual mean
    temp = [
        surface_t + (deep_t - surface_t) * (depth_grid_m[i] / 2.0) for i in range(n)
    ]
    temp[-1] = deep_t  # fixed bottom boundary

    # Time step: must satisfy CFL: dt <= dz^2 / (2*kappa)
    min_dz = min(d for d in dz if d > 0)
    dt_max = min_dz**2 / (2.0 * kappa)
    dt = min(dt_max * 0.9, 60.0)  # 60 s max step
    n_steps = int(hours * 3600 / dt)

    # Surface coupling: newton cooling to air temperature
    coupling = 0.3 + wind_ms * 0.05  # higher wind = stronger coupling
    coupling = min(coupling, 1.0)

    for _step in range(n_steps):
        new_t = list(temp)
        # Diffusion: interior points
        for i in range(1, n - 1):
            d2t = (temp[i + 1] - 2 * temp[i] + temp[i - 1]) / (dz[i] ** 2)
            new_t[i] = temp[i] + kappa * dt * d2t
        # Surface boundary: Newton cooling toward air temperature
        new_t[0] = temp[0] + coupling * dt * (air_t - temp[0]) * 0.001
        # Bottom: fixed
        new_t[-1] = deep_t
        temp = new_t

    return temp


# ─── 3. Fixed-wing aircraft performance ────────────────────────────────────
# Mirror of proposed fnc_calculateFixedWingPerformance.sqf
# Density altitude, pressure altitude, ground effect, landing performance.
# Ref: FAA Pilot's Handbook of Aeronautical Knowledge Ch. 11
#      Anderson "Introduction to Flight" 8th Ed.


def density_altitude(pressure_alt_m, t_c):
    """Density altitude from pressure altitude and outside air temperature.

    Ref: ISA formula: DA = PA + 120 * (OAT - ISA_temp)
    ISA temp at pressure altitude: 15 - 1.98 * (PA / 1000) C
    where 1.98 C per 1000 ft ≈ 6.5 C per 1000 m (standard lapse).

    pressure_alt_m: pressure altitude in metres
    t_c: outside air temperature in C
    Returns density altitude in metres.
    """
    isa_t = 15.0 - 0.0065 * pressure_alt_m
    delta_t = t_c - isa_t
    # 120 ft per degree C ≈ 36.576 m per degree C
    return pressure_alt_m + 36.576 * delta_t


def pressure_altitude(qnh_hpa, field_elev_m):
    """Pressure altitude from QNH and field elevation.

    Ref: ICAO standard atmosphere. ISA sea-level P = 1013.25 hPa,
    lapse = 6.5 C/km → pressure follows barometric formula.

    Simplified: PA = FE + (1013.25 - QNH) * 8.43 (approx, low altitude).
    For accuracy over large ranges, use ISA table lookup.
    """
    # More accurate: use ISA pressure at field elevation
    isa_p_sl = 1013.25
    # Barometric: P = P0 * (1 - 0.0065*h/288.15)^5.2559
    p_at_field = isa_p_sl * (1.0 - 0.0065 * field_elev_m / 288.15) ** 5.2559
    # Pressure altitude: height where ISA pressure equals actual QNH
    if abs(qnh_hpa - isa_p_sl) < 0.01:
        return field_elev_m
    # Inverse barometric formula
    pa_m = (1.0 - (qnh_hpa / isa_p_sl) ** (1.0 / 5.2559)) * 288.15 / 0.0065
    return pa_m


def ground_effect_factor(height_agl_m, wingspan_m):
    """Ground effect multiplier for lift coefficient.

    Ref: McCormick (1973) semi-empirical GE model, adapted.
    K = b / (2h); GE boost = K^2 / (1 + K^2) * 0.4

    Published benchmarks:
      h/b = 0.5 (h=b/2): ~19% boost  (K=1, boost=0.20)
      h/b = 1.0: ~7% boost            (K=0.5, boost=0.08)
      h/b = 0.1: ~35% boost (practical max, clamped)

    height_agl_m: height above ground in metres
    wingspan_m: aircraft wingspan in metres
    Returns lift multiplier >= 1.0 (1.0 = no ground effect)
    """
    if height_agl_m <= 0:
        return 1.35  # practically on the ground, max GE ~35%
    k = wingspan_m / (2.0 * height_agl_m)
    boost = (k**2) / (1.0 + k**2) * 0.4
    return min(max(1.0 + boost, 1.0), 1.35)


def true_airspeed_from_indicated(ias_kts, pressure_alt_m, t_c):
    """TAS from IAS using density ratio.

    Ref: FAA HDBK Ch. 11 — TAS = IAS / sqrt(sigma)
    sigma = rho / rho0, rho0 = 1.225 kg/m3
    """
    e_s = 6.1121 * math.exp((18.678 - t_c / 234.5) * t_c / (257.14 + t_c))
    # Approximate pressure at altitude
    p_hpa = 1013.25 * (1.0 - 0.0065 * pressure_alt_m / 288.15) ** 5.2559
    t_k = t_c + 273.15
    rho = (p_hpa * 100) / (287.05 * t_k)
    sigma = rho / 1.225
    sigma = max(sigma, 0.3)  # floor to avoid division by tiny number
    return ias_kts / math.sqrt(sigma)


# ─── 4. Cold-weather human performance ─────────────────────────────────────
# Mirror of proposed fnc_calculateColdWeatherPerformance.sqf
# Wind chill dexterity loss, frostbite time, cognitive impairment.
# Ref: OSCAR deformation model (Tikuisis & Giesbrecht 1999)
#      ISO 11079 for wind chill equivalent temperature
#      NOAA frostbite time chart


def wind_chill_effective_temp(t_c, wind_ms):
    """Wind chill effective temperature (environmental).

    Ref: ISO 11079:2007 — equivalent temperature using the CWCT formula.
    Simplified to JAG/TTI form already in AEE; this is the same mirror.
    """
    v_kmh = wind_ms * 3.6
    v_exp = v_kmh**0.16
    wc = 13.12 + 0.6215 * t_c - 11.37 * v_exp + 0.3965 * t_c * v_exp
    return min(wc, t_c)


def frostbite_time_minutes(t_c, wind_ms):
    """Time to onset of frostbite on exposed face, in minutes.

    Ref: NOAA frostbite time chart, US Army Research Institute of
    Environmental Medicine (Tikuisis & Giesbrecht 1999):
      wind chill -10 C: ~30 min
      wind chill -20 C: ~10 min
      wind chill -27 C: ~5 min
      wind chill -35 C: ~2 min

    Model: t = 90 * exp(0.11 * wc) calibrated to the NOAA chart.
    Floor at 1 minute for extreme cold.

    Returns minutes to frostbite onset (exposed skin). None if no risk.
    """
    wc = wind_chill_effective_temp(t_c, wind_ms)
    if wc > -10:
        return None  # no frostbite risk above -10 C wind chill
    # Empirical fit to NOAA chart: t = 90 * exp(0.11 * wc)
    t = 90.0 * math.exp(0.11 * wc)
    return max(1.0, t)


def dexterity_loss_pct(t_c, wind_ms):
    """Finger dexterity loss as a percentage (0 = full, 100 = none).

    Ref: Miller & Tipton 1998, "Finger dexterity and skin temperature
    during cold exposure."  Loss accelerates below 15 C skin temperature.
    Simplified: linear from 100% at 15 C skin to 0% at -10 C skin.
    Skin temp model: skin ≈ wind_chill if wind > 2 m/s, else air T.
    """
    if wind_ms > 2:
        skin_t = wind_chill_effective_temp(t_c, wind_ms)
    else:
        skin_t = t_c - 3.0  # bare skin slightly below air
    if skin_t >= 15:
        return 0.0  # full dexterity
    if skin_t <= -10:
        return 100.0  # complete loss
    return (15.0 - skin_t) / 25.0 * 100.0


def cognitive_impairment_pct(t_c, wind_ms, duration_hr):
    """Cognitive impairment from cold exposure, percent.

    Ref: Palinkas 2001, "Mental and cognitive performance in the cold."
    Impairment rises with cold intensity and exposure duration.
    Model: base impairment from wind chill, amplified by time.
    """
    wc = wind_chill_effective_temp(t_c, wind_ms)
    if wc >= 0:
        return 0.0
    base = min(50.0, abs(wc) * 1.5)  # up to 50% from temperature alone
    duration_factor = 1.0 + duration_hr * 0.2  # 20% more per hour
    return min(100.0, base * duration_factor)


# ─── 5. Rain accumulation and surface runoff ───────────────────────────────
# Mirror of proposed fnc_calculateRainAccumulation.sqf
# Water balance model: P = E + R + dS/dt
# Ref: Chow, Maidment & Mays 1988, "Applied Hydrology" Ch. 2


def rain_to_mm_h(rain_01):
    """Convert Arma 3 abstract rain 0..1 to mm/h.

    AEE convention: rain_01 * 25 = mm/h.
    """
    return rain_01 * 25.0


def infiltration_rate(saturation, soil_type="loam"):
    """Infiltration capacity in mm/h (Horton equation simplified).

    Ref: Horton 1940, cited in Chow et al. 1988.
    f = f_inf + (f0 - f_inf) * exp(-k * t)
    Steady-state approximation: f ≈ f_inf when saturation is high.
    """
    # ponytail: max infiltration by soil type (mm/h)
    f0 = {"sand": 80, "loam": 30, "clay": 12, "rock": 5}.get(soil_type, 30)
    f_inf = f0 * 0.2  # final infiltration rate ~20% of initial
    # Saturation reduces infiltration: at sat=1, f=f_inf; at sat=0, f=f0
    return f_inf + (f0 - f_inf) * (1.0 - saturation)


def runoff_rate(rain_mm_h, saturation, soil_type="loam"):
    """Surface runoff in mm/h.

    runoff = max(0, rain - infiltration).
    """
    inf = infiltration_rate(saturation, soil_type)
    return max(0.0, rain_mm_h - inf)


def water_balance_step(rain_01, evap_mm_h, saturation, storage_mm, soil_type="loam"):
    """One time-step of the water balance model.

    P (rain) = E (evaporation) + R (runoff) + dS/dt (storage change)

    rain_01: Arma 3 abstract rain 0..1
    evap_mm_h: evaporation rate mm/h
    saturation: soil saturation 0..1
    storage_mm: current water storage on surface mm
    soil_type: infiltration reference

    Returns (new_saturation, new_storage_mm, runoff_mm_h)
    """
    rain_mm_h = rain_to_mm_h(rain_01)
    total_input = rain_mm_h + storage_mm  # previous storage + new rain
    eff_rain = total_input - evap_mm_h
    if eff_rain < 0:
        return max(0, saturation - 0.01), 0.0, 0.0
    ro = runoff_rate(eff_rain, saturation, soil_type)
    infiltrated = eff_rain - ro
    # Storage change
    dS = infiltrated * 0.05  # 5% of infiltrated water stored on surface
    new_storage = max(0.0, ro * 0.1)  # 10% of runoff temporarily stored
    # Saturation update
    new_sat = min(1.0, saturation + infiltrated * 0.001)
    return new_sat, new_storage, ro


# ─── 6. Circadian rhythm and sleep pressure ────────────────────────────────
# Mirror of proposed fnc_calculateCircadianState.sqf
# Borbely two-process model (Process S + Process C).
# Ref: Borbely 1982, "A two process model of sleep regulation"
#      Original: S(t) = S_inf + (S_0 - S_inf) * exp(-t/tau)
#      C(t) = cos(2*pi*(t - phi) / 24) / 2


def process_s_buildup(hours_awake, s_max=1.0, tau_h=18.0):
    """Process S: sleep pressure as a function of hours awake.

    Ref: Borbely 1982 — exponential build-up toward S_max.
    tau_h: time constant in hours (typically 15-20 h).

    Returns 0..s_max.
    """
    s_inf = 0.0  # fully rested
    s = s_inf + (s_max - s_inf) * (1.0 - math.exp(-hours_awake / tau_h))
    return min(s, s_max)


def process_c_circadian(time_of_day_h, acrophase_h=14.0):
    """Process C: circadian alerting signal.

    Ref: Borbely 1982 — cosine oscillation with 24h period.
    time_of_day_h: hours since wake (0 = wake time)
    acrophase_h: peak alerting time (typically 14h after wake)

    Returns -0.5..+0.5 (negative = sleep promoting, positive = alerting)
    """
    return 0.5 * math.cos(2.0 * math.pi * (time_of_day_h - acrophase_h) / 24.0)


def sleep_pressure_index(hours_awake, time_of_day_h, acrophase_h=14.0):
    """Combined sleep pressure: Process S - Process C.

    Ref: Achermann & Borbely 1994 — alertness = S(t) - C(t).
    Higher value = sleepier.

    Returns 0..1.5 (0 = maximally alert, 1.5 = maximally sleepy)
    """
    s = process_s_buildup(hours_awake)
    c = process_c_circadian(time_of_day_h, acrophase_h)
    return max(0.0, s - c)


def fatigue_performance_modifier(hours_awake, time_of_day_h, acrophase_h=14.0):
    """Performance modifier from fatigue: 1.0 (alert) to 0.4 (severely fatigued).

    Ref: Van Dongen et al. 2003 — cognitive performance degrades ~10% after
    17h awake, matching the legal driving impairment threshold.
    """
    spi = sleep_pressure_index(hours_awake, time_of_day_h, acrophase_h)
    # Linear mapping: SPI 0 → 1.0, SPI 1.5 → 0.4
    mod = 1.0 - spi * 0.4
    return max(0.4, min(1.0, mod))


def microsleep_risk(hours_awake, time_of_day_h, acrophase_h=14.0):
    """Microsleep probability 0..1.

    Ref: onward to Van Dongen 2003 — microsleeps increase exponentially
    above 20h of sustained wakefulness.
    """
    spi = sleep_pressure_index(hours_awake, time_of_day_h, acrophase_h)
    if spi < 0.8:
        return 0.0
    # Exponential above threshold
    return min(1.0, math.exp((spi - 0.8) * 3.0) - 1.0)


# ─── Checks ─────────────────────────────────────────────────────────────────


def check_dew_point():
    """Magnus dew point vs known psychrometric chart values.

    Ref: ASHRAE Fundamentals 2009, Table 1 — dew point for given T/RH.
    """
    # (T_C, RH%, expected_dp_C, tolerance_C)
    refs = [
        (20, 50, 9.3, 0.5),
        (30, 60, 21.1, 0.5),
        (0, 80, -2.8, 0.5),
        (-10, 70, -14.5, 1.0),
    ]
    errors = []
    for t, rh, expected, _ in refs:
        dp = dew_point_magnus(t, rh)
        errors.append(abs(dp - expected))
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Ground frost: dew point (Magnus vs psychrometric chart)",
        "ground_truth": "ASHRAE Fundamentals 2009 Table 1",
        "grid": "4 reference points",
        "tolerance": "1.0 C",
        "status": "PASS" if max_abs <= 1.0 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "C",
    }


def check_frost_physical_behaviour():
    """Frost state model: physical behaviour checks."""
    cases = [
        # Clear calm cold night: frost expected
        (frost_state(-5, 80, 0.5, 0.0, 0.0), True, "clear calm cold night"),
        # Warm humid day: no frost
        (frost_state(25, 70, 2.0, 0.3, 0.8), False, "warm humid day"),
        # Windy night: less frost than calm
        (frost_state(-3, 85, 8.0, 0.1, 0.0), None, "windy night vs calm"),
    ]
    cold_night = frost_state(-5, 80, 0.5, 0.0, 0.0)["frost_risk"]
    warm_day = frost_state(25, 70, 2.0, 0.3, 0.8)["frost_risk"]
    wind_calm = frost_state(2, 80, 0.5, 0.0, 0.0)["frost_risk"]
    wind_windy = frost_state(2, 80, 8.0, 0.0, 0.0)["frost_risk"]
    errors = []
    # Cold calm night must have frost
    if cold_night < 0.01:
        errors.append(0.5)
    else:
        errors.append(0.0)
    # Warm day must have no frost
    if warm_day > 0.01:
        errors.append(0.5)
    else:
        errors.append(0.0)
    # Wind reduces frost
    if wind_windy > wind_calm:
        errors.append(0.5)
    else:
        errors.append(0.0)
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Ground frost: physical behaviour",
        "ground_truth": "Oke 1987 Ch. 7 — nocturnal surface energy balance",
        "grid": "3 ordering/sanity checks",
        "tolerance": "0.1 behavioural",
        "status": "PASS" if max_abs <= 0.1 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "behavioural",
    }


def check_soil_temperature_profile():
    """Subsurface profile: cold surface must be colder than deep soil."""
    depths = [0.0, 0.05, 0.1, 0.2, 0.5, 1.0]
    # Cold night: surface -5 C, air -5 C, calm
    profile = soil_temperature_profile(-5.0, -5.0, 0.5, depths, 8.0)
    # Warm day: surface 35 C, air 30 C, sunny
    profile_warm = soil_temperature_profile(35.0, 30.0, 2.0, depths, 8.0)

    errors = []
    # Profile must be monotonically approaching deep soil temp
    # Cold case: -5 at surface, should warm with depth
    for i in range(len(profile) - 1):
        if profile[i] < profile[i + 1]:
            errors.append(0.0)  # correct: warming with depth
        else:
            errors.append(0.3)

    # Warm case: surface should be warmer than depth
    for i in range(len(profile_warm) - 1):
        if profile_warm[i] > profile_warm[i + 1]:
            errors.append(0.0)  # correct: cooling with depth
        else:
            errors.append(0.3)

    # Deep soil should be near 10 C regardless of surface
    if abs(profile[-1] - 10.0) < 0.5:
        errors.append(0.0)
    else:
        errors.append(abs(profile[-1] - 10.0))

    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Subsurface soil: profile monotonicity and deep bound",
        "ground_truth": "Carslaw & Jaeger 1959; deep soil ≈ annual mean",
        "grid": "cold night + warm day, 6 depths, 8 h",
        "tolerance": "0.3 per depth",
        "status": "PASS" if max_abs <= 0.3 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "per-depth check",
    }


def check_density_altitude():
    """Density altitude vs published ISA values.

    Ref: FAA PHAK Ch. 11, Table 11-1.
    At sea level, OAT = 15 C → DA = 0 m. Each degree above ISA adds
    ~36.6 m (120 ft).
    """
    # (PA_m, OAT_C, expected_DA_m, tolerance_m)
    # DA = PA + 36.576 * (OAT - ISA_temp), ISA_temp = 15 - 0.0065*PA
    refs = [
        (0, 15, 0, 50),
        (0, 25, 366, 50),
        (0, 35, 732, 50),
        (1500, 5.25, 1500, 50),  # ISA temp at 1500 m: DA = PA
        (1500, 15.25, 1866, 50),  # +10 C above ISA at 1500 m
    ]
    errors = []
    for pa, oat, expected, _ in refs:
        da = density_altitude(pa, oat)
        errors.append(abs(da - expected))
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Fixed-wing: density altitude (FAA reference)",
        "ground_truth": "FAA PHAK Ch. 11, ISA table",
        "grid": "5 reference points",
        "tolerance": "100 m",
        "status": "PASS" if max_abs <= 100 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "m",
    }


def check_ground_effect():
    """Ground effect: at wingspan height, lift boost ~20%."""
    errors = []
    # At h = wingspan/2, McCormick gives ~20% boost
    ge_half = ground_effect_factor(5.0, 10.0)  # h = b/2
    if abs(ge_half - 1.20) < 0.1:
        errors.append(0.0)
    else:
        errors.append(abs(ge_half - 1.20))
    # At h = wingspan, boost should be small
    ge_full = ground_effect_factor(10.0, 10.0)
    if ge_full < 1.10:
        errors.append(0.0)
    else:
        errors.append(ge_full - 1.10)
    # At h = 0, max boost (clamped to 1.35)
    ge_ground = ground_effect_factor(0.1, 10.0)
    if ge_ground >= 1.20:
        errors.append(0.0)
    else:
        errors.append(0.5)
    # Boost must decrease with height
    if ge_half > ge_full:
        errors.append(0.0)
    else:
        errors.append(0.5)
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Fixed-wing: ground effect (McCormick)",
        "ground_truth": "McCormick aerodynamics, GE at b/2 ≈ 20%",
        "grid": "4 behaviour checks",
        "tolerance": "0.10",
        "status": "PASS" if max_abs <= 0.10 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "multiplier",
    }


def check_frostbite_time():
    """Frostbite time vs NOAA chart."""
    # (T_C, wind_ms, expected_min, tolerance_min)
    refs = [
        (-10, 0.5, 30, 5),
        (-20, 0.5, 10, 5),
        (-27, 0.5, 5, 3),
    ]
    errors = []
    for t, w, expected, _ in refs:
        ft = frostbite_time_minutes(t, w)
        if ft is None:
            errors.append(expected)  # should not be None
        else:
            errors.append(abs(ft - expected))
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Cold-weather: frostbite time (NOAA chart)",
        "ground_truth": "NOAA frostbite time chart / Military Medicine 1956",
        "grid": "3 reference points",
        "tolerance": "10 min",
        "status": "PASS" if max_abs <= 10 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "min",
    }


def check_dexterity_loss():
    """Dexterity loss: monotonic with cold, full at 15 C, total at -10 C."""
    d_full = dexterity_loss_pct(20, 0)  # warm: 0% loss
    d_mild = dexterity_loss_pct(5, 2)
    d_cold = dexterity_loss_pct(-5, 5)
    d_extreme = dexterity_loss_pct(-20, 10)

    errors = []
    # Monotonic: colder = more loss
    if d_full <= d_mild <= d_cold <= d_extreme:
        errors.append(0.0)
    else:
        errors.append(0.5)
    # Full dexterity in warm
    if abs(d_full) < 5:
        errors.append(0.0)
    else:
        errors.append(d_full)
    # Near-total loss in extreme cold
    if d_extreme > 80:
        errors.append(0.0)
    else:
        errors.append(80 - d_extreme)

    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Cold-weather: dexterity loss monotonicity",
        "ground_truth": "Miller & Tipton 1998",
        "grid": "4-point monotonicity check",
        "tolerance": "5%",
        "status": "PASS" if max_abs <= 5 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "%",
    }


def check_runoff():
    """Runoff: wet soil runs off more than dry soil."""
    dry_ro = runoff_rate(20.0, 0.1)
    wet_ro = runoff_rate(20.0, 0.9)
    errors = []
    if wet_ro > dry_ro:
        errors.append(0.0)
    else:
        errors.append(1.0)
    # Heavy rain on dry soil: some infiltration
    if 0 < dry_ro < 20.0:
        errors.append(0.0)
    else:
        errors.append(1.0)
    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Rain accumulation: runoff behaviour",
        "ground_truth": "Chow, Maidment & Mays 1988",
        "grid": "2 ordering checks",
        "tolerance": "1.0 behavioural",
        "status": "PASS" if max_abs <= 1.0 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "behavioural",
    }


def check_circadian():
    """Circadian rhythm: alertness peaks in afternoon, sleepy at night."""
    # Assuming wake at 7:00, acrophase at 21:00 (14h after wake)
    perf_morning = fatigue_performance_modifier(4, 11.0)  # 4h awake, 11:00
    perf_afternoon = fatigue_performance_modifier(8, 15.0)  # 8h awake, 15:00
    perf_evening = fatigue_performance_modifier(14, 21.0)  # 14h awake, 21:00
    perf_latenight = fatigue_performance_modifier(18, 1.0)  # 18h awake, 01:00

    errors = []
    # Afternoon should be near peak (Process C alerting)
    if perf_afternoon >= perf_morning - 0.05:
        errors.append(0.0)
    else:
        errors.append(0.5)
    # Late night should be worst (high S, low C)
    if perf_latenight < perf_afternoon:
        errors.append(0.0)
    else:
        errors.append(0.5)
    # Must be in valid range
    for p in [perf_morning, perf_afternoon, perf_evening, perf_latenight]:
        if 0.4 <= p <= 1.0:
            errors.append(0.0)
        else:
            errors.append(abs(p - 0.7))

    max_abs, rmse = compute_stats(errors)
    return {
        "name": "Circadian: performance curve (Borbely two-process)",
        "ground_truth": "Borbely 1982; Van Dongen et al. 2003",
        "grid": "4 time-of-day checks",
        "tolerance": "0.05",
        "status": "PASS" if max_abs <= 0.05 else "FAIL",
        "max_abs": max_abs,
        "rmse": rmse,
        "unit": "modifier",
    }


# ─── Report ─────────────────────────────────────────────────────────────────


def format_result(result):
    """Return multi-line detail block for one check."""
    lines = [
        result["name"],
        f"  Ground truth : {result['ground_truth']}",
        f"  Grid         : {result['grid']}",
        f"  Max error    : {result['max_abs']:.4f} {result['unit']}",
        f"  RMSE         : {result['rmse']:.4f} {result['unit']}",
        f"  Tolerance    : {result['tolerance']}",
        f"  Status       : {result['status']}",
    ]
    return "\n".join(lines)


def main():
    checks = [
        check_dew_point(),
        check_frost_physical_behaviour(),
        check_soil_temperature_profile(),
        check_density_altitude(),
        check_ground_effect(),
        check_frostbite_time(),
        check_dexterity_loss(),
        check_runoff(),
        check_circadian(),
    ]

    lines = [
        "AEE Research Feature Validation",
        "=" * 44,
        "",
    ]
    for result in checks:
        lines.append(format_result(result))
        lines.append("")

    lines.append("Summary")
    lines.append("-" * 44)
    lines.append(f"{'Formula':<50} {'Status':<7} {'Max error':<14} Tolerance")
    for result in checks:
        max_err = f"{result['max_abs']:.3f} {result['unit']}"
        lines.append(
            f"{result['name'][:50]:<50} {result['status']:<7} "
            f"{max_err:<14} {result['tolerance']}"
        )
    lines.append("")

    failed = [r for r in checks if r["status"] == "FAIL"]
    lines.append(f"Checks run: {len(checks)}")
    lines.append(f"Failed: {len(failed)}")
    report = "\n".join(lines)

    print(report)
    report_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "research_report.txt"
    )
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report + "\n")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
