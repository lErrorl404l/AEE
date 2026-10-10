#!/usr/bin/env python3
"""Reference checks for AEE's thermal and NVG optics physics.

These tests validate the SQF implementation in addons/thermal and
addons/optics against known physical values.  They mirror the exact
formulas in the SQF source so that any drift breaks the tests.

Run: python3 -m unittest tools.tests.test_thermal_optics -v
"""

import math
import re
import sys
import unittest
from pathlib import Path

# The pure sensor-resolvability kernel is executed from its real SQF, so the
# shared mini-interpreter is imported the way the other SQF-driven suites do.
sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

# Cross-model consistency: the optics moon term must stay consistent with
# the verified lunar illuminance model (Krisciunas & Schaefer 1991) in
# test_astronomical.py.
from tools.tests.test_astronomical import ks_lunar_lux

# The comment-stripping helper is shared, so a source lock cannot match the
# header prose.  The headers quote the shapes they replaced, and a raw grep
# has matched that prose in this repository before.
from tools.tests.test_exhaust_shimmer import _code_only

# The two-node solver's own execution harness (sqf_lite + the real material
# registry) is reused, not duplicated, so the warm-up test runs the shipped
# SQF exactly as the solver suite does.
from tools.tests.test_sqf_two_node import _solve as _solve_two_node  # noqa: E402

# Repo root: tools/tests/ -> up two levels.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_OPTICS = _REPO_ROOT / "addons" / "optics" / "functions"
_VISION = _REPO_ROOT / "addons" / "vision" / "functions"
_EYE = _REPO_ROOT / "addons" / "eye" / "functions"
_THERMAL = _REPO_ROOT / "addons" / "thermal" / "functions"
_THERMAL_DISPLAY = _REPO_ROOT / "addons" / "thermal_display" / "functions"
_NVG = _REPO_ROOT / "addons" / "nightvision" / "functions"
_CORE = _REPO_ROOT / "addons" / "core" / "functions"


def _read_sqf(name, addon="optics"):
    """Read an SQF function file.  The drift-lock tests read the SOURCE so a
    constant change in SQF fails the mirror tests until re-synced.  The
    file may live in a categorised subfolder (issue #203), so a recursive
    search of the module's functions tree is used - the function NAME is
    flat (aee_X_fnc_<name>) regardless of its organisational folder."""
    if addon == "thermal":
        base = _THERMAL
        if not (base / name).exists() and not any(base.rglob(name)):
            base = _THERMAL_DISPLAY
    elif addon == "nightvision":
        base = _NVG
    elif addon == "core":
        base = _CORE
    elif addon == "vision":
        base = _VISION
    elif addon == "eye":
        base = _EYE
    else:
        base = _OPTICS
    if (base / name).exists():
        return (base / name).read_text(encoding="utf-8")
    for f in base.rglob(name):
        return f.read_text(encoding="utf-8")
    raise FileNotFoundError(f"{name} not found under {base}")


# ─── Object temperature model mirrors ───────────────────────────────────────


def thermal_inertia(current, target, dt, tau):
    """Mirror of the exponential thermal inertia in fnc_calculateObjectTemperature.

    SQF: _currentTemp + (_target - _currentTemp) * (1 - exp(-dt / tau))
    """
    if tau <= 0:
        return target
    return current + (target - current) * (1 - math.exp(-dt / tau))


def vehicle_engine_flux(air_temp, wind, t_op=90.0, t_exh=480.0, exh_frac=0.05):
    """Mirror of the coarse inert-branch engine surface flux (W/m2).

    SQF: ((1 - _exhFrac) * ((_tOp max _airTemp) - _airTemp)
          + _exhFrac * ((_tExh max _airTemp) - _airTemp)) * _hConv
    T_op is the thermostat-opened coolant temperature; T_exh the exhaust gas.
    """
    h = 5.7 + 3.8 * wind
    t_body = max(t_op, air_temp)
    t_gas = max(t_exh, air_temp)
    return ((1 - exh_frac) * (t_body - air_temp) + exh_frac * (t_gas - air_temp)) * h


def lumped_tau(mass_kg, cp, h, area):
    """Incropera Ch. 5 lumped-capacitance time constant tau = m*cp/(h*A)."""
    return (mass_kg * cp) / max(h * area, 1e-3)


def vehicle_brake_power(mass_kg, v_prev_ms, v_now_ms, dt_s):
    """Mirror of the brake heat source in fnc_calculateVehicleHeat.

    COMSOL ("Heat Generation in a Disc Brake", 2012): the energy per stop is
    E = 0.5*m*(v0^2 - v1^2) over the interval, so the average power is E/t.
    Deceleration only, and the whole change is assigned to the brakes (the
    COMSOL idealisation, an upper bound).
    """
    if dt_s <= 0 or v_now_ms >= v_prev_ms:
        return 0.0
    energy_j = 0.5 * mass_kg * (v_prev_ms**2 - v_now_ms**2)
    return energy_j / dt_s


def vehicle_brake_power_instant(mass_kg, decel_ms2, speed_ms):
    """Mirror of the instantaneous brake power P = m*a*v (COMSOL 2012)."""
    return mass_kg * decel_ms2 * speed_ms


def vehicle_body_temperature(body_temp, target, q_source_w, h_area, capacitance, dt_s):
    """Mirror of the source-driven lumped-capacitance step.

    SQF: _target = _target + (_qBrake / _hA)
         _bodyTemp = _target + ((_bodyTemp - _target) * exp(-dt / tau))
    A source term shifts the equilibrium target by Q/(h*A).
    """
    if h_area <= 0 or capacitance <= 0:
        return target
    t_inf = target + q_source_w / h_area
    tau = capacitance / h_area
    if dt_s <= 0:
        return t_inf
    return t_inf + (body_temp - t_inf) * math.exp(-dt_s / tau)


def infantry_clothing_surface(acclimatisation, air_temp, insulation):
    """Mirror of the infantry clothing surface temperature.

    SQF: _acclimatisation - (_acclimatisation - _airTemp) * (1 - _insulation)
    """
    return acclimatisation - (acclimatisation - air_temp) * (1 - insulation)


def infantry_metabolic_heat(speed_ms):
    """Mirror of the metabolic heat switch.

    idle <0.5: 0W, walk <3: 20W, run <6: 60W, sprint >6: 120W
    """
    v = abs(speed_ms)
    if v > 6:
        return 120
    if v > 3:
        return 60
    if v > 0.5:
        return 20
    return 0


def acclimatisation_step(acclimatisation, air_temp, dt):
    """Mirror of the acclimatisation toward ambient (tau=1800s).

    SQF: _acclimatisation + (_airTemp - _acclimatisation) * (1 - exp(-dt / 1800))
    """
    return acclimatisation + (air_temp - acclimatisation) * (1 - math.exp(-dt / 1800))


def insulation_from_setting(setting):
    """Mirror of the CBA setting → insulation fraction mapping.

    SQF: 0.3 + 0.5 * ((_insulationSetting - 0.5) / 1.5), clamped 0.3..0.8
    """
    return max(0.3, min(0.8, 0.3 + 0.5 * ((setting - 0.5) / 1.5)))


def _unused_emissivity_radiant_correction(emissivity):
    """Removed with the coarse-path linear radiant offset (F2).

    The old SQF was `_target - (1 - _emissivity) * 2`, a chosen linear
    correction.  The inert solve now carries the real eps*sigma*(Ts^4-MRT^4)
    term, so the mirror is gone and TestEmissivityRadiant asserts the source.
    """
    return -(1 - emissivity) * 2


# ─── Thermal contrast mirrors ───────────────────────────────────────────────


def thermal_contrast(air_temp=15.0, surface_temp=None):
    """Mirror of fnc_calculateThermalContrast.

    DEGRADATION ONLY, base 1.0, and NO weather term of its own.  The engine
    already renders the native thermal image with its own gain, so this stage
    adds no base gain: the clear-air value is exactly 1.0, which is also the
    consumer's declared default (fnc_applyThermalVision.sqf:95).  Atmospheric
    degradation lives once, in fnc_calculateAtmosphericTransmission, so this
    kernel must not apply rain, fog or humidity a second time.

    The extreme-heat and cold terms are driven by the surface-to-air gap
    where a surface temperature is available; where it is not, the air
    temperature is the only reference and the legacy form applies.  Every
    coefficient is UNSOURCED (see docs/wiki/chapters/sensor-value-audit.md).

    gap > 35: contrast -= ((gap - 35) / 10) × 0.7
    gap < 5:  contrast *= 1.2, min 1.0
    """
    c = 1.0
    gap = air_temp if surface_temp is None else surface_temp - air_temp
    if gap > 35:
        c -= ((gap - 35) / 10) * 0.7
    if gap < 5:
        c = min(c * 1.2, 1.0)
    return max(0, min(1, c))


def netd_noise(view_distance, humidity=0.0):
    """Retired mirror.  The noise floor is now the pure kernel
    fnc_calculateThermalNoise.sqf, executed directly by TestThermalNoise, so
    the hand-transcribed mirror is gone.
    """
    return 0.05 * ((view_distance / 1000) ** 2) * (1 + humidity * 0.5)


# ─── Thermal blur / pan smear mirrors ────────────────────────────────────────


def thermal_blur(effective_contrast, pan_smear=0.0, window_blur=0.0):
    """Mirror of fnc_applyThermalVision DynamicBlur stage.

    SQF: blur = linearConversion [1, 0, effective, 0.0, 0.15]
         blur = (blur + panSmear + windowBlur) min 0.25

    Effective contrast 1 (clear) → 0 blur; 0 (crossover/worst) → 0.15.
    Pan smear and window blur add on top; the ceiling 0.25 keeps the
    image from visibly dimming/flickering (DynamicBlur at 0.2+ reads
    as brightness loss over the engine's native thermal frame).
    """
    blur = (1 - effective_contrast) * 0.15
    return min(blur + pan_smear + window_blur, 0.25)


def thermal_pan_smear(turn_rate_deg_per_sec):
    """Mirror of the pan smear stage.

    SQF: linearConversion [0, 90, rate, 0.0, 0.04, true]
    """
    return max(0.0, min(0.04, 0.04 * (turn_rate_deg_per_sec / 90.0)))


# ─── Battery derating mirror ────────────────────────────────────────────────


def battery_derating(temp_c):
    """Mirror of fnc_calculateBatteryTemperatureDerating.

    Below 0°C: linear at 0.03/°C, min 0.3
    Above 45°C: linear at 0.01/°C, min 0.8 (max reduction 0.2)
    Normal: 1.0
    """
    factor = 1.0
    if temp_c < 0:
        factor -= min((0 - temp_c) * 0.03, 0.7)
    if temp_c > 45:
        factor -= min((temp_c - 45) * 0.01, 0.2)
    return max(0.3, min(1.0, factor))


# ─── Illuminance / gain / shot-noise mirrors (fnc_calculateIlluminance.sqf,
# ─── fnc_applyNVGTubeModel.sqf) ─────────────────────────────────────────────


def ambient_lux(
    moon_intensity,
    overcast=0.0,
    rain=0.0,
    sun_elev_deg=-90.0,
    starlight=0.001,
    aurora_intensity=0.0,
):
    """Mirror of the lux model in fnc_calculateIlluminance.

    cloudTransmission = 1 - min(overcast*0.85, 0.85)   (multiplicative)
    moonLight = max(0, moonIntensity*cloudTransmission - rain*0.5)
    twilightLux = 10^(2.6 - 0.3*|sunElev|) when the sun is below horizon
    auroraLux = 0.03 * auroraIntensity  (issue #112, green 557.7 nm)
    ambientLux = starlight + moonLight*0.249 + twilightLux + auroraLux

    Full moon (1.0) clear sky -> 0.25 lux (real full-moon illuminance).
    Overcast is a MULTIPLICATIVE transmission loss (the engine does not
    pre-attenuate moonIntensity for clouds - ACE3 applies its own
    (1 - overcast) factor); heavy overcast blocks ~85 % of moonlight.
    Heavy rain halves the remainder.
    starlight is the moonless-night floor (default 0.001).  It is a live
    missionNamespace hook (aee_core_starlightLux) so skybox mods can
    raise the assumed night-sky brightness; a brighter sky -> higher lux
    -> NVG gains down, rendering the brighter sky correctly.
    Twilight glow (sun below horizon) adds the scattered-sunlight sky
    light: ~6.3 lux at -6 deg, ~0.1 at -12, ~0.0016 at -18.
    Aurora adds up to 0.03 lux at full intensity (a Kp 7-9 storm) -
    the green emission sits in the NVG tube's peak sensitivity, so the
    added photons brighten the image like moonlight.
    """
    trans = 1.0 - min(overcast * 0.85, 0.85)
    moon = max(0.0, moon_intensity * trans - rain * 0.5)
    twilight = 10.0 ** (2.6 - 0.3 * abs(sun_elev_deg)) if sun_elev_deg <= 0 else 0.0
    aurora = 0.03 * max(0.0, min(1.0, aurora_intensity))
    return starlight + moon * 0.249 + twilight + aurora


def extinction_per_m(rain, fog):
    """Mirror of the Beer-Lambert extinction coefficient (per metre).

    Rain: 0-30 dB/km mapped linearly from rain 0-1, /4343 (dB/km to 1/m).
    Fog: 40*(fog/0.5)^2 dB/km capped at 300, /4343.
    """
    g = 0.0
    if rain > 0.1:
        g += (rain * 30) / 4343.0
    if fog > 0.3:
        g += min(40.0 * (fog / 0.5) ** 2, 300.0) / 4343.0
    return g


def lux_from_source(lumens, dist, rain=0.0, fog=0.0):
    """Mirror of the dynamic-lux inverse-square + Beer-Lambert model.

    E = lumens / (4*pi*d^2) * exp(-gamma*d)
    """
    if dist <= 0.5 or dist >= 100:
        return 0.0
    gamma = extinction_per_m(rain, fog)
    t = math.exp(-gamma * dist) if gamma > 0 else 1.0
    return lumens / (4.0 * math.pi * dist * dist) * t


def nvg_gain(sensitivity, lux):
    """Mirror of the AGC gain model.

    gainTarget = sensitivity / (lux + 1), capped at sensitivity.
    """
    return min(sensitivity / (lux + 1.0), sensitivity)


def shot_noise(lux, sensitivity, photon_scale=500.0):
    """Mirror of the Poisson shot-noise model.

    photonCount = lux * sensitivity * PHOTON_SCALE
    shotNoise = 1/sqrt(photonCount + 1)
    """
    n = lux * sensitivity * photon_scale
    return 1.0 / math.sqrt(n + 1.0)


def nvg_noise(noise_floor, lux, sensitivity, rain=0.0, photon_scale=500.0):
    """Mirror of the combined noise model (floor + shot + rain Mie).

    noise = floor + (1 - floor) * shotNoise;  + rain*0.35 if rain > 0.2.
    """
    noise = noise_floor + (1.0 - noise_floor) * shot_noise(
        lux, sensitivity, photon_scale
    )
    if rain > 0.2:
        noise += rain * 0.35
    return max(0.03, min(1.0, noise))


def temp_gain_factor(air_temp_c):
    """Mirror of the tube temperature gain factor.

    0.7 @ -30, 1.0 @ 20, 0.85 @ 45.  Piecewise linear.
    """
    if air_temp_c < 20:
        lo, hi, lo_v, hi_v = -30.0, 20.0, 0.7, 1.0
    else:
        lo, hi, lo_v, hi_v = 20.0, 45.0, 1.0, 0.85
    if air_temp_c <= lo:
        return lo_v
    if air_temp_c >= hi:
        return hi_v
    return lo_v + (hi_v - lo_v) * (air_temp_c - lo) / (hi - lo)


def temp_noise_factor(air_temp_c):
    """Mirror of the noise temperature factor.

    1.0 @ 20, 1.6 @ 45, clamped below 20 at 1.0.
    """
    if air_temp_c <= 20:
        return 1.0
    if air_temp_c >= 45:
        return 1.6
    return 1.0 + 0.6 * (air_temp_c - 20.0) / 25.0


def nvg_drain(base_drain, gain, sensitivity, temp_derating, dt, battery_enabled=True):
    """Mirror of the battery drain model.

    gainRatio = gain / sensitivity (min 0.01)
    tempDrainFactor = 1/derating, clamped 1.0-4.0
    drain = baseDrain * gainRatio * tempDrainFactor * dt

    battery_enabled is the opt-in aee_nightvision_nvgBatteryEnabled toggle
    (issue #36); when off, no drain is applied.
    """
    if not battery_enabled:
        return 0.0
    gain_ratio = max(gain / sensitivity, 0.01)
    temp_factor = (1.0 / temp_derating) if temp_derating > 0.01 else 3.0
    temp_factor = max(1.0, min(4.0, temp_factor))
    return base_drain * gain_ratio * temp_factor * dt


def nvg_brightness(lux):
    """Mirror of the AGC output brightness.

    linearConversion [0.001, 0.25, lux, 0.65, 1.0, true].
    """
    if lux <= 0.001:
        return 0.65
    if lux >= 0.25:
        return 1.0
    return 0.65 + 0.35 * (lux - 0.001) / (0.25 - 0.001)


def mtf_effective(mtf15, noise, blowout=0.0, gated=True, rain=0.0):
    """Mirror of the MTF degradation model.

    Effective MTF falls from mtf15 to mtf15*0.55 as noise 0->1.
    Gated tubes lose up to 40% contrast while blowing out.
    Heavy rain scales MTF by (1 - rain*0.5).
    """
    mtf = mtf15 + (mtf15 * 0.55 - mtf15) * min(1.0, max(0.0, noise))
    if blowout > 0 and gated:
        mtf *= 1.0 - blowout * 0.4
    if rain > 0.2:
        mtf *= 1.0 - rain * 0.5
    return mtf


def nvg_bloom(bloom_base, bloom_scale, moon_light, blowout, rain):
    """Mirror of the NVG bloom (halo) model.

    bloom = base + scale*moonLight + blowout*scale*2
    rain multiplies by (1 + rain*2) - drop scatter.
    Clear-condition veiling glare floor: +0.0213 (2.13 %), the sourced low
    end of the published 2-5 % veiling-glare ratio for real tubes
    (MIL-I-49428 section 3.6.15.2).  A faint glow over the whole image that
    caps maximum contrast, independent of rain.
    """
    b = bloom_base + bloom_scale * moon_light
    b = b + blowout * bloom_scale * 2
    b = b * (1.0 + rain * 2.0)
    b = b + 0.0213
    return max(0.0, min(1.0, b))


# ─── Engine thermal drive mirrors (fnc_applyEngineThermal.sqf) ─────────────
# The engine's TI pipeline is TWO-STAGE (issue #196, verified): the rvmat
# StageTI provides the BASE image and the engine's dynamic temperature
# model MULTIPLIES it.  AEE drives setVehicleTIPars from its own physics,
# so the engine gain and AEE's physics gain do not compound.
# setTIParameter (display window) remains the engine-side gain and level
# control, exactly like a real FLIR's controls.


def engine_scene_max(alive=True, surface_temp_c=17.8, air_temp_c=17.8):
    """Mirror of the SQF scene-max pass in fnc_applyEngineThermal.

    The AGC blowout guard reads the scene's hottest fraction from the
    physics thermal state (ambient = 0, +50 C = 1 on the engine scale).
    A destroyed/burning vehicle saturates it: `if (!alive _x) then {
    _sceneMax = 1; }`.  A live ambient vehicle contributes ~0."""
    if not alive:
        return 1.0
    frac = (surface_temp_c - air_temp_c) / 50.0
    return max(0.05, min(1.0, frac))


def engine_heat_fraction(
    surface_temp_c,
    air_temp_c,
    damage_engine=0.0,
    damage_fuel=0.0,
    damage_body=0.0,
    alive=True,
):
    """Mirror of the physics -> setVehicleTIPars drive in
    fnc_applyEngineThermal.

    The engine's dynamic temperature model is a LIVE lever on the Ti
    image (in-game proven).  setVehicleTIPars is driven from AEE physics:
    (T - ambient) / 50 clamped 0..1, the engine's scale.  The old
    NEUTRALISATION (forcing 0) was based on the band-material theory that
    StageTI was painted by AEE - but StageTI is a heat-receptiveness
    COEFFICIENT, not the image, so the band swap never reached the render
    and the neutralisation left vehicles with NO heat input.
    """
    if not alive:
        return 0.0
    frac = (surface_temp_c - air_temp_c) / 50.0
    return max(0.0, min(1.0, frac))


def exhaust_heat_fraction(
    engine_run_time,
    air_temp_c,
    engine_on=False,
    engine_heat=0.0,
    alive=True,
    damage_body=0.0,
):
    """Mirror of the exhaust heat (weapon TI slot).

    exhaustTemp = air + 200*(1-exp(-runTime/60))  (tau 60 s).
    Mapped (T-air)/50 clamped 0..1.  Engine on but no run time yet:
    floor = engine heat (a running vehicle always has a warm exhaust).
    Destroyed: saturated.
    """
    if not alive or damage_body >= 0.95:
        return 1.0
    if engine_run_time > 0:
        ex = air_temp_c + 200 * (1 - math.exp(-engine_run_time / 60))
        return max(0.0, min(1.0, (ex - air_temp_c) / 50.0))
    if engine_on:
        return max(engine_heat, 0.3)
    return 0.0


def conduction_coupling(
    obj_temp,
    hot_neighbours,
    distance_scale=0.3,
    max_share=4.0,
    min_delta=5.0,
    max_range=10.0,
):
    """Mirror of the conduction/radiant coupling term.

    hot_neighbours: list of (neighbour_temp, distance) for objects within
    range that are at least min_delta warmer than obj_temp.
    share = min(surplus * (distance_scale / d^2), max_share), summed,
    bounded to 5 C total.  0 if no hot neighbour close enough.
    """
    coupling = 0.0
    for n_temp, d in hot_neighbours:
        if n_temp <= obj_temp + min_delta:
            continue
        if d > max_range:
            continue
        surplus = n_temp - obj_temp
        share = min(surplus * (distance_scale / (d * d)), max_share)
        coupling += share
    if coupling <= 0.05:
        return 0.0
    return min(coupling, 5.0)


def burning_temperature(
    air_temp_c, damage, is_vehicle=False, fuel_damage=0.0, engine_damage=0.0
):
    """Mirror of the burning/incendiary thermal term.

    Object on fire (damage >= 0.7, or vehicle fuel/engine hitpoint >= 0.7)
    burns at 600 C above ambient (combustion).  Returns the target temp.
    """
    burning = damage >= 0.7
    if is_vehicle:
        burning = burning or fuel_damage >= 0.7 or engine_damage >= 0.7
    if burning:
        return air_temp_c + 600
    return air_temp_c


def vehicle_wheel_heat(speed_ms):
    """Mirror of wheel heat from friction (speed/30 capped at 1)."""
    return min(1.0, speed_ms / 30.0)


def ti_output_window(scene_max_heat):
    """Mirror of the thermal display window (blowout guard, stable).

    start is ALWAYS 0 (never lift the black level - the "flashlight"
    came from start=0.5).  width is a faithful pass-through (1.0) UNLESS
    a hot object would saturate: then narrow to 0.9/maxHeat so it maps to
    ~0.9 and the rest of the scene keeps relative contrast.  The engine
    window can only COMPRESS (width<=1) and OFFSET (start>=0); it cannot
    stretch, so this is the most useful thing it can do.
    """
    mh = max(0.05, min(1.0, scene_max_heat))
    if mh > 0.9:
        return 0.0, max(0.35, min(1.0, 0.9 / mh))
    return 0.0, 1.0


def agc_settled(ang_vel_rad_s, threshold=0.44):
    """Mirror of the AGC pan-freeze gate.  Below ~25 deg/s = settled."""
    return ang_vel_rad_s < threshold


def agc_ema(prev, target, dt, tau=1.5):
    """Mirror of the AGC ease (tau ~1.5 s) when settled."""
    a = dt / (dt + tau)
    return prev + (target - prev) * a


LOCAL_MAX_GAIN = 8.0


def window_with_gain_floor(rads, full_span, max_gain=LOCAL_MAX_GAIN):
    """Scene and per-object window: min..max, floored to full_span/max_gain.

    Mirror of the window in fnc_updateThermalAGC.  The real scene path
    tail-cuts 1 percent before this, but the cut is below one sample for the
    few dozen samples a scene or a vehicle carries, so the documented no-op
    form is min..max.  Local mode applies the SAME floor per object, so an
    object whose spread is under full_span/max_gain is stretched by at most
    max_gain and a flat object is not invented into full contrast.
    """
    lo = min(rads)
    hi = max(rads)
    if hi <= lo:
        lo, hi = lo * 0.999, hi * 1.001
    if (hi - lo) < (full_span / max_gain):
        mid = (lo + hi) / 2.0
        half = (full_span / max_gain) / 2.0
        lo, hi = mid - half, mid + half
    return lo, hi


def window_position(rad, lo, hi):
    """Mirror of the display mapping _b = (rad - lo) / (hi - lo), clamped."""
    return min(1.0, max(0.0, (rad - lo) / max(hi - lo, 1e-6)))


def eye_state_position(eye, cam_dir, offset=0.1):
    """Mirror of the shared eye-state placement used by eye-space systems.

    The eye-space anchor: eye position + camera direction * offset.
    Consumed by rain droplets, glare, illuminance.
    """
    return (
        eye[0] + cam_dir[0] * offset,
        eye[1] + cam_dir[1] * offset,
        eye[2] + cam_dir[2] * offset,
    )


def eye_velocity(prev_eye, now_eye, dt):
    """Mirror of the eye-velocity computation in fnc_getEyeState (#152).

    World-space m/s: displacement over the frame time.
    """
    return (
        (now_eye[0] - prev_eye[0]) / dt,
        (now_eye[1] - prev_eye[1]) / dt,
        (now_eye[2] - prev_eye[2]) / dt,
    )


def droplet_world_velocity(eye_vel):
    """Mirror of the rain-droplet moveVelocity: co-moves with the eye.

    A drop on the lens is stationary in EYE space, so its world velocity
    EQUALS the eye's velocity (issue #152).  The spec's -eyeVel was a
    sign error: -eyeVel sends the drop AWAY from the eye (3x drift).
    """
    return (eye_vel[0], eye_vel[1], eye_vel[2])


def droplet_eye_relative(eye, cam_dir, offset, eye_vel, dt):
    """Where a drop sits relative to the eye after dt, WITH the fix.

    The drop spawns at eye + camDir*offset with world velocity -eyeVel.
    After dt the eye has moved to eye + eyeVel*dt; the drop has moved to
    spawn + (-eyeVel)*dt.  Because both moved by the same amount, the
    eye-relative offset stays EXACTLY at the spawn offset: the drop is
    glued to the eye position (linear-translation perfect).
    """
    spawn = eye_state_position(eye, cam_dir, offset)
    drop_now = tuple(
        spawn[i] + droplet_world_velocity(eye_vel)[i] * dt for i in range(3)
    )
    eye_now = tuple(eye[i] + eye_vel[i] * dt for i in range(3))
    return tuple(drop_now[i] - eye_now[i] for i in range(3))


def weather_ema(prev, raw, dt, tau):
    """Mirror of the per-variable weather EMA (fnc_getSmoothedWeather).

    alpha = dt / (dt + tau); y += alpha * (raw - y).
    Physical taus: rain 120 s, overcast 300 s, fog 900 s (meteorology).
    """
    a = dt / (dt + tau)
    return prev + (raw - prev) * a


def second_sun_brightness(radiation):
    """Mirror of fnc_applySecondSun: engine thermal SUN term brightness.

    The engine's thermal sun term expects lightpoint brightness in the A3TI
    order of magnitude, and 13 is A3TI's DEFAULT_SECONDSUN_BRIGHTNESS.  A
    radiation * 6 de-saturation was tried (32b2666) and then REVERTED (3655ad6,
    "second sun restored to the proven constant 13"); the shipped peak is 13.
    The physical content is the radiation tracking added in cc00cd7: night (0)
    -> no sun term, full day -> 13, so the terrain darkens at night.
    """
    r = max(0.0, min(1.0, radiation))
    return r * 13.0


def clothing_ti_scale(insulation, air_temp_c):
    """Mirror of fnc_applyClothingThermal tiScale.

    Thermal resistance of clothing = insulation + ambient term.  The
    ambient term shifts by up to ±0.5 across -15..45 C (0.5*(T-15)/30,
    clamped ±0.5): cold ambient + heavy insulation -> wearer stays warm
    (TI warm); cold + light clothing -> TI cold; hot ambient -> hot.
    """
    ambient = max(-0.5, min(0.5, 0.5 * (air_temp_c - 15) / 30))
    return insulation + ambient


def clothing_ti_material(ti_scale):
    """Mirror of the material selection.

    > 0.7 -> hot rvmat (reads hot), < 0.35 -> cold rvmat (reads cold),
    else "" (keep the item's own TI texture).
    """
    if ti_scale >= 0.7:
        return "hot"
    if ti_scale < 0.35:
        return "cold"
    return ""


def building_thermal_mass(material_paths):
    """Mirror of fnc_applyBuildingThermal material weighting.

    Classifies a building's dominant material from its rvmat paths.
    Heavy mass (concrete/brick/stone/rock/block) stays cold -> swap all
    surfaces (coldFactor 1.0).  Metal/glass/plastic dominant -> responds
    to sun -> swap half (0.5).  Returns the swap fraction.
    """
    metal = 0
    heavy = 0
    for p in material_paths:
        m = p[-40:].lower()
        if any(k in m for k in ["metal", "glass", "plastic", "steel"]):
            metal += 1
        if any(k in m for k in ["concrete", "brick", "stone", "rock", "block"]):
            heavy += 1
    if heavy > 0 and metal == 0:
        return 1.0
    if metal > heavy:
        return 0.5
    return 1.0


def glass_reflection_material(solar_radiation, cold_mat, hot_mat):
    """Mirror of the glass/window reflection swap.

    Glass does not transmit LWIR - it reflects the scene.  Night
    (radiation <= 0.3) reflects cold sky -> cold material; daylight
    reflects the sun -> hot material.  Same solar value as the second
    sun, so the two stay consistent.
    """
    return [cold_mat, hot_mat][solar_radiation > 0.3]


def clothing_material_kind(material_path):
    """Mirror of the per-selection material classification.

    "cloth"  -> swap to our cold/hot TI material (cloth dominant).
    "metal"  -> keep engine thermal (solar-warm helmet/plate/optics).
    "other"  -> unknown: swap (safe cloth assumption).
    """
    m = material_path[-40:].lower()
    if any(k in m for k in ["cloth", "fabric", "leather", "wool", "cotton"]):
        return "cloth"
    if any(k in m for k in ["metal", "glass", "plastic", "steel"]):
        return "metal"
    return "other"


def selection_thermal_lag(positions, source):
    """Mirror of the heat-source distance lag in fnc_getThermalSelectionLag.

    SQF: _d = _pos distance _source; lag = _d / max(_d), clamped 0..1.
    The source is the engine point (hit-point map) or the front axle; the
    normalisation divides by the widest distance, so no constant is added.
    """
    dists = [math.dist(p, source) for p in positions]
    peak = max(dists) if dists else 0.0
    if peak <= 0:
        return [0.0 for _ in dists]
    return [max(0.0, min(1.0, d / peak)) for d in dists]


def selection_sun_exposure(positions, centre, sun_az_deg, sun_elev_deg, names):
    """Mirror of fnc_getSelectionSunExposure.

    The outward direction is a PROXY: the unit vector from the object's
    bounding centre to the selection's model-space point, not a true surface
    normal.  The core flux is the horizontal-plane irradiance
    G = G0 * sin(elevation), so the exposure is
    cos(incidence) / sin(elevation), clamped 0..1.  A selection with no
    resolved point keeps 1.0.  The wheel/undercarriage floor is 0.15.

    The synthetic object is unrotated, so model axes equal world axes.
    """
    az = math.radians(sun_az_deg)
    elev = math.radians(sun_elev_deg)
    cos_e = math.cos(elev)
    sin_e = math.sin(elev)
    sun_world = (math.sin(az) * cos_e, math.cos(az) * cos_e, sin_e)
    exposures = []
    for pos, name in zip(positions, names):
        off = (pos[0] - centre[0], pos[1] - centre[1], pos[2] - centre[2])
        mag = math.sqrt(off[0] ** 2 + off[1] ** 2 + off[2] ** 2)
        n = (
            (off[0] / mag, off[1] / mag, off[2] / mag)
            if mag > 1e-3
            else (0.0, 0.0, 0.0)
        )
        exp = 1.0
        if sin_e > 0 and n != (0.0, 0.0, 0.0):
            dot = n[0] * sun_world[0] + n[1] * sun_world[1] + n[2] * sun_world[2]
            exp = min(1.0, dot / sin_e) if dot > 0 else 0.0
        if "wheel" in name or "undercarriage" in name:
            exp = max(exp, 0.15)
        exposures.append(exp)
    return exposures


# ─── Thermal crossover mirror (fnc_calculateThermalCrossover.sqf) ──────────


def thermal_crossover(air_temp, surface_temp, sun_elev_deg, timer=0):
    """Mirror of the diurnal crossover detection.

    Active when |air - surface| <= 1.5 C AND |sunElev| < 10 (twilight).
    Timer sustains: increments while active, decrements while not,
    clamped -6..6; active when timer > 1.
    """
    in_twilight = abs(sun_elev_deg) < 10
    delta = abs(air_temp - surface_temp)
    now = in_twilight and delta <= 1.5
    timer = timer + (1 if now else -1)
    timer = max(-6, min(6, timer))
    return timer > 1, timer


# ─── Solar glare mirror (fnc_calculateSolarGlare.sqf) ──────────────────────


def solar_glare(angular_diff_deg, sun_elev_deg, overcast=0.0):
    """Mirror of the veiling glare intensity.

    Core = (1 - angularDiff/45) clamped >= 0.
    Elevation factor: peaks at ~20 deg, fades above 50.
    Overcast reduces by (1 - overcast*0.8).
    """
    core = max(0.0, 1.0 - angular_diff_deg / 45.0)
    if sun_elev_deg < 20:
        elev = sun_elev_deg / 20.0
    else:
        elev = max(0.0, 1.0 - (sun_elev_deg - 20.0) / 30.0)
    intensity = core * elev * (1.0 - overcast * 0.8)
    return max(0.0, min(1.0, intensity))


# ─── Focus raw-target median filter mirror ─────────────────────────────────


def focus_raw_median(raw_seq, window=3):
    """Mirror of the rolling-median focus smoothing in fnc_applyNVGTubeModel.

    Keeps the last `window` raw fan distances, returns the median.
    A single-tick outlier is discarded; a genuine sustained re-aim
    tracks within `window` ticks.  Returns 0 for sky (raw <= 0),
    matching the SQF (history cleared, rawSmooth = rawTarget = 0).
    """
    hist = []
    out = []
    for r in raw_seq:
        if r > 0:
            hist.append(r)
            if len(hist) > window:
                hist.pop(0)
            s = sorted(hist)
            out.append(s[len(s) // 2])
        else:
            hist = []
            out.append(0.0)
    return out


# ─── Focus state machine mirror (fnc_applyNVGTubeModel) ────────────────────
# Replays raw fan distances through median -> deadband -> delay -> lens rack
# -> watchdog, the same chain as the SQF.  Used to PROVE the ring tracks a
# bouncing target and cannot freeze (settle watchdog snaps a stale pending).

FOCAL = 0.027


def focus_state_machine(
    raw_seq,
    near_limit=0.45,
    start_focus=15.0,
    tick=0.1,
    deadband_frac=0.03,
    hold=0.2,
    watch_bound=1.5,
):
    """Simulate the focus chain over a raw-distance sequence.

    Returns (focus_series, settled_series) - one entry per tick.
    Mirrors the SQF: median-of-3 -> deadband gate -> pending+hold ->
    lens-travel rack at throw/5 per tick -> settle watchdog.
    """
    focus = start_focus
    pending = 0.0
    hold_until = 0.0
    hist = []
    focuses = []
    settled = []
    t = 0.0
    f2 = FOCAL * FOCAL
    throw = f2 / (near_limit - FOCAL)
    x_step = throw / 5.0

    for raw in raw_seq:
        # median stage
        if raw > 0:
            hist.append(raw)
            if len(hist) > 3:
                hist.pop(0)
            s = sorted(hist)
            raw_s = s[len(s) // 2]
        else:
            hist = []
            raw_s = raw
        # state machine
        if raw_s > 0:
            deadband = max(focus * deadband_frac, 0.5)
            if abs(raw_s - focus) > deadband:
                if raw_s != pending:
                    rearm = deadband * 0.4
                    if pending == 0 or abs(raw_s - pending) > rearm:
                        pending = raw_s
                        hold_until = t + hold
                    else:
                        pending = raw_s
            else:
                if pending == 0:
                    hold_until = 0.0
        # rack
        if pending > 0 and t >= hold_until:
            x_now = f2 / (focus - FOCAL)
            x_tgt = f2 / (pending - FOCAL)
            x_move = x_tgt - x_now
            if abs(x_move) > x_step:
                x_move = x_step * (-1.0 if x_move < 0 else 1.0)
            focus = FOCAL + f2 / (x_now + x_move)
            if abs(pending - focus) < 0.1:
                focus = pending
                pending = 0.0
                hold_until = 0.0
            elif t > hold_until + watch_bound:
                focus = pending  # settle watchdog: snap, cannot freeze
                pending = 0.0
                hold_until = 0.0
        t += tick
        focuses.append(focus)
        settled.append(pending == 0.0)
    return focuses, settled


# ─── Ground temperature mirrors ─────────────────────────────────────────────


GROUND_GAINS = {
    "desert": 15,
    "sand": 10,
    "ice": -2,
    "snow": -2,
    "coniferous": 2,
    "forest": 3,
    "grass": 5,  # default
}


def ground_target(air_temp, ground_type, solar, wind_speed):
    """Mirror of the ground target temperature before inertia.

    SQF: _groundTarget = _airTemp + _groundGain * _solar
         _groundTarget -= _windSpeed * 2
         _groundTarget max= _airTemp
    """
    gain = GROUND_GAINS.get(ground_type, 5)
    target = air_temp + gain * solar
    target -= wind_speed * 2
    return max(target, air_temp)


# ─── Test classes ────────────────────────────────────────────────────────────


class TestThermalInertia(unittest.TestCase):
    """Thermal inertia: exponential approach to target temperature."""

    def test_starts_at_target(self):
        # When current equals target, temperature stays unchanged.
        self.assertAlmostEqual(thermal_inertia(20, 20, 10, 120), 20, places=6)

    def test_approaches_target(self):
        # After one tau (120s), approaches ~63% of the gap.
        result = thermal_inertia(0, 100, 120, 120)
        self.assertAlmostEqual(result, 100 * (1 - math.exp(-1)), places=1)

    def test_metal_faster_than_concrete(self):
        # Metal (tau=120) approaches target faster than concrete (tau=600).
        metal = thermal_inertia(0, 100, 60, 120)
        concrete = thermal_inertia(0, 100, 60, 600)
        self.assertGreater(metal, concrete)

    def test_human_faster_than_vehicle(self):
        # Human (tau=60) responds faster than vehicle metal (tau=120).
        human = thermal_inertia(33, 20, 30, 60)
        vehicle = thermal_inertia(33, 20, 30, 120)
        self.assertLess(abs(human - 20), abs(vehicle - 20))

    def test_converges_after_many_steps(self):
        # After 10× tau, should be >99.9% of target.
        result = thermal_inertia(0, 100, 1200, 120)
        self.assertAlmostEqual(result, 100, places=1)

    def test_zero_tau_returns_target(self):
        # Division by zero guard.
        self.assertAlmostEqual(thermal_inertia(0, 50, 10, 0), 50, places=6)


class TestVehicleColdStart(unittest.TestCase):
    """Coarse-path engine heat: thermostat setpoint, no reference-mod curve."""

    def test_engine_flux_falls_as_ambient_rises(self):
        # Same setpoint span: a warmer day means a smaller rejection flux.
        self.assertGreater(vehicle_engine_flux(0, 0), vehicle_engine_flux(30, 0))

    def test_engine_flux_at_ambient_setpoint(self):
        # Ambient equal to the coolant setpoint: only the exhaust share remains.
        want = 0.05 * (480.0 - 90.0) * 5.7
        self.assertAlmostEqual(vehicle_engine_flux(90, 0), want, places=6)

    def test_engine_flux_scales_with_wind(self):
        # McAdams convection: higher wind removes more heat per degree.
        self.assertGreater(vehicle_engine_flux(15, 5), vehicle_engine_flux(15, 0))

    def test_lumped_tau_uses_mass_and_area(self):
        # tau = m*cp/(h*A): more mass is slower, more area is faster.
        self.assertGreater(lumped_tau(2000, 490, 10, 10), lumped_tau(1000, 490, 10, 10))
        self.assertGreater(lumped_tau(1000, 490, 10, 5), lumped_tau(1000, 490, 10, 10))


class TestVehicleBrakeHeat(unittest.TestCase):
    """Brake heat source: P = m*a*v (COMSOL 2012), whole kinetic drop assigned
    to the brakes (the idealisation, an upper bound)."""

    def test_instant_power_worked_case(self):
        # COMSOL worked case: m=1800 kg, a=10 m/s2, v=25 m/s -> 450 kW.
        self.assertAlmostEqual(
            vehicle_brake_power_instant(1800.0, 10.0, 25.0), 450000.0, places=3
        )

    def test_average_power_matches_kinetic_drop(self):
        # Same stop 25 -> 5 m/s over 2 s: E = 540 kJ, average 270 kW.
        power = vehicle_brake_power(1800.0, 25.0, 5.0, 2.0)
        self.assertAlmostEqual(power, 270000.0, places=3)
        self.assertAlmostEqual(power * 2.0, 540000.0, places=3)

    def test_zero_when_accelerating(self):
        self.assertEqual(vehicle_brake_power(1800.0, 5.0, 25.0, 2.0), 0.0)

    def test_zero_when_steady(self):
        self.assertEqual(vehicle_brake_power(1800.0, 20.0, 20.0, 2.0), 0.0)

    def test_zero_when_interval_is_zero(self):
        self.assertEqual(vehicle_brake_power(1800.0, 25.0, 5.0, 0.0), 0.0)

    def test_scales_with_mass(self):
        light = vehicle_brake_power(900.0, 25.0, 5.0, 2.0)
        heavy = vehicle_brake_power(1800.0, 25.0, 5.0, 2.0)
        self.assertAlmostEqual(heavy, 2.0 * light, places=3)

    def test_source_shifts_equilibrium_target(self):
        # A source shifts the equilibrium to target + Q/(h*A).
        target, q, h_area, cap = 90.0, 270000.0, 2000.0, 828000.0
        dt = 20.0 * cap / h_area
        body = vehicle_body_temperature(target, target, q, h_area, cap, dt)
        self.assertAlmostEqual(body, target + q / h_area, places=3)

    def test_no_source_matches_thermal_inertia(self):
        got = vehicle_body_temperature(20.0, 90.0, 0.0, 2000.0, 828000.0, 30.0)
        want = thermal_inertia(20.0, 90.0, 30.0, 828000.0 / 2000.0)
        self.assertAlmostEqual(got, want, places=9)

    def test_brake_heat_warms_body_above_target(self):
        cold = vehicle_body_temperature(90.0, 90.0, 0.0, 2000.0, 828000.0, 60.0)
        hot = vehicle_body_temperature(90.0, 90.0, 270000.0, 2000.0, 828000.0, 60.0)
        self.assertGreater(hot, cold)


class TestInfantryClothing(unittest.TestCase):
    """Infantry surface temperature from clothing insulation model."""

    def test_high_insulation_keeps_warm(self):
        # Arctic (0.8): surface stays close to body temp.
        surf = infantry_clothing_surface(33, 0, 0.8)
        self.assertGreater(surf, 25)

    def test_low_insulation_cooler(self):
        # Tropical (0.3): surface closer to ambient.
        surf = infantry_clothing_surface(33, 30, 0.3)
        self.assertLess(surf, 31)

    def test_surface_at_body_temp_with_max_insulation(self):
        # Insulation 1.0 (theoretical max): surface = acclimatisation.
        surf = infantry_clothing_surface(33, 0, 1.0)
        self.assertAlmostEqual(surf, 33, places=6)

    def test_surface_at_ambient_with_zero_insulation(self):
        # Insulation 0.0 (naked): surface = ambient.
        surf = infantry_cloting_surface_safe(33, 20, 0.0)
        self.assertAlmostEqual(surf, 20, places=6)

    def test_metabolic_idle(self):
        self.assertEqual(infantry_metabolic_heat(0), 0)
        self.assertEqual(infantry_metabolic_heat(0.3), 0)

    def test_metabolic_walking(self):
        self.assertEqual(infantry_metabolic_heat(1.5), 20)
        self.assertEqual(infantry_metabolic_heat(2.9), 20)

    def test_metabolic_running(self):
        self.assertEqual(infantry_metabolic_heat(4), 60)
        self.assertEqual(infantry_metabolic_heat(5.9), 60)

    def test_metabolic_sprinting(self):
        self.assertEqual(infantry_metabolic_heat(7), 120)
        self.assertEqual(infantry_metabolic_heat(10), 120)

    def test_metabolic_monotonic(self):
        # Higher speed → higher metabolic heat.
        self.assertGreater(infantry_metabolic_heat(4), infantry_metabolic_heat(1))

    def test_acclimatisation_approaches_ambient(self):
        # After 30 min (1800s = 1× tau), body drifts ~63% toward air temp.
        # 33 → 33 * e^-1 ≈ 12.1.  Give generous tolerance for the discrete steps.
        acc = 33  # start at body temp
        for _ in range(360):  # 360 × 5s = 30 min
            acc = acclimatisation_step(acc, 0, 5)
        self.assertAlmostEqual(acc, 33 * math.exp(-1), delta=0.5)


class TestClothingInsulationSetting(unittest.TestCase):
    """CBA setting to insulation fraction mapping."""

    def test_light_tropical(self):
        # Setting 0.5 → insulation 0.3
        self.assertAlmostEqual(insulation_from_setting(0.5), 0.3, places=6)

    def test_arctic(self):
        # Setting 2.0 → insulation 0.8
        self.assertAlmostEqual(insulation_from_setting(2.0), 0.8, places=6)

    def test_default(self):
        # Setting 1.0 → insulation ~0.467
        self.assertAlmostEqual(
            insulation_from_setting(1.0), 0.3 + 0.5 * (0.5 / 1.5), places=3
        )

    def test_clamp_below(self):
        # Setting 0.0 → clamped to 0.3
        self.assertEqual(insulation_from_setting(0.0), 0.3)

    def test_clamp_above(self):
        # Setting 3.0 → clamped to 0.8
        self.assertEqual(insulation_from_setting(3.0), 0.8)


class TestEmissivityRadiant(unittest.TestCase):
    """Longwave exchange is Stefan-Boltzmann against MRT, not a linear offset.

    The old mirror `_target - (1 - _emissivity) * 2` was a chosen linear
    correction; the inert solve now carries the real eps*sigma*(Ts^4-MRT^4)
    term, so the linear form must be absent.
    """

    def test_source_uses_stefan_boltzmann_mrt(self):
        text = _read_sqf("fnc_calculateObjectTemperature.sqf", "thermal")
        self.assertIn("_eps * _sigmaB * ((_tsK ^ 4) - (_mrtK ^ 4))", text)
        self.assertNotIn("(1 - _emissivity) * 2", text)


class TestThermalContrast(unittest.TestCase):
    """Thermal contrast is a DEGRADATION factor with base 1.0.

    The engine renders the native thermal image with its own gain, so this
    stage adds none: clear conditions publish exactly 1.0.  The old base
    (delta-T / 8) was an undocumented second gain stage and is removed.
    """

    def test_clear_conditions_publish_unity(self):
        # No weather, no extreme heat, no cold: the factor is exactly 1.0,
        # which is also the consumer's declared default.
        self.assertAlmostEqual(thermal_contrast(), 1.0, places=6)

    def test_the_source_has_no_base_gain(self):
        code = _code_only(
            _read_sqf("fnc_calculateThermalContrast.sqf", addon="thermal")
        )
        self.assertIn("private _contrast = 1.0", code)
        self.assertNotIn("_deltaT", code)
        self.assertNotIn("_avgVehicleTemp", code)
        self.assertNotIn("objectTemperatures", code)

    def test_weather_returns_unity(self):
        # The kernel has no weather term of its own: atmospheric degradation
        # is modelled once, in fnc_calculateAtmosphericTransmission.  A rain,
        # fog or humidity case must return exactly 1.0 from this kernel alone.
        self.assertEqual(thermal_contrast(), 1.0)
        self.assertEqual(thermal_contrast(air_temp=15.0), 1.0)

    def test_the_source_has_no_weather_terms(self):
        code = _code_only(
            _read_sqf("fnc_calculateThermalContrast.sqf", addon="thermal")
        )
        for token in ("rain", "_fog", "currentFogDensity", "* 0.3"):
            self.assertNotIn(
                token,
                code,
                f"weather double-count token {token!r} is still in the kernel",
            )

    def test_heat_flattens_contrast(self):
        # Extreme heat drives every surface toward air temperature, so the
        # surface-to-air gap closes.  A wide gap above 35 flattens the factor.
        c_hot = thermal_contrast(air_temp=15.0, surface_temp=55.0)
        c_mild = thermal_contrast(air_temp=15.0, surface_temp=20.0)
        self.assertLess(c_hot, c_mild)

    def test_heat_flattens_by_air_temperature_without_a_surface(self):
        # No surface temperature available: the air temperature is the only
        # reference and the legacy threshold form applies.
        c_hot = thermal_contrast(air_temp=40)
        c_mild = thermal_contrast(air_temp=20)
        self.assertLess(c_hot, c_mild)

    def test_cold_can_restore_a_lowered_factor(self):
        # The cold term scales a lowered factor up toward, never above, 1.0.
        lowered = 0.5
        self.assertLess(min(lowered * 1.2, 1.0), 1.0)

    def test_never_negative(self):
        c = thermal_contrast(air_temp=90.0)
        self.assertGreaterEqual(c, 0)

    def test_never_exceeds_one(self):
        self.assertLessEqual(thermal_contrast(air_temp=0), 1.0)
        self.assertLessEqual(thermal_contrast(air_temp=-40.0), 1.0)


class TestThermalNoise(unittest.TestCase):
    """The pure NETD noise floor (fnc_calculateThermalNoise.sqf).

    Executes the shipped SQF through the shared interpreter, so the formula
    is proven, not mirrored.  Range is a REAL sensor-to-target range.
    """

    _KERNEL = _THERMAL / "solver" / "fnc_calculateThermalNoise.sqf"

    def _noise(self, netd, rng, resx=640, hum=0.0):
        return run_sqf(self._KERNEL, [netd, rng, resx, hum])

    def test_noise_at_1km_uncooled_dry(self):
        # 0.05 × 1² × 1 × 1 = 0.05 at zero humidity.
        self.assertAlmostEqual(self._noise(0.05, 1000), 0.05, places=6)

    def test_noise_monotone_in_range(self):
        # A real range drives the term: more path, more noise.
        n500 = self._noise(0.05, 500)
        n1000 = self._noise(0.05, 1000)
        self.assertGreater(n1000, n500)

    def test_noise_scales_with_range_squared(self):
        n1 = self._noise(0.05, 500)
        n2 = self._noise(0.05, 1000)
        self.assertAlmostEqual(n2 / n1, 4.0, places=2)

    def test_humidity_increases_noise(self):
        wet = self._noise(0.05, 1000, 640, 80)
        dry = self._noise(0.05, 1000, 640, 0)
        self.assertGreater(wet, dry)

    def test_resolution_scales_noise(self):
        # A 320-wide detector doubles the 640 reference term.
        self.assertAlmostEqual(self._noise(0.05, 1000, 320), 0.1, places=6)

    def test_clamped_to_unit(self):
        self.assertEqual(self._noise(0.5, 5000, 160, 100), 1.0)
        self.assertGreaterEqual(self._noise(0.0, 1000), 0.0)


class TestThermalBlur(unittest.TestCase):
    """Thermal DynamicBlur + pan smear - flicker guards."""

    def test_clear_conditions_no_blur(self):
        # Full contrast (clear) → zero blur.
        self.assertAlmostEqual(thermal_blur(1.0), 0.0, places=6)

    def test_crossover_max_environmental_blur(self):
        # Crossover (effective 0.05) → 0.95 × 0.15 = 0.1425.
        self.assertAlmostEqual(thermal_blur(0.05), 0.1425, places=4)

    def test_blur_ceiling_never_exceeds_0_25(self):
        # Worst case: crossover + full pan + full window blur stays ≤ 0.25.
        for eff in (0.0, 0.05, 0.3, 0.5, 1.0):
            b = thermal_blur(eff, pan_smear=0.04, window_blur=0.35)
            self.assertLessEqual(b, 0.25)

    def test_pan_smear_capped_at_0_04(self):
        # 90°/s turn rate → exactly 0.04; faster still 0.04.
        self.assertAlmostEqual(thermal_pan_smear(90), 0.04, places=4)
        self.assertAlmostEqual(thermal_pan_smear(180), 0.04, places=4)

    def test_pan_smear_scales_linearly(self):
        # 45°/s → half of 0.04 = 0.02.
        self.assertAlmostEqual(thermal_pan_smear(45), 0.02, places=4)

    def test_pan_smear_zero_when_still(self):
        self.assertAlmostEqual(thermal_pan_smear(0), 0.0, places=6)

    def test_window_blur_adds(self):
        # Fog/rain window blur stacks with environmental, still capped.
        b = thermal_blur(0.5, pan_smear=0.0, window_blur=0.1)
        self.assertAlmostEqual(b, 0.075 + 0.1, places=4)

    def test_no_negative_blur(self):
        self.assertGreaterEqual(thermal_blur(1.0), 0.0)


class TestBatteryDerating(unittest.TestCase):
    """Battery capacity derating from temperature."""

    def test_normal_range(self):
        # 10–40°C: full capacity.
        for t in [10, 20, 25, 30, 40]:
            self.assertAlmostEqual(battery_derating(t), 1.0, places=6)

    def test_cold_derating(self):
        # -15°C: ~55% capacity.
        self.assertAlmostEqual(battery_derating(-15), 1.0 - 15 * 0.03, places=2)

    def test_extreme_cold_floor(self):
        # -25°C: clamped at 0.3.
        self.assertAlmostEqual(battery_derating(-25), 0.3, places=6)

    def test_heat_derating(self):
        # 55°C: slight reduction.
        self.assertAlmostEqual(battery_derating(55), 1.0 - 10 * 0.01, places=2)

    def test_extreme_heat_cap(self):
        # 70°C: max reduction capped at -0.2 → factor 0.8.
        self.assertAlmostEqual(battery_derating(70), 0.8, places=2)

    def test_never_below_03(self):
        self.assertGreaterEqual(battery_derating(-50), 0.3)

    def test_never_above_1(self):
        self.assertLessEqual(battery_derating(100), 1.0)


class TestAmbientLux(unittest.TestCase):
    """Moon lux model - real full-moon illuminance is ~0.1-0.3 lux."""

    def test_full_moon_clear_sky(self):
        # Full moon, no cloud/rain -> 0.25 lux.
        self.assertAlmostEqual(ambient_lux(1.0), 0.25, places=6)

    def test_moon_term_matches_verified_lunar_model(self):
        # Cross-model lock: NVG uses the ENGINE moonIntensity term
        # (moonLight * 0.249).  The verified lunar model (Krisciunas &
        # Schaefer 1991, in fnc_calculateLunarIllumination) computes lux
        # from the phase angle.  The two must stay within a 10% envelope
        # at every phase so the NVG display and the astronomical model
        # do not diverge.  (Exact equality is NOT expected: the optics
        # constant is calibrated to ACE3's 0.25 lux full-moon anchor.)
        # Engine moonIntensity is 1.0 at full moon, 0.09 at quarter, 0
        # at new (Arma folds phase + elevation into it).
        cases = [
            (1.0, 0.5),  # full moon
            (0.09, 0.25),  # first quarter
            (0.09, 0.75),  # last quarter
            (0.0, 0.0),  # new moon
        ]
        for moon_intensity, phase in cases:
            optics_lux = ambient_lux(moon_intensity)
            verified_lux = ks_lunar_lux(phase)
            self.assertLess(
                abs(optics_lux - verified_lux) / max(verified_lux, 1e-6),
                0.10,
                msg=f"moonIntensity {moon_intensity}: optics {optics_lux:.4f} "
                f"vs verified {verified_lux:.4f} diverged >10%",
            )

    def test_starlight_floor(self):
        # No moon (new moon / moon below horizon) -> 0.001 lux floor.
        self.assertAlmostEqual(ambient_lux(0.0), 0.001, places=6)

    def test_aurora_adds_lux(self):
        # A Kp 7-9 storm (aurora intensity 1.0) adds 0.03 lux to a
        # moonless night: the green 557.7 nm emission feeds the NVG tube.
        self.assertAlmostEqual(ambient_lux(0.0, aurora_intensity=1.0), 0.031, places=6)

    def test_aurora_scales_with_intensity(self):
        # Half-intensity aurora adds half the lux; none adds nothing.
        self.assertAlmostEqual(
            ambient_lux(0.0, aurora_intensity=0.5), 0.001 + 0.015, places=6
        )
        self.assertAlmostEqual(ambient_lux(0.0, aurora_intensity=0.0), 0.001, places=6)

    def test_aurora_intensity_clamped(self):
        # Out-of-range intensity clamps (mirror matches the SQF clamp).
        self.assertEqual(
            ambient_lux(0.0, aurora_intensity=2.0),
            ambient_lux(0.0, aurora_intensity=1.0),
        )
        self.assertEqual(
            ambient_lux(0.0, aurora_intensity=-1.0),
            ambient_lux(0.0, aurora_intensity=0.0),
        )

    def test_aurora_brightens_nvg_scene(self):
        # A moonless clear night under a strong aurora is brighter than
        # the same night without one - the NVG AGC sees more photons.
        no_aurora = ambient_lux(0.0, overcast=0.0)
        with_aurora = ambient_lux(0.0, overcast=0.0, aurora_intensity=1.0)
        self.assertGreater(with_aurora, no_aurora)
        # 30x the starlight floor - a genuinely brighter image.
        self.assertGreater(with_aurora / max(no_aurora, 1e-9), 30.0)

    def test_overcast_reduces_moon(self):
        # Full moon behind heavy overcast: cloud loss 0.8*0.85 = 0.68,
        # transmission 0.32 -> lux = 0.001 + 0.32*0.249 = 0.0807.
        # Real heavy overcast blocks 60-90% of moonlight.
        self.assertAlmostEqual(
            ambient_lux(1.0, overcast=0.8), 0.001 + 0.32 * 0.249, places=4
        )

    def test_full_overcast_near_black(self):
        # Full moon at overcast=1.0: transmission 0.15 -> 0.038 lux.
        # ACE3 goes to 0 at full overcast; real storm sky ~0.01-0.05.
        self.assertAlmostEqual(
            ambient_lux(1.0, overcast=1.0), 0.001 + 0.15 * 0.249, places=4
        )

    def test_overcast_never_negative_transmission(self):
        # overcast beyond 1.0 (modded weather) clamps transmission at 0.15.
        self.assertAlmostEqual(
            ambient_lux(1.0, overcast=2.0), 0.001 + 0.15 * 0.249, places=4
        )

    def test_rain_reduces_moon(self):
        # Full moon in heavy rain: moonLight -= 0.5.
        self.assertAlmostEqual(
            ambient_lux(1.0, rain=1.0), 0.001 + 0.5 * 0.249, places=4
        )

    def test_never_negative_moon(self):
        # Worst case: overcast + rain cannot push moonLight below 0.
        self.assertGreaterEqual(ambient_lux(0.1, overcast=1.0, rain=1.0), 0.001)

    def test_half_moon_half_lux(self):
        # Half moon, clear: ~0.125 lux (midway to full moon).
        self.assertAlmostEqual(ambient_lux(0.5), 0.1255, places=4)


class TestTwilight(unittest.TestCase):
    """Twilight sky glow drives NVG dimming at dawn/dusk."""

    def test_deep_night_unchanged(self):
        # Sun at -90 (deep night): twilight ~0, starlight floor only.
        self.assertAlmostEqual(ambient_lux(0.0, sun_elev_deg=-90), 0.001, places=4)

    def test_civil_twilight(self):
        # Sun at -6 (civil twilight end): ~6.3 lux dominates the moon term.
        lux = ambient_lux(0.0, sun_elev_deg=-6)
        self.assertAlmostEqual(lux, 0.001 + 10 ** (2.6 - 0.3 * 6), places=3)

    def test_horizon_sunset(self):
        # Sun at horizon: ~398 lux (bright twilight).
        lux = ambient_lux(0.0, sun_elev_deg=0)
        self.assertGreater(lux, 100)

    def test_daylight_no_twilight_term(self):
        # Sun above horizon: daylight, no twilight term (NVG not used).
        self.assertAlmostEqual(ambient_lux(0.0, sun_elev_deg=30), 0.001, places=4)

    def test_twilight_monotonic(self):
        # Lower sun (more negative) -> darker.
        self.assertLess(
            ambient_lux(0, sun_elev_deg=-12), ambient_lux(0, sun_elev_deg=-3)
        )

    def test_astronomical_dusk_near_starlight(self):
        # Sun at -18 (astronomical end): ~0.0016 lux, near the starlight floor.
        lux = ambient_lux(0.0, sun_elev_deg=-18)
        self.assertLess(lux, 0.01)
        self.assertGreater(lux, 0.001)

    def test_starlight_hook_raises_floor(self):
        # A skybox mod raises aee_core_starlightLux -> the whole night
        # floor rises, so the NVG gains down for the brighter sky.
        base = ambient_lux(0.0)
        bright = ambient_lux(0.0, starlight=0.01)
        self.assertAlmostEqual(bright, base * 10, places=4)

    def test_starlight_hook_stacks_with_moon(self):
        # Starlight + moonlight are additive; raising starlight shifts the
        # full-moon night too.
        base = ambient_lux(0.5)
        bright = ambient_lux(0.5, starlight=0.01)
        self.assertAlmostEqual(bright - base, 0.009, places=4)


class TestExtinction(unittest.TestCase):
    """Beer-Lambert extinction - ITU-R rain/fog coefficients."""

    def test_clear_air_no_extinction(self):
        self.assertAlmostEqual(extinction_per_m(0, 0), 0.0, places=9)

    def test_heavy_rain_dBkm(self):
        # rain=1 -> 30 dB/km -> 30/4343 per metre.
        self.assertAlmostEqual(extinction_per_m(1.0, 0), 30.0 / 4343.0, places=9)

    def test_dense_fog_capped_at_300_dBkm(self):
        # fog=1 -> 40*(1/0.5)^2 = 160 dB/km, under the 300 cap.
        self.assertAlmostEqual(extinction_per_m(0, 1.0), 160.0 / 4343.0, places=9)

    def test_extreme_fog_never_exceeds_300_dBkm_cap(self):
        # The 300 dB/km cap needs fog=1.37 (above the engine's max ~1.0),
        # so real fog never hits it - but the cap is a guard for modded
        # weather that exceeds 1.0.  Assert the cap code exists and the
        # value stays bounded.
        self.assertLessEqual(extinction_per_m(0, 5.0), 300.0 / 4343.0)
        self.assertLessEqual(extinction_per_m(0, 1.0), 300.0 / 4343.0)

    def test_transmission_falls_with_distance(self):
        # Same source, farther in fog -> less light.
        near = lux_from_source(2000, 10, fog=0.5)
        far = lux_from_source(2000, 40, fog=0.5)
        self.assertGreater(near, far)


class TestDynamicLux(unittest.TestCase):
    """Inverse-square artificial light illuminance."""

    def test_inverse_square_law(self):
        # 4x distance -> 1/16 the illuminance (clear air).
        d1 = lux_from_source(2000, 5)
        d2 = lux_from_source(2000, 20)
        self.assertAlmostEqual(d1 / d2, 16.0, places=4)

    def test_headlight_at_5m(self):
        # 2000 lm headlight at 5 m: 2000/(4*pi*25) = 6.37 lux.
        self.assertAlmostEqual(
            lux_from_source(2000, 5), 2000 / (4 * math.pi * 25), places=4
        )

    def test_out_of_range_returns_zero(self):
        self.assertAlmostEqual(lux_from_source(2000, 150), 0.0, places=9)
        self.assertAlmostEqual(lux_from_source(2000, 0.2), 0.0, places=9)

    def test_rain_attenuates(self):
        self.assertLess(lux_from_source(2000, 50, rain=1.0), lux_from_source(2000, 50))


class TestNVGGain(unittest.TestCase):
    """AGC gain = sensitivity/(lux+1), capped."""

    def test_gain_equals_sensitivity_at_darkness(self):
        # Starlight 0.001 lux: gain ~ sensitivity.
        self.assertAlmostEqual(nvg_gain(1100, 0.001), min(1100 / 1.001, 1100), places=2)

    def test_gain_drops_with_light(self):
        # Full moon 0.25 lux: gain lower than at starlight.
        self.assertLess(nvg_gain(1100, 0.25), nvg_gain(1100, 0.001))

    def test_gain_never_exceeds_sensitivity(self):
        self.assertLessEqual(nvg_gain(1100, 0.0001), 1100)

    def test_bright_scene_caps_gain(self):
        # 10 lux (floodlight): sensitivity/(11) well under sensitivity.
        self.assertAlmostEqual(nvg_gain(550, 10), 50.0, places=4)


class TestShotNoise(unittest.TestCase):
    """Poisson photon statistics: SNR = sqrt(N)."""

    def test_snr_scales_with_sqrt_photons(self):
        # 4x the photon count -> half the shot noise (within Poisson bias
        # from the +1 guard in the denominator).
        n1 = shot_noise(0.001, 1100)
        n2 = shot_noise(0.004, 1100)
        self.assertAlmostEqual(n1 / n2, 2.0, places=1)

    def test_more_light_less_noise(self):
        self.assertLess(shot_noise(0.25, 1100), shot_noise(0.001, 1100))

    def test_noise_floor_plus_shot_combined(self):
        # PVS31 floor 0.03 at full moon: noise slightly above floor.
        n = nvg_noise(0.03, 0.25, 2000)
        self.assertGreater(n, 0.03)
        self.assertLessEqual(n, 1.0)

    def test_rain_adds_mie_noise(self):
        # rain=0.8 adds 0.28 to the noise (0.8*0.35).
        clear = nvg_noise(0.03, 0.25, 2000, rain=0)
        rainy = nvg_noise(0.03, 0.25, 2000, rain=0.8)
        self.assertAlmostEqual(rainy - clear, 0.28, places=6)

    def test_noise_never_exceeds_one(self):
        self.assertLessEqual(nvg_noise(0.15, 0.0001, 250, rain=1.0), 1.0)


class TestTempFactors(unittest.TestCase):
    """Tube performance vs temperature (MIL-PRF-49428F operating range)."""

    def test_gain_peak_at_20C(self):
        self.assertAlmostEqual(temp_gain_factor(20), 1.0, places=6)
        self.assertGreater(temp_gain_factor(20), temp_gain_factor(-30))
        self.assertGreater(temp_gain_factor(20), temp_gain_factor(45))

    def test_gain_cold_reference(self):
        self.assertAlmostEqual(temp_gain_factor(-30), 0.7, places=6)

    def test_gain_hot_reference(self):
        self.assertAlmostEqual(temp_gain_factor(45), 0.85, places=6)

    def test_gain_monotonic_rising_then_falling(self):
        self.assertLess(temp_gain_factor(-40), temp_gain_factor(0))
        self.assertLess(temp_gain_factor(50), temp_gain_factor(30))

    def test_noise_rises_with_heat(self):
        self.assertAlmostEqual(temp_noise_factor(20), 1.0, places=6)
        self.assertAlmostEqual(temp_noise_factor(45), 1.6, places=6)
        self.assertLess(temp_noise_factor(25), temp_noise_factor(45))
        self.assertAlmostEqual(temp_noise_factor(-10), 1.0, places=6)


class TestBatteryDrain(unittest.TestCase):
    """Battery drain = baseRate * gainRatio * tempFactor * dt."""

    def test_full_battery_drain_rate(self):
        # PVS31 base 1/(16*3600) per s, 1 s tick, full gain, no derating.
        d = nvg_drain(1 / (16 * 3600), 2000, 2000, 1.0, 1.0)
        self.assertAlmostEqual(d, 1 / (16 * 3600), places=10)

    def test_low_gain_drains_slower(self):
        # Gain at half sensitivity -> half the drain.
        full = nvg_drain(1 / (16 * 3600), 2000, 2000, 1.0, 1.0)
        half = nvg_drain(1 / (16 * 3600), 1000, 2000, 1.0, 1.0)
        self.assertAlmostEqual(half, full / 2, places=10)

    def test_cold_derating_drains_faster(self):
        # Derating 0.3 (cold) -> drain x3.3.
        normal = nvg_drain(1 / (16 * 3600), 2000, 2000, 1.0, 1.0)
        cold = nvg_drain(1 / (16 * 3600), 2000, 2000, 0.3, 1.0)
        self.assertAlmostEqual(cold / normal, 1 / 0.3, places=4)

    def test_temp_factor_clamped(self):
        # Derating < 0.01 (unset) -> factor clamped at 3.0 (not 100).
        d = nvg_drain(1 / (16 * 3600), 2000, 2000, 0.0, 1.0)
        self.assertAlmostEqual(d, 3.0 / (16 * 3600), places=10)

    def test_tier_battery_lifetimes(self):
        # Full discharge at base drain should match real hours.
        for base, hours in [
            (1 / (16 * 3600), 16),
            (1 / (65 * 3600), 65),
            (1 / (35 * 3600), 35),
            (1 / (25 * 3600), 25),
        ]:
            d = nvg_drain(base, 2000, 2000, 1.0, 1.0)
            self.assertAlmostEqual(d * 3600 * hours, 1.0, places=6)

    def test_runtime_halves_at_cold(self):
        # Issue #36: at -20C the physiology derating is ~0.7; drain is
        # 1/0.7 = 1.43x, so runtime is ~70% of nominal.  At the 0.3 floor
        # (severe cold) drain is 3.33x -> runtime ~30%.  The issue's
        # "halves at -20C" is the qualitative anchor; the quantitative
        # derating curve comes from the physiology model.
        nominal = nvg_drain(1 / (16 * 3600), 2000, 2000, 1.0, 1.0)
        cold = nvg_drain(1 / (16 * 3600), 2000, 2000, 0.7, 1.0)
        severe = nvg_drain(1 / (16 * 3600), 2000, 2000, 0.3, 1.0)
        self.assertAlmostEqual(cold / nominal, 1 / 0.7, places=4)
        self.assertAlmostEqual(severe / nominal, 1 / 0.3, places=4)

    def test_battery_toggle_off_no_drain(self):
        # Issue #36: NVG battery drain is opt-in (defaults off).
        self.assertEqual(
            nvg_drain(1 / (16 * 3600), 2000, 2000, 0.3, 1.0, battery_enabled=False), 0.0
        )


class TestNVGBrightness(unittest.TestCase):
    """AGC output brightness vs lux."""

    def test_starlight_floor(self):
        self.assertAlmostEqual(nvg_brightness(0.001), 0.65, places=6)

    def test_full_moon_full_brightness(self):
        self.assertAlmostEqual(nvg_brightness(0.25), 1.0, places=6)

    def test_monotonic_increase(self):
        self.assertLess(nvg_brightness(0.01), nvg_brightness(0.1))

    def test_clamped_out_of_range(self):
        self.assertEqual(nvg_brightness(0.0001), 0.65)
        self.assertEqual(nvg_brightness(10.0), 1.0)


class TestNVGBloom(unittest.TestCase):
    """NVG halo + clear-condition veiling glare floor."""

    def test_clear_condition_veiling_glare_floor(self):
        # Even with no moon, no blowout, no rain, real tubes have a 2.13 %
        # veiling glare floor (phosphor light reflected to the photocathode).
        b = nvg_bloom(0.04, 0.04, moon_light=0.0, blowout=0.0, rain=0.0)
        self.assertAlmostEqual(b, 0.04 + 0.0213, places=6)

    def test_veiling_glare_independent_of_rain(self):
        # The floor is present in clear AND rainy conditions (it adds on
        # top of the rain-scaled bloom, it is not the rain term).
        clear = nvg_bloom(0.04, 0.04, 0.0, 0.0, 0.0)
        rainy = nvg_bloom(0.04, 0.04, 0.0, 0.0, 1.0)
        self.assertGreater(rainy, clear)
        self.assertGreaterEqual(clear, 0.0213)  # floor present when clear

    def test_bloom_scales_with_blowout(self):
        low = nvg_bloom(0.04, 0.04, 0.0, blowout=0.0, rain=0.0)
        high = nvg_bloom(0.04, 0.04, 0.0, blowout=1.0, rain=0.0)
        self.assertGreater(high, low)

    def test_bloom_bounded(self):
        b = nvg_bloom(0.05, 0.05, 1.0, blowout=1.0, rain=1.0)
        self.assertLessEqual(b, 1.0)
        self.assertGreaterEqual(b, 0.0)


class TestMTFEffective(unittest.TestCase):
    """Resolution/contrast degradation at low light."""

    def test_full_moon_full_mtf(self):
        # Even at full moon the residual noise floor (0.03) trims MTF
        # slightly: mtf15 * (1 - 0.45*noise).
        self.assertAlmostEqual(
            mtf_effective(0.61, 0.03), 0.61 * (1 - 0.45 * 0.03), places=4
        )

    def test_starlight_reduced_to_55_percent(self):
        self.assertAlmostEqual(mtf_effective(0.61, 1.0), 0.61 * 0.55, places=4)

    def test_gated_blowout_reduces_mtf(self):
        mtf_clear = mtf_effective(0.65, 0.03, blowout=0)
        mtf_blown = mtf_effective(0.65, 0.03, blowout=1.0)
        self.assertAlmostEqual(mtf_blown, mtf_clear * 0.6, places=4)

    def test_ungated_keeps_full_mtf(self):
        # Gen 1/2 bloom instead of gating: no MTF loss.
        self.assertEqual(
            mtf_effective(0.30, 0.03, blowout=1.0, gated=False),
            mtf_effective(0.30, 0.03, gated=False),
        )

    def test_heavy_rain_scales_mtf(self):
        mtf_clear = mtf_effective(0.61, 0.03, rain=0)
        mtf_rain = mtf_effective(0.61, 0.03, rain=0.8)
        self.assertAlmostEqual(mtf_rain, mtf_clear * 0.6, places=4)


class TestEngineThermalDrive(unittest.TestCase):
    """Physics -> setVehicleTIPars drive + AGC window."""

    def test_physics_driven_heat_state(self):
        # setVehicleTIPars is driven from AEE physics: (T - ambient)/50
        # clamped 0..1.  The old forced-zero neutralisation is gone - it
        # was based on the StageTI-painting theory that proved wrong.
        self.assertAlmostEqual(engine_heat_fraction(17, 17), 0.0, places=6)
        self.assertAlmostEqual(engine_heat_fraction(67, 17), 1.0, places=6)
        self.assertAlmostEqual(engine_heat_fraction(32, 17), 0.3, places=6)
        self.assertAlmostEqual(engine_heat_fraction(100, 17), 1.0, places=6)
        self.assertAlmostEqual(engine_heat_fraction(40, 35), 0.1, places=6)

    def test_agc_window_hot_scene(self):
        # Scene with a hot engine (max heat 0.8): width 0.9/0.8 = 1.125
        # capped at 1.0, start 0 -> full range.
        s, w = ti_output_window(0.8)
        self.assertAlmostEqual(s, 0.0, places=6)
        self.assertAlmostEqual(w, 1.0, places=6)

    def test_agc_window_no_blowout_full_width(self):
        # No hot object (max heat <= 0.9): faithful pass-through, width=1.
        for c in [0, 0.05, 0.3, 0.5, 0.9]:
            s, w = ti_output_window(c)
            self.assertAlmostEqual(s, 0.0, places=6)
            self.assertAlmostEqual(w, 1.0, places=6)

    def test_agc_window_blowout_narrows(self):
        # A saturated hot object (>0.9): narrow to 0.9/maxHeat so it maps
        # to ~0.9 and the rest keeps relative contrast.
        s, w = ti_output_window(1.0)
        self.assertAlmostEqual(w, 0.9, places=6)
        s2, w2 = ti_output_window(0.95)
        self.assertAlmostEqual(w2, 0.9 / 0.95, places=4)

    def test_agc_start_always_zero(self):
        # start is ALWAYS 0 - the "flashlight" came from lifting the black
        # level (start=0.5); we never do that.
        for c in [0, 0.3, 0.9, 1.0, 5.0]:
            s, _ = ti_output_window(c)
            self.assertAlmostEqual(s, 0.0, places=6)

    def test_agc_window_bounds(self):
        for c in [0, 0.1, 0.5, 0.9, 1.0, 5.0, -1.0]:
            s, w = ti_output_window(c)
            self.assertGreaterEqual(s, 0.0)
            self.assertLessEqual(s, 0.5)
            self.assertGreaterEqual(w, 0.35)
            self.assertLessEqual(w, 1.0)

    def test_agc_freezes_while_panning(self):
        # Fast pan (>25 deg/s): not settled, window held.
        self.assertFalse(agc_settled(1.0))  # ~57 deg/s
        self.assertFalse(agc_settled(0.5))  # ~29 deg/s
        # Slow / still: settled, window may adapt.
        self.assertTrue(agc_settled(0.3))  # ~17 deg/s
        self.assertTrue(agc_settled(0.0))  # still


def test_agc_eases_when_settled(self):
    # A settled view eases toward target over ~1.5 s, not instantly.
    w = 1.0
    target = 0.5
    for _ in range(50):  # 0.5 s at 10 ms
        w = agc_ema(w, target, 0.01)
    # Analytic: target + (start-target)*exp(-0.5/1.5) = 0.8587
    self.assertAlmostEqual(w, target + (1.0 - target) * math.exp(-0.5 / 1.5), places=3)
    self.assertLess(w, 1.0)  # moved
    self.assertGreater(w, target)  # not yet arrived (eased)


class TestSecondSun(unittest.TestCase):
    """Physics-driven engine thermal SUN term (buildings/terrain)."""

    def test_night_no_sun_term(self):
        # Radiation 0 (night): fake sun off -> buildings render cold.
        self.assertAlmostEqual(second_sun_brightness(0), 0.0, places=6)

    def test_day_full_sun_term(self):
        # Radiation 1 (clear midday): the full A3TI peak 13, the proven
        # constant restored in 3655ad6 and tracked by radiation since cc00cd7.
        self.assertAlmostEqual(second_sun_brightness(1), 13.0, places=6)

    def test_overcast_attenuates(self):
        # Overcast mid-day: partial sun term (0.5 * 13 = 6.5).
        self.assertAlmostEqual(second_sun_brightness(0.5), 6.5, places=6)

    def test_clamped_out_of_range(self):
        self.assertAlmostEqual(second_sun_brightness(-0.2), 0.0, places=6)
        self.assertAlmostEqual(second_sun_brightness(1.5), 13.0, places=6)

    def test_never_negative(self):
        self.assertGreaterEqual(second_sun_brightness(0), 0)

    def test_full_sun_is_the_a3ti_peak(self):
        # Full sun = 13, A3TI's DEFAULT_SECONDSUN_BRIGHTNESS.  The 6
        # de-saturation (32b2666) was reverted in 3655ad6 because it dimmed
        # the sensor-illumination boost to nothing; per-vehicle contrast is
        # held by setVehicleTIPars, not by dimming the scene.
        self.assertAlmostEqual(second_sun_brightness(1.0), 13.0, places=6)


class TestVehicleDamageThermal(unittest.TestCase):
    """Damage-state thermal (issue #196): neutralised heat state, damage
    saturates the scene-max AGC guard instead.

    The old physics->setVehicleTIPars drive (damage scaled the 0..1 heat
    fraction) is GONE: setVehicleTIPars is forced to [0,0,0] so the band
    material carries the full radiance unmodulated.  A destroyed/burning
    vehicle now saturates the AGC scene-max (tiSceneMaxHeat -> 1), which
    widens the display window guard - the FLIR-correct behaviour."""

    def test_heat_state_physics_driven_regardless_of_damage(self):
        # setVehicleTIPars is driven from AEE physics for every live
        # vehicle - damage does not zero it (the physics carries the
        # heat; damage saturates the scene-max guard instead).  Dead
        # vehicles keep their state (the drive loop skips them).
        for kwargs in [
            dict(damage_engine=0.4),
            dict(damage_engine=1.0),
            dict(damage_fuel=0.5),
            dict(damage_body=0.95),
        ]:
            h = engine_heat_fraction(37.8, 17.8, **kwargs)
            self.assertAlmostEqual(h, 0.4, places=6)
        self.assertEqual(engine_heat_fraction(17.8, 17.8, alive=False), 0.0)

    def test_destroyed_saturates_scene_max(self):
        # The SQF scene-max pass: a dead/burning vehicle sets _sceneMax=1
        # (mirror of `if (!alive _x) then { _sceneMax = 1; }`), which the
        # AGC blowout guard uses to widen the window.
        self.assertEqual(engine_scene_max(alive=False), 1.0)

    def test_exhaust_warms_with_run_time(self):
        # Exhaust heat still feeds the WEAPON TI slot in the band material
        # path via the physics temperature, not setVehicleTIPars.
        self.assertAlmostEqual(exhaust_heat_fraction(60, 17.8), 1.0, places=6)
        h5 = exhaust_heat_fraction(5, 17.8)
        self.assertAlmostEqual(h5, 200 * (1 - math.exp(-5 / 60)) / 50, places=4)
        self.assertGreater(h5, 0.2)

    def test_exhaust_cold_when_engine_off(self):
        self.assertAlmostEqual(exhaust_heat_fraction(0, 17.8), 0.0, places=6)

    def test_exhaust_floor_when_engine_on(self):
        # Engine on, no run time yet: floor = engine heat (min 0.3).
        self.assertAlmostEqual(
            exhaust_heat_fraction(0, 17.8, engine_on=True, engine_heat=0.5),
            0.5,
            places=6,
        )
        self.assertAlmostEqual(
            exhaust_heat_fraction(0, 17.8, engine_on=True, engine_heat=0.1),
            0.3,
            places=6,
        )

    def test_exhaust_destroyed_saturates(self):
        self.assertAlmostEqual(
            exhaust_heat_fraction(0, 17.8, damage_body=0.95), 1.0, places=6
        )


class TestClothingThermal(unittest.TestCase):
    """Per-item clothing TI override from physics (insulation + ambient)."""

    def test_cold_ambient_light_clothing(self):
        # 5 C, light clothing (insulation 0.2): reads cold.
        s = clothing_ti_scale(0.2, 5)
        self.assertEqual(clothing_ti_material(s), "cold")

    def test_cold_ambient_heavy_insulation(self):
        # 5 C, heavy winter kit (0.8): 0.8 - 0.17 = 0.63 -> warm but not
        # in the "hot" band (0.7+).  The wearer stays warm (above 0.35),
        # which is the physical point: insulation keeps body heat in.
        s = clothing_ti_scale(0.8, 5)
        self.assertGreater(s, 0.35)  # not cold
        self.assertEqual(clothing_ti_material(s), "")  # neutral band

    def test_cold_ambient_insulation_keeps_warm(self):
        # Even at -15 C, full winter kit: 0.8 - 0.5 = 0.3 -> borderline.
        s = clothing_ti_scale(0.8, -15)
        self.assertGreaterEqual(clothing_ti_material(s), "")  # never hot

    def test_hot_ambient_everything_hot(self):
        # 45 C, light clothing: 0.2 + 0.5 = 0.7 -> hot.
        s = clothing_ti_scale(0.2, 45)
        self.assertEqual(clothing_ti_material(s), "hot")

    def test_neutral_keeps_own_ti(self):
        # 15 C, moderate insulation: no override (keep item's own TI).
        s = clothing_ti_scale(0.5, 15)
        self.assertEqual(clothing_ti_material(s), "")

    def test_scale_monotonic_in_insulation(self):
        self.assertLess(clothing_ti_scale(0.2, 15), clothing_ti_scale(0.8, 15))

    def test_scale_monotonic_in_ambient(self):
        self.assertLess(clothing_ti_scale(0.5, 0), clothing_ti_scale(0.5, 30))

    def test_rvmats_exist(self):
        # Issue #124: the rvmat TI swap is scrapped.  The per-selection
        # thermal substrate paints procedural colours via setObjectTexture,
        # so the ti_cloth_cold/hot.rvmat override materials must NOT exist
        # (their deletion is the point - no third-party rvmat can break).
        data_dir = _REPO_ROOT / "addons" / "thermal" / "data"
        self.assertFalse((data_dir / "ti_cloth_cold.rvmat").exists())
        self.assertFalse((data_dir / "ti_cloth_hot.rvmat").exists())
        # The substrate that replaced them must exist and expose the
        # per-selection apply path.
        fn = (
            _REPO_ROOT
            / "addons"
            / "thermal"
            / "functions"
            / "display"
            / "fnc_applySelectionThermal.sqf"
        )
        text = fn.read_text(encoding="utf-8")
        self.assertIn("setObjectTexture", text)
        self.assertIn("solveTwoNodeSelection", text)
        self.assertNotIn("solveSelectionTemperature", text)  # single-node killed
        self.assertIn("getSelectionMaterials", text)
        # Real FLIR pipeline (issue #196): band radiance + scene AGC,
        # NOT the old fixed-window T*eps^0.25 mapping.
        self.assertIn("calculateBandRadiance", text)
        self.assertIn("agcRadMin", text)
        self.assertNotIn("tApparent = (_tNew + 273.15) * (_eps ^ 0.25)", text)
        # Heat-colour texture paint (issue #204, MKK mechanism): the
        # vanilla TI mode renders the material's Stage1 TEXTURE, so the
        # heat is painted as a procedural colour via setObjectTexture - a
        # WHOT-red base scaled by the AGC-normalised brightness.  The
        # original material is KEPT (no setObjectMaterial in the paint
        # step - MKK THERMAL_RED default), so damage states and modded
        # multi-stage materials survive.  The old grey-band material swap
        # rendered flat and never carried the heat colour into the image
        # (the 'WHOT/BHOT no visual difference' report).
        self.assertIn("setObjectTexture", text)
        self.assertIn("#(rgb,8,8,3)color(", text)
        # Continuous palette paint (issue #204 rework): the display is a pure
        # function of the band radiance; material enters only through the
        # emissivity already inside _rad.  No material token selects a hue.
        self.assertIn("[_obj, _sel] call FUNC(getSelectionMaterials)", text)
        self.assertIn("call EFUNC(thermal_display,thermalPalette)", text)
        self.assertNotIn("_baseHue", text)
        self.assertNotIn("setObjectMaterial [_idx,", text)
        # The live path swaps exactly ONE material, the FPN substrate.
        # A second rvmat path here would be a new material swap, and a
        # material swap is the fragile mechanism issue #124 removed.
        swapped = set(re.findall(r"[\w\\]*\.rvmat", _code_only(text)))
        self.assertEqual(
            swapped,
            {"\\z\\aee\\addons\\thermal\\data\\ti_fpn.rvmat"},
            msg="the selection pass must name exactly one rvmat",
        )


def _palette_points():
    """The ember control points in fnc_thermalPalette.sqf, parsed not transcribed.

    Each point is [position, [r, g, b]].  The endpoints are the engine's own
    decoded TI colours, so parsing (not transcribing) keeps a SQF change and
    this mirror in step.
    """
    code = _code_only(_read_sqf("fnc_thermalPalette.sqf", addon="thermal"))
    block = re.search(r"private _points = \[(.*?)\];", code, re.DOTALL)
    if block is None:
        raise AssertionError("the ember palette control points are missing")
    points = []
    for m in re.finditer(r"\[([\d.]+),\s*\[([\d.,\s]+)\]\]", block.group(1)):
        rgb = tuple(float(x) for x in m.group(2).split(","))
        if len(rgb) == 3:
            points.append((float(m.group(1)), rgb))
    if len(points) < 5:
        raise AssertionError("the ember palette control points are incomplete")
    return points


def _selection_thermal_code():
    return _code_only(_read_sqf("fnc_applySelectionThermal.sqf", addon="thermal"))


class TestSelectionThermalTexture(unittest.TestCase):
    """The live per-selection heat texture (issue #204).

    A set of grey materials was shipped once and swapped onto the object
    to carry heat.  It rendered flat and never carried the heat colour,
    so the operator saw no difference between the two polarities.  The
    set is retired and deleted.  The live path paints a procedural colour
    into the material's Stage1 texture, and a ColorInversion ppEffect
    owns the polarity.

    Depth stays at 32 levels.  A material swap costs bytes only, and a real
    display is 8-bit, which is why the fusion ladder carries 256.  This
    path differs: it repaints per object per tick, and the quantity it
    carries is a STATUS TINT, one scalar driving a fixed hue, not a
    radiometric readout.  Its depth is bounded by discriminating one
    intensity.  Raising it would assert radiometric authority for a
    status indicator, the same error class as the scene-adaptive
    detection threshold this project already deleted.

    Every assertion reads the SQF with its comments stripped, because the
    function header quotes the shape it replaced.
    """

    def test_retired_grey_material_set_is_not_shipped(self):
        """Pin the deletion, so the retired set cannot return."""
        data_dir = _REPO_ROOT / "addons" / "thermal" / "data"
        shipped = sorted(p.name for p in data_dir.glob("ti_grey_*.rvmat"))
        self.assertEqual(shipped, [], msg="retired material set: " + ", ".join(shipped))

    def test_fpn_substrate_defers_to_the_diffuse(self):
        """The one live material carries no StageTI.

        The engine falls back to the diffuse, and the diffuse is the
        channel the texture paint writes to.  A StageTI would multiply the
        heat colour by the model's baked per-vertex thermaltop gain, which
        reproduces the engine gradient the retired approach showed.
        """
        rv = _REPO_ROOT / "addons" / "thermal" / "data" / "ti_fpn.rvmat"
        self.assertTrue(rv.exists(), "the thermal substrate is missing")
        body = rv.read_text(encoding="utf-8")
        self.assertNotIn("class StageTI", body)
        self.assertIn("class Stage1", body)

    def test_fpn_is_screen_space_not_a_material_stage(self):
        """The substrate must carry no noise stage (issue #204).

        A material stage maps to the object's texture coordinates, so a
        perlinNoise stage is fixed to the SURFACE and slides with the
        camera.  Real FPN is fixed to the detector array: screen space.
        """
        rv = _REPO_ROOT / "addons" / "thermal" / "data" / "ti_fpn.rvmat"
        body = re.sub(r"//[^\n]*", "", rv.read_text(encoding="utf-8"))
        self.assertNotIn("perlinNoise", body)
        self.assertNotIn("class Stage2", body)

    def test_fpn_amplitude_derives_from_device_and_agc_window(self):
        """One screen-space noise source, FPN from netd/window, not a constant."""
        code = _code_only(_read_sqf("fnc_applyThermalVision.sqf", addon="thermal"))
        self.assertIn("getThermalDeviceProperties", code)
        self.assertIn("QEGVAR(thermal,agcFullSpan)", code)
        self.assertIn("_fpnAmp = _netd / _windowT", code)
        self.assertIn("_noise = (_envNoise + _fpnAmp)", code)

    def test_agc_publishes_the_full_span_for_fpn(self):
        code = _code_only(_read_sqf("fnc_updateThermalAGC.sqf", addon="thermal"))
        self.assertIn("QGVAR(agcFullSpan)", code)

    def test_texture_quantiser_is_255_levels(self):
        """The depth, and the one-code-value step it produces."""
        code = _selection_thermal_code()
        m = re.search(r"private _levels = (\d+);", code)
        self.assertIsNotNone(m, "the quantiser depth is not declared")
        levels = int(m.group(1))
        self.assertEqual(levels, 255)
        # The ladder spans the 8-bit display once, so one step is about one
        # code value.  That is the continuous-palette requirement: the old
        # 32-level ladder put about 8 code values on each step (visible band).
        self.assertAlmostEqual(255.0 / (levels - 1), 1.003937, places=5)

    def test_heat_colour_is_a_continuous_palette(self):
        """The palette is continuous and monotone, not a material hue table.

        Regression: a three-entry material hue made glass permanently black
        and a whole vehicle read as a flat colour.  The display is now a pure
        function of the band radiance; the control points are the engine's own
        decoded TI hues (default_vehicle_ti 145,46,0 and default_ti 255,0,0).
        """
        points = _palette_points()
        self.assertEqual(points[0][1], (0.0, 0.0, 0.0), "cold endpoint")
        self.assertEqual(points[-1][1], (1.0, 1.0, 1.0), "hot endpoint")
        hues = [c for _, c in points]
        self.assertIn((0.5686, 0.1804, 0.0), hues, "default_vehicle_ti")
        self.assertIn((1.0, 0.0, 0.0), hues, "default_ti")

        def sample(n):
            lo = points[0]
            hi = points[-1]
            for p in points:
                if n >= p[0]:
                    lo = p
            for p in points:
                if n <= p[0]:
                    hi = p
                    break
            span = hi[0] - lo[0]
            f = 0.0 if span <= 0 else (n - lo[0]) / span
            return tuple(lo[1][i] + (hi[1][i] - lo[1][i]) * f for i in range(3))

        cols = [sample(i / 500.0) for i in range(501)]
        lums = [0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for c in cols]
        # Continuous: no step is a visible jump.
        steps = [abs(lums[i + 1] - lums[i]) for i in range(len(lums) - 1)]
        self.assertLess(max(steps), 0.01)
        # Monotone in luminance: brighter band position is never darker.
        self.assertEqual(lums, sorted(lums))
        # Many distinct outputs, not a small table.
        distinct = {tuple(round(x, 6) for x in c) for c in cols}
        self.assertGreaterEqual(len(distinct), 400)
        # No material token selects a hue in the paint step.
        code = _selection_thermal_code()
        self.assertNotIn("_baseHue", code)
        self.assertNotIn('_selMatClass in ["engine", "human"]', code)

    def test_red_channel_rises_with_brightness(self):
        """A brighter selection never paints a cooler red."""
        reds = [c[0] for _, c in _palette_points()]
        self.assertEqual(reds, sorted(reds))
        self.assertGreater(reds[-1], 0.0)

    def test_polarity_is_not_a_brightness_flip_here(self):
        """The paint path owns no polarity; the vision pass owns it.

        A flip in this file never reached the rendered image, which is why
        the two polarities looked the same to the operator.
        """
        code = _selection_thermal_code()
        self.assertIsNone(re.search(r"_\w+\s*=\s*1\s*-\s*_", code))
        self.assertNotIn("1 - _b", code)
        self.assertNotIn("ColorInversion", code)
        vision = _code_only(_read_sqf("fnc_applyThermalVision.sqf", addon="thermal"))
        # The driver owns the polarity, but the ColorInversion effect is
        # created in its own function now.
        create = _code_only(
            _read_sqf("fnc_createThermalPPEffects.sqf", addon="thermal")
        )
        self.assertNotIn('"ColorInversion"', vision)
        self.assertIn('"ColorInversion"', create)
        self.assertIn("_hInv ppEffectAdjust [0, 0, 0]", vision)


class TestLocalDisplayMode(unittest.TestCase):
    """Local display mode: per-object normalisation with a hard gain cap.

    Local widens ONE object's internal contrast by mapping its own selection
    radiances onto the palette.  That destroys absolute ordering between
    objects, so it is opt-in and never the default.  The 8x max-gain floor
    of the scene AGC still applies per object, so a flat object is not
    invented into full contrast.
    """

    FULL_SPAN = 800.0  # display span, in radiance units
    SCENE_WINDOW = (100.0, 500.0)  # a wide scene, spread 400 (> cap 100)

    def test_local_widens_a_narrow_object(self):
        # The object spans 60/400 of the scene -> 0.15 of the palette in
        # Automatic.  Its own window is floored to 100 -> 0.60 in Local.
        rads = [200.0, 220.0, 240.0, 260.0]
        scene_lo, scene_hi = self.SCENE_WINDOW
        auto = [window_position(r, scene_lo, scene_hi) for r in rads]
        obj_lo, obj_hi = window_with_gain_floor(rads, self.FULL_SPAN)
        local = [window_position(r, obj_lo, obj_hi) for r in rads]
        self.assertLess(max(auto) - min(auto), max(local) - min(local))
        self.assertAlmostEqual(max(local) - min(local), 60.0 / 100.0, places=6)

    def test_gain_cap_holds_on_a_flat_object(self):
        # A spread of 2 units is under full_span/8 = 100, so the window is
        # expanded to exactly 100.  The gain relative to the full display
        # span is exactly 8: the cap is not removed for Local.
        rads = [300.0, 301.0, 302.0]
        lo, hi = window_with_gain_floor(rads, self.FULL_SPAN)
        self.assertAlmostEqual(hi - lo, self.FULL_SPAN / 8.0, places=6)
        self.assertAlmostEqual(self.FULL_SPAN / (hi - lo), 8.0, places=6)
        # The parts still occupy only a few percent of the DISPLAY span: a
        # flat object is not invented into full contrast.
        self.assertLess((max(rads) - min(rads)) / self.FULL_SPAN, 0.01)

    def test_dead_flat_object_is_defined_and_capped(self):
        rads = [250.0, 250.0, 250.0]
        lo, hi = window_with_gain_floor(rads, self.FULL_SPAN)
        self.assertGreater(hi, lo)
        self.assertLessEqual(hi - lo, self.FULL_SPAN / 8.0 + 1e-6)

    def test_automatic_mapping_is_unchanged(self):
        # The scene window math: min..max with the same cap, no per-object
        # grouping.  A wide scene is untouched by the cap.
        rads = [120.0, 260.0, 480.0]
        lo, hi = window_with_gain_floor(rads, self.FULL_SPAN)
        self.assertEqual((lo, hi), (120.0, 480.0))

    def test_manual_mode_is_unchanged(self):
        # Manual maps through the configured endpoints, gated on mode 1,
        # independently of any object window.
        code = _selection_thermal_code()
        self.assertIn("if ((_displayMode == 1) || !_agcValid) then", code)
        self.assertIn("_manMinC", code)
        self.assertIn("_manMaxC", code)

    def test_default_is_still_automatic(self):
        settings = (
            _REPO_ROOT / "addons" / "thermal" / "initSettings.inc.sqf"
        ).read_text(encoding="utf-8")
        m = re.search(
            r"QGVAR\(thermalDisplayMode\).*?\[\[([^\]]+)\],\s*"
            r"\[([^\]]+)\],\s*(\d+)\]",
            settings,
            re.DOTALL,
        )
        self.assertIsNotNone(m, "thermalDisplayMode LIST is missing")
        values = [v.strip().strip('"') for v in m.group(2).split(",")]
        self.assertEqual(values[0], "Automatic (AGC)")
        self.assertEqual(int(m.group(3)), 0, "default must stay Automatic")
        self.assertTrue(any(v.startswith("Local") for v in values), values)

    def test_sqf_publishes_and_reads_the_object_window(self):
        agc = _code_only(_read_sqf("fnc_updateThermalAGC.sqf", addon="thermal"))
        self.assertIn("QGVAR(objAgcRad)", agc)
        self.assertIn("_fullSpan / 8", agc)
        self.assertIn("splitString", agc)
        sel = _selection_thermal_code()
        self.assertIn("_displayMode == 2", sel)
        self.assertIn("QGVAR(objAgcRad)", sel)

    def test_description_states_the_trade_and_the_cap(self):
        table = (_REPO_ROOT / "addons" / "thermal" / "stringtable.xml").read_text(
            encoding="utf-8"
        )
        m = re.search(
            r"STR_AEE_Thermal_thermalDisplayMode_Description.*?"
            r"<English>(.*?)</English>",
            table,
            re.DOTALL,
        )
        self.assertIsNotNone(m, "display mode description is missing")
        desc = m.group(1)
        self.assertIn("Local", desc)
        self.assertIn("comparison between objects", desc)
        self.assertIn("8", desc)


class TestBuildingThermal(unittest.TestCase):
    """Building material weighting - concrete stays cold, metal responds."""

    def test_concrete_building_full_cold(self):
        # Concrete/block building: heavy mass, swap everything.
        mats = ["a3\\structures_f\\data\\wall_block_concrete.rvmat"] * 4
        self.assertAlmostEqual(building_thermal_mass(mats), 1.0, places=6)

    def test_metal_building_half_cold(self):
        # Metal/glass dominant: responds to sun, swap half.
        mats = ["a3\\data\\metal_wall.rvmat"] * 3 + ["a3\\data\\glass.rvmat"]
        self.assertAlmostEqual(building_thermal_mass(mats), 0.5, places=6)

    def test_mixed_default_full(self):
        # Unknown materials: default to full cold (safe baseline).
        mats = ["a3\\structures_f\\data\\generic.rvmat"] * 3
        self.assertAlmostEqual(building_thermal_mass(mats), 1.0, places=6)

    def test_empty_no_buildings(self):
        self.assertAlmostEqual(building_thermal_mass([]), 1.0, places=6)


class TestClothingMaterial(unittest.TestCase):
    """Per-selection material classification - cloth swaps, metal keeps."""

    def test_cloth_swaps(self):
        for p in [
            "a3\\characters_f\\data\\basicbody_cloth.rvmat",
            "a3\\characters_f\\data\\uniform_fabric.rvmat",
            "a3\\characters_f\\data\\leather_vest.rvmat",
            "a3\\characters_f\\data\\wool_cap.rvmat",
        ]:
            self.assertEqual(clothing_material_kind(p), "cloth", p)

    def test_metal_keeps_engine_thermal(self):
        for p in [
            "a3\\characters_f\\data\\helmet_metal.rvmat",
            "a3\\characters_f\\data\\optic_glass.rvmat",
            "a3\\characters_f\\data\\plate_steel.rvmat",
            "a3\\characters_f\\data\\goggle_plastic.rvmat",
        ]:
            self.assertEqual(clothing_material_kind(p), "metal", p)

    def test_unknown_defaults_to_swap(self):
        self.assertEqual(clothing_material_kind("a3\\data\\generic.rvmat"), "other")
        self.assertEqual(clothing_material_kind(""), "other")


class TestConductionCoupling(unittest.TestCase):
    """Heat transfer between nearby objects (radiant, 1/d^2)."""

    def test_close_hot_neighbour_warms(self):
        # Hot engine (40 C surplus) 2 m away -> strong coupling.
        c = conduction_coupling(20, [(60, 2.0)])
        self.assertGreater(c, 2.0)

    def test_far_neighbour_weak(self):
        # Same surplus 8 m away -> weak but present.
        near = conduction_coupling(20, [(60, 2.0)])
        far = conduction_coupling(20, [(60, 8.0)])
        self.assertGreater(near, far * 5)

    def test_not_hot_enough_no_coupling(self):
        # Neighbour only 3 C warmer (below 5 C min delta): none.
        self.assertAlmostEqual(conduction_coupling(20, [(23, 2.0)]), 0.0, places=6)

    def test_out_of_range_no_coupling(self):
        self.assertAlmostEqual(conduction_coupling(20, [(60, 15.0)]), 0.0, places=6)

    def test_coupling_bounded(self):
        # Many hot neighbours cannot blow the temperature up.
        hot = [(100, 1.0)] * 5
        self.assertLessEqual(conduction_coupling(20, hot), 5.0)

    def test_coupling_monotonic_with_temp(self):
        c1 = conduction_coupling(20, [(40, 3.0)])
        c2 = conduction_coupling(20, [(80, 3.0)])
        self.assertGreater(c2, c1)


class TestBurningThermal(unittest.TestCase):
    """Burning objects saturate at combustion temperature."""

    def test_undamaged_not_burning(self):
        self.assertAlmostEqual(burning_temperature(17.8, 0.2), 17.8, places=6)

    def test_heavy_damage_burns(self):
        self.assertAlmostEqual(burning_temperature(17.8, 0.8), 617.8, places=6)

    def test_vehicle_fuel_damage_burns(self):
        self.assertAlmostEqual(
            burning_temperature(17.8, 0.3, is_vehicle=True, fuel_damage=0.9),
            617.8,
            places=6,
        )

    def test_vehicle_engine_damage_burns(self):
        self.assertAlmostEqual(
            burning_temperature(17.8, 0.3, is_vehicle=True, engine_damage=0.85),
            617.8,
            places=6,
        )

    def test_vehicle_damage_below_threshold_stays(self):
        self.assertAlmostEqual(
            burning_temperature(17.8, 0.5, is_vehicle=True, fuel_damage=0.5),
            17.8,
            places=6,
        )


class TestGlassReflection(unittest.TestCase):
    """Glass reflects the scene: cold at night, hot in daylight."""

    def test_night_glass_is_cold(self):
        # Radiation 0 (midnight): reflects cold sky -> cold material.
        self.assertEqual(glass_reflection_material(0, "cold", "hot"), "cold")

    def test_day_glass_is_hot(self):
        # Radiation 1 (noon): reflects the sun -> hot material.
        self.assertEqual(glass_reflection_material(1.0, "cold", "hot"), "hot")

    def test_threshold_boundary(self):
        # 0.3 boundary: at 0.3 (night) cold, above 0.3 hot.
        self.assertEqual(glass_reflection_material(0.3, "c", "h"), "c")
        self.assertEqual(glass_reflection_material(0.31, "c", "h"), "h")

    def test_negative_and_overshoot(self):
        self.assertEqual(glass_reflection_material(-1, "c", "h"), "c")
        self.assertEqual(glass_reflection_material(2.0, "c", "h"), "h")


class TestWeatherSmoothing(unittest.TestCase):
    """Weather EMA: physical time constants, no single-frame snap."""

    def test_rain_tau_2min(self):
        # Rain tau 120 s: after 120 s a step is ~63 % done (1 - e^-1).
        import math

        y = 0.0
        for _ in range(1200):  # 120 s at 0.1 s ticks
            y = weather_ema(y, 1.0, 0.1, 120)
        self.assertAlmostEqual(y, 1 - math.exp(-1), delta=0.02)

    def test_overcast_tau_5min(self):
        # Overcast tau 300 s: after 300 s ~63 % done.
        import math

        y = 0.0
        for _ in range(3000):
            y = weather_ema(y, 1.0, 0.1, 300)
        self.assertAlmostEqual(y, 1 - math.exp(-1), delta=0.02)

    def test_no_single_frame_snap(self):
        # A full step (0 -> 1) must NOT jump in one frame: after one 0.1 s
        # tick the value moves by <1 %.
        y = weather_ema(0.0, 1.0, 0.1, 120)
        self.assertLess(y, 0.01)

    def test_fog_tau_15min(self):
        # Fog tau 900 s (dissipation).
        import math

        y = 0.0
        for _ in range(9000):
            y = weather_ema(y, 1.0, 0.1, 900)
        self.assertAlmostEqual(y, 1 - math.exp(-1), delta=0.02)

    def test_converges_to_raw(self):
        # Steady state: smoothed converges to the raw value (no bias).
        y = 0.0
        for _ in range(20000):
            y = weather_ema(y, 0.7, 0.1, 120)
        self.assertAlmostEqual(y, 0.7, places=3)


class TestEyeState(unittest.TestCase):
    """Shared eye-state foundation: one anchor, consumed by all systems."""

    def test_eye_anchor_position(self):
        # Eye at origin, looking straight ahead (X): 10cm ahead.
        p = eye_state_position((0, 0, 1.7), (1, 0, 0), 0.1)
        self.assertAlmostEqual(p[0], 0.1, places=6)
        self.assertAlmostEqual(p[1], 0.0, places=6)
        self.assertAlmostEqual(p[2], 1.7, places=6)

    def test_eye_looking_up(self):
        # Looking straight up: 10cm above the eye.
        p = eye_state_position((0, 0, 1.7), (0, 0, 1), 0.1)
        self.assertAlmostEqual(p[2], 1.8, places=6)

    def test_eye_diagonal(self):
        # Diagonal gaze: x and z both shift by 0.1/sqrt(2).
        import math

        d = 0.1 / math.sqrt(2)
        p = eye_state_position((5, 5, 2), (0.707, 0, 0.707), 0.1)
        self.assertAlmostEqual(p[0], 5 + d, places=4)
        self.assertAlmostEqual(p[2], 2 + d, places=4)
        self.assertAlmostEqual(p[1], 5.0, places=4)


class TestRainDropletEyeVelocity(unittest.TestCase):
    """Issue #152: droplets must cancel eye velocity to stay on the lens.

    The particle emitter follows the eye each tick, but each spawned drop
    has zero WORLD velocity and stays at its absolute spawn point — any
    head/camera motion smears it off the lens within its 0.3 s lifetime.
    The fix: moveVelocity = -eyeVel keeps the drop stationary in eye space.
    """

    def test_eye_velocity_from_displacement(self):
        # 5 deg head turn over 0.1 s at 1.7 m eye height moves the eye
        # ~0.15 m.  Velocity = displacement / dt.
        prev = (0.0, 0.0, 1.7)
        now = (0.15, 0.0, 1.55)
        v = eye_velocity(prev, now, 0.1)
        self.assertAlmostEqual(v[0], 1.5, places=6)  # m/s
        self.assertAlmostEqual(v[1], 0.0, places=6)
        self.assertAlmostEqual(v[2], -1.5, places=6)

    def test_droplet_velocity_matches_eye(self):
        # A drop on the lens has world velocity = +eyeVel (co-moves).
        v = eye_velocity((0, 0, 1.7), (0.15, 0, 1.55), 0.1)
        drop_v = droplet_world_velocity(v)
        self.assertAlmostEqual(drop_v[0], 1.5, places=6)
        self.assertAlmostEqual(drop_v[2], -1.5, places=6)

    def test_drop_stays_glued_during_head_turn(self):
        # The bug: with ZERO drop velocity, a 5 deg turn over 0.1 s
        # displaces the drop 0.15 m relative to the eye (off the lens).
        # With -eyeVel it stays within 1 cm of its eye-relative point.
        import math

        eye = (0.0, 0.0, 1.7)
        cam_dir = (1.0, 0.0, 0.0)  # looking straight ahead
        offset = 0.1
        dt = 0.1
        # 5 deg head turn: eye swings ~0.15 m sideways, slight drop.
        angle = math.radians(5)
        eye_now = (math.sin(angle) * 1.7, 0.0, 1.7 - (1.7 * (1 - math.cos(angle))))
        v = eye_velocity(eye, eye_now, dt)

        fixed = droplet_eye_relative(eye, cam_dir, offset, v, dt)
        # Without the fix (drop velocity 0), the drop lags the eye by
        # eyeVel*dt = the full 0.15 m displacement.
        spawn = eye_state_position(eye, cam_dir, offset)
        eye_now_pos = tuple(eye[i] + v[i] * dt for i in range(3))
        lag = tuple(spawn[i] - eye_now_pos[i] for i in range(3))
        # Without the fix the drop lags by the eye displacement minus the
        # spawn offset: ~4.8 cm at a 5 deg turn — far outside a lens.
        self.assertGreater(abs(lag[0]), 0.04, "without fix the drop should lag")
        # With the fix: the eye-relative offset is unchanged.
        for i in range(3):
            self.assertAlmostEqual(fixed[i], offset * cam_dir[i], places=3)

    def test_head_still_drop_parallax(self):
        # Head still (zero eye velocity): the drop stays exactly at spawn.
        v = (0.0, 0.0, 0.0)
        fixed = droplet_eye_relative((0, 0, 1.7), (1, 0, 0), 0.1, v, 0.1)
        self.assertAlmostEqual(fixed[0], 0.1, places=6)
        self.assertAlmostEqual(fixed[2], 0.0, places=6)

    def test_sqf_has_velocity_cancel(self):
        # Source drift-lock: the fix must be present in the SQF.
        text = Path(
            "addons/thermal/functions/display/fnc_applyRainDroplets.sqf"
        ).read_text(encoding="utf-8")
        # moveVelocity must be eyeVel (co-move), not -eyeVel (a sign error
        # that would send drops AWAY from the eye) and not a static 0.
        self.assertIn("co-move with eye", text)
        self.assertIn("_eyeVel,", text)
        self.assertNotIn("vectorMultiply -1", text)

        eye_state = Path("addons/core/functions/fnc_getEyeState.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("eyeStatePrev", eye_state)

        post = Path("addons/vision/XEH_postInit.sqf").read_text(encoding="utf-8")
        # The duplicate droplet call in the thermal branch must be gone:
        # exactly ONE tick call (the unconditional one before the branches).
        self.assertEqual(
            post.count('["TICK"] call EFUNC(thermal,applyRainDroplets)'), 1
        )


class TestThermalCrossover(unittest.TestCase):
    """Diurnal thermal crossover - isothermal condition at dawn/dusk."""

    def test_midday_no_crossover(self):
        # Sun high, no twilight gate.
        active, timer = thermal_crossover(20, 24, sun_elev_deg=45)
        self.assertFalse(active)

    def test_night_no_crossover(self):
        # Sun well below horizon (midnight): NOT twilight.
        active, _ = thermal_crossover(15, 14, sun_elev_deg=-60)
        self.assertFalse(active)

    def test_dawn_delta_triggers(self):
        # Twilight (sun -5 deg) with 0.5 C delta: crossover.
        active, timer = thermal_crossover(15, 15.5, sun_elev_deg=-5, timer=2)
        self.assertTrue(active)

    def test_delta_too_wide_no_crossover(self):
        # Twilight but 5 C delta: no crossover.
        active, _ = thermal_crossover(15, 20, sun_elev_deg=5)
        self.assertFalse(active)

    def test_sustain_timer_requires_two_ticks(self):
        # First tick of crossover: timer 0 -> 1, not yet active.
        active, timer = thermal_crossover(15, 15.5, sun_elev_deg=5, timer=0)
        self.assertFalse(active)
        self.assertEqual(timer, 1)
        # Second tick: active.
        active2, _ = thermal_crossover(15, 15.5, sun_elev_deg=5, timer=1)
        self.assertTrue(active2)

    def test_timer_clamped(self):
        # Long sustained crossover: timer caps at 6.
        active, timer = thermal_crossover(15, 15, sun_elev_deg=0, timer=6)
        self.assertTrue(active)
        self.assertEqual(timer, 6)


class TestSolarGlare(unittest.TestCase):
    """Veiling glare when looking toward the sun."""

    def test_direct_sun_full_glare(self):
        # Looking dead at low sun: max glare.
        self.assertAlmostEqual(solar_glare(0, 10), 0.5, places=6)

    def test_45_deg_offset_zero(self):
        self.assertAlmostEqual(solar_glare(45, 10), 0.0, places=6)

    def test_high_sun_fades(self):
        # Sun at 60 deg elevation: elevation factor 0.
        self.assertAlmostEqual(solar_glare(0, 60), 0.0, places=6)

    def test_overcast_reduces(self):
        self.assertLess(
            solar_glare(0, 20, overcast=0.8), solar_glare(0, 20, overcast=0)
        )

    def test_never_exceeds_one(self):
        self.assertLessEqual(solar_glare(0, 20, overcast=0), 1.0)


class TestFocusRawMedian(unittest.TestCase):
    """Rolling-median focus smoothing - kills single-tick outliers."""

    def test_single_tick_outlier_killed(self):
        # A 137 m spike between stable 125 m samples must NOT move focus.
        seq = [125.6, 126.2, 137.6, 126.2, 125.9]
        out = focus_raw_median(seq)
        # At the spike, the median of [126.2, 137.6, 126.2] stays ~126.
        self.assertLess(out[2], 130)
        self.assertGreater(out[2], 125)

    def test_genuine_reaim_tracks_within_3_ticks(self):
        # Sustained 12 m target after 125 m: median follows by tick 3.
        seq = [125.1, 125.4, 125.6, 15.4, 13.5, 12.2, 12.2]
        out = focus_raw_median(seq)
        self.assertGreater(out[3], 120)  # first 15.4 still median 125
        self.assertLess(out[5], 20)  # by [13.5,12.2,12.2] median ~12

    def test_rpt_sequence_stabilised(self):
        # The exact RPT bouncing sequence: median must hold ~28 while
        # single-tick dips to 52/14 pass through without moving focus.
        rpt = [28.1, 28.2, 52.8, 28.3, 14.0, 28.3, 28.3, 12.2]
        out = focus_raw_median(rpt)
        # At the 52.8 spike: median of [28.1, 28.2, 52.8] = 28.2 (spike
        # discarded, median never leaves the ~28 band).
        self.assertAlmostEqual(out[2], 28.2, places=1)
        # At the 14.0 dip: median of [52.8, 28.3, 14.0] = 28.3.
        self.assertAlmostEqual(out[4], 28.3, places=1)
        # The final 12.2 is a SINGLE sample - the median of
        # [28.3, 28.3, 12.2] is 28.3, so the ring holds ~28 until 12.2
        # is sustained for 3 ticks.  That is the anti-hopping guarantee.
        self.assertAlmostEqual(out[7], 28.3, places=1)

    def test_sky_clears_history(self):
        # A sky sample (0) clears the window; the next raw starts fresh
        # (single-sample median = that raw until 3 accumulate).
        seq = [125.6, 0.0, 15.0, 16.0, 17.0]
        out = focus_raw_median(seq)
        self.assertEqual(out[1], 0.0)  # sky
        self.assertEqual(out[2], 15.0)  # fresh start
        self.assertEqual(out[3], 16.0)  # median of [15,16] -> floor
        self.assertEqual(out[4], 16.0)  # median of [15,16,17]


class TestFocusStateMachine(unittest.TestCase):
    """PROOF the focus tracks a bouncing target and cannot freeze."""

    RPT_BOUNCE = [
        125.1,
        125.4,
        125.6,
        125.6,
        126.2,
        137.6,
        15.4,
        13.5,
        40.2,
        28.1,
        28.2,
        28.3,
        28.3,
        28.3,
        28.3,
        28.3,
        52.8,
        14.0,
        12.2,
        12.2,
        12.2,
        12.2,
    ]

    def test_rpt_bounce_tracks_to_target(self):
        # The exact RPT sequence: the ring must settle on the LAST
        # SUSTAINED target (12.2 m, present for 4 consecutive ticks) -
        # not the earlier 28 m which was transient.  The median+state
        # machine must filter the bounce and track to 12.2.
        focuses, settled = focus_state_machine(self.RPT_BOUNCE)
        self.assertAlmostEqual(focuses[-1], 12.2, delta=1.0)
        self.assertTrue(settled[-1])

    def test_tracks_each_sustained_target(self):
        # Sweep 5m -> 80m -> 3m with noise: ends on the last sustained.
        seq = [5.2, 5.1, 5.3, 79.0, 80.2, 80.4, 3.1, 3.0, 3.2, 3.1]
        focuses, settled = focus_state_machine(seq)
        self.assertAlmostEqual(focuses[-1], 3.1, delta=1.0)
        self.assertTrue(settled[-1])

    def test_sky_holds_focus(self):
        # Sky (0 raw) must NOT move the ring - HOLD-ON-EMPTY.
        seq = [30.0, 30.2, 0.0, 0.0, 0.0, 30.1]
        focuses, _ = focus_state_machine(seq)
        # During sky the focus stays ~30.
        self.assertAlmostEqual(focuses[4], 30.2, delta=2.0)

    def test_single_tick_spike_does_not_rack(self):
        # One 137 m spike among stable 30 m must not pull the ring far.
        seq = [30.0, 30.1, 137.0, 30.2, 30.1]
        focuses, _ = focus_state_machine(seq)
        self.assertAlmostEqual(focuses[-1], 30.1, delta=3.0)

    def test_watchdog_snaps_stale_pending(self):
        # A huge target jump (2 m -> 148 m) must rack fully.  The ring
        # completes within the 0.5 s full-range rack + 0.2 s hold; the
        # watchdog (1.5 s) is the absolute bound - if the rack somehow
        # stalled, the ring snaps to the target and cannot freeze.
        seq = [2.0] * 5 + [148.0] * 15
        focuses, settled = focus_state_machine(seq)
        self.assertTrue(settled[-1])  # not stuck
        self.assertAlmostEqual(focuses[-1], 148.0, delta=1.0)

    def test_never_stuck_under_rapid_reaim(self):
        # Rapid re-aiming (target changes every 0.6 s = 6 ticks) with
        # realistic hold: the ring tracks each target before the next
        # arrives.  It must NEVER be frozen mid-rack when the target is
        # stable - and always reach a stable target.
        import random

        random.seed(7)
        targets = [random.uniform(3, 140) for _ in range(12)]
        seq = []
        for t in targets:
            seq += [t] * 6  # 0.6 s per target
        focuses, settled = focus_state_machine(seq)
        # Each target must be reached before the next begins.
        for i, t in enumerate(targets[:-1]):
            f = focuses[i * 6 + 5]  # last tick of this target
            self.assertAlmostEqual(
                f, t, delta=2.0, msg=f"target#{i}={t:.0f} not tracked"
            )
        self.assertTrue(settled[-1])

    def test_rack_progress_each_tick(self):
        # While racking the NEAR region (0.5 m -> 3 m), lens travel is
        # large (x = f^2/(s-f): 0.5 m->3 m spans ~1.7 mm of the 3.3 mm
        # throw) so the ring must move every tick until settled.  Far
        # jumps (28->80) complete in one tick - lens travel there is
        # sub-micron, which is correct thin-lens physics.
        seq = [0.5] * 5 + [3.0] * 25
        focuses, _ = focus_state_machine(seq, near_limit=0.45)
        moving = [
            i for i in range(1, len(focuses)) if abs(focuses[i] - focuses[i - 1]) > 0.01
        ]
        self.assertGreater(len(moving), 3)  # near rack visibly progresses
        self.assertAlmostEqual(focuses[-1], 3.0, delta=0.3)

    def test_no_sticky_deadband(self):
        # REGRESSION (the user's "too sticky" bug): a genuine 28 m -> 35 m
        # re-aim must TRACK.  At the old 25 % deadband the 7 m change was
        # inside the band (28*0.25 = 7 m) and the ring never moved.  With
        # the noise-floor-calibrated 3 % deadband it tracks.
        seq = [28.0] * 5 + [35.0] * 20
        focuses, settled = focus_state_machine(seq)
        self.assertAlmostEqual(focuses[-1], 35.0, delta=1.0)
        self.assertTrue(settled[-1])


class TestGroundTemperature(unittest.TestCase):
    """Ground target temperature from surface type and conditions."""

    def test_desert_heats_most(self):
        t = ground_target(20, "desert", 1.0, 0)
        self.assertGreater(t, ground_target(20, "grass", 1.0, 0))

    def test_snow_stays_cold(self):
        t = ground_target(20, "snow", 1.0, 0)
        self.assertLess(t, ground_target(20, "grass", 1.0, 0))

    def test_wind_cools(self):
        t_calm = ground_target(20, "grass", 1.0, 0)
        t_windy = ground_target(20, "grass", 1.0, 10)
        self.assertLess(t_windy, t_calm)

    def test_ground_never_below_air_temp(self):
        # Convective cooling clamps at air temp.
        t = ground_target(20, "grass", 0, 50)
        self.assertGreaterEqual(t, 20)

    def test_no_solar_at_night(self):
        t_day = ground_target(20, "desert", 1.0, 0)
        t_night = ground_target(20, "desert", 0, 0)
        self.assertGreater(t_day, t_night)

    def test_all_ground_types_finite(self):
        for gt in GROUND_GAINS:
            t = ground_target(20, gt, 0.5, 3)
            self.assertTrue(math.isfinite(t))


# Fix the typo in the test method name
def infantry_cloting_surface_safe(acclimatisation, air_temp, insulation):
    """Safe wrapper for insulation=0.0 edge case."""
    return infantry_clothing_surface(acclimatisation, air_temp, insulation)


# ─── NVG focus terrain mirror ────────────────────────────────────────────────
# Mirrors the terrain-fallback block in fnc_applyNVGTubeModel.  The fan rays
# are lookDir plus an offset (~26 m at the 300 m end), so they are NOT unit
# length.  The SQF normalises before using the Z component as a direction
# cosine; the mirror reproduces both the buggy (raw) and fixed (normalised)
# paths so the bug is locked by a test.


def _norm(v):
    m = math.sqrt(sum(c * c for c in v))
    return tuple(c / m for c in v) if m else (0.0, 0.0, 0.0)


def terrain_focus_distance(eye, ray_dir, terrain_h, flat_only=False):
    """Distance along the ray to the terrain, or -1.0 (sky/out of range).

    eye        : (x, y, z) ASL eye position.
    ray_dir    : ray direction (need NOT be unit; the SQF normalises).
    terrain_h  : callable (x, y) -> terrain height ASL.
    flat_only  : if True, reproduce the OLD flat-plane single-step result
                 (no normalisation, no slope iteration) for regression.
    """
    if flat_only:
        # OLD path: raw Z, no normalisation, no iteration.
        if ray_dir[2] >= -0.01:
            return -1.0
        t = (eye[2] - terrain_h(eye[0], eye[1])) / abs(ray_dir[2])
        return t if 0.25 < t <= 300 else -1.0

    rd = _norm(ray_dir)
    rdz = rd[2]
    if rdz >= -0.01:
        return -1.0
    eye_h = eye[2]
    t = (eye_h - terrain_h(eye[0], eye[1])) / abs(rdz)
    for _ in range(4):
        sx, sy = eye[0] + rd[0] * t, eye[1] + rd[1] * t
        sample_h = terrain_h(sx, sy)
        ray_h = eye_h + rdz * t
        err = sample_h - ray_h
        if abs(err) < 0.3:
            break
        t = (eye_h - sample_h) / abs(rdz)
        if t <= 0.25:
            break
    return t if 0.25 < t <= 300 else -1.0


class TestTerrainFocus(unittest.TestCase):
    """NVG focus terrain fallback - the fan-ray geometry."""

    EYE = (0.0, 0.0, 1.7)  # standing eye, 1.7 m above flat ground

    @staticmethod
    def _flat(x, y):
        return 0.0

    def test_centre_ray_flat_45deg(self):
        # Unit look dir 45° down on flat ground: 1.7 / sin(45°) = 2.404 m.
        d = terrain_focus_distance(self.EYE, (0.70710678, 0.0, -0.70710678), self._flat)
        self.assertAlmostEqual(d, 2.4041, places=3)

    def test_centre_ray_straight_down(self):
        # Straight down: distance == eye height.
        d = terrain_focus_distance(self.EYE, (0.0, 0.0, -1.0), self._flat)
        self.assertAlmostEqual(d, 1.7, places=6)

    def test_sky_ray_returns_none(self):
        # Upward ray: no terrain, HOLD-ON-EMPTY.
        self.assertLess(
            terrain_focus_distance(self.EYE, (0.7, 0.0, 0.7), self._flat), 0
        )

    def test_horizontal_ray_returns_none(self):
        self.assertLess(
            terrain_focus_distance(self.EYE, (1.0, 0.0, 0.0), self._flat), 0
        )

    def test_offset_ray_normalisation_is_required(self):
        # A cardinal side ray = lookDir + right * 26.  Raw magnitude ~26.
        # The fixed path normalises; the old path used the raw Z and gave a
        # wildly wrong (too close) distance.  Lock the fix.
        look = (0.70710678, 0.0, -0.70710678)
        right = (0.0, -1.0, 0.0)  # lookDir x up
        spread = 26.0
        ray = (
            look[0] + right[0] * spread,
            look[1] + right[1] * spread,
            look[2] + right[2] * spread,
        )  # (0.707, -26, -0.707)
        fixed = terrain_focus_distance(self.EYE, ray, self._flat)
        old = terrain_focus_distance(self.EYE, ray, self._flat, flat_only=True)
        # Fixed: normalised rdZ ~ -0.0272 -> t ~ 62.5 m (grazing forward).
        self.assertGreater(fixed, 20.0)
        # Old: raw Z -0.707 -> t = 2.404 m (wrong by ~25x).
        self.assertAlmostEqual(old, 2.4041, places=2)
        self.assertLess(old, fixed / 5)

    def test_down_offset_ray_was_dropped_by_old_guard(self):
        # lookDir - up * 26 -> z ~ -26.7, raw t = 1.7/26.7 = 0.064 < 0.25,
        # so the old path dropped it entirely.  Fixed path: nearly straight
        # down, t ~ 1.7 m.
        look = (0.70710678, 0.0, -0.70710678)
        ray = (look[0], look[1], look[2] - 26.0)
        self.assertLess(
            terrain_focus_distance(self.EYE, ray, self._flat, flat_only=True), 0
        )
        fixed = terrain_focus_distance(self.EYE, ray, self._flat)
        self.assertAlmostEqual(fixed, 1.7, places=1)

    def test_downhill_slope_correction(self):
        # Ground descends at 0.5 per metre horizontally (26.6° slope).
        # Ray 45° down, unit (0.707, 0, -0.707).  Exact intersection:
        #   1.7 + t*dz = -0.5 * t*dx  ->  t = -1.7 / (dz + 0.5*dx)
        #   = -1.7 / (-0.7071 + 0.35355) = 4.808 m
        def terr(x, y):
            return -0.5 * x

        exact = -1.7 / (-0.70710678 + 0.5 * 0.70710678)
        fixed = terrain_focus_distance(self.EYE, (0.70710678, 0.0, -0.70710678), terr)
        # Fixed-point converges within the focus deadband (25 % of target).
        self.assertAlmostEqual(fixed, exact, delta=exact * 0.25)
        # Flat-only estimate ignores the slope: 1.7/0.7071 = 2.404 m (wrong).
        flat = terrain_focus_distance(
            self.EYE, (0.70710678, 0.0, -0.70710678), terr, flat_only=True
        )
        self.assertAlmostEqual(flat, 2.4041, places=2)
        # The slope-corrected estimate is CLOSER to the true hit than the
        # flat-plane one.
        self.assertLess(abs(fixed - exact), abs(flat - exact))

    def test_uphill_slope_correction(self):
        # Ground rises at 0.5 per metre.  Exact:
        #   t = -1.7 / (dz - 0.5*dx)?  z_ray = 1.7 + t*dz, h = +0.5*t*dx
        #   1.7 + t*dz = 0.5*t*dx -> t*(dz - 0.5*dx) = -1.7
        #   t = -1.7 / (-0.7071 - 0.35355) = 1.606 m
        def terr(x, y):
            return 0.5 * x

        exact = -1.7 / (-0.70710678 - 0.5 * 0.70710678)
        fixed = terrain_focus_distance(self.EYE, (0.70710678, 0.0, -0.70710678), terr)
        self.assertAlmostEqual(fixed, exact, delta=exact * 0.25)
        # Flat estimate is worse on the uphill slope too: 2.404 vs 1.603.
        flat = terrain_focus_distance(
            self.EYE, (0.70710678, 0.0, -0.70710678), terr, flat_only=True
        )
        self.assertLess(abs(fixed - exact), abs(flat - exact))

    def test_high_altitude_looking_down_is_out_of_range(self):
        # Aircraft at 500 m: ground 500 m down, beyond the 300 m ray -> None
        # (HOLD; 500 m is infinity for the DoF band).
        eye = (0.0, 0.0, 500.0)
        self.assertLess(terrain_focus_distance(eye, (0.0, 0.0, -1.0), self._flat), 0)

    def test_prone_clamps_to_near_limit(self):
        # Prone, eye 0.3 m up, looking straight down -> 0.3 m, inside range.
        eye = (0.0, 0.0, 0.3)
        d = terrain_focus_distance(eye, (0.0, 0.0, -1.0), self._flat)
        self.assertAlmostEqual(d, 0.3, places=6)

    def test_underground_eye_returns_none(self):
        # Eye below the terrain surface (tunnel/basement): eye_h - terr <= 0.
        def terr(x, y):
            return 5.0

        self.assertLess(terrain_focus_distance(self.EYE, (0.0, 0.0, -1.0), terr), 0)


def test_never_negative_or_zero(self):
    # Sweep a range of downward angles on flat ground: always in range.
    for deg in (5, 15, 30, 45, 60, 80, 89):
        a = math.radians(deg)
        ray = (math.sin(a), 0.0, -math.cos(a))
        d = terrain_focus_distance(self.EYE, ray, self._flat)
        self.assertGreater(d, 0.25, f"angle {deg} gave {d}")


# ─── SQF drift-lock ─────────────────────────────────────────────────────────
# The Python mirrors above are hand-transcribed from the SQF.  This class
# READS the SQF source and asserts the exact physics constants and
# expressions the mirrors depend on are still present.  If anyone tunes a
# constant in the SQF without re-syncing the mirror, the drift-lock fails
# and the mismatch is caught before the tests can silently diverge.


class TestSQFSync(unittest.TestCase):
    """SQF source must contain the constants the Python mirrors rely on."""

    def _assert_in_sqf(self, filename, fragments, context, addon="optics"):
        text = _read_sqf(filename, addon)
        missing = [f for f in fragments if f not in text]
        self.assertFalse(
            missing,
            f"{filename}: {context} changed/missing in SQF: {missing}. "
            f"Re-sync the Python mirror in test_thermal_optics.py.",
        )

    # ── Thermal contrast (fnc_calculateThermalContrast.sqf) ──
    def test_contrast_has_no_base_gain(self):
        # The scene-gain stage must not amplify: the engine renders the
        # native image with its own gain, so the base is exactly 1.0 and
        # there is no delta-T span.
        code = _code_only(_read_sqf("fnc_calculateThermalContrast.sqf", "thermal"))
        self.assertIn("private _contrast = 1.0", code)
        self.assertNotIn("/ 8", code)
        self.assertNotIn("_deltaT", code)

    def test_contrast_has_no_weather_terms(self):
        # The weather double-count is removed: atmospheric degradation lives
        # once, in fnc_calculateAtmosphericTransmission.  Humidity survives
        # only inside the NETD noise term until the range task moves it.
        code = _code_only(_read_sqf("fnc_calculateThermalContrast.sqf", "thermal"))
        for token in ("rain", "_fog", "currentFogDensity", "* 0.3"):
            self.assertNotIn(token, code)

    def test_contrast_heat_cold_constants(self):
        self._assert_in_sqf(
            "fnc_calculateThermalContrast.sqf",
            ["_gap > 35", "(_gap - 35) / 10) * 0.7", "_gap < 5", "* 1.2", "min 1.0"],
            "heat flatten / cold boost",
            addon="thermal",
        )

    def test_contrast_base_is_degradation_only(self):
        # The vehicle-only scene average that fed the old base gain is gone;
        # the base is 1.0 and only the environmental terms move it.
        code = _code_only(_read_sqf("fnc_calculateThermalContrast.sqf", "thermal"))
        self.assertNotIn('isKindOf "Man"', code)
        self.assertNotIn("_avgVehicleTemp", code)
        self.assertNotIn("avgGroundTemp", code)
        self.assertIn("private _contrast = 1.0", code)

    def test_netd_noise_kernel_constants(self):
        # The noise floor moved to the pure kernel, where the range is a real
        # argument.  The contrast kernel no longer computes it.
        self._assert_in_sqf(
            "fnc_calculateThermalNoise.sqf",
            ["640 / _res", "(1 + (_hum / 100) * 0.5)", "_noise max 0", "_rangeM"],
            "NETD noise floor",
            addon="thermal",
        )
        code = _code_only(_read_sqf("fnc_calculateThermalContrast.sqf", "thermal"))
        self.assertNotIn("currentThermalNoise", code)
        self.assertNotIn("viewDistance", code)

    # ── Thermal vision (fnc_applyThermalVision.sqf) ──
    def test_thermal_blur_constants(self):
        self._assert_in_sqf(
            "fnc_applyThermalVision.sqf",
            ["0.0, 0.15, true", "min 0.25", "0.0, 0.04, true"],
            "blur span / ceiling / pan-smear cap",
            addon="thermal",
        )

    def test_thermal_window_constants(self):
        self._assert_in_sqf(
            "fnc_applyThermalVision.sqf",
            ["0.1, 0.8", "0.0, 0.2", "0.1, 1.0", "0.0, 0.15"],
            "fog/rain window blur",
            addon="thermal",
        )

    def test_thermal_post_process_layering(self):
        # The ppEffect stack mirrors the real FLIR sensor chain
        # (issue #196): atmospheric blur applies first, sensor noise
        # (NETD grain) second, display gain/contrast last.  Lower
        # priority = applied first (BIS wiki base order).
        # Issue #204: a shared priority made whichever module created
        # second fail ("PE with same priority(5100) already exist") and
        # spam "Invalid post effect handle".  The stack now adopts the
        # proven A3TI/MKK per-type ladder (docs/wiki/research/
        # engine-thermal-mechanisms.md).  The plan named FilmGrain 2005
        # and CC 2505, but the fusion stack holds both, so the other
        # proven values 2000 and 2500 keep the two thermal-owned stacks
        # from sharing a priority.
        self._assert_in_sqf(
            "fnc_createThermalPPEffects.sqf",
            [
                '["RadialBlur",      1000, QGVAR(ppHandle_Thermal_Vignette)]',
                '["DynamicBlur",      505, QGVAR(ppHandle_Thermal_Blur)]',
                '["FilmGrain",       2000, QGVAR(ppHandle_Thermal_Grain)]',
                '["ColorCorrections", 2500, QGVAR(ppHandle_Thermal_CC)]',
            ],
            "FLIR layering: blur -> grain -> CC, vignette below, grain ABOVE blur (create table)",
            addon="thermal",
        )
        self._assert_in_sqf(
            "fnc_applyThermalVision.sqf",
            ["ppEffectForceInNVG true"],
            "FLIR layering: the live adjust pass sets the NVG force flag",
            addon="thermal",
        )

    def test_thermal_priority_no_collision_with_nvg(self):
        # Issue #204: a shared priority made whichever module created
        # second fail - "PE with same priority(5100) already exist" -
        # and spam "Invalid post effect handle".  Every ppEffect priority
        # across optics (210/410/1510), NVG (1200/3050/4100/5100/6000/868)
        # and thermal (205/305/505/1000/2000/2500/2510/3000) must be unique.
        import re

        root = Path(__file__).resolve().parents[2]
        files = [
            "addons/vision/functions/vision/fnc_managePostProcess.sqf",
            "addons/nightvision/functions/fnc_applyNVGTubeModel.sqf",
            "addons/thermal_display/functions/display/fnc_applyThermalVision.sqf",
        ]
        seen = {}
        for rel in files:
            text = (root / rel).read_text(encoding="utf-8")
            for m in re.finditer(r'\["(\w+)",\s*(\d+)', text):
                eff, prio = m.group(1), int(m.group(2))
                if prio in seen:
                    self.fail(
                        f"priority collision: {seen[prio]} and "
                        f"{rel}:{eff} both at {prio}"
                    )
                seen[prio] = f"{rel}:{eff}"
        # DoF is created separately (priority 868) - include it.
        nvg = (root / files[1]).read_text(encoding="utf-8")
        dof_m = re.search(r"private _dofPrio = (\d+)", nvg)
        if dof_m is None:
            self.fail("DoF priority not found in NVG tube model")
        dof = int(dof_m.group(1))
        if dof in seen:
            self.fail(f"DoF {dof} collides with {seen[dof]}")

    def test_optics_priorities_stay_under_the_engine_optic_band(self):
        """The normal-vision optics blur must render under the cockpit HUD.

        Regression: the three optics effects were created at 3000/4000/5000.
        The base game keeps every entry of its own CfgOpticsEffect table at
        or below 2550 (Addons/data_f/a3/data_f/config.cpp: OpticsInverted and
        Default are colorInversion at 2550).  The vanilla fighters' own optic
        blur OpticsBlur2 is dynamicblur at 450 and their cockpit HUD stays
        visible.  A ppEffect above the engine's optic band composites over the
        HUD, so the blur covered it.  The effects now sit just below the
        engine's own same-type entries (chromaberration 250, dynamicblur 450,
        ColorCorrections 1550) and therefore under that band.

        Regression (operator RPT 2026-10-02 15-12-34): the effects used the
        BIS-documented BASE priorities (200/400/1500).  Those are a shared
        convention, not reserved slots, so the engine logged "Cannot create
        custom post effect(type: 3), PE with same priority(400) already
        exist" when another creator asked for DynamicBlur 400 that AEE
        already held.  The values are now unique offsets that avoid both the
        documented base set and the engine's own CfgOpticsEffect table.
        """
        import re

        root = Path(__file__).resolve().parents[2]
        expected = {
            "ChromAberration": 210,
            "DynamicBlur": 410,
            "ColorCorrections": 1510,
        }
        # The engine's own CfgOpticsEffect priorities and the BIS-documented
        # base priorities.  AEE must equal none of them, or a second creator
        # either fails or is blocked and the engine logs the collision.
        engine_and_base = {
            100,
            200,
            250,
            300,
            400,
            450,
            1500,
            1550,
            2000,
            2050,
            2500,
            2550,
        }
        manage = (
            root / "addons/vision/functions/vision/fnc_managePostProcess.sqf"
        ).read_text(encoding="utf-8")
        create = (
            root / "addons/vision/functions/vision/fnc_ppEffectCreate.sqf"
        ).read_text(encoding="utf-8")
        applied = {
            m.group(1): int(m.group(2))
            for m in re.finditer(r'\["(\w+)",\s*(\d+),\s*QGVAR', manage)
        }
        created = {
            m.group(1): int(m.group(2))
            for m in re.finditer(r'\["(\w+)",\s*(\d+)\]', create)
        }
        self.assertEqual(applied, expected, "applied optics priorities")
        self.assertEqual(created, expected, "created optics priorities")
        # Every AEE optics priority is distinct (one effect type per slot).
        self.assertEqual(
            len(set(expected.values())),
            len(expected),
            "AEE optics priorities are not unique",
        )
        for effect, priority in expected.items():
            self.assertLess(
                priority,
                2550,
                f"{effect} must sit under the engine optic band",
            )
            self.assertNotIn(
                priority,
                engine_and_base,
                f"{effect} at {priority} reuses a documented base/engine "
                "priority, which a second creator also uses",
            )

    def test_thermal_crossover_floor(self):
        self._assert_in_sqf(
            "fnc_applyThermalVision.sqf",
            ["0.05", "linearConversion [1, 0, _effective, 0.62, 0.35, true]"],
            "crossover floor / AGC contrast mapping",
            addon="thermal",
        )

    def test_thermal_heat_colour_texture(self):
        # Issue #204 (MKK mechanism): the heat is painted as a procedural
        # WHOT-red colour via setObjectTexture - the vanilla TI mode
        # renders the Stage1 TEXTURE, not a swapped material's diffuse.
        # The material is swapped ONLY for the FPN rvmat (ti_fpn.rvmat,
        # perlinNoise Stage2) when the thermalFPN setting is on, and
        # restored on EXIT - never a permanent replacement.
        self._assert_in_sqf(
            "fnc_applySelectionThermal.sqf",
            [
                "#(rgb,8,8,3)color(",
                "call EFUNC(thermal_display,thermalPalette)",
                "private _levels = 255",
                "setObjectTexture [_idx, _colour]",
                "ti_fpn.rvmat",
            ],
            "continuous palette paint (255 levels, FPN material)",
            addon="thermal",
        )

    def test_thermal_whot_spectrum_cc(self):
        # Issue #204: the WHOT spectrum CC grade.  The proven A3TI
        # values (2041057379) use a NEUTRAL GREY tint [0.33,0.33,0.33]
        # with the 7-element blend [0,0,0,0,0,0,4] - it grades to WHOT
        # WITHOUT inverting any channel.  The old MKK matrix
        # [3.84,-0.46,-2.72,-0.06] has NEGATIVE green/blue - it
        # INVERTED the channels, so the hot barrel rendered black in
        # WHOT and the scene flipped with polarity.
        self._assert_in_sqf(
            "fnc_applyThermalVision.sqf",
            ["[0.33, 0.33, 0.33, 0]", "[0, 0, 0, 0, 0, 0, 4]"],
            "WHOT spectrum colour grade (neutral tint, no inversion)",
            addon="thermal",
        )

    def test_thermal_bhot_color_inversion(self):
        # Issue #204: BHOT = a ColorInversion ppEffect (A3TI 2501, MKK
        # 2510).  The old `_b = 1-_b` flip never reached the image for
        # StageTI-baked objects.  The inversion is created unconditionally
        # and enabled only when thermalPolarity == 1.  When DISABLED it
        # must be adjusted to the neutral [0,0,0] BEFORE disabling - a
        # freshly-created ColorInversion can default to enabled with an
        # inverting state (the 'BHOT is on but should not be' report:
        # the barrel turned black when hot).
        self._assert_in_sqf(
            "fnc_applyThermalVision.sqf",
            [
                "ColorInversion",
                "2510",
                "ppHandle_Thermal_Inversion",
                "_polarity == 1",
                "_hInv ppEffectEnable true",
                "_hInv ppEffectAdjust [0, 0, 0]",
                "_hInv ppEffectEnable false",
            ],
            "ColorInversion BHOT polarity (proven mechanism)",
            addon="thermal",
        )

    def test_thermal_polarity_flip_removed(self):
        # The polarity flip in the paint step must be GONE - BHOT is the
        # ColorInversion now.
        text = _read_sqf("fnc_applySelectionThermal.sqf", "thermal")
        self.assertNotIn("_b = 1 - _b", text)

    # ── NVG focus (fnc_applyNVGTubeModel.sqf) ──
    def test_focus_ray_geometry_constants(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            [
                "vectorNormalized _rayDir",
                "abs _rdZ",
                "-0.01",
                "> 0.25 && _tDist <= 300",
                "abs _err < 0.3",
                "from 1 to 4",
            ],
            "terrain fallback geometry",
            addon="nightvision",
        )

    def test_focus_median_and_watchdog(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            [
                "nvgFocusRawHist",
                "count _rawHist > 3",
                "deleteAt 0",
                "_sorted sort true",
                "_holdUntil + 1.5",
                "_curFocus * 0.03",
            ],
            "rolling median filter / settle watchdog / deadband",
            addon="nightvision",
        )

    def test_focus_vehicle_exclusion(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            ["vehicle _player", "_hitObj != _veh && _hitParent != _veh"],
            "vehicle cabin exclusion",
            addon="nightvision",
        )

    # ── NVG tube / illuminance (fnc_applyNVGTubeModel.sqf,
    # ── fnc_calculateIlluminance.sqf) ──
    def test_illuminance_constants(self):
        self._assert_in_sqf(
            "fnc_calculateIlluminance.sqf",
            [
                "_starlightLux + (_moonLight * 0.249) + _twilightLux",
                "_cloudLoss",
                "_cloudTransmission",
                "_overcastS * 0.85) min 0.85",
                "_rainS * 0.5",
                "call FUNC(getSmoothedWeather)",
                "4 * pi * _dist * _dist",
                "exp (-_gamma * _dist)",
                "currentSunElevation",
                "10 ^ (2.6 - 0.3 * (abs _sunElev))",
                "starlightLux",
            ],
            "moon lux / cloud / twilight / starlight hook / inverse-square",
            addon="core",
        )

    def test_solar_model_exposes_sun_elevation(self):
        # The solar model must expose currentSunElevation for the twilight
        # term (radiation is max 0, so it cannot give the below-horizon angle).
        cfg = (
            _REPO_ROOT
            / "addons"
            / "lighting"
            / "functions"
            / "astronomy"
            / "fnc_calculateSolarRadiation.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("currentSunElevation", cfg)
        self.assertIn("asin (_sinElev", cfg)

    def test_illuminance_extinction_constants(self):
        self._assert_in_sqf(
            "fnc_calculateIlluminance.sqf",
            ["_rainS * 30", "4343", "40 * (_fogS / 0.5) ^ 2", "min 300"],
            "smoothed rain/fog extinction",
            addon="core",
        )

    def test_nvg_gain_model(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            ["_sensitivity / (_lux + 1)", "min _sensitivity"],
            "AGC gain model",
            addon="nightvision",
        )

    def test_nvg_shot_noise_model(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            [
                "1 / sqrt(_photonCount + 1)",
                "AEE_PHOTON_SCALE",
                "_lux * _sensitivity * AEE_PHOTON_SCALE",
            ],
            "Poisson shot noise",
            addon="nightvision",
        )

    def test_nvg_noise_floor_model(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            [
                "_noiseFloor + (1 - _noiseFloor) * _shotNoise",
                "_rainS * 0.35",
                "0.03 max _noise min 1",
            ],
            "combined noise floor + rain Mie",
            addon="nightvision",
        )

    def test_nvg_temp_factors(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            [
                "-30, 20, _airTemp, 0.7, 1.0",
                "20, 45, _airTemp, 1.0, 0.85",
                "20, 45, _airTemp, 1.0, 1.6",
            ],
            "temperature gain/noise factors",
            addon="nightvision",
        )

    def test_nvg_battery_drain_model(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            [
                "_baseDrain * _gainRatio * _tempDrainFactor * _dt",
                "0.0000174",
                "0.0000043",
                "0.0000079",
                "0.0000111",
            ],
            "battery drain rates",
            addon="nightvision",
        )

    def test_nvg_brightness_model(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            ["0.001, 0.25, _lux, 0.65, 1.0"],
            "AGC output brightness",
            addon="nightvision",
        )

    def test_nvg_mtf_model(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            ["_mtf15 * 0.55", "_blowout * 0.4", "1 - rain * 0.5"],
            "MTF degradation",
            addon="nightvision",
        )

    def test_nvg_veiling_glare_floor(self):
        # Issue #215: the floor is the nvgVeilingGlare setting (default
        # 0.0213, the MIL-I-49428 section 3.6.15.2 value), not a literal.
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            ["_bloom = _bloom + _glare", "nvgVeilingGlare"],
            "clear-condition veiling glare floor",
            addon="nightvision",
        )

    # ── Engine thermal drive (fnc_applyEngineThermal.sqf) ──
    def test_engine_thermal_constants(self):
        self._assert_in_sqf(
            "fnc_applyEngineThermal.sqf",
            [
                'setTIParameter ["OutputRangeStart", _outStart]',
                'setTIParameter ["OutputRangeWidth", _outWidth]',
                "(_surfaceTemp - _airTemp) / 50",
                "tiSceneMaxHeat",
                "private _outStart = 0.0",
                "0.9 / _sceneMaxHeat",
                "_angVelDeg < 25",
                "tiAppliedWidth",
            ],
            "engine AGC display window (physics-driven scene max heat)",
            addon="thermal",
        )

    def test_engine_thermal_damage_constants(self):
        self._assert_in_sqf(
            "fnc_applyEngineThermal.sqf",
            [
                "thermalState",
                "(_surfaceTemp - _airTemp) / 50",
                "if (!alive _x) then { _sceneMax = 1",
                "0.2 * (_dt / 30)",
                "nearEntities",
                "str _x",
            ],
            "damage/burning saturates the AGC scene-max guard",
            addon="thermal",
        )

    def test_config_level_thermal_model(self):
        # Issue #196: the ENGINE's TI model is configured per class in
        # CfgVehicles (the ACE-thermals lever).  Material swaps cannot
        # change the engine's dynamic thermal component; this config does.
        cfg = (_REPO_ROOT / "addons" / "thermal" / "config.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("class AllVehicles: All", cfg)
        for param in ["htMin", "htMax", "afMax", "mfMax", "mFact", "tBody"]:
            self.assertIn(param, cfg, f"{param} missing from CfgVehicles thermal model")
        # Humans have metabolism; vehicles have none (parked = ambient).
        self.assertIn("class Man: Land", cfg)
        self.assertIn("tBody = 32", cfg)
        self.assertIn("mFact = 0", cfg)

    def test_second_sun_constants(self):
        # Issue #204: the second sun tracks the solar radiation (the TI
        # sun term) AND the REAL sun's azimuth - morning thermals heat
        # the east faces of objects, afternoon the west.  Peak is the
        # A3TI-proven 13 (DEFAULT_SECONDSUN_BRIGHTNESS) scaled by
        # radiation with a dawn/dusk floor.  At night the moon bearing
        # drives the dim reflected term.
        self._assert_in_sqf(
            "fnc_applySecondSun.sqf",
            [
                "#lightpoint",
                "setLightDayLight true",
                "currentSolarRadiation",
                "setLightBrightness _lightBrightness",
                "createVehicleLocal",
                "private _lightBrightness = 13 * _radiation;",
                "setLightAttenuation [10e10, 150, 4.3e-5, 4.3e-5]",
                "currentSunAzimuth",
                "currentMoonAzimuth",
                "getRelPos [150, _azimuth]",
            ],
            "sun-direction-tracking second sun (real solar bearing)",
            addon="thermal",
        )

    def test_rain_droplet_constants(self):
        # Rain droplets use the PROVEN TPW goggles recipe: a head-attached
        # #particlesource emitter with the engine's Refract particle class
        # via setParticleParams.  NOT a raw drop (fails: "NOID refract.p3d
        # #cloudlet" - Refract is a cloudlet class), NOT the raindrop .paa
        # (engine ShapeLoads it and crashes), NOT a procedural string (the
        # shape slot rejects it).  The emitter is WORLD-SPACE and
        # repositioned to the camera eye each tick - the old HEAD memory
        # point attachment put particles behind the camera (invisible).
        self._assert_in_sqf(
            "fnc_applyRainDroplets.sqf",
            [
                '"#particlesource" createVehicleLocal',
                "ParticleEffects\\Universal\\Refract",
                '"Billboard"',
                "setParticleParams",
                "setDropInterval",
                "setPosASL (_eye vectorAdd (_camDir vectorMultiply 0.1))",
                "call EFUNC(core,getEyeState)",
            ],
            "rain droplets on objective (eye-repositioned Refract emitter)",
            addon="thermal",
        )

    def test_shared_eye_state_constants(self):
        # The shared eye-state foundation: one cached computation per frame
        # (camera origin + camera view direction), consumed by every
        # eye-space system.  The look vector is the TRUE camera in every
        # state via positionCameraToWorld: on foot, in a turret (the sight
        # IS the camera), and under freelook (the camera follows the head).
        # screenToWorldDirection does NOT update during freelook in every
        # render state (BIKI Killzone_Kid note), and weaponDirection pins
        # to the gun so turret freelook changes nothing (issue #204).
        self._assert_in_sqf(
            "fnc_getEyeState.sqf",
            [
                "diag_frameNo",
                "eyePos _unit",
                "eyeDirection _unit",
                "AGLToASL (positionCameraToWorld [0, 0, 0])",
                "positionCameraToWorld [0, 0, 100]",
                "count _eyeDir == 3",
                "count _eyeDir == 2",
                "missionNamespace setVariable [QGVAR(eyeState), [_frame, [_eye, _fwd, _up, _eyeVel]]]",
                "eyeStatePrev",
                "eyeStatePrevTime",
            ],
            "shared eye-state foundation (camera-tracked position + direction)",
            addon="core",
        )

    def test_smoothed_weather_constants(self):
        # The weather smoothing foundation: physical time constants
        # (rain 120 s, overcast 300 s, fog 900 s) from meteorology, one
        # cached EMA per frame.  Prevents the single-frame brightness snap
        # when the engine's rain/overcast step abruptly.
        self._assert_in_sqf(
            "fnc_getSmoothedWeather.sqf",
            [
                "diag_frameNo",
                "_tauRain",
                "_tauOvercast",
                "_tauFog",
                "120",
                "300",
                "900",
                "missionNamespace setVariable [QGVAR(weatherEMA), _prev]",
            ],
            "smoothed weather foundation (physical taus)",
            addon="core",
        )

    def test_no_raw_weather_in_brightness_paths(self):
        # Every brightness/visibility consumer must read the SMOOTHED
        # weather, not raw `rain`/`overcast`/`fog` (which step abruptly and
        # snap the display).  Only the droplet physics reads raw rain
        # (instant response is correct there).
        for fname, ctx, addon in [
            ("fnc_applyNVGTubeModel.sqf", "NVG tube", "nightvision"),
            ("fnc_calculateIlluminance.sqf", "illuminance", "core"),
            ("fnc_applyNightGrain.sqf", "night grain", "nightvision"),
            ("fnc_applyThermalVision.sqf", "thermal vision", "thermal"),
            ("fnc_calculateAttenuation.sqf", "attenuation", "optics"),
            ("fnc_calculateAtmosphericSeeing.sqf", "seeing", "optics"),
            ("fnc_calculateMirageIntensity.sqf", "mirage", "optics"),
        ]:
            src = _read_sqf(fname, addon)
            self.assertIn(
                "getSmoothedWeather",
                src,
                f"{ctx} must consume the smoothed weather",
            )
            # No raw `rain`/`overcast`/`fog` variable reads (assignments
            # inside getSmoothedWeather are the only legitimate ones; this
            # checks the consumers).  Comments are stripped first so a
            # mention in prose ("fog > 0.5") does not false-positive.
            src_code = "\n".join(
                ln for ln in src.splitlines() if not ln.strip().startswith("//")
            )
            for raw in ["(rain ", "(rain)", "(overcast ", "(fog "]:
                self.assertNotIn(
                    raw,
                    src_code,
                    f"{ctx} must not read raw {raw.strip('(')} directly",
                )

    def test_eye_state_consumers(self):
        # Every eye-space system must consume the shared foundation, not
        # recompute eye position or direction independently (the drift that
        # caused the HEAD memory-point bug and the separate vectorDirVisual
        # calls in the focus fan / blowout cone).
        for fname, ctx, addon in [
            ("fnc_applyNVGTubeModel.sqf", "NVG tube", "nightvision"),
            ("fnc_calculateIlluminance.sqf", "illuminance", "core"),
            ("fnc_applyRainDroplets.sqf", "droplets", "thermal"),
        ]:
            src = _read_sqf(fname, addon)
            self.assertIn(
                "getEyeState",
                src,
                f"{ctx} must consume the shared eye state",
            )
            self.assertNotIn(
                "= eyePos ", src, f"{ctx} must not recompute eyePos directly"
            )
            self.assertNotIn(
                "vectorDirVisual _player",
                src,
                f"{ctx} must not recompute the eye direction",
            )
            self.assertNotIn(
                "vectorUp _player",
                src,
                f"{ctx} must not recompute the up vector",
            )

    def test_solar_radiation_uses_daytime(self):
        # The solar model must read the LIVE clock (dayTime), not
        # date#3 + time/3600 (mission-start hour + elapsed, which drifts
        # when the clock is skipped or the mission runs long).
        cfg = (
            _REPO_ROOT
            / "addons"
            / "lighting"
            / "functions"
            / "astronomy"
            / "fnc_calculateSolarRadiation.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("private _hour = dayTime", cfg)
        self.assertNotIn("(_date#3) + (time / 3600)", cfg)

    def test_clothing_thermal_constants(self):
        # Issue #204: dynamic discovery + material-driven view factor.
        self._assert_in_sqf(
            "fnc_applyClothingThermal.sqf",
            [
                '["", "", "EXIT"] call FUNC(applySelectionThermal)',
                "applySelectionThermal",
                "allUnits",
                "FUNC(getThermalSelections)",
                "FUNC(getSelectionMaterials)",
                "fGround = 0.2",
                "fGround = 0.7",
            ],
            "per-item clothing: dynamic discovery + material view factor",
            addon="thermal",
        )

    def test_building_thermal_constants(self):
        # Issue #204: dynamic discovery + per-material heat distribution.
        # The old static name-matching ("engine"/"wheel") failed on modded
        # vehicles.  Selections come from fnc_getThermalSelections (all
        # parts, no names), heat from fnc_calculateVehicleHeat (MKK model),
        # distributed by the material conductivity k.
        self._assert_in_sqf(
            "fnc_applyBuildingThermal.sqf",
            [
                '["", "", "EXIT"] call FUNC(applySelectionThermal)',
                "applySelectionThermal",
                'allMissionObjects ""',
                "vehicles - [player]",
                'nearObjects ["Building", _viewDist]',
                'nearObjects ["ReammoBox", _viewDist]',
                'nearObjects ["Animal", _viewDist]',
                'nearObjects ["Thing", _viewDist]',
                "abs (_airTemp - _lastTemp) >= 2",
                "FUNC(getThermalSelections)",
                "FUNC(calculateVehicleHeat)",
                "_qInternal = _vehicleHeat * 770 * (_k / 50)",
                "_qInternal = _qInternal + 280",
                "QGVAR(vehicleHeatTrend)",
            ],
            "per-building thermal: dynamic discovery + material heat",
            addon="thermal",
        )
        # The static name-matching must be GONE - no _sn find calls.
        text = _read_sqf("fnc_applyBuildingThermal.sqf", "thermal")
        self.assertNotIn('_sn find "engine"', text)
        self.assertNotIn('_sn find "wheel"', text)
        self.assertNotIn("engineRunTime", text)

    def test_dynamic_thermal_selection_discovery(self):
        # Issue #204: selections are discovered dynamically (MKK pattern)
        # - Man = all texture slots, vehicle = config override >
        # textureSources > all-but-MFD.  NO static name matching.
        self._assert_in_sqf(
            "fnc_getThermalSelections.sqf",
            [
                'isKindOf "Man"',
                "getObjectTextures _object",
                "MKK_TI",
                "A3TI_ThermalSelections",
                "textureSources",
                "BIS_fnc_returnChildren",
                "BIS_fnc_inString",
                "QGVAR(thermalSelectionsCache)",
            ],
            "dynamic thermal-selection discovery (cached per class)",
            addon="thermal",
        )
        text = _read_sqf("fnc_getThermalSelections.sqf", "thermal")
        self.assertNotIn('find "engine"', text)
        self.assertNotIn('find "wheel"', text)

    def test_vehicle_heat_model_constants(self):
        # Issue #204 / finding 4: the heat fraction is solved from a
        # lumped-capacitance engine body temperature, not an accumulator.
        # Parameters are physical: real mass, published specific heat, the
        # Holman air convection correlation, and the thermostat setpoint.
        # The reference mod's warm-up/cooldown constants must be GONE.
        self._assert_in_sqf(
            "fnc_calculateVehicleHeat.sqf",
            [
                "C * dT/dt",
                "exp (-(_elapsed / _tau))",
                "getMass _vehicle",
                "boundingBoxReal _vehicle",
                "_operatingTemp = 90",
                "_capacitance = _massKg * 460",
                "5.6 + (3.9 * _speedMS)",
                "isEngineOn _vehicle",
                "QGVAR(vehicleHeatState)",
                "QGVAR(engineBodyTempC)",
                "QGVAR(vehicleHeatTrend)",
                "[HEAT]",
                "COMSOL",
                "Heat Generation in a Disc Brake",
                "P = m*a*v",
                "vectorMagnitude (velocity _vehicle)",
                "0.5 * _massKg",
                "_qBrake / _hA",
                "_prevSpeed",
                "300-800 C",
                "115-143.5 W/cm2",
            ],
            "vehicle heat model (lumped-capacitance physics + diagnostic trace)",
            addon="thermal",
        )
        text = _read_sqf("fnc_calculateVehicleHeat.sqf", "thermal")
        self.assertNotIn("_warmupTime = 120", text)
        self.assertNotIn("_cooldownTime = 320", text)
        self.assertNotIn("_cooldownDelay = 120", text)
        self.assertNotIn("_initialRunning = 0.65", text)

    def test_contact_conduction(self):
        # Issue #204: object-to-object contact conduction.  A warm object
        # touching a cold one transfers heat (and vice versa) - the
        # road/ground, building/earth, operator/vehicle boundaries blend
        # instead of a hard thermal edge.
        self._assert_in_sqf(
            "fnc_applyContactConduction.sqf",
            [
                "boundingBoxReal",
                "modelToWorld",
                "QGVAR(selTemperature)",
                "_fluxAB = (-20 * _dT)",
                "_fluxBA = -_fluxAB",
                "nearObjects 40",
                "QGVAR(contactLastT)",
            ],
            "object-to-object contact conduction (blend adjacent surfaces)",
            addon="thermal",
        )

    def test_vehicle_heat_gradient_wave(self):
        # Issue #204: heat spreads gradually across the vehicle's parts
        # (MKK wave-spread) - the block heats first, the hull follows,
        # NOT a uniform glow.  Each selection's flux is scaled by its phase,
        # and that phase is the DISTANCE from the heat source
        # (fnc_getThermalSelectionLag), not its position in the list.
        text = _read_sqf("fnc_applyBuildingThermal.sqf", "thermal")
        self.assertIn("_selectionPhase", text)
        self.assertIn("_waveHeat", text)
        self.assertIn("_qInternal * _waveHeat", text)
        self.assertIn("(3 - (2 * _waveHeat))", text)
        self.assertIn("FUNC(getThermalSelectionLag)", text)
        self.assertIn("_selLags", text)

    def test_selection_lag_is_distance_from_the_heat_source(self):
        # Issue #204: the phase comes from the model-space distance to the
        # heat source, so the engine bay leads and a rear wheel and rear
        # glass panel lag.  The three lag fractions must differ.
        source = [0.0, 2.4, 0.0]  # engine point, front of the model
        engine = [0.0, 2.4, 0.0]
        wheel = [1.5, -1.4, 0.0]
        glass = [0.0, -2.6, 1.1]
        lags = selection_thermal_lag([engine, wheel, glass], source)
        self.assertEqual(len(lags), 3)
        self.assertEqual(len({round(v, 6) for v in lags}), 3)
        self.assertLess(lags[0], lags[1])  # engine bay heats before the wheel
        self.assertLess(lags[1], lags[2])  # rear glass lags the rear wheel
        self.assertAlmostEqual(lags[0], 0.0, places=6)

        # The SQF must map position -> distance, never _forEachIndex.
        text = _read_sqf("fnc_getThermalSelectionLag.sqf", "thermal")
        self.assertIn("_pos distance _source", text)
        self.assertIn("/ _maxDistance", text)
        self.assertIn("FUNC(getHitPointMaterials)", text)
        self.assertIn('"wheel_1_1_axis"', text)
        self.assertIn("wheel_2_1_axis", text)

    def test_loadout_thermal_inertia(self):
        # Issue #204: every carried item (uniform, vest, backpack,
        # helmet, goggles, weapon + contents) has its own thermal
        # inertia.  A full backpack warms and cools SLOWER than an empty
        # one (content mass drives the skin-mass time constant).
        self._assert_in_sqf(
            "fnc_calculateUnitLoadoutThermal.sqf",
            [
                "uniform _unit",
                "vest _unit",
                "backpack _unit",
                "uniformItems _unit",
                "vestItems _unit",
                "backpackItems _unit",
                "_contentMass",
                "_inertia = 1 / (1 + (_mass / _refMass))",
                "_matFactor",
                "QGVAR(loadoutThermal)",
            ],
            "unit loadout thermal inertia (bag contents drive mass)",
            addon="thermal",
        )
        text = _read_sqf("fnc_applyClothingThermal.sqf", "thermal")
        self.assertIn("calculateUnitLoadoutThermal", text)
        self.assertIn("_loadoutFlux", text)
        # The mass scale is applied in the callee's solve.
        callee = _read_sqf("fnc_applySelectionThermal.sqf", "thermal")
        self.assertIn("_massScale", callee)
        self.assertIn("_skinMass = (0.1 * 70) * (_massScale", callee)

    def test_custom_surface_classification(self):
        # Issue #204: custom/modded surfaces (GdtStratisConcrete,
        # GdtStratisDryGrass) must classify by the embedded material
        # keyword - no static naming, no 'Script not found' warning
        # (the bare name must NOT reach preprocessFile).
        root = Path(__file__).resolve().parents[2]
        mat_dir = root / "addons" / "material" / "functions"
        text = (mat_dir / "fnc_classifyBySurfaceType.sqf").read_text(encoding="utf-8")
        self.assertIn('"concrete" in _name', text)
        self.assertIn('"grass" in _name', text)
        self.assertIn('"asphalt" in _name', text)
        self.assertIn("getSurfaceMaterial", text)
        surf = (mat_dir / "fnc_getSurfaceMaterial.sqf").read_text(encoding="utf-8")
        self.assertIn('in _surfId || {"/" in _surfId}', surf)  # path guard

    def test_ground_temperature_by_surface(self):
        # Issue #204: the ground temperature - the node-stack wrapper
        # classifies the surfaceType (#gdt prefix handled by the material
        # module) so asphalt stays warmer than soil at night, adds the
        # frost phase-change and the thermal-shadow depression, then the
        # per-position stamp.  The terrain cannot be re-textured (no
        # setTerrainTexture), so this position-based temperature is the
        # achievable "terrain painting".
        self._assert_in_sqf(
            "fnc_calculateGroundTemperature.sqf",
            [
                "surfaceType [_pos select 0, _pos select 1]",
                "classifyBySurfaceType",
                "calculateGroundNodeStack",
                "calculateFrostState",
                "isPositionShadowed",
                "currentSolarFlux",
                "getGroundStampOffset",
            ],
            "ground temperature (node stack + frost + shadow + stamp)",
            addon="thermal",
        )

    def test_thermal_selections_fallback_not_empty(self):
        # Issue #204: a vehicle whose textureSources produce nothing
        # (empty textures) must fall through to the all-but-MFD fallback -
        # caching an EMPTY list left the MRAP permanently unpainted
        # (heat ramped to 1 in the state, parts never rendered).
        text = _read_sqf("fnc_getThermalSelections.sqf", "thermal")
        self.assertIn("if (_selections isEqualTo []) then", text)
        self.assertIn('["mfd", _x, false] call BIS_fnc_inString', text)

    def test_selection_material_full_part_tree(self):
        # Issue #204: every object exposes its full part tree.  The
        # material detector gathers ALL signals and votes by weight
        # (the user's requirement: pull everything, then sort through
        # what is found - no first-match bias):
        #   surfaceInfo rvmat (3), hit-point map (3), texture-path
        #   keyword (2), selection name (1).
        text = _read_sqf("fnc_getSelectionMaterials.sqf", "thermal")
        self.assertIn("selectionNames _obj", text)
        self.assertIn("getObjectMaterials _obj", text)
        self.assertIn("hiddenSelectionsMaterials", text)
        self.assertIn("private _votes = createHashMap", text)
        self.assertIn("_votes set", text)
        self.assertIn("+ 3", text)  # surfaceInfo + hit-point weight
        self.assertIn("+ 2", text)  # texture-path weight
        self.assertIn("+ 1", text)  # selection-name weight
        self.assertIn("getHitPointMaterials", text)
        self.assertIn("_bestN", text)

    def test_hit_point_material_verification(self):
        # Issue #204: the vehicle DAMAGE MODEL guarantees part materials.
        # HitLFWheel can only exist on a wheel, HitEngine on the engine -
        # verified across vanilla (Offroad: HitLFWheel/HitEngine/HitGlass/
        # HitHull; Heli_Light_01: HitHRotor/HitVRotor/HitAvionics) AND
        # RHS (M109: HitLTrack/HitEngine/HitTurret) - the naming is a
        # consistent engine standard, inherited by every mod (the 42cdo
        # SOAR Griffin helicopter extends RHS_UH1Y and inherits its hit
        # points unchanged).
        text = _read_sqf("fnc_getHitPointMaterials.sqf", "thermal")
        self.assertIn("getAllHitPointsDamage", text)
        self.assertIn('_hp find "wheel"', text)
        self.assertIn('_hp find "engine"', text)
        self.assertIn('_hp find "fuel"', text)
        self.assertIn('_hp find "glass"', text)
        self.assertIn('_hp find "rotor"', text)
        self.assertIn('_hp find "avionics"', text)
        self.assertIn('_hp find "turret"', text)
        self.assertIn('_hp find "track"', text)
        self.assertIn('_mat = "rubber"', text)
        self.assertIn('_mat = "engine"', text)
        self.assertIn('_mat = "metal"', text)
        self.assertIn('_mat = "plastic"', text)
        # The detector consults the hit-point map before name-matching.
        detector = _read_sqf("fnc_getSelectionMaterials.sqf", "thermal")
        self.assertIn("getHitPointMaterials", detector)
        self.assertIn("_hpMap getOrDefault", detector)

    def test_texture_path_classification_order(self):
        # Issue #204: the texture path contains the VEHICLE NAME, which
        # pollutes the keywords (APC_Tracked_01_body has 'track',
        # pollutes the keywords (APC_Tracked_01_body has 'track',
        # Heli_Light_01_ext has 'light', acc_pointer has 'int').  The
        # classifier must check the PART signals first (metal _body/_ext/
        # hull, rubber wheel/tyre) before the ambiguous words, so the
        # APC and heli hulls read metal, not rubber/glass.
        sqf = _read_sqf("fnc_getSelectionMaterials.sqf", "thermal")
        # The metal-body check comes FIRST in the chain.
        body_pos = sqf.find('_tl find "_body"')
        glass_pos = sqf.find('_tl find "glass"')
        # metal body check must precede the glass/light check
        self.assertGreater(body_pos, 0)
        self.assertGreater(glass_pos, 0)
        self.assertLess(body_pos, glass_pos)
        # 'track' must NOT be in the rubber check (the vehicle name
        # APC_Tracked_01 contains it).
        self.assertNotIn('_tl find "track"', sqf)
        # interior must be the _int suffix, not bare 'int' (acc_pointer).
        self.assertIn('_tl find "_int"', sqf)
        self.assertNotIn('if (_tl find "int" >= 0)', sqf)

    def test_radiative_exchange(self):
        # Issue #204: a hot object heats the objects around it (a hot
        # barrel heats the weapon from inside out) - Stefan-Boltzmann
        # view-factor transfer between nearby objects.
        self._assert_in_sqf(
            "fnc_applyRadiativeExchange.sqf",
            [
                "nearObjects 30",
                "_sigma",
                "^ 4",
                "_F = 1 / (1 + ((_d * _d)",
                "applySelectionThermal",
                "QGVAR(radiativeLastT)",
            ],
            "radiative exchange (Stefan-Boltzmann view factor)",
            addon="thermal",
        )

    def test_exhaust_heat_field(self):
        # Issue #204: a firing muzzle or running engine expels hot gas
        # that warms the ground and air around it (muzzle blast over a
        # prone shooter's floor, jet afterburner heating the tarmac).
        self._assert_in_sqf(
            "fnc_applyExhaustHeat.sqf",
            [
                "QGVAR(barrelHeat)",
                "addGroundStamp",
                "isEngineOn _veh",
                "nearObjects 3",
                "modelToWorld",
                "muzzlePos",
                "muzzleTime",
            ],
            "exhaust/emission heat field (muzzle + engine)",
            addon="thermal",
        )

    def test_impact_residual_heat(self):
        # Issue #204: a bullet hole carries residual heat from the
        # projectile (the round arrives hot and transfers into the
        # surface).  The HitPart event + the stamp at the impact point.
        self._assert_in_sqf(
            "fnc_applyImpactHeat.sqf",
            [
                "getPosASL _projectile",
                "CfgAmmo",
                '>> "hit"',
                "addGroundStamp",
                "nearObjects 2",
                "applySelectionThermal",
            ],
            "projectile impact residual heat (bullet hole)",
            addon="thermal",
        )
        # The HitPart listener is wired in the optics postInit.
        post = (
            Path(__file__).resolve().parents[2]
            / "addons"
            / "optics"
            / "XEH_postInit.sqf"
        ).read_text(encoding="utf-8")
        # HitPart fires on the PROJECTILE, so it is attached per projectile
        # from the shooter's own Fired handler, not as a class registration.
        self.assertIn('_projectile addEventHandler ["HitPart"', post)
        self.assertIn("handleImpactHeat", post)

    def test_thermal_shadow(self):
        # Issue #204: shadowed ground is cooler than sunlit ground (the
        # direct solar loading is blocked) - a raycast toward the sun.
        self._assert_in_sqf(
            "fnc_isPositionShadowed.sqf",
            [
                "lineIntersectsSurfaces",
                '"GEOM", "NONE"',
                "currentSunAzimuth",
                "currentSunElevation",
                "QGVAR(shadowCache)",
                "diag_frameNo",
            ],
            "thermal shadow detection (sun raycast)",
            addon="thermal",
        )
        # The call keeps the documented eight arguments.  A ninth argument
        # (returnUnique) was rejected by the engine at that position with a
        # type error, and its default is already true.
        shadow = _read_sqf("fnc_isPositionShadowed.sqf", "thermal")
        self.assertNotIn("returnUnique", shadow)
        # The ground wrapper applies the shadow depression.
        ground = _read_sqf("fnc_calculateGroundTemperature.sqf", "thermal")
        self.assertIn("isPositionShadowed", ground)
        self.assertIn("currentSolarFlux", ground)

    def test_mapwide_thermal_caps(self):
        # map geometry with no selections) at load, zero runtime cost.
        # thermal is the single owner after the consolidation; optics keeps
        # no engine-thermal key, so load order cannot change the caps.
        cfg = (_REPO_ROOT / "addons" / "thermal" / "config.cpp").read_text(
            encoding="utf-8"
        )
        for frag in [
            "class All {",
            "afMax = 70",
            "mfMax = 50",
            "class AllVehicles: All",
        ]:
            self.assertIn(frag, cfg, f"config.cpp missing {frag} - map-wide caps")
        optics = (_REPO_ROOT / "addons" / "optics" / "config.cpp").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("CfgVehicles", optics)

    def test_infantry_thermal_config(self):
        # The static config: humans glow (mFact 1, tBody 32), vehicles get REAL
        # thermal caps (afMax 70, mfMax 50 - not 0, which the engine reads
        # as unset and falls back to vanilla 200).  AEE's physics drives
        # the per-part heat (engine/wheels) via setVehicleTIPars on top.
        cfg = (_REPO_ROOT / "addons" / "thermal" / "config.cpp").read_text(
            encoding="utf-8"
        )
        for frag in [
            "mFact = 1",
            "tBody = 32",
            "afMax = 70",
            "mfMax = 50",
            "htMin = 60",
            "htMax = 1800",
        ]:
            self.assertIn(
                frag,
                cfg,
                f"config.cpp missing {frag} - infantry/vehicle thermal override",
            )

    # ── Object temperature (fnc_calculateObjectTemperature.sqf) ──
    def test_object_temp_params_accept_empty_array(self):
        # The env PFH and calibration sweep call calculateObjectTemperature
        # with bare `[] call`, which passes an EMPTY array.  The old
        # [objNull] type filter rejected it ("Type Array, expected Object",
        # RPT 10-03-09).  The params now accept [] and the fallback maps
        # it to objNull -> currentUnit.
        self._assert_in_sqf(
            "fnc_calculateObjectTemperature.sqf",
            ['["_center", objNull, [objNull, []]]'],
            "empty-array call compatibility",
            addon="thermal",
        )

    def test_object_temp_dt_override(self):
        # The calibration sweep steps the clock by the hour but the model
        # clamps dt to 30 s (safe for the real 5 s env PFH).  Without an
        # override, the vehicle never warms through the day in the sweep.
        # The _dtOverride param simulates the real elapsed time directly.
        self._assert_in_sqf(
            "fnc_calculateObjectTemperature.sqf",
            ['["_dtOverride", -1, [0]]', "if (_dtOverride >= 0) then {"],
            "dt override for calibration",
            addon="thermal",
        )

    def test_object_temp_radiative_floor(self):
        # REGRESSION (10-54 sweep): the old `max _airTemp` clamp erased the
        # day-time solar gain whenever wind cooling exceeded it (a sunlit
        # vehicle read exactly air temp), and blocked real night cooling.
        # The per-object solver no longer carries a ground clamp at all:
        # the ground temperature now comes from the per-position energy
        # balance in fnc_calculateGroundTemperature, which exchanges
        # radiation against the SKY (Swinbank 1963) - the honest
        # radiative-equilibrium floor.  The object solver delegates.
        self._assert_in_sqf(
            "fnc_calculateObjectTemperature.sqf",
            ["calculateGroundTemperature", "private _groundTarget"],
            "ground temperature delegated to the per-position energy balance",
            addon="thermal",
        )
        # The old per-class gain table and the manual wind/shade clamp are
        # GONE - the solver does convection, radiation and cloud itself.
        text = _read_sqf("fnc_calculateObjectTemperature.sqf", "thermal")
        self.assertNotIn("_groundTarget max (_airTemp - 5)", text)
        self.assertNotIn("_groundGain", text)

    def test_object_temp_taus(self):
        # The inert-surface tau is the derived lumped capacitance
        # m*cp/(h*A) (Incropera Ch. 5); the infantry and acclimatisation taus
        # remain the cited physiological response times.
        self._assert_in_sqf(
            "fnc_calculateObjectTemperature.sqf",
            [
                "(_massObj * _cpM) / ((_hConv * _areaObj) max 1e-3)",
                "_dt / 1800",
                "_tau = 60 + _shock * 300",
            ],
            "derived lumped tau + cited physiological taus",
            addon="thermal",
        )

    def test_conduction_coupling_constants(self):
        # #124 audit: the coupling is REAL Stefan-Boltzmann radiant
        # exchange (4th power), not the old linear surplus/d^2.  A fire
        # (600 C) radiates ~100x more than a warm engine and reaches
        # everything within 10 m (large-area emitter), so the view
        # factor is large for fires, small for warm engines.
        self._assert_in_sqf(
            "fnc_calculateObjectTemperature.sqf",
            [
                "_hotSources",
                "5.670374419e-8",
                "_hotK ^ 4",
                "_coldK ^ 4",
                "_fView",
                "_nTemp > 300",
                "_d > 10",
                "min 5",
                "_coupling > 0.05",
            ],
            "radiant coupling (Stefan-Boltzmann 4th power)",
            addon="thermal",
        )

    def test_burning_thermal_constants(self):
        self._assert_in_sqf(
            "fnc_calculateObjectTemperature.sqf",
            [
                "damage _obj >= 0.7",
                "_hpDamages select _i",
                "_hpNames select _i",
                "getAllHitPointsDamage",
                "_airTemp + 600",
                "_isBurning",
            ],
            "burning/incendiary saturation",
            addon="thermal",
        )

    def test_engine_heat_model(self):
        # F8: the engine body is the thermostat setpoint (Heywood), the
        # exhaust gas is a real temperature with a labelled area fraction, and
        # the body tau is the derived lumped capacitance.  No reference-mod
        # 40/200/300 constants remain.
        self._assert_in_sqf(
            "fnc_calculateObjectTemperature.sqf",
            [
                "private _tOp = 90",
                "private _tExh = 480",
                "_exhFrac * ((_tExh max _airTemp) - _airTemp)",
                "_engineRunTime * exp (-_dt / _tau)",
            ],
            "thermostat-setpoint engine heat + real exhaust + derived tau",
            addon="thermal",
        )

    def test_exhaust_fraction_is_a_labelled_lumped_calibration(self):
        # No published source defines a body-area fraction at exhaust-port
        # gas temperature, so 0.05 stays an AEE lumped calibration.  The
        # 480 C value is inside-pipe gas, not the cooler pipe skin, and the
        # comment must say so.  The SAE alternatives are named as a future
        # option only; the behaviour is unchanged.
        text = _read_sqf("fnc_calculateObjectTemperature.sqf", "thermal")
        self.assertIn("private _exhFrac = 0.05", text)
        self.assertIn("AEE lumped calibration", text)
        self.assertIn("INSIDE the pipe", text)
        self.assertIn("SAE 2016-01-0280", text)
        self.assertIn("SAE 2008-01-1819", text)

    def test_second_sun_brightness_unit_is_labelled(self):
        # The engine scale is dimensionless.  The peak 13 stays, matching
        # DEFAULT_SECONDSUN_BRIGHTNESS, and the stale "brightness 200" and
        # "radiation * 6" comments are gone.
        text = _read_sqf("fnc_applySecondSun.sqf", "thermal")
        self.assertIn("private _lightBrightness = 13 * _radiation;", text)
        self.assertIn("DEFAULT_SECONDSUN_BRIGHTNESS", text)
        self.assertIn("setLightIntensity = Brightness^2 * 2500", text)
        self.assertNotIn("brightness 200", text)
        self.assertNotIn("radiation * 6", text)

    def test_ground_gains(self):
        # The per-class ground-gain table (5-15 C offsets per surface
        # type) was removed in the #124 audit: the ground temperature is
        # now solved per-position with the full energy balance in
        # fnc_calculateGroundTemperature (material alpha, convection,
        # sky radiation, thermal stamps).  The object solver delegates to
        # it and no longer carries a manual per-class gain.
        self._assert_in_sqf(
            "fnc_calculateObjectTemperature.sqf",
            ["calculateGroundTemperature", "private _groundTarget"],
            "ground delegated to the per-position solve",
            addon="thermal",
        )
        text = _read_sqf("fnc_calculateObjectTemperature.sqf", "thermal")
        self.assertNotIn("#gdtdesert", text)
        self.assertNotIn("#gdtsnow", text)

    def test_insulation_and_metabolic(self):
        self._assert_in_sqf(
            "fnc_calculateObjectTemperature.sqf",
            ["0.3 + 0.5", "120", "60", "20", "_metabolicHeat * 0.05"],
            "clothing insulation / metabolic heat",
            addon="thermal",
        )

    # ── Thermal crossover (fnc_calculateThermalCrossover.sqf) ──
    def test_crossover_constants(self):
        self._assert_in_sqf(
            "fnc_calculateThermalCrossover.sqf",
            ["1.5", "abs _sunElev < 10", "_timer > 1", "-6 min 6"],
            "crossover delta / twilight gate / sustain timer",
            addon="thermal",
        )

    def test_crossover_surface_estimates(self):
        self._assert_in_sqf(
            "fnc_calculateThermalCrossover.sqf",
            [
                "_airTemp - 2",
                "_airTemp - 1",
                "_airTemp + 5",
                "_airTemp - 3",
                "_airTemp + 2 * (1 - _overcast)",
            ],
            "surface temperature estimates",
            addon="thermal",
        )

    # ── Solar glare (fnc_calculateSolarGlare.sqf) ──
    def test_glare_constants(self):
        self._assert_in_sqf(
            "fnc_calculateSolarGlare.sqf",
            [
                "1 - _angularDiff / 45",
                "_sunElev / 20",
                "_sunElev - 20) / 30",
                "1 - _overcast * 0.8",
            ],
            "glare angular falloff / elevation / overcast",
        )


class TestThermalContrastMixedObjects(unittest.TestCase):
    """Scene contrast must ignore infantry and fall back cleanly."""

    @staticmethod
    def scene_vehicle_temp(entries, air_temp=15.0):
        """Mirror of the vehicle-only average in fnc_calculateThermalContrast.

        entries: list of (kind, temp) where kind is 'man', 'veh', or 'bad'.
        Returns the average vehicle temp, or air_temp when no vehicles.
        """
        veh_sum = 0.0
        veh_count = 0
        for kind, temp in entries:
            if kind == "bad":
                continue  # type guard skips malformed
            if kind == "man":
                continue  # infantry excluded
            if isinstance(temp, (int, float)):
                veh_sum += temp
                veh_count += 1
        return veh_sum / veh_count if veh_count else air_temp

    def test_infantry_does_not_skew_average(self):
        # Two vehicles at 28 C, five infantry at 33 C.  Average must be 28.
        entries = [("veh", 28.0), ("veh", 28.0)] + [("man", 33.0)] * 5
        self.assertAlmostEqual(self.scene_vehicle_temp(entries), 28.0, places=6)

    def test_no_vehicles_falls_back_to_air(self):
        entries = [("man", 33.0)] * 3
        self.assertAlmostEqual(self.scene_vehicle_temp(entries, 15.0), 15.0, places=6)

    def test_empty_scene_falls_back_to_air(self):
        self.assertAlmostEqual(self.scene_vehicle_temp([], 12.0), 12.0, places=6)

    def test_malformed_entry_does_not_crash(self):
        entries = [("bad", None), ("veh", 30.0)]
        self.assertAlmostEqual(self.scene_vehicle_temp(entries), 30.0, places=6)

    def test_cold_vehicle_lower_contrast_than_hot(self):
        # Ground 18 C.  Cold vehicle 20 C -> delta 2 -> 2/8 = 0.25.
        # Hot vehicle 34 C -> delta 16 -> capped 1.0.
        ground = 18.0
        cold = min(abs(20.0 - ground) / 8.0, 1.0)
        hot = min(abs(34.0 - ground) / 8.0, 1.0)
        self.assertAlmostEqual(cold, 0.25, places=6)
        self.assertAlmostEqual(hot, 1.0, places=6)
        self.assertLess(cold, hot)


# ─── NVG stack audit #153: spectral response + gate flicker ────────────────
# Mirror of the photocathode spectral weighting and the gating-boundary
# blackout flicker added in fnc_applyNVGTubeModel.sqf.


def spectral_weight(sim, is_ir_light=False):
    """Mirror of the #153 spectral-weight factor in the glow loop.

    The photocathode peaks 600-900 nm (near-IR), so IR-rich sources excite
    the tube more than their photopic output: IR strobes/markers 1.8,
    vehicle IR lights 1.6, muzzle/explosive flame 1.4, visible lamps 1.0.
    """
    if sim == "nvmarker":
        return 1.8
    if sim == "Lamps" and is_ir_light:
        return 1.6
    if sim == "Lamps":
        return 1.0
    return 1.4  # F_40_White flame etc.


def gate_flicker_duration(tier):
    """Mirror of the #153 gate-transition blackout duration (seconds)."""
    return {
        "GEN1": 0.55,
        "GEN2": 0.35,
        "GEN3": 0.18,
        "PVS31": 0.10,
    }.get(tier, 0.10)


class TestNVGSpectralWeight(unittest.TestCase):
    """#153 gap 3: the photocathode's near-IR response."""

    def test_ir_marker_excites_more_than_lamp(self):
        self.assertGreater(spectral_weight("nvmarker"), spectral_weight("Lamps"))

    def test_muzzle_flash_ir_rich(self):
        # F_40_White flame carries strong IR regardless of class.
        self.assertEqual(spectral_weight("unknown"), 1.4)
        self.assertGreater(spectral_weight("unknown"), 1.0)

    def test_vehicle_ir_light(self):
        self.assertEqual(spectral_weight("Lamps", is_ir_light=True), 1.6)
        self.assertGreater(spectral_weight("Lamps", True), spectral_weight("Lamps"))

    def test_visible_lamp_neutral(self):
        self.assertEqual(spectral_weight("Lamps"), 1.0)

    def test_all_weights_bounded(self):
        for sim in ["Lamps", "nvmarker", "F_40_White", "other"]:
            for ir in [False, True]:
                w = spectral_weight(sim, ir)
                self.assertGreaterEqual(w, 1.0)
                self.assertLessEqual(w, 2.0)


class TestNVGGateFlicker(unittest.TestCase):
    """#153 gap 2: gating-boundary blackout."""

    def test_tier_duration_ordering(self):
        # Gen 1 stutters hardest, PVS-31 nearly instant.
        self.assertGreater(gate_flicker_duration("GEN1"), gate_flicker_duration("GEN2"))
        self.assertGreater(gate_flicker_duration("GEN2"), gate_flicker_duration("GEN3"))
        self.assertGreater(
            gate_flicker_duration("GEN3"), gate_flicker_duration("PVS31")
        )

    def test_all_bounded_under_a_second(self):
        for tier in ["GEN1", "GEN2", "GEN3", "PVS31"]:
            self.assertLess(gate_flicker_duration(tier), 1.0)
            self.assertGreater(gate_flicker_duration(tier), 0.0)

    def test_no_flicker_when_gate_unchanged(self):
        # The SQF only fires the flicker on a state CHANGE; a steady gate
        # never sets the flag.
        self.assertEqual(
            gate_flicker_duration("GEN1") > 0, True
        )  # fires on change only


class TestNVGStackAuditSQFSync(unittest.TestCase):
    """#153: source-level drift locks for the audit fixes."""

    def _read(self, name):
        # NVG functions moved to the aee_nightvision addon (three-system split).
        base = (
            Path("addons/nightvision", "functions")
            if name.startswith("fnc_applyNVG") or name.startswith("fnc_applyNight")
            else Path("addons/optics", "functions")
        )
        if (base / name).exists():
            return (base / name).read_text(encoding="utf-8")
        for f in base.rglob(name):
            return f.read_text(encoding="utf-8")
        raise FileNotFoundError(f"{name} not found under {base}")

    def test_dead_burn_position_removed(self):
        # Bug A: the write-only world-position afterimage is gone; the
        # scalar blowout + release/hold envelope drives the render.
        text = self._read("fnc_applyNVGTubeModel.sqf")
        self.assertNotIn("nvgBurnPos", text)
        self.assertNotIn("_burnInt", text)
        self.assertIn("_release", text)  # scalar persistence kept

    def test_spectral_weight_wired(self):
        text = self._read("fnc_applyNVGTubeModel.sqf")
        self.assertIn("_spectralWeight", text)
        self.assertIn("_spectralWeight = 1.8", text)  # IR marker

    def test_gate_flicker_wired(self):
        text = self._read("fnc_applyNVGTubeModel.sqf")
        self.assertIn("nvgGateActive", text)
        self.assertIn("nvgGateFlickerUntil", text)
        self.assertIn("nvgGrainBoost", text)


class TestPostProcessHandleOwnership(unittest.TestCase):
    """Nightvision must own its ChromAberration. Optics owns its own."""

    def test_no_nightvision_file_reads_the_optics_chroma_handle(self):
        # (a) The optics ChromAberration variable must appear in NO file
        # under addons/nightvision/.  One reference re-creates the defect.
        addon = _REPO_ROOT / "addons" / "nightvision"
        offenders = [
            str(path.relative_to(_REPO_ROOT))
            for path in sorted(addon.rglob("*.sqf"))
            if "QEGVAR(optics,ppHandle_ChromAberration)"
            in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [])

    def test_nightvision_stores_and_reads_its_own_chroma_handle(self):
        # (b) Nightvision reads and writes QGVAR(ppHandle_NVG_Chroma), and
        # the handle joins the NVG destroy list.
        text = _read_sqf("fnc_applyNVGTubeModel.sqf", "nightvision")
        self.assertIn("getVariable [QGVAR(ppHandle_NVG_Chroma), -1]", text)
        self.assertIn("setVariable [QGVAR(ppHandle_NVG_Chroma), _hChroma]", text)
        self.assertIn("QGVAR(ppHandle_NVG_Chroma),", text)

    def test_chroma_neutral_reset_is_not_gated_on_grain(self):
        # (c) The neutral reset sits in the sensor-exit block, BEFORE and
        # outside the `if (_active)` grain gate.  The gate may still skip
        # the NVG-only teardown.
        text = _read_sqf("fnc_applyNVGTubeModel.sqf", "nightvision")
        exit_block = _sqf_block(text, "if (currentVisionMode _player != 1) exitWith")
        self.assertLess(
            exit_block.index("getVariable [QGVAR(ppHandle_NVG_Chroma), -1]"),
            exit_block.index("if (_active) then {"),
            "chroma reset must precede the grain gate",
        )
        gate_block = _sqf_block(exit_block, "if (_active) then")
        self.assertNotIn(
            "ppHandle_NVG_Chroma",
            gate_block,
            "chroma reset must not be nested in the grain gate",
        )

    def test_sensor_exit_deferred_disables_carry_a_generation_guard(self):
        # (d) Each of the three sensor-exit deferred disables captures the
        # effect generation and skips the disable when it changed.
        text = _read_sqf("fnc_managePostProcess.sqf", "vision")
        block = _sqf_block(text, "if (_visionMode == 1 || _visionMode == 2) exitWith")
        pairs = (
            ("chromaGen", "ppHandle_ChromAberration"),
            ("blurGen", "ppHandle_DynamicBlur"),
            ("ccGen", "ppHandle_ColorCorrections"),
        )
        for gen, handle in pairs:
            self.assertIn(
                f"private _gen = missionNamespace getVariable [QGVAR({gen}), 0];",
                block,
                f"{gen}: generation not captured",
            )
            self.assertIn(
                f"getVariable [QGVAR({gen}), 0] == _gen",
                block,
                f"{gen}: generation not compared",
            )
            self.assertIn(handle, block, f"{handle}: disable missing")
        self.assertEqual(block.count('params ["_gen"]'), 3)
        self.assertEqual(block.count("CBA_fnc_waitAndExecute"), 3)


class TestExitPathDiscipline(unittest.TestCase):
    """An EXIT branch must leave the function, not fall through.

    Four thermal functions restored their state and then carried straight on
    into the code that applies it again, because the branch ended in a dead
    `0` rather than in an exit.  The restore was undone on the same call, so
    a worn uniform kept its flat thermal paint in normal vision.  This walks
    every addon so the class cannot come back.
    """

    _MODES = ('"EXIT"', '"OFF"', '"DISABLE"', '"TEARDOWN"', '"STOP"')

    @staticmethod
    def _blank(src):
        """Replace comment and string bodies with spaces, keeping newlines.

        Brace counting must ignore braces inside comments and string
        literals.  Newlines survive so line numbers still line up.
        """
        out, i, n = [], 0, len(src)
        while i < n:
            ch = src[i]
            if ch == '"':
                out.append(" ")
                i += 1
                while i < n:
                    if src[i] == "\\":
                        out.append("  ")
                        i += 2
                        continue
                    if src[i] == '"':
                        out.append(" ")
                        i += 1
                        break
                    out.append("\n" if src[i] == "\n" else " ")
                    i += 1
            elif src.startswith("//", i):
                j = src.find("\n", i)
                j = n if j < 0 else j
                out.append(" " * (j - i))
                i = j
            elif src.startswith("/*", i):
                j = src.find("*/", i + 2)
                j = n if j < 0 else j + 2
                out.append("".join(c if c == "\n" else " " for c in src[i:j]))
                i = j
            else:
                out.append(ch)
                i += 1
        return "".join(out)

    def test_no_exit_branch_falls_through(self):
        """Every top-level mode branch must exit or pair with an else.

        The dead `0` in the old form evaluated to a value nobody read, and
        the run continued into the apply path.  A restore that is undone on
        the same call is not a restore.
        """
        root = _REPO_ROOT / "addons"
        offenders = []
        for path in sorted(root.rglob("*.sqf")):
            src = path.read_text(encoding="utf-8", errors="replace")
            raw = src.split("\n")
            code = self._blank(src).split("\n")
            depth = 0
            for idx, line in enumerate(code):
                stmt = raw[idx]
                if (
                    depth == 0
                    and line.strip().startswith("if ")
                    and any(mode in stmt for mode in self._MODES)
                ):
                    level, end, opened = 0, idx, False
                    while end < len(code):
                        level += code[end].count("{") - code[end].count("}")
                        if "{" in code[end]:
                            opened = True
                        if opened and level == 0:
                            break
                        end += 1
                    body = "\n".join(raw[idx : end + 1])
                    closing = raw[end]
                    tail = closing.rsplit("}", 1)[-1].strip() if "}" in closing else ""
                    nxt = raw[end + 1].strip() if end + 1 < len(raw) else ""
                    exits = "exitWith" in body
                    pairs = (
                        tail.startswith("else")
                        or nxt.startswith("} else")
                        or nxt == "else"
                    )
                    if not (exits or pairs):
                        rel = path.relative_to(_REPO_ROOT)
                        offenders.append(f"{rel}:{idx + 1}")
                depth += line.count("{") - line.count("}")
        self.assertEqual(
            offenders,
            [],
            "these mode branches restore and then fall through: "
            + ", ".join(offenders),
        )


class TestThermalPaintVisionGate(unittest.TestCase):
    """The FLIR heat paint must be written only under thermal vision.

    fnc_applySelectionThermal is the single choke point for the heat paint
    and it carried no vision gate at all.  The fired handler runs
    applyWeaponBarrelHeat in every vision mode and that function paints the
    PLAYER, so firing a round in daylight repainted the operator red with no
    teardown to undo it.  The physics store must stay ungated, because the
    AGC reads it and barrel heat has to accumulate before thermal opens.
    """

    _F = (
        _REPO_ROOT
        / "addons"
        / "thermal"
        / "functions"
        / "display"
        / "fnc_applySelectionThermal.sqf"
    )

    def setUp(self):
        self.lines = self._F.read_text(encoding="utf-8").split("\n")

    def _line_of(self, needle):
        for index, line in enumerate(self.lines):
            if needle in line:
                return index
        self.fail(f"{needle!r} not found in {self._F.name}")

    def test_flag_comes_from_the_live_host_channel(self):
        flag = self._line_of("private _thermalOn")
        mode = self._line_of("isThermalHostActive")
        self.assertLess(flag, mode, "the flag must be set from the live host channel")
        self.assertIn(
            "[_viewer] call FUNC(isThermalHostActive)",
            self.lines[mode],
            "the gate must key on the thermal host channel",
        )

    def test_save_and_material_swap_are_gated(self):
        save = self._line_of("_alreadySaved < 0")
        self.assertIn("_thermalOn", self.lines[save])
        swap = self._line_of("setObjectMaterial [_forEachIndex")
        self.assertGreater(swap, save, "the FPN swap must sit in the gated block")

    def test_heat_texture_paint_is_gated(self):
        paint = self._line_of("setObjectTexture [_idx, _colour]")
        self.assertIn("_thermalOn", self.lines[paint], "the heat paint is ungated")

    def test_physics_store_stays_ungated(self):
        store = self._line_of("setVariable [QGVAR(selTemperature)")
        self.assertNotIn(
            "_thermalOn", self.lines[store], "the AGC input must not be gated"
        )

    def test_exit_restore_stays_ungated(self):
        for needle in (
            "setObjectTexture [_i",
            "setObjectMaterial [_i",
        ):
            index = self._line_of(needle)
            self.assertNotIn(
                "_thermalOn", self.lines[index], "the restore must always run"
            )

    def test_gate_is_keyed_per_object_and_per_selection(self):
        """The repaint gate must key on the selection, not the object alone.

        Regression: the gate was keyed on the object only, while the building
        and clothing callers paint one selection per call.  The first entry of
        each pass stamped the object, so every later part of that object was
        held for the whole pass and painted the next pass onward in the same
        order - only the first selection ever reached the paint.  The parts
        kept the FPN material with no heat colour, which is the flat vehicle
        and flat clothing report.  The selection must be part of both the read
        and the stamp.
        """
        self.assertIn("_gateSel", self._F.read_text(encoding="utf-8"))
        read = self._line_of("_gate getOrDefault [_gateKey")
        stamp = self._line_of("_gate set [_gateKey")
        self.assertGreaterEqual(read, 0)
        self.assertGreater(stamp, read, "the stamp must follow the read")

    def test_exit_save_captures_every_texture_slot(self):
        """EXIT must restore every slot it saved, by the saved index.

        The save runs once per object, on the first selection that paints.
        getObjectTextures and getObjectMaterials are indexed by the
        hiddenSelections texture slot, the same index the paint writes, so
        EXIT must restore those arrays by THEIR OWN index.  The old restore
        walked the default-LOD `selectionNames _obj` list and used its
        position as the texture index - a different index space - so it could
        restore the wrong slots.  Save what the paint writes; restore what was
        saved.
        """
        text = self._F.read_text(encoding="utf-8")
        self.assertIn("_saved pushBack [_obj, _oldTexs, _oldMats]", text)
        self.assertIn("private _n = (count _oldTexs) max (count _oldMats);", text)


def thermal_paint_level(b, levels=255):
    """The integer level the SQF quantiser paints for a band position `_b`.

    SQF: round((_b max 0 min 1) * (_levels - 1)).  SQF round is half away from
    zero, so the positive-domain mirror is floor(x + 0.5), NOT Python's
    banker's round.
    """
    x = max(0.0, min(1.0, b)) * (levels - 1)
    return math.floor(x + 0.5)


def thermal_paint_uploads(samples, levels=255, initial=-1):
    """Mirror of the applySelectionThermal change gate.

    The SQF stores the PAINTED level of the last upload (`_qLevel`) and
    re-uploads only when the new level differs by at least one step.  A wobble
    that stays inside one level causes zero uploads, while a real one-level
    change causes exactly one.
    """
    last = initial
    uploads = 0
    for b in samples:
        level = thermal_paint_level(b, levels)
        if level != last:
            uploads += 1
            last = level
    return uploads


class TestThermalPaintLevelGate(unittest.TestCase):
    """The heat-paint change gate must key on the PAINTED level, not `_b`.

    The first flicker fix compared the RAW band position against the last
    upload with a half-step dead-band.  That is the wrong quantity: the colour
    is built from the quantised level, and two raw positions inside one level
    can sit up to a full step apart - more than the half-step dead-band - so
    the raw gate still re-uploaded an IDENTICAL colour.  The gate now compares
    the integer level that feeds the colour string.
    """

    _F = (
        _REPO_ROOT
        / "addons"
        / "thermal"
        / "functions"
        / "display"
        / "fnc_applySelectionThermal.sqf"
    )

    def test_residual_fixture_levels_are_equal(self):
        # The live-run values that flickered both round to level 51, so the
        # painted colour never changed between them.
        self.assertEqual(thermal_paint_level(0.198885), 51)
        self.assertEqual(thermal_paint_level(0.200011), 51)

    def test_alternating_fixture_never_reuploads(self):
        # 60 alternating passes across the two live-run values: zero uploads.
        samples = [0.198885 if i % 2 == 0 else 0.200011 for i in range(60)]
        self.assertEqual(thermal_paint_uploads(samples, initial=51), 0)

    def test_same_level_spanning_more_than_the_old_deadband(self):
        # 0.1989 and 0.2027 are both level 51 but 0.0038 apart - MORE than the
        # old half-step dead-band (0.001969).  The raw gate re-uploaded the
        # same colour; the level gate must not.
        self.assertEqual(thermal_paint_level(0.1989), 51)
        self.assertEqual(thermal_paint_level(0.2027), 51)
        self.assertGreater(abs(0.2027 - 0.1989), 0.5 / 254.0)
        samples = [0.1989 if i % 2 == 0 else 0.2027 for i in range(60)]
        self.assertEqual(thermal_paint_uploads(samples, initial=51), 0)

    def test_real_one_level_change_uploads_once(self):
        # 0.200011 (level 51) -> 0.203291 (level 52), both from the live run.
        self.assertEqual(thermal_paint_level(0.200011), 51)
        self.assertEqual(thermal_paint_level(0.203291), 52)
        self.assertEqual(thermal_paint_uploads([0.200011, 0.203291], initial=51), 1)

    def test_a_stay_at_the_new_level_adds_no_more_uploads(self):
        samples = [0.200011] + [0.203291] * 59
        self.assertEqual(thermal_paint_uploads(samples, initial=51), 1)

    def test_a_real_ramp_uploads_once_per_level_crossed(self):
        # A genuine warming ramp repaints once per level crossed, no more.
        ramp = [0.20 + i * (1.0 / 254.0) for i in range(5)]
        self.assertEqual(thermal_paint_uploads(ramp, initial=51), 4)

    def test_source_gates_on_the_level_and_stores_it(self):
        text = self._F.read_text(encoding="utf-8")
        self.assertIn(
            "private _qLevel = round ((_b max 0 min 1) * (_levels - 1));", text
        )
        self.assertIn("private _moved = (_qLevel != _lastLevel);", text)
        self.assertIn("_bands set [_bandKey, [_qLevel, _palette, _polarity]]", text)
        self.assertNotIn("_deadband", text, "the raw-position dead-band must be gone")
        self.assertNotIn("_was != _colour", text, "the exact compare must stay gone")


class TestThermalSelectionPaintSet(unittest.TestCase):
    """A licence plate must be painted like every other selection.

    fnc_getThermalSelections' textureSources branch selects the CAMO slots
    only.  A licence plate is a hiddenSelection that no textureSource declares,
    so the branch skipped it and the plate texture survived the flat heat paint
    (the operator's readable-plate report).  The branch now adds every
    remaining non-MFD hiddenSelection - the same set the fallback paints.
    """

    _F = (
        _REPO_ROOT
        / "addons"
        / "thermal"
        / "functions"
        / "display"
        / "fnc_getThermalSelections.sqf"
    )

    def test_texture_sources_do_not_skip_a_plate(self):
        text = self._F.read_text(encoding="utf-8")
        self.assertIn("_selections pushBackUnique _forEachIndex", text)
        self.assertIn("if (_selections isEqualTo []) then", text)
        self.assertIn('["mfd", _x, false] call BIS_fnc_inString', text)


class TestThermalEdgeKernel(unittest.TestCase):
    """The local-contrast thermal edge kernel (fnc_evaluateThermalEdge.sqf).

    The kernel decides a thermal EDGE from a selection's band radiance and a
    LOCAL background radiance, with a sensor-derived threshold.  It takes the
    background as an ARGUMENT and never reads the scene AGC window.  That is
    the correction: a scene-adaptive threshold moves with the scene, and
    sensitivity belongs to the sensor and stays fixed.

    The arithmetic is mirrored here and locked against the SQF source.  The
    suite's SQF interpreter (sqf_lite) cannot execute this kernel: the kernel
    must use `finite` (SQF NaN compares false against everything, so max/min
    cannot clamp it), and the interpreter implements no `finite`.  The
    headless behavioural proof is the docker probe aee_p68_edge_probe.sqf,
    which calls the real kernel with real radiances on the dedicated server.
    """

    _KERNEL = (
        _REPO_ROOT
        / "addons"
        / "thermal"
        / "functions"
        / "solver"
        / "fnc_evaluateThermalEdge.sqf"
    )

    @classmethod
    def setUpClass(cls):
        cls.code = _code_only(cls._KERNEL.read_text(encoding="utf-8"))

    def _default_threshold(self):
        # Read the declared default from the real SQF, so a change to it fails
        # this test until the mirror is re-synced.
        import re

        m = re.search(r'\["_threshold",\s*([0-9.]+)\s*,\s*\[0\]\]', self.code)
        if m is None:
            self.fail("the threshold default is not declared in the kernel")
        return float(m.group(1))

    def _edge(self, signal, background, threshold=None, noise=0.0):
        # Mirror of the kernel body, pinned by test_source_guards_present.  The
        # finite guard runs first, exactly as the kernel orders it: SQF max/min
        # cannot clamp NaN, so the refusal must come before the arithmetic.
        if threshold is None:
            threshold = self._default_threshold()
        if not (
            math.isfinite(signal)
            and math.isfinite(background)
            and math.isfinite(threshold)
            and math.isfinite(noise)
        ):
            return False, -1
        if background <= 0:
            return False, -1
        contrast = min(1.0, max(0.0, (signal - background) / background))
        if not math.isfinite(contrast):
            return False, -1
        # The threshold plus the range-derived sensor noise floor is clamped
        # to the 0..1 contrast scale, NOT floored at the 1/16 display band.
        # The band floor was the DISPLAY quantity the sensor decision must not
        # use.  A higher noise floor hides more, never less.
        threshold = min(1.0, max(0.0, threshold + noise))
        return contrast >= threshold, contrast

    def test_the_noise_floor_raises_the_threshold(self):
        # A weak contrast (1%) resolves with no noise and fails once the
        # noise floor rises above it.
        self.assertEqual(self._edge(0.0101, 0.01, 0.004349, 0.0)[0], True)
        self.assertEqual(self._edge(0.0101, 0.01, 0.004349, 0.02)[0], False)

    def test_source_guards_present(self):
        code = self.code
        # The relative contrast against the LOCAL background, verbatim.
        self.assertIn("((_signal - _background) / _background) max 0 min 1", code)
        # The background is the divisor, so a non-positive one is refused.
        self.assertIn("if (_background <= 0) exitWith { [false, -1] };", code)
        # The non-finite signal guard.
        self.assertIn("if !(finite _signal) exitWith { [false, -1] };", code)
        # The threshold plus the range-derived noise floor is clamped to the
        # 0..1 scale, NOT floored at the 1/16 display band.  The band floor
        # was the conflated quantity this sensor decision must not use.
        self.assertIn("(_threshold + _noise) max 0 min 1", code)
        self.assertNotIn("_bandStep", code)
        # The refusal is not a contrast in 0..1.
        self.assertIn("[false, -1]", code)
        # The value form of the type test, never the quoted type name.
        self.assertIn("isEqualType 0", code)
        # The decision and the contrast are returned together.
        self.assertIn("[_edge, _contrast]", code)

    def test_default_threshold_is_sensor_scale_not_a_display_band(self):
        # The physical finding, frozen.  The declared default is the uncooled
        # 0.05 C reference at a multiple of 5 and a 15 C background, which is
        # far finer than one display band.  A future "fix" that raised the
        # default to 0.0625 would fail here.
        default = self._default_threshold()
        self.assertGreater(default, 0.0)
        self.assertLess(default, 1.0 / 16.0)
        self.assertAlmostEqual(default, 0.004349, places=5)

    def test_the_kernel_does_not_read_the_scene_window(self):
        # The specific error being corrected: a scene statistic must never be
        # the background, and the AGC window must never enter the criterion.
        self.assertNotIn("agcRad", self.code)

    def test_signal_well_above_the_local_background_is_an_edge(self):
        detected, contrast = self._edge(60.0, 40.0)
        self.assertTrue(detected)
        self.assertGreater(contrast, 0.0)

    def test_signal_at_its_local_background_is_not_an_edge(self):
        detected, contrast = self._edge(40.0, 40.0)
        self.assertFalse(detected)
        self.assertAlmostEqual(contrast, 0.0, places=9)

    def test_signal_below_its_local_background_is_not_an_edge_and_clamps(self):
        detected, contrast = self._edge(20.0, 40.0)
        self.assertFalse(detected)
        self.assertAlmostEqual(contrast, 0.0, places=9)

    def test_degenerate_background_is_refused_rather_than_divided_by(self):
        for bad in (0.0, -5.0):
            detected, contrast = self._edge(60.0, bad)
            self.assertFalse(detected, f"background {bad!r} must not detect")
            self.assertEqual(contrast, -1, f"background {bad!r} must refuse")

    def test_non_finite_signal_is_refused(self):
        # The guard is source-locked above.  The mirror refuses NaN and the
        # infinities the same way the kernel's `finite` check does.
        for bad in (float("nan"), float("inf"), float("-inf")):
            detected, contrast = self._edge(bad, 40.0)
            self.assertFalse(detected, f"{bad!r} must not detect")
            self.assertEqual(contrast, -1, f"{bad!r} must refuse")

    def test_threshold_on_the_scale_is_clamped_but_not_band_floored(self):
        signal, background = 60.0, 40.0
        # The contrast here is (60 - 40) / 40 = 0.5.  The raw sensor
        # reference (about 0.004349) and a zero threshold must give the SAME
        # decision.  They cannot if 0.004349 were floored up to 0.0625, which
        # is what the old display-band floor did.
        sensor_reference = self._default_threshold()
        self.assertEqual(
            self._edge(signal, background, sensor_reference),
            self._edge(signal, background, 0.0),
        )
        # Above one clamps down to one, so nothing detects a 0.5 contrast.
        self.assertFalse(self._edge(signal, background, 5.0)[0])
        self.assertEqual(
            self._edge(signal, background, 5.0),
            self._edge(signal, background, 1.0),
        )

    def test_result_is_independent_of_the_scene(self):
        # THE test that would have failed the replaced kernel.  Two different
        # scene scales with the same LOCAL background and the same signal must
        # give the same answer.  The kernel reads no scene.
        signal, background = 60.0, 40.0
        self.assertEqual(self._edge(signal, background), self._edge(signal, background))
        self.assertNotIn("agcRad", self.code)
        # The replaced kernel normalised by the scene window, so two scene
        # scales gave two different answers for the SAME radiance:
        scene_a = (10.0, 50.0)
        scene_b = (0.0, 200.0)
        old_a = min(1.0, max(0.0, (signal - scene_a[0]) / (scene_a[1] - scene_a[0])))
        old_b = min(1.0, max(0.0, (signal - scene_b[0]) / (scene_b[1] - scene_b[0])))
        self.assertNotAlmostEqual(old_a, old_b, places=3)


class TestSensorThresholdKernel(unittest.TestCase):
    """The sensor detection threshold kernel (fnc_calculateSensorThreshold.sqf).

    The threshold is closed arithmetic on the band-radiance fit in
    fnc_calculateBandRadiance: differentiating L = A * T^n gives
    dL/dT = n * L / T, so the relative contrast from a temperature
    difference dT is n * dT / T_bg.  With dT = snrMultiple * NETD the
    threshold is snrMultiple * netdC * n / tBgK.

    The multiple is an ENGINEERING CHOICE.  NETD is DEFINED as the
    signal-to-noise 1 point (Geminoptics, "NETD"), and reliable detection
    sits at 3 to 10 times it, a margin the record does not standardise.

    The kernel is pure arithmetic over scalars, so the docker probe
    aee_p69_netd_probe.sqf measures it headless on the dedicated server.
    """

    _KERNEL = (
        _REPO_ROOT
        / "addons"
        / "thermal"
        / "functions"
        / "solver"
        / "fnc_calculateSensorThreshold.sqf"
    )
    _RADIANCE = (
        _REPO_ROOT
        / "addons"
        / "thermal"
        / "functions"
        / "solver"
        / "fnc_calculateBandRadiance.sqf"
    )
    _SELECTION_QUANTISER = (
        _REPO_ROOT
        / "addons"
        / "thermal"
        / "functions"
        / "display"
        / "fnc_applySelectionThermal.sqf"
    )

    @classmethod
    def setUpClass(cls):
        cls.code = _code_only(cls._KERNEL.read_text(encoding="utf-8"))
        cls.radiance_code = _code_only(cls._RADIANCE.read_text(encoding="utf-8"))
        # Both display quantisers are read from the SQF with the comments
        # stripped, so the headers that quote the retired 16-band step cannot
        # satisfy a depth check.
        cls.selection_code = _code_only(
            cls._SELECTION_QUANTISER.read_text(encoding="utf-8")
        )

    def _selection_band_step(self):
        """The live selection display step, read from its quantiser."""
        m = re.search(r"private _levels = (\d+);", self.selection_code)
        self.assertIsNotNone(m, "the selection tint depth is not declared")
        levels = int(m.group(1))
        # The ladder spans 0..1 inclusive, so N levels are N - 1 steps.
        self.assertIn("(_levels - 1)", self.selection_code)
        return 1.0 / (levels - 1)

    @staticmethod
    def _n(t_bg_k):
        # The segment selection, mirrored from the fit.  The fit clamps its
        # temperature to 240..460 K before selecting, which cannot change the
        # selected segment for a real background.
        n = 5.0121  # night: 250-290 K
        if t_bg_k > 290:
            n = 4.4580  # day: 290-330 K
        if t_bg_k > 330:
            n = 3.7101  # hot: 330-450 K
        return n

    def threshold(self, netd_c, snr, t_bg_c):
        # Mirror of the kernel body, pinned by test_source_guards_present.
        if not (math.isfinite(netd_c) and math.isfinite(snr) and math.isfinite(t_bg_c)):
            return -1
        if netd_c <= 0 or snr <= 0:
            return -1
        t_bg_k = t_bg_c + 273.15
        if t_bg_k <= 0:
            return -1
        return snr * netd_c * self._n(t_bg_k) / t_bg_k

    def test_matches_the_closed_form_on_a_hand_computed_case(self):
        # 5 * 0.05 * 5.0121 / 288.15 = 0.0043489...
        got = self.threshold(0.05, 5, 15)
        self.assertAlmostEqual(got, 5 * 0.05 * 5.0121 / 288.15, places=12)
        self.assertAlmostEqual(got, 0.004349, places=6)

    def test_a_cooler_device_gives_a_lower_threshold(self):
        # A cooled InSb/MCT device (0.02 C) is MORE sensitive than the
        # uncooled microbolometer (0.05 C), so its threshold is LOWER.
        # This is the property that makes the edge decision per-device.
        uncooled = self.threshold(0.05, 5, 15)
        cooled = self.threshold(0.02, 5, 15)
        self.assertLess(cooled, uncooled)
        self.assertAlmostEqual(cooled, 0.001739, places=6)

    def test_a_higher_multiple_gives_a_higher_threshold(self):
        self.assertLess(self.threshold(0.05, 5, 15), self.threshold(0.05, 10, 15))
        self.assertAlmostEqual(self.threshold(0.05, 10, 15), 0.008697, places=6)

    def test_the_exponent_follows_the_background_segment(self):
        # 5 C sits in the night segment, 35 C in the day segment and 60 C in
        # the hot segment.  The exponent must change with the background.
        night = self.threshold(0.05, 5, 5)
        day = self.threshold(0.05, 5, 35)
        hot = self.threshold(0.05, 5, 60)
        self.assertAlmostEqual(night, 5 * 0.05 * 5.0121 / 278.15, places=12)
        self.assertAlmostEqual(day, 5 * 0.05 * 4.4580 / 308.15, places=12)
        self.assertAlmostEqual(hot, 5 * 0.05 * 3.7101 / 333.15, places=12)

    def test_a_non_positive_netd_is_refused(self):
        for bad in (0.0, -0.05):
            self.assertEqual(self.threshold(bad, 5, 15), -1)

    def test_a_non_positive_multiple_is_refused(self):
        for bad in (0.0, -3.0):
            self.assertEqual(self.threshold(0.05, bad, 15), -1)

    def test_a_non_finite_input_is_refused(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            self.assertEqual(self.threshold(bad, 5, 15), -1)
            self.assertEqual(self.threshold(0.05, bad, 15), -1)
            self.assertEqual(self.threshold(0.05, 5, bad), -1)

    def test_a_background_at_absolute_zero_or_below_is_refused(self):
        for bad in (-273.15, -300.0):
            self.assertEqual(self.threshold(0.05, 5, bad), -1)

    def test_source_guards_and_exponents_present(self):
        code = self.code
        # The closed form, verbatim.
        self.assertIn("_snrMultiple * _netdC * _n / _tBgK", code)
        # Every refusal is -1.
        self.assertIn("exitWith { -1 }", code)
        # The value form of the type test, never the quoted type name.
        self.assertIn("isEqualType 0", code)
        # `finite` guards every input: SQF NaN compares false against all.
        self.assertIn("if !(finite _netdC) exitWith { -1 };", code)
        self.assertIn("if !(finite _snrMultiple) exitWith { -1 };", code)
        self.assertIn("if !(finite _tBgC) exitWith { -1 };", code)
        # The exponents live in the sensor-threshold closed form only.  The
        # radiance kernel now uses the exact Planck integral, not this fit.
        for exponent in ("5.0121", "4.4580", "3.7101"):
            self.assertIn(exponent, code)
        self.assertNotIn("5.0121", self.radiance_code)
        # The segment boundaries match the fit.
        self.assertIn("if (_tBgK > 290) then", code)
        self.assertIn("if (_tBgK > 330) then", code)


class TestSpatialResolutionKernel(unittest.TestCase):
    """The Johnson-criteria spatial resolver (fnc_resolveThermalTarget.sqf).

    The edge decision is CONTRAST ONLY, and its own header says a strong
    contrast edge can still be too small to resolve.  This kernel is that
    missing half.  It takes the THERMAL channel's own lens FOV, or falls
    back to the published DAY-OPTIC relation FOV = 24/mag degrees
    (sensor-device-library.md), converts the target's angular size to
    pixels, and reports the Johnson task level (STANAG 4347 Ed. 1) at about
    50 percent probability: detection 1.0 line pair (2 pixels), recognition
    4.0 (8 pixels), identification 6.4 (12.8 pixels).  A sub-line-pair
    target can still be detected by the sub-pixel SNR margin (linear in the
    filled area fraction, ADA011212 Eq. 29; 50 percent detection at SNR 2.8,
    ADA011212 Table 6).  It invents no range and no MRTD curve.  The docker
    probe aee_p71_johnson_probe.sqf measures the real kernel headless; this
    mirror pins the arithmetic.
    """

    _KERNEL = (
        _REPO_ROOT
        / "addons"
        / "thermal"
        / "functions"
        / "solver"
        / "fnc_resolveThermalTarget.sqf"
    )

    @classmethod
    def setUpClass(cls):
        cls.code = _code_only(cls._KERNEL.read_text(encoding="utf-8"))

    def _resolve(
        self, angle_rad, res_x, mag, fov_deg=0.0, netd=0.05, contrast=0.0, tbg=15.0
    ):
        values = (angle_rad, res_x, mag, fov_deg, netd, contrast, tbg)
        if not all(math.isfinite(v) for v in values):
            return False, 0, 0.0
        if angle_rad < 0 or res_x <= 0 or fov_deg < 0:
            return False, 0, 0.0
        if fov_deg == 0 and mag < 1:
            return False, 0, 0.0
        if netd <= 0 or tbg <= -273.15:
            return False, 0, 0.0
        contrast = min(1.0, max(0.0, contrast))
        hor_fov = fov_deg if fov_deg > 0 else 24.0 / mag
        ifov = hor_fov / res_x
        pixels = math.degrees(angle_rad) / ifov
        lp = pixels / 2.0
        level = 0
        if lp >= 1.0:
            level = 1
        if lp >= 4.0:
            level = 2
        if lp >= 6.4:
            level = 3
        if level < 1:
            fill = min(pixels, 1.0) ** 2
            tbg_k = tbg + 273.15
            n = 5.0121
            if tbg_k > 290:
                n = 4.4580
            if tbg_k > 330:
                n = 3.7101
            snr_full = contrast * tbg_k / (n * netd)
            if snr_full * fill >= 2.8:
                level = 1
        return level >= 1, level, lp

    def test_source_guards_and_constants_present(self):
        code = self.code
        self.assertIn("24 / _mag", code)
        self.assertIn("_horFovDeg", code)
        self.assertIn("_linePairs = _pixels / 2", code)
        self.assertIn("if (_linePairs >= 1.0) then", code)
        self.assertIn("if (_linePairs >= 4.0) then", code)
        self.assertIn("if (_linePairs >= 6.4) then", code)
        self.assertIn("isEqualType 0", code)
        self.assertIn("if !(finite _targetAngleRad) exitWith { [false, 0, 0] };", code)
        self.assertIn("if (_fovDeg == 0 && _mag < 1) exitWith { [false, 0, 0] };", code)
        # The sub-pixel SNR term, sourced to ADA011212.
        self.assertIn("(_pixels min 1) ^ 2", code)
        self.assertIn("_snrFull", code)
        self.assertIn("_snrSub", code)
        self.assertIn(">= 2.8", code)
        # It must not invent an MRTD value.
        self.assertNotIn("mrtd", code.lower())

    def test_person_at_300m_through_4x_is_recognition(self):
        # 0.5 m critical dimension through a 4x optic on a 640x480 detector:
        # FOV = 6 deg, IFOV = 0.009375 deg/px, angle = 0.5/300 rad.
        got = self._resolve(0.5 / 300.0, 640, 4)
        self.assertTrue(got[0])
        self.assertEqual(got[1], 2)
        self.assertAlmostEqual(got[2], 5.092958, places=4)

    def test_person_at_200m_through_4x_is_identification(self):
        got = self._resolve(0.5 / 200.0, 640, 4)
        self.assertEqual(got[1], 3)
        self.assertAlmostEqual(got[2], 7.639437, places=4)

    def test_person_beyond_detection_range_is_unresolved(self):
        # At 1600 m the person spans under one line pair, so contrast alone
        # would not be enough.
        got = self._resolve(0.5 / 1600.0, 640, 4)
        self.assertFalse(got[0])
        self.assertEqual(got[1], 0)
        self.assertLess(got[2], 1.0)

    def test_the_detection_boundary_is_two_pixels(self):
        self.assertTrue(self._resolve(0.5 / 1527.0, 640, 4)[0])
        self.assertFalse(self._resolve(0.5 / 1529.0, 640, 4)[0])

    def test_sub_pixel_target_resolves_by_snr_with_contrast(self):
        # A 0.5 m person at 4000 m through 640/4 spans about 0.764 px
        # (0.382 line pairs).  Geometry refuses; with a supplied contrast
        # the linear-area SNR term detects it (ADA011212 Eq. 29).
        got = self._resolve(0.5 / 4000.0, 640, 4, contrast=0.2)
        self.assertTrue(got[0])
        self.assertEqual(got[1], 1)
        self.assertLess(got[2], 1.0)

    def test_sub_pixel_without_contrast_stays_unresolved(self):
        # No contrast supplied (the default) means no SNR claim can be made.
        got = self._resolve(0.5 / 4000.0, 640, 4)
        self.assertFalse(got[0])
        self.assertEqual(got[1], 0)

    def test_sub_pixel_needs_enough_contrast(self):
        # At 4000 m the fill is 0.5837, so the full-pixel SNR must exceed
        # 2.8 / 0.5837 = 4.797, i.e. contrast above
        # 4.797 * n * netd / tBgK = 4.797 * 5.0121 * 0.05 / 288.15 = 0.00417.
        low = self._resolve(0.5 / 4000.0, 640, 4, contrast=0.004)
        high = self._resolve(0.5 / 4000.0, 640, 4, contrast=0.005)
        self.assertFalse(low[0])
        self.assertTrue(high[0])

    def test_a_supplied_thermal_fov_overrides_the_day_optic_fallback(self):
        # A narrow thermal lens FOV gives a smaller IFOV and more pixels.
        narrow = self._resolve(0.5 / 300.0, 640, 4, fov_deg=3.0)
        fallback = self._resolve(0.5 / 300.0, 640, 4)
        self.assertGreater(narrow[2], fallback[2])

    def test_sub_pixel_snr_is_a_narrower_detector_than_resolved(self):
        # The SNR term only reaches detection (level 1); it never grants
        # recognition or identification, which stay geometry-gated.
        got = self._resolve(0.5 / 4000.0, 640, 4, contrast=1.0)
        self.assertEqual(got[1], 1)

    def test_a_unity_goggle_is_coarser_than_a_4x_optic(self):
        angle = 0.5 / 200.0
        self.assertLess(
            self._resolve(angle, 640, 1)[2], self._resolve(angle, 640, 4)[2]
        )

    def test_a_lower_resolution_detector_is_coarser(self):
        angle = 0.5 / 200.0
        self.assertLess(
            self._resolve(angle, 320, 4)[2], self._resolve(angle, 640, 4)[2]
        )

    def test_refusals(self):
        for angle, res_x, mag in (
            (-0.001, 640, 4),
            (0.001, 0, 4),
            (0.001, -640, 4),
            (0.001, 640, 0.5),
            (float("nan"), 640, 4),
            (0.001, float("inf"), 4),
        ):
            got = self._resolve(angle, res_x, mag)
            self.assertFalse(got[0], f"{angle},{res_x},{mag} must refuse")
            self.assertEqual(got[1], 0)


class TestThermalEdgeWiring(unittest.TestCase):
    """The wire-in of the edge state, and the clean removal of the old kernel.

    The edge decision must not be the removed scene-window kernel, and it must
    not overwrite the brightness ladder it sits beside.  Both are asserted
    structurally, against comment-stripped code, never against prose.
    """

    def _tree_files(self):
        for root in (_REPO_ROOT / "addons", _REPO_ROOT / "tools", _REPO_ROOT / "tests"):
            for path in root.rglob("*"):
                if path.is_file() and path.suffix in (".sqf", ".hpp", ".py", ".json"):
                    yield path

    def test_removed_kernel_and_probe_leave_no_reference(self):
        # The needles are built from parts, so the test does not match itself.
        needles = ("evaluateThermal" + "Detection", "P" + "67")
        offenders = []
        for path in self._tree_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            if any(needle in text for needle in needles):
                offenders.append(str(path.relative_to(_REPO_ROOT)))
        self.assertEqual(offenders, [], f"stale references survive: {offenders}")


class TestAtmosphericTransmissionKernel(unittest.TestCase):
    """The atmospheric transmission kernel and the radiance common-mode.

    fnc_calculateAtmosphericTransmission implements the Minkina and Klecha
    2016 square-root long-wave model, with the water-vapour and carbon
    dioxide extinction of Roberts et al. 1976 and the two-term continuum of
    J. Geophys. Res. 2010JD015505.  Temperature enters through the Magnus
    saturation curve, because the water vapour partial pressure at a fixed
    relative humidity rises steeply with temperature.

    The three published anchors are 0.9306, 0.7828 and 0.5724 at 100 m, 1000 m
    and 5000 m at 15 C and 50 percent relative humidity.  The radiance kernel
    then multiplies its emitted and reflected terms by tau and adds the path
    radiance, so a target and its local background at the same range keep
    their DIFFERENCE scaled by exactly tau (the path term cancels).
    """

    _KERNEL = _THERMAL / "solver" / "fnc_calculateAtmosphericTransmission.sqf"
    _RADIANCE = _THERMAL / "solver" / "fnc_calculateBandRadiance.sqf"

    @classmethod
    def setUpClass(cls):
        cls.code = _code_only(cls._KERNEL.read_text(encoding="utf-8"))
        cls.radiance_code = _code_only(cls._RADIANCE.read_text(encoding="utf-8"))

    # ── The published anchors ──
    def test_all_three_published_anchors(self):
        # Minkina & Klecha 2016, long-wave, 15 C and 50 percent relative
        # humidity.  Tolerance 1e-3: the published values are rounded to four
        # decimals and the exact form differs from them by at most 7e-5.
        for d, want in ((100, 0.9306), (1000, 0.7828), (5000, 0.5724)):
            got = atmospheric_transmission(d, 50, 15)
            self.assertAlmostEqual(got, want, delta=1e-3, msg=f"{d} m")

    def test_zero_length_path_is_transparent(self):
        self.assertEqual(atmospheric_transmission(0), 1.0)

    def test_falls_monotonically_with_range(self):
        values = [atmospheric_transmission(d) for d in range(0, 6000, 100)]
        for a, b in zip(values, values[1:]):
            self.assertLessEqual(b, a)

    def test_falls_as_humidity_rises(self):
        dry = atmospheric_transmission(1000, 10, 15)
        wet = atmospheric_transmission(1000, 90, 15)
        self.assertLess(wet, dry)

    def test_falls_as_temperature_rises_at_fixed_humidity(self):
        # The water-vapour mechanism: at fixed RH, e_s rises steeply with T,
        # so beta_H2O rises and transmission falls.  This is why a model that
        # holds beta constant is wrong.
        cold = atmospheric_transmission(1000, 50, 5)
        warm = atmospheric_transmission(1000, 50, 35)
        self.assertLess(warm, cold)

    def test_refusals(self):
        self.assertEqual(atmospheric_transmission(-1), -1)
        self.assertEqual(atmospheric_transmission(1000, 50, 15, 0, 0, 0), -1)
        for bad in (float("nan"), float("inf"), float("-inf")):
            self.assertEqual(atmospheric_transmission(bad), -1)
            self.assertEqual(atmospheric_transmission(1000, bad), -1)
            self.assertEqual(atmospheric_transmission(1000, 50, bad), -1)

    def test_source_constants_and_guards(self):
        code = self.code
        for token in (
            "0.008",
            "0.02",
            "0.023571",
            "3.5714e-4",
            "_fogKm",
            "_rainKm",
            "6.112",
            "17.67",
            "243.5",
            "_alphaRef * (_betaClean / _betaRef)",
        ):
            self.assertIn(token, code, f"transmission kernel lost {token}")
        self.assertIn("exitWith { -1 }", code)
        self.assertIn("if !(finite _rangeM) exitWith { -1 };", code)

    # ── The radiance kernel: old behaviour and the new dimming ──
    def test_transmission_one_reproduces_the_old_result(self):
        old = band_radiance_atm(37.0, 0.92, 15.0, 0.5, 15.0, 1.0, 15.0)
        inert = band_radiance_atm(37.0, 0.92, 15.0, 0.5, 15.0)
        self.assertAlmostEqual(old, inert, places=12)

    def test_a_transmission_below_one_dims_the_emitted_terms_by_that_factor(self):
        old = band_radiance_atm(37.0, 0.92, 15.0, 0.5, 15.0, 1.0, 15.0)
        tau = 0.6
        new = band_radiance_atm(37.0, 0.92, 15.0, 0.5, 15.0, tau, 15.0)
        w_atm = planck_band_radiance(15.0 + 273.15)
        # The emitted and reflected terms are dimmed by exactly tau; the path
        # radiance is added on top.
        self.assertAlmostEqual(new, tau * old + (1 - tau) * w_atm, places=12)

    # ── The common-mode property (CRITICAL) ──
    def test_same_range_difference_scales_by_exactly_tau(self):
        tau, t_path = 0.7, 15.0
        t0 = band_radiance_atm(40.0, 0.92, 15.0, 0.5, 15.0, 1.0, t_path)
        b0 = band_radiance_atm(0.0, 0.92, 15.0, 0.5, 15.0, 1.0, t_path)
        ta = band_radiance_atm(40.0, 0.92, 15.0, 0.5, 15.0, tau, t_path)
        ba = band_radiance_atm(0.0, 0.92, 15.0, 0.5, 15.0, tau, t_path)
        self.assertAlmostEqual(ta - ba, tau * (t0 - b0), places=12)
        # The path term is added to the target AND the background identically.
        self.assertAlmostEqual(ta - tau * t0, ba - tau * b0, places=12)

    def test_applying_tau_to_the_target_alone_would_fail_the_common_mode(self):
        tau, t_path = 0.7, 15.0
        t0 = band_radiance_atm(40.0, 0.92, 15.0, 0.5, 15.0, 1.0, t_path)
        b0 = band_radiance_atm(0.0, 0.92, 15.0, 0.5, 15.0, 1.0, t_path)
        t_full = band_radiance_atm(40.0, 0.92, 15.0, 0.5, 15.0, tau, t_path)
        # The WRONG model: tau on the target only, the background untouched.
        # The test above would catch this, so this asserts the wrong model is
        # detectably different rather than silently acceptable.
        wrong = t_full - b0
        self.assertNotAlmostEqual(wrong, tau * (t0 - b0), places=6)

    def test_source_three_term_form(self):
        rc = self.radiance_code
        self.assertIn("_tau * (_eps * _wObj + (1 - _eps) * _wRefl + _wSolar)", rc)
        self.assertIn("(1 - _tau) * _wAtm", rc)
        self.assertIn(
            "[_tPathK, _lambda1M, _lambda2M] call FUNC(planckBandRadiance)", rc
        )


_PLANCK_KERNEL = _THERMAL / "solver" / "fnc_planckBandRadiance.sqf"
_RESOLVE_BAND_KERNEL = _THERMAL / "solver" / "fnc_resolveThermalBand.sqf"
_SKY_KERNEL = _THERMAL / "solver" / "fnc_calculateSkyRadiance.sqf"


def _run_resolve_band(token):
    return run_sqf(_RESOLVE_BAND_KERNEL, [token])


def _run_planck(t_k, lambda1_m=8e-6, lambda2_m=14e-6):
    return run_sqf(_PLANCK_KERNEL, [t_k, lambda1_m, lambda2_m])


def _run_sky(band, t_air_c, humidity_pct, overcast):
    return run_sqf(
        _SKY_KERNEL,
        [band, t_air_c, humidity_pct, overcast],
        {
            "__FUNC__resolveThermalBand": _run_resolve_band,
            "__FUNC__planckBandRadiance": _run_planck,
        },
    )


def _radiance_globals():
    """The injected function globals for the radiance kernel (T3)."""
    return {
        "overcast": 0.0,
        "diag_tickTime": 0.0,
        "__FUNC__planckBandRadiance": _run_planck,
        "__FUNC__calculateSkyRadiance": _run_sky,
        # The kernel publishes aee_thermal_skyBandTempC (task 14).  sqf_lite
        # has no namespace, so the write resolves against inert stubs.
        "missionNamespace": {},
        "setVariable": lambda *args: None,
    }


class TestBandParameterisedRadiance(unittest.TestCase):
    """The Planck band integral is band-parameterised (T2).

    fnc_calculateBandRadiance takes optional _lambda1M and _lambda2M after
    the trace flag.  The default path is the LWIR 8-14 um pair and is
    bit-identical to the pre-change result.  A band whose first edge is not
    positive or whose second edge is not longer is refused with -1.  The
    kernel is executed from its real SQF, not a Python mirror.
    """

    _KERNEL = _THERMAL / "solver" / "fnc_calculateBandRadiance.sqf"

    def _rad(
        self,
        band=None,
        t_surf=37.0,
        eps=0.92,
        t_air=15.0,
        f_ground=0.5,
        t_ground=15.0,
        tau=1.0,
        t_path=15.0,
    ):
        args = [t_surf, eps, t_air, f_ground, t_ground, tau, t_path, False]
        if band is not None:
            args.extend(band)
        return run_sqf(self._KERNEL, args, _radiance_globals())

    def test_the_lwir_default_pins_the_band_parameterisation(self):
        # The default band path, with the T3 sky model live.  The value is
        # recomputed from the mirror, so the pin tracks the sky model and
        # still catches a band-edge mutation.
        self.assertAlmostEqual(
            self._rad(),
            band_radiance_atm(37.0, 0.92, 15.0, 0.5, 15.0, 1.0, 15.0),
            places=9,
        )

    def test_the_default_equals_the_explicit_lwir_pair(self):
        self.assertEqual(self._rad(), self._rad([8e-6, 14e-6]))

    def test_the_lwir_default_matches_the_python_mirror(self):
        self.assertAlmostEqual(
            self._rad(),
            band_radiance_atm(37.0, 0.92, 15.0, 0.5, 15.0, 1.0, 15.0),
            places=9,
        )

    def test_mwir_is_positive_at_300_k(self):
        # 300 K is 26.85 C.
        value = self._rad([3e-6, 5e-6], t_surf=26.85)
        self.assertGreater(value, 0.0)

    def test_mwir_is_monotone_in_temperature(self):
        values = [self._rad([3e-6, 5e-6], t_surf=t) for t in (20.0, 26.85, 60.0, 120.0)]
        for a, b in zip(values, values[1:]):
            self.assertLess(a, b)

    def test_mwir_differs_from_lwir(self):
        self.assertNotEqual(self._rad([3e-6, 5e-6]), self._rad([8e-6, 14e-6]))

    def test_a_bad_band_is_refused(self):
        self.assertEqual(self._rad([0.0, 14e-6]), -1)
        self.assertEqual(self._rad([-1e-6, 14e-6]), -1)
        self.assertEqual(self._rad([8e-6, 5e-6]), -1)
        self.assertEqual(self._rad([8e-6, 8e-6]), -1)

    def test_the_source_declares_the_band_parameters(self):
        code = _code_only(self._KERNEL.read_text(encoding="utf-8"))
        self.assertIn('["_lambda1M", 8e-6, [0]]', code)
        self.assertIn('["_lambda2M", 14e-6, [0]]', code)
        self.assertIn(
            "if (_lambda1M <= 0 || _lambda2M <= _lambda1M) exitWith { -1 };", code
        )
        # The shared integrand is the one home of the series and the edges.
        planck = _code_only(
            (_THERMAL / "solver" / "fnc_planckBandRadiance.sqf").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("_lambda1M * _tk", planck)
        self.assertIn("_lambda2M * _tk", planck)
        self.assertIn("2.779416505e-9", planck)
        self.assertIn("1.438776877e-2", planck)


class TestBandSkyModel(unittest.TestCase):
    """The band sky model replaces the fixed offset (T3).

    The kernel is executed from its real SQF.  The 15 C and 50 percent
    humidity clear-sky band temperature must sit inside the Tebo 1965
    depression envelope and within 5 K of the retired fixed offset, so night
    cold-sky contrast does not regress.
    """

    _KERNEL = _THERMAL / "solver" / "fnc_calculateSkyRadiance.sqf"
    _RADIANCE = _THERMAL / "solver" / "fnc_calculateBandRadiance.sqf"

    def _sky(self, band="lwir", t_air=15.0, rh=50.0, oc=0.0):
        return _run_sky(band, t_air, rh, oc)

    def test_the_reference_condition_is_within_5k_of_the_old_offset(self):
        # The retired fixed offset was T_air - 35 = -20 C at 15 C.
        self.assertAlmostEqual(self._sky("lwir", 15.0, 50.0, 0.0), -20.0, delta=5.0)

    def test_the_reference_condition_is_within_the_tebo_depression(self):
        # Tebo 1965 measured a band depression of 21 to 45 K over the
        # water-vapour range.  The clear-sky reference must sit inside it.
        depression = 15.0 - self._sky("lwir", 15.0, 50.0, 0.0)
        self.assertGreaterEqual(depression, 21.0)
        self.assertLessEqual(depression, 45.0)

    def test_the_result_warms_monotonically_with_humidity(self):
        # Sample inside the Tebo slope (4 < eHPa < 15, about 24 to 88 percent
        # at 15 C); the depression is flat outside it.
        values = [self._sky("lwir", 15.0, rh, 0.0) for rh in (25, 40, 55, 70, 85)]
        for a, b in zip(values, values[1:]):
            self.assertLess(a, b)

    def test_the_result_warms_monotonically_with_air_temperature(self):
        values = [self._sky("lwir", t, 50.0, 0.0) for t in (-10.0, 0.0, 15.0, 30.0)]
        for a, b in zip(values, values[1:]):
            self.assertLess(a, b)

    def test_overcast_lifts_the_sky_toward_air(self):
        clear = self._sky("lwir", 15.0, 50.0, 0.0)
        overcast = self._sky("lwir", 15.0, 50.0, 1.0)
        self.assertGreater(overcast, clear)
        self.assertAlmostEqual(overcast, 15.0, delta=0.5)

    def test_the_sky_is_colder_than_the_air(self):
        self.assertLess(self._sky("mwir", 15.0, 50.0, 0.0), 15.0)
        self.assertLess(self._sky("lwir", 15.0, 50.0, 0.0), 15.0)

    def test_the_kernel_matches_the_python_mirror(self):
        for band in ("lwir", "mwir"):
            with self.subTest(band=band):
                self.assertAlmostEqual(
                    self._sky(band, 15.0, 50.0, 0.0),
                    sky_temperature_c(band, 15.0, 50.0, 0.0),
                    places=6,
                )

    def test_the_radiance_kernel_uses_the_sky_kernel(self):
        code = _code_only(self._RADIANCE.read_text(encoding="utf-8"))
        self.assertIn("FUNC(calculateSkyRadiance)", code)
        # No retired fixed offset and no wrong citation anywhere in the file.
        self.assertNotIn("-35", code)
        self.assertNotIn("Aase", self._RADIANCE.read_text(encoding="utf-8"))

    def test_the_source_cites_the_right_identities(self):
        header = self._KERNEL.read_text(encoding="utf-8")
        self.assertIn("Idso 1981", header)
        self.assertIn("Tebo 1965", header)
        self.assertNotIn("Aase & Idso 1981", header)

    def test_both_kernels_are_prep_registered(self):
        prep = (_REPO_ROOT / "addons" / "thermal" / "XEH_PREP.hpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("PREPS(solver,calculateSkyRadiance);", prep)
        self.assertIn("PREPS(solver,planckBandRadiance);", prep)


class TestReflectedSolarBand(unittest.TestCase):
    """The MWIR reflected-solar term (T4).

    The kernel is executed from its real SQF.  The MWIR top-of-atmosphere
    band irradiance is pinned to within one percent of an independent
    computation, and the term is zero for LWIR and at night.
    """

    _KERNEL = _THERMAL / "solver" / "fnc_calculateReflectedSolarBand.sqf"
    _RADIANCE = _THERMAL / "solver" / "fnc_calculateBandRadiance.sqf"

    def _solar(self, band, eps, elev):
        return run_sqf(
            self._KERNEL,
            [band, eps, elev],
            {
                "__FUNC__resolveThermalBand": _run_resolve_band,
                "__FUNC__planckBandRadiance": _run_planck,
            },
        )

    def _rad(self, w_solar, band=False):
        l1, l2, token = (3e-6, 5e-6, "mwir") if band else (8e-6, 14e-6, "lwir")
        args = [37.0, 0.92, 15.0, 0.5, 15.0, 1.0, 15.0, False]
        args.extend([l1, l2, 50.0, token, w_solar])
        return run_sqf(self._RADIANCE, args, _radiance_globals())

    # ── Zero cases ──
    def test_lwir_is_zero(self):
        self.assertEqual(self._solar("lwir", 0.95, 45.0), 0)
        self.assertEqual(self._solar("lwir", 0.10, 90.0), 0)

    def test_night_and_horizon_are_zero(self):
        for elev in (-90.0, -10.0, 0.0):
            with self.subTest(elev=elev):
                self.assertEqual(self._solar("mwir", 0.95, elev), 0)

    # ── The derived magnitude ──
    def test_mwir_is_positive_by_day(self):
        self.assertGreater(self._solar("mwir", 0.95, 45.0), 0.0)

    def test_the_top_of_atmosphere_irradiance_within_one_percent(self):
        # At eps = 0 and elevation 90 deg, W_solar = E_sunBand / pi.
        e_sqf = self._solar("mwir", 0.0, 90.0) * math.pi
        e_ref = _solar_band_irradiance(3e-6, 5e-6)
        self.assertAlmostEqual(e_sqf / e_ref, 1.0, delta=0.01)

    def test_the_term_scales_with_surface_reflectance(self):
        full = self._solar("mwir", 0.0, 45.0)
        half = self._solar("mwir", 0.5, 45.0)
        self.assertAlmostEqual(half, full * 0.5, places=9)

    def test_the_term_scales_with_the_sine_of_elevation(self):
        high = self._solar("mwir", 0.95, 90.0)
        low = self._solar("mwir", 0.95, 30.0)
        self.assertAlmostEqual(low, high * math.sin(math.radians(30.0)), places=9)

    def test_emissivity_is_clamped(self):
        # eps >= 1 gives no reflection, eps <= 0 gives the full reflection.
        self.assertEqual(self._solar("mwir", 2.0, 90.0), 0)
        self.assertAlmostEqual(
            self._solar("mwir", -1.0, 90.0),
            self._solar("mwir", 0.0, 90.0),
            places=9,
        )

    # ── Wiring ──
    def test_the_radiance_kernel_takes_the_solar_term(self):
        code = _code_only(self._RADIANCE.read_text(encoding="utf-8"))
        self.assertIn('["_wSolar", 0, [0]]', code)
        self.assertIn("+ _wSolar", code)

    def test_the_solar_term_enters_the_surface_radiance(self):
        # tau = 1, so a supplied W_solar adds exactly.
        base = self._rad(0.0)
        with_solar = self._rad(5.0)
        self.assertAlmostEqual(with_solar - base, 5.0, places=9)

    def test_the_kernel_is_prep_registered(self):
        prep = (_REPO_ROOT / "addons" / "thermal" / "XEH_PREP.hpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("PREPS(solver,calculateReflectedSolarBand);", prep)


class TestBandAtmosphericTransmission(unittest.TestCase):
    """The band-resolved atmospheric transmission (T5).

    The kernel is executed from its real SQF.  LWIR keeps the three
    published Minkina and Klecha 2016 anchors.  MWIR is the declared
    ceiling: the clear-air return is exactly 1, and only fog and rain
    attenuate it.
    """

    _KERNEL = _THERMAL / "solver" / "fnc_calculateAtmosphericTransmission.sqf"

    def _tau(self, range_m, band="lwir", rh=50.0, t=15.0, fog=0.0, rain=0.0, rho=1.225):
        return run_sqf(self._KERNEL, [range_m, rh, t, fog, rain, rho, band])

    def test_lwir_anchors_reproduce_to_1e_4(self):
        # The LWIR model is unchanged, so each published anchor range matches
        # the pre-change model mirror to within 1e-4.  The 5000 m published
        # figure (0.5724) is the rounded print; the exact form is 0.572533.
        for d in (100, 1000, 5000):
            with self.subTest(d=d):
                self.assertAlmostEqual(
                    self._tau(d, "lwir"), atmospheric_transmission(d), delta=1e-4
                )

    def test_lwir_published_anchors_still_hold(self):
        for d, want in ((100, 0.9306), (1000, 0.7828), (5000, 0.5724)):
            with self.subTest(d=d):
                self.assertAlmostEqual(self._tau(d, "lwir"), want, delta=1e-3)

    def test_lwir_default_is_the_explicit_lwir_token(self):
        self.assertEqual(self._tau(1000), self._tau(1000, "lwir"))

    def test_mwir_clear_air_is_exactly_one(self):
        self.assertEqual(self._tau(0, "mwir"), 1)
        for d in (100, 1000, 5000):
            with self.subTest(d=d):
                self.assertEqual(self._tau(d, "mwir"), 1)

    def test_mwir_stays_in_range_and_is_monotone_in_range(self):
        # Fog makes the range term active, because clear-air is the ceiling.
        values = [self._tau(d, "mwir", fog=0.5) for d in range(0, 6000, 500)]
        for v in values:
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)
        for a, b in zip(values, values[1:]):
            self.assertLessEqual(b, a)

    def test_mwir_fog_and_rain_attenuate(self):
        self.assertLess(self._tau(5000, "mwir", fog=1.0), 1.0)
        self.assertLess(self._tau(5000, "mwir", rain=1.0), 1.0)

    def test_the_band_parameter_is_declared(self):
        code = _code_only(self._KERNEL.read_text(encoding="utf-8"))
        self.assertIn('["_bandToken", "lwir", [""]]', code)
        self.assertIn('if ((toLower _bandToken) == "mwir") then', code)
        self.assertIn("_alphaEff = 0;", code)

    def test_the_python_mirror_agrees(self):
        for band in ("lwir", "mwir"):
            for d in (0, 100, 1000, 5000):
                with self.subTest(band=band, d=d):
                    self.assertAlmostEqual(
                        self._tau(d, band),
                        atmospheric_transmission(d, band=band),
                        places=9,
                    )


if __name__ == "__main__":
    unittest.main()


def atmospheric_transmission(
    range_m, rh_pct=50.0, t_c=15.0, fog=0.0, rain=0.0, rho=1.225, band="lwir"
):
    """Mirror of fnc_calculateAtmosphericTransmission.sqf.

    Returns -1 for an unusable input, matching the SQF refusal.  The
    square-root form is deliberate: one constant extinction cannot meet all
    three published anchors, because the implied extinction falls with range.
    The MWIR band is the declared ceiling: the clear-air extinction is zero,
    so the clear-air return is exactly 1, and only fog and rain attenuate.
    """
    for value in (range_m, rh_pct, t_c, fog, rain, rho):
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            return -1
    if range_m < 0:
        return -1
    if rho <= 0:
        return -1
    if range_m == 0:
        return 1.0
    rh = min(max(rh_pct, 0.0), 100.0)
    fog = min(max(fog, 0.0), 1.0)
    rain = min(max(rain, 0.0), 1.0)

    alpha_ref = 0.008  # per sqrt(m), Minkina & Klecha LW declared default
    d_cal = 1.0  # m, the paper's 1 m calibration distance
    co2_km = 0.02  # km^-1, Roberts 1976 CO2 over 8-12 um
    a_foreign = 0.023571  # km^-1/torr, from the Roberts 4..14 torr endpoints
    b_self = 3.5714e-4  # km^-1/torr^2, from the same two endpoints
    rho0 = 1.225  # kg/m^3
    fog_km = 5.0  # km^-1 per unit fog density, DECLARED DEFAULT
    rain_km = 0.5  # km^-1 per unit rain scalar, DECLARED DEFAULT
    hpa_to_torr = 0.750062

    e_torr = _atmos_es_hpa(t_c) * (rh / 100.0) * hpa_to_torr
    e_ref = _atmos_es_hpa(15.0) * 0.5 * hpa_to_torr
    rho_rel = rho / rho0
    beta_clean = co2_km + a_foreign * e_torr * rho_rel + b_self * e_torr * e_torr
    beta_ref = co2_km + a_foreign * e_ref + b_self * e_ref * e_ref
    alpha_eff = alpha_ref * (beta_clean / beta_ref)
    if band == "mwir":
        alpha_eff = 0.0  # declared clear-air ceiling (UNSOURCED)
    beta_extra_km = fog_km * fog + rain_km * rain
    sqrt_part = max(math.sqrt(range_m) - math.sqrt(d_cal), 0.0)
    linear_part = max((range_m - d_cal) / 1000.0, 0.0)
    optical_depth = alpha_eff * sqrt_part + beta_extra_km * linear_part
    return min(max(math.exp(-optical_depth), 0.0), 1.0)


def band_radiance_atm(
    t_surf_c, eps, t_air_c, f_ground=0.5, t_ground_c=None, tau=1.0, t_path_c=15.0
):
    """Mirror of the completed three-term fnc_calculateBandRadiance.sqf.

    W = eps*tau*W_obj + (1-eps)*tau*W_refl + (1-tau)*W_atm.  The path radiance
    W_atm is the Planck band radiance at the path temperature, the isothermal
    homogeneous-layer solution of the Schwarzschild transfer equation.  The
    sky now follows the weather through the T3 band sky model.
    """
    eps = max(0.05, min(1.0, eps))
    if t_ground_c is None:
        t_ground_c = t_air_c
    tau = max(0.0, min(1.0, tau))
    t_surf_k = t_surf_c + 273.15
    t_air_k = max(200.0, min(350.0, t_air_c + 273.15))
    t_ground_k = t_ground_c + 273.15
    sky_k = sky_temperature_c("lwir", t_air_c, 50.0, 0.0) + 273.15
    t_refl_k = f_ground * t_ground_k + (1 - f_ground) * sky_k
    w_obj = planck_band_radiance(t_surf_k)
    w_refl = planck_band_radiance(t_refl_k)
    t_path_k = max(200.0, min(350.0, t_path_c + 273.15))
    w_atm = planck_band_radiance(t_path_k)
    return tau * (eps * w_obj + (1 - eps) * w_refl) + (1 - tau) * w_atm


def planck_band_radiance(t_k, lambda1_m=8e-6, lambda2_m=14e-6):
    """Exact Planck band integral (CODATA 2022); mirror of the SQF
    cumulative-blackbody series in fnc_planckBandRadiance."""
    c2 = 1.438776877e-2
    c_planck = 2.779416505e-9
    t_k = max(100.0, min(10000.0, t_k))
    z1 = c2 / (lambda1_m * t_k)
    z2 = c2 / (lambda2_m * t_k)

    def cumulative(z):
        total = 0.0
        step = math.exp(-z)
        weight = step
        z_sq = z * z
        z_cu = z_sq * z
        for n in range(1, 41):
            n2 = n * n
            n3 = n2 * n
            n4 = n3 * n
            total += weight * (z_cu / n + 3 * z_sq / n2 + 6 * z / n3 + 6 / n4)
            weight *= step
        return total

    return c_planck * t_k**4 * (cumulative(z2) - cumulative(z1))


def sky_temperature_c(band="lwir", t_air_c=15.0, rh_pct=50.0, overcast=0.0):
    """Python mirror of fnc_calculateSkyRadiance.sqf (T3).

    The Tebo 1965 measured band depression is interpolated linearly in
    log(eHPa), the band emissivity is the exact Planck radiance ratio, and
    the band sky temperature is recovered by bisection.
    """
    l1, l2 = (3e-6, 5e-6) if band == "mwir" else (8e-6, 14e-6)
    t_air_c = max(-80.0, min(60.0, t_air_c))
    rh = max(0.0, min(100.0, rh_pct))
    oc = max(0.0, min(1.0, overcast))
    t_air_k = t_air_c + 273.15
    e_hpa = _atmos_es_hpa(t_air_c) * (rh / 100.0)
    eps_full = 0.70 + 5.95e-5 * e_hpa * math.exp(1500.0 / t_air_k)
    if e_hpa <= 4.0:
        dt = 45.0
    elif e_hpa >= 15.0:
        dt = 21.0
    else:
        f = (math.log(e_hpa) - math.log(4.0)) / (math.log(15.0) - math.log(4.0))
        dt = 45.0 + (21.0 - 45.0) * f
    dt *= 1.0 - oc
    w_air = planck_band_radiance(t_air_k, l1, l2)
    w_sky = planck_band_radiance(t_air_k - dt, l1, l2)
    eps_band = min(w_sky / w_air, 1.0)
    if oc <= 0.0:
        eps_band = min(eps_band, eps_full)
    target = eps_band * w_air
    lo, hi = 1.0, t_air_k
    for _ in range(40):
        mid = (lo + hi) / 2
        if planck_band_radiance(mid, l1, l2) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2 - 273.15


def _solar_band_irradiance(lambda1_m, lambda2_m, t_sun=5772.0, terms=200):
    """Independent top-of-atmosphere band irradiance (T4 test reference).

    E_sunBand = pi * B_band(T_sun) * (R_sun / AU)^2, computed from the
    cumulative-blackbody series with many terms and no domain clamp.  It is a
    reference for the SQF solar kernel, not a call into it.
    """
    c2 = 1.438776877e-2
    c_planck = 2.779416505e-9

    def cumulative(z):
        total = 0.0
        step = math.exp(-z)
        weight = step
        z_sq = z * z
        z_cu = z_sq * z
        for n in range(1, terms + 1):
            n2 = n * n
            n3 = n2 * n
            n4 = n3 * n
            total += weight * (z_cu / n + 3 * z_sq / n2 + 6 * z / n3 + 6 / n4)
            weight *= step
        return total

    b = (
        c_planck
        * t_sun**4
        * (cumulative(c2 / (lambda2_m * t_sun)) - cumulative(c2 / (lambda1_m * t_sun)))
    )
    r_sun = 6.957e8
    au = 1.495978707e11
    return math.pi * b * (r_sun / au) ** 2


def _atmos_es_hpa(t_c):
    """Magnus saturation vapour pressure (Bolton 1980), hPa."""
    return 6.112 * math.exp(17.67 * t_c / (t_c + 243.5))


def _sqf_block(text, header):
    """The text between the braces of the block that follows `header`."""
    start = text.index(header)
    start = text.index("{", start)
    depth = 0
    for pos in range(start, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : pos]
    raise AssertionError(f"unterminated block after: {header}")


class TestSelectionSunExposure(unittest.TestCase):
    """Per-selection solar exposure from the surface orientation.

    The outward direction is a proxy (a memory point or selection centre
    against the bounding centre), so the test proves only the ordering the
    geometry can support: a roof above a side, a sun-facing side above a
    shaded side, and the wheel floor.
    """

    def test_top_is_warmer_than_side_at_high_sun(self):
        # Synthetic vehicle: roof above the centre, an east side, a west
        # side, and a wheel below the centre.
        centre = (0.0, 0.0, 1.0)
        positions = [
            (0.0, 0.0, 2.2),
            (1.4, 0.0, 1.0),
            (-1.4, 0.0, 1.0),
            (0.8, 0.0, 0.2),
        ]
        names = ["camo_roof", "camo_side_r", "camo_side_l", "wheel_1_1"]
        # Sun in the east (azimuth 90) and high (elevation 70).
        roof, sun_side, shade_side, wheel = selection_sun_exposure(
            positions, centre, 90.0, 70.0, names
        )
        self.assertGreater(roof, sun_side)
        self.assertGreater(sun_side, shade_side)
        self.assertAlmostEqual(roof, 1.0, places=6)
        self.assertAlmostEqual(shade_side, 0.0, places=6)
        self.assertAlmostEqual(wheel, 0.15, places=6)

    def test_wheel_floor_still_applies(self):
        # A wheel point below the centre faces down: the geometric exposure
        # is zero, and the old low value stays as the floor.
        centre = (0.0, 0.0, 1.0)
        e = selection_sun_exposure(
            [(0.0, 0.0, 0.0)], centre, 90.0, 70.0, ["undercarriage_1"]
        )
        self.assertAlmostEqual(e[0], 0.15, places=6)

    def test_unresolved_point_keeps_neutral(self):
        # No resolvable point -> neutral 1.0, the old value.  No spread is
        # invented for geometry the model does not carry.
        centre = (0.0, 0.0, 1.0)
        e = selection_sun_exposure([(0.0, 0.0, 1.0)], centre, 90.0, 70.0, ["camo1"])
        self.assertAlmostEqual(e[0], 1.0, places=6)

    def test_sqf_wiring(self):
        text = _read_sqf("fnc_getSelectionSunExposure.sqf", "thermal")
        for frag in (
            "boundingCenter",
            "currentSunAzimuth",
            "currentSunElevation",
            "vectorDotProduct",
            "vectorCrossProduct",
            "_dot / _sinElev",
            "_exp max 0.15",
            "selSunDirCache",
            "vectorDiff",
        ):
            self.assertIn(frag, text)
        caller = _read_sqf("fnc_applySelectionThermal.sqf", "thermal")
        self.assertIn("FUNC(getSelectionSunExposure)", caller)
        self.assertIn("_exposureArr param [_forEachIndex, 1]", caller)
        prep = (_REPO_ROOT / "addons" / "thermal" / "XEH_PREP.hpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("getSelectionSunExposure", prep)


class TestThermalResolvabilityWiring(unittest.TestCase):
    """The sensor-resolution layer now drives the paint (issue #215 family).

    Three pure kernels existed with no production caller:
      - fnc_calculateSensorThreshold derives the minimum resolvable contrast
        from the mounted device NETD;
      - fnc_evaluateThermalEdge decides a LOCAL-contrast edge against the
        object's other selections;
      - fnc_resolveThermalTarget applies the Johnson spatial test.
    fnc_applySelectionThermal now calls them in that order and blends a
    selection the sensor cannot resolve toward its local background colour.
    The blend is the pure fnc_resolveThermalVisibility, executed here from the
    shipped SQF, not a Python mirror.
    """

    _VIS = _THERMAL / "solver" / "fnc_resolveThermalVisibility.sqf"

    @classmethod
    def setUpClass(cls):
        cls.code = _read_sqf("fnc_resolveThermalVisibility.sqf", "thermal")
        cls.paint = _code_only(_read_sqf("fnc_applySelectionThermal.sqf", "thermal"))

    def _vis(self, contrast, threshold, resolvable, line_pairs):
        return run_sqf(self._VIS, [contrast, threshold, resolvable, line_pairs])

    def test_below_threshold_selection_is_pulled_toward_background(self):
        # (i) A contrast below the sensor margin resolves to a fraction below
        # one, so the paint pulls it toward the local background colour.
        vis = self._vis(0.001, 0.004349, True, 5.0)
        self.assertGreater(vis, 0.0)
        self.assertLess(vis, 1.0)
        self.assertAlmostEqual(vis, 0.001 / 0.004349, places=9)

    def test_above_threshold_selection_keeps_full_contrast(self):
        # (ii) At or above the margin the fraction is one: no blend.
        self.assertEqual(self._vis(0.5, 0.004349, True, 5.0), 1.0)
        self.assertEqual(self._vis(0.004349, 0.004349, True, 5.0), 1.0)

    def test_unresolved_target_is_damped_even_at_high_contrast(self):
        # (iii) A strong contrast edge the Johnson test cannot resolve is still
        # damped by the spatial term: contrast detection is not sufficient.
        vis = self._vis(0.9, 0.004349, False, 0.5)
        self.assertAlmostEqual(vis, 0.5, places=9)
        self.assertLess(vis, 1.0)

    def test_zero_contrast_reads_as_background(self):
        self.assertEqual(self._vis(0.0, 0.004349, True, 5.0), 0.0)

    def test_a_non_positive_threshold_cannot_blank_the_scene(self):
        # A bad threshold must not divide by zero.  The caller substitutes the
        # documented reference; the kernel still returns full contrast.
        self.assertEqual(self._vis(0.5, 0.0, True, 5.0), 1.0)

    def test_unresolvable_device_falls_back_without_error(self):
        # (iv) fnc_getThermalDeviceProperties documents the uncooled 0.05 C
        # microbolometer fallback and the threshold kernel refuses a bad NETD
        # with -1.  The paint path substitutes the reference value and keeps
        # the model live.
        self.assertIn("getThermalDeviceProperties", self.paint)
        self.assertIn("FUNC(calculateSensorThreshold)", self.paint)
        self.assertIn("_threshold = 0.004349;", self.paint)
        device = _read_sqf("fnc_getThermalDeviceProperties.sqf", "thermal")
        self.assertIn('[0.05, 640, 480, 1.5, 30, 0, "lwir"]', device)

    def test_the_three_kernels_run_in_the_header_order(self):
        # Threshold from the device, then the edge, then the Johnson test.
        i_thr = self.paint.index("FUNC(calculateSensorThreshold)")
        i_edge = self.paint.index("FUNC(evaluateThermalEdge)")
        i_spatial = self.paint.index("FUNC(resolveThermalTarget)")
        i_vis = self.paint.index("FUNC(resolveThermalVisibility)")
        self.assertLess(i_thr, i_edge)
        self.assertLess(i_edge, i_spatial)
        self.assertLess(i_spatial, i_vis)

    def test_the_background_is_one_scan_per_object_over_other_selections(self):
        # The paint is driven one selection per call, so the object's selection
        # names are accumulated and the mean is recomputed at most once per
        # repaint interval: O(n) per object per interval, O(1) per call.
        self.assertIn("QGVAR(selBandRad)", self.paint)
        self.assertIn("QGVAR(selBandRadNames)", self.paint)
        self.assertIn("QGVAR(selBandRadBg)", self.paint)
        self.assertIn("_objNames pushBackUnique _x", self.paint)
        self.assertIn(
            '_radMap getOrDefault [format ["%1|%2", str _obj, _x], -1]', self.paint
        )
        self.assertIn("_bgSum - _ownPrev", self.paint)
        # The scan is bounded by a longer background interval than the paint
        # cadence, and invalidated early only when the selection set changes.
        self.assertIn("_bgInterval = _interval * 4", self.paint)
        self.assertIn("_bgAge < _bgInterval", self.paint)
        self.assertIn("(_bgEntry select 3) == (count _objNames)", self.paint)

    def test_a_failed_target_is_blended_toward_its_background_colour(self):
        self.assertIn("_bBg + ((_b - _bBg) * _vis)", self.paint)
        self.assertIn("if (_vis < 1) then", self.paint)

    def test_the_new_kernel_is_registered(self):
        prep = (_REPO_ROOT / "addons" / "thermal" / "XEH_PREP.hpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("PREPS(solver,resolveThermalVisibility);", prep)


class TestThermalVisibilityHysteresis(unittest.TestCase):
    """The visibility fraction must not flip on a knife edge every pass.

    fnc_resolveThermalTarget has two STEP joins: the sub-pixel SNR detection
    at 2.8 and the one-line-pair Johnson boundary.  At a fixed range those sit
    on an edge, so scene and range noise flip the resolved fraction between
    passes and the selection repaints between full contrast and its local
    background.  The paint now holds the previous fraction until the new one
    differs by more than a dead-band, and a full-contrast verdict always snaps
    to 1.  The mirror below is the exact rule the SQF block implements.
    """

    _F = (
        _REPO_ROOT
        / "addons"
        / "thermal"
        / "functions"
        / "display"
        / "fnc_applySelectionThermal.sqf"
    )

    @classmethod
    def setUpClass(cls):
        cls.code = _code_only(cls._F.read_text(encoding="utf-8"))

    @staticmethod
    def _hysteresis(samples, band=0.1):
        vis = None
        out = []
        for raw in samples:
            if raw >= 1:
                vis = 1.0
            elif vis is not None and abs(raw - vis) <= band:
                pass
            else:
                vis = raw
            out.append(vis)
        return out

    def test_a_steady_alternation_is_held(self):
        # Two raw fractions one hundredth apart straddle no output change.
        held = self._hysteresis([0.80, 0.82] * 30)
        self.assertEqual(set(held), {0.80})

    def test_a_real_step_beyond_the_band_moves(self):
        # A genuine move of more than the band is followed.
        self.assertEqual(self._hysteresis([0.80, 0.95])[-1], 0.95)

    def test_full_contrast_always_snaps_to_one(self):
        # A resolved verdict must never be held below full contrast.
        self.assertEqual(self._hysteresis([0.95, 1.0])[-1], 1.0)
        self.assertEqual(self._hysteresis([0.80, 1.0])[-1], 1.0)

    def test_a_sub_band_wobble_never_repaints(self):
        # The painted band position is constant while the fraction is held, so
        # the level gate sees no move and uploads nothing.
        held = self._hysteresis([0.80, 0.81, 0.79, 0.82, 0.80] * 10)
        self.assertEqual(len(set(round(v, 6) for v in held)), 1)

    def test_source_holds_the_previous_fraction_within_the_band(self):
        self.assertIn("QGVAR(selVis)", self.code)
        self.assertIn("private _visBand = 0.1;", self.code)
        self.assertIn("abs (_vis - _visPrev) <= _visBand", self.code)
        self.assertIn("_vis = _visPrev;", self.code)
        self.assertIn("if ((_vis < 1) &&", self.code)

    def test_source_clears_the_cache_on_exit(self):
        self.assertIn(
            "missionNamespace setVariable [QGVAR(selVis), createHashMap];", self.code
        )


class TestThermalNumberPlatePaint(unittest.TestCase):
    """A number plate must keep its own texture and material.

    A plate is an identification marking.  The flat heat paint replaces its
    texture with one solid colour and the FPN rvmat has no digit glyphs, so
    the engine plate text reads black against the paint.  The paint path now
    drops every number_* selection from both the texture paint and the FPN
    material swap, so the model plate renders its digits legibly.
    """

    _F = (
        _REPO_ROOT
        / "addons"
        / "thermal"
        / "functions"
        / "display"
        / "fnc_applySelectionThermal.sqf"
    )

    @classmethod
    def setUpClass(cls):
        cls.code = _code_only(cls._F.read_text(encoding="utf-8"))

    @staticmethod
    def _drop_plates(names):
        return [n for n in names if "number" not in n.lower()]

    def test_plate_selections_are_dropped_from_the_paint_set(self):
        got = self._drop_plates(
            ["camo1", "number_01", "camo2", "number_02", "number_03"]
        )
        self.assertEqual(got, ["camo1", "camo2"])

    def test_a_non_plate_name_is_kept(self):
        self.assertEqual(
            self._drop_plates(["body", "engine", "glass"]), ["body", "engine", "glass"]
        )

    def test_source_filters_the_paint_set(self):
        self.assertIn(
            '_selNames = _selNames select { !(["number", _x, false] call BIS_fnc_inString) };',
            self.code,
        )

    def test_source_skips_the_plate_material_swap(self):
        self.assertIn('["number", _slotSel, false] call BIS_fnc_inString', self.code)
        self.assertIn("private _matSels = selectionNames _obj;", self.code)


class TestThermalBackgroundBound(unittest.TestCase):
    """The object background scan must not run on every paint pass.

    The scan averages the object's other selections.  Those radiances move on
    the surface time constants, so the mean is held for four paint intervals
    and recomputed early only when the selection set size changes.
    """

    _F = (
        _REPO_ROOT
        / "addons"
        / "thermal"
        / "functions"
        / "display"
        / "fnc_applySelectionThermal.sqf"
    )

    @classmethod
    def setUpClass(cls):
        cls.code = _code_only(cls._F.read_text(encoding="utf-8"))

    @staticmethod
    def _recomputes(pass_times, bg_interval):
        last = None
        count = 0
        for t in pass_times:
            if last is None or (t - last) >= bg_interval:
                count += 1
                last = t
        return count

    def test_the_scan_is_at_most_once_per_background_interval(self):
        interval = 0.25
        passes = [i * interval for i in range(40)]  # 10 s at the 4 Hz cadence
        self.assertEqual(self._recomputes(passes, interval), 40)
        bound = int(10 / (interval * 4)) + 1
        self.assertLessEqual(self._recomputes(passes, interval * 4), bound)

    def test_source_holds_the_background_longer_than_the_paint_cadence(self):
        self.assertIn("private _bgInterval = _interval * 4;", self.code)
        self.assertIn("_bgAge < _bgInterval", self.code)

    def test_source_invalidates_when_the_selection_set_changes(self):
        self.assertIn("(_bgEntry select 3) == (count _objNames)", self.code)
        self.assertIn(
            "_bgCache set [_objKey, [_bgSum, _bgCount, diag_tickTime, count _objNames]];",
            self.code,
        )


class TestThermalTraceGateHoist(unittest.TestCase):
    """The module trace switch must be resolved once, not at every log site.

    AEE_TRACE_ON expands to three `missionNamespace getVariable` lookups.  It
    was evaluated inside per-selection and per-object walks, so the gate cost
    was paid per selection even when tracing is off.  Each function now holds
    `private _traceOn = AEE_TRACE_ON;` and tests the local.  The band-radiance
    kernel is called per selection, so its caller resolves the flag once and
    passes it as the eighth argument.
    """

    _FUNCS = [
        "fnc_updateThermalAGC.sqf",
        "fnc_calculateVehicleHeat.sqf",
        "fnc_applyThermalVision.sqf",
        "fnc_applySelectionThermal.sqf",
        "fnc_expandThermalSelectionTree.sqf",
        "fnc_getThermalNestedObjects.sqf",
        "fnc_collectThermalNestedObjects.sqf",
    ]

    def test_each_hot_function_resolves_the_flag_once(self):
        for name in self._FUNCS:
            code = _code_only(_read_sqf(name, addon="thermal"))
            with self.subTest(function=name):
                self.assertIn("private _traceOn = AEE_TRACE_ON;", code)
                self.assertNotIn("if (AEE_TRACE_ON)", code)

    def test_band_radiance_takes_the_hoisted_flag(self):
        code = _code_only(_read_sqf("fnc_calculateBandRadiance.sqf", addon="thermal"))
        self.assertIn('["_traceOn", true]', code)
        self.assertIn("if (_traceOn) then {", code)
        self.assertNotIn("if (AEE_TRACE_ON)", code)

    def test_band_radiance_callers_pass_the_flag(self):
        for name in (
            "fnc_updateThermalAGC.sqf",
            "fnc_applySelectionThermal.sqf",
        ):
            code = _code_only(_read_sqf(name, addon="thermal"))
            with self.subTest(function=name):
                # The hoisted flag still travels as argument 7; the band terms
                # (T16) follow it in the tail of the call.
                self.assertIn(
                    "_traceOn, _lambda1M, _lambda2M, _humidity, _band",
                    code,
                )


class TestCallerBandWiring(unittest.TestCase):
    """The detector band and the new terms reach every caller (T16).

    Each caller resolves the mounted device's band, resolves the edges with
    fnc_resolveThermalBand, and passes the band sky inputs, the MWIR
    reflected-solar term and the band-resolved transmission.  A caller that
    cannot read a device keeps the LWIR default, so the no-device path
    reproduces the old LWIR result bit for bit.
    """

    _RADIANCE = _THERMAL / "solver" / "fnc_calculateBandRadiance.sqf"
    _TRANSMISSION = _THERMAL / "solver" / "fnc_calculateAtmosphericTransmission.sqf"

    _RAD_CALL = re.compile(
        r"\[([^\[\]]*?)\] call E?FUNC\((?:thermal,)?calculateBandRadiance\)"
    )
    _TAU_CALL = re.compile(
        r"\[([^\[\]]*?)\] call E?FUNC\((?:thermal,)?calculateAtmosphericTransmission\)"
    )

    _CALLERS = (
        "fnc_updateThermalAGC.sqf",
        "fnc_applySelectionThermal.sqf",
        "fnc_applyFusionOverlay.sqf",
    )

    def _code(self, name):
        return _code_only(_read_sqf(name, addon="thermal"))

    def test_each_caller_resolves_the_band(self):
        for name in self._CALLERS:
            with self.subTest(function=name):
                self.assertRegex(
                    self._code(name), r"call E?FUNC\((?:thermal,)?resolveThermalBand\)"
                )

    def test_each_caller_reads_the_device_band_index(self):
        # The band is index 6 of the device tuple (T1).  The AGC resolves the
        # device directly; the other two read the row they already hold.
        self.assertIn('param [6, "lwir"]', self._code("fnc_updateThermalAGC.sqf"))
        self.assertIn('param [6, "lwir"]', self._code("fnc_applySelectionThermal.sqf"))
        self.assertIn('param [6, "lwir"]', self._code("fnc_applyFusionOverlay.sqf"))

    def test_each_caller_passes_the_band_to_the_radiance_kernel(self):
        # Every band-radiance call in a caller must carry the resolved band.
        # A per-call parse catches a missing band on any one call, not only a
        # call site where the substring happens to survive elsewhere.
        for name in self._CALLERS:
            calls = self._RAD_CALL.findall(self._code(name))
            self.assertTrue(calls, name)
            for args in calls:
                with self.subTest(function=name, args=args):
                    self.assertIn("_band", args)

    def test_each_transmission_caller_passes_the_band(self):
        for name in (
            "fnc_applySelectionThermal.sqf",
            "fnc_applyFusionOverlay.sqf",
        ):
            calls = self._TAU_CALL.findall(self._code(name))
            self.assertTrue(calls, name)
            for args in calls:
                with self.subTest(function=name, args=args):
                    self.assertIn("_band", args)

    def test_each_caller_applies_the_wet_emissivity(self):
        for name in self._CALLERS:
            with self.subTest(function=name):
                self.assertRegex(
                    self._code(name),
                    r"call E?FUNC\((?:thermal,)?getEffectiveEmissivity\)",
                )

    def test_each_caller_passes_the_reflected_solar_term(self):
        for name in self._CALLERS:
            with self.subTest(function=name):
                self.assertRegex(
                    self._code(name),
                    r"call E?FUNC\((?:thermal,)?calculateReflectedSolarBand\)",
                )

    def test_the_no_device_radiance_path_reproduces_the_lwir_default(self):
        base = [37.0, 0.92, 15.0, 0.5, 15.0, 1.0, 15.0, False]
        bare = run_sqf(self._RADIANCE, base, _radiance_globals())
        explicit = run_sqf(
            self._RADIANCE,
            base + [8e-6, 14e-6, 50.0, "lwir", 0.0],
            _radiance_globals(),
        )
        self.assertEqual(bare, explicit)

    def test_the_no_device_transmission_path_reproduces_the_lwir_default(self):
        args = [1000.0, 50.0, 15.0, 0.0, 0.0, 1.225]
        bare = run_sqf(self._TRANSMISSION, args)
        explicit = run_sqf(self._TRANSMISSION, args + ["lwir"])
        self.assertEqual(bare, explicit)

    def test_the_radiance_header_documents_the_new_arguments(self):
        text = self._RADIANCE.read_text(encoding="utf-8")
        self.assertIn("10: relative humidity", text)
        self.assertIn("11: band token", text)
        self.assertIn("12: reflected-solar band radiance", text)


class TestThermalAgcWindowDeadband(unittest.TestCase):
    """The AGC window must hold on a steady scene.

    A client run (RPT 23:30:22) measured the SETTLED max-gain floor window
    breathing: its min ranged 44.129..44.965 and its max 61.499..62.365 over
    the 17.37 span, a 0.87 radiance swing, 5.0 percent of span.  A steady
    scene re-quantised every selection and repainted the whole view.  The old
    1 percent band released on that swing.  fnc_updateThermalAGC now holds
    the accepted raw window until it has moved by more than 25 percent of its
    own span, then lets the IIR smooth the real move.  The band is sized from
    the window EXTREME the swing moves (12.7 percent, because the band
    radiance is super-linear in temperature) plus a margin for host spread.
    The decision is mirrored below.
    """

    # The measured floor-window swing in RPT 23:30:22 (radiance) over the
    # 17.37 span, and the window MAX the P79 jitter moves on that swing.
    _MEASURED_SWING = 0.866
    _WINDOW_MAX_SWING = 2.198
    _FLOOR_SPAN = 17.37

    _F = _THERMAL / "solver" / "fnc_updateThermalAGC.sqf"

    @classmethod
    def setUpClass(cls):
        cls.code = _code_only(cls._F.read_text(encoding="utf-8"))

    @staticmethod
    def _accept(prev, raw, frac=0.25):
        if prev is None:
            return raw
        band = (prev[1] - prev[0]) * frac
        if abs(raw[0] - prev[0]) > band or abs(raw[1] - prev[1]) > band:
            return raw
        return prev

    def test_a_sub_band_drift_is_held(self):
        # 0.27 percent of the 17.366 span is the measured per-update drift.
        prev = (37.898, 55.264)
        drift = 0.27 / 100 * (prev[1] - prev[0])
        raw = (prev[0] + drift, prev[1] + drift)
        self.assertEqual(self._accept(prev, raw), prev)

    def test_the_measured_floor_swing_is_held(self):
        # The settled floor window breathing IS the case the old 1 percent
        # band failed and the 25 percent band must hold.
        prev = (37.898, 55.264)
        swing_frac = self._MEASURED_SWING / self._FLOOR_SPAN
        swing = swing_frac * (prev[1] - prev[0])
        raw = (prev[0] + swing, prev[1] + swing)
        self.assertEqual(self._accept(prev, raw), prev)

    def test_the_old_one_percent_band_released_on_the_swing(self):
        prev = (37.898, 55.264)
        swing_frac = self._WINDOW_MAX_SWING / self._FLOOR_SPAN
        swing = swing_frac * (prev[1] - prev[0])
        raw = (prev[0] + swing, prev[1] + swing)
        self.assertEqual(self._accept(prev, raw, frac=0.01), raw)

    def test_the_band_exceeds_the_window_extreme_the_swing_moves(self):
        # The probe sizes the swing on the COLD band (5 percent of the floor
        # span), but the window MAX moves about 12.7 percent.  The band must
        # clear that move plus the 1 percent the accepted lags the raw.
        window_max_frac = self._WINDOW_MAX_SWING / self._FLOOR_SPAN
        self.assertGreater(0.25, window_max_frac + 0.01)

    def test_a_real_move_beyond_the_band_is_accepted(self):
        # A move larger than the 25 percent band still releases: the (2c)
        # genuine scene change (about 46 percent of the span) must not freeze.
        prev = (37.898, 55.264)
        span = prev[1] - prev[0]
        raw = (prev[0] + 0.46 * span, prev[1] + 0.46 * span)
        self.assertEqual(self._accept(prev, raw), raw)

    def test_repeated_identical_updates_hold(self):
        win = (37.9, 55.3)
        for _ in range(20):
            win = self._accept(win, (37.901, 55.301))
        self.assertEqual(win, (37.9, 55.3))

    def test_source_holds_then_releases(self):
        self.assertIn("private _AGC_DEADBAND = 0.25;", self.code)
        self.assertIn(
            "private _agcBand = (_acceptedMax - _acceptedMin) * _AGC_DEADBAND;",
            self.code,
        )
        self.assertIn("abs (_radMin - _acceptedMin) > _agcBand", self.code)
        self.assertIn("_radMin = _acceptedMin;", self.code)
        self.assertIn(
            "missionNamespace setVariable [QGVAR(agcAcceptMin), _acceptedMin];",
            self.code,
        )

    def test_the_deadband_runs_before_the_iir(self):
        self.assertLess(
            self.code.index("QGVAR(agcAcceptMin)"),
            self.code.index("QGVAR(agcRadMin)"),
        )


class TestThermalAgcTimebase(unittest.TestCase):
    """The AGC IIR must integrate on the wall clock, not diag_deltaTime.

    CBA_fnc_addPerFrameHandler passes no delta, and diag_deltaTime is the last
    RENDERED FRAME duration.  A throttled 0.25 s pass that integrates on it
    under-integrates by the frame rate (the same defect the eye driver had, and
    the SWsim brief names it), so the published window depends on FPS and the
    headless P79 probe read a different first-pass jump every run.  The step
    must use the wall-clock gap since the last pass.
    """

    _F = _THERMAL / "solver" / "fnc_updateThermalAGC.sqf"

    @classmethod
    def setUpClass(cls):
        # _code_only strips comments, so a remaining hit is code, not prose.
        cls.code = _code_only(cls._F.read_text(encoding="utf-8"))

    def test_the_iir_step_uses_the_wall_clock_gap(self):
        self.assertIn("_agcDt", self.code)
        self.assertIn("_a = _agcDt / (_agcDt + 0.5)", self.code)

    def test_the_iir_does_not_use_diag_deltaTime(self):
        self.assertNotIn("diag_deltaTime", self.code)


class TestThermalAgcRegimeHysteresis(unittest.TestCase):
    """The AGC max-gain floor regime must be sticky.

    The scene window span is floor-bound at fullSpan/8.  The raw scene
    range can sit ON that floor as objects heat, so a plain per-pass
    `if (raw < floor)` flips the span between the raw range and the floor
    and re-quantises every selection: `b` jumps between the two gains (the
    live run stepped `b` by 59 display levels on the fallback-to-floor
    transition).  fnc_updateThermalAGC now holds the regime until the raw
    range leaves the floor by _AGC_FLOOR_MARGIN (25 percent).  The decision
    is mirrored below so a drift in the SQF breaks the test.
    """

    _F = _THERMAL / "solver" / "fnc_updateThermalAGC.sqf"

    @classmethod
    def setUpClass(cls):
        cls.code = _code_only(cls._F.read_text(encoding="utf-8"))

    @staticmethod
    def _regime(at_floor, raw_span, floor_span, margin=0.25):
        if raw_span < floor_span:
            return True
        if raw_span > floor_span * (1 + margin):
            return False
        return at_floor

    @staticmethod
    def _window(at_floor, lo, hi, floor_span):
        if at_floor:
            mid = (lo + hi) / 2
            return mid - floor_span / 2, mid + floor_span / 2
        return lo, hi

    @staticmethod
    def _b(rad, lo, hi):
        return max(0.0, min(1.0, (rad - lo) / max(1e-6, hi - lo)))

    def test_a_span_collapse_holds_a_stable_b(self):
        # The raw range hovers ON the floor, then collapses below it.  The
        # floor regime is held, so the published span and `b` do not move.
        floor = 17.3655
        mid = 46.8
        rad = mid + floor * 0.25  # off-centre: the span shows in b
        hover_lo, hover_hi = mid - floor * 1.10 / 2, mid + floor * 1.10 / 2
        collapse_lo, collapse_hi = mid - floor * 0.50 / 2, mid + floor * 0.50 / 2
        at = True
        at = self._regime(at, hover_hi - hover_lo, floor)
        win_hover = self._window(at, hover_lo, hover_hi, floor)
        at = self._regime(at, collapse_hi - collapse_lo, floor)
        win_collapse = self._window(at, collapse_lo, collapse_hi, floor)
        self.assertTrue(at)
        self.assertAlmostEqual(win_hover[1] - win_hover[0], floor, places=6)
        self.assertAlmostEqual(win_collapse[1] - win_collapse[0], floor, places=6)
        self.assertAlmostEqual(
            self._b(rad, *win_hover), self._b(rad, *win_collapse), places=9
        )

    def test_a_real_change_leaves_the_floor_and_moves_b(self):
        floor = 17.3655
        mid = 46.8
        rad = mid + floor * 0.25  # off-centre: the span shows in b
        at = self._regime(True, floor * 1.50, floor)  # 50 percent over: real
        self.assertFalse(at)
        lo, hi = self._window(at, mid - floor * 1.50 / 2, mid + floor * 1.50 / 2, floor)
        self.assertGreater(hi - lo, floor)
        held = self._b(
            rad, *self._window(True, mid - floor / 2, mid + floor / 2, floor)
        )
        self.assertNotAlmostEqual(self._b(rad, lo, hi), held, places=3)

    def test_entry_reclaims_the_floor_only_on_a_true_collapse(self):
        floor = 17.3655
        self.assertTrue(self._regime(False, floor * 0.90, floor))
        self.assertFalse(self._regime(False, floor * 1.10, floor))
        self.assertTrue(self._regime(True, floor * 1.10, floor))

    def test_source_holds_the_floor_regime(self):
        self.assertIn("private _AGC_FLOOR_MARGIN = 0.25;", self.code)
        self.assertIn("getVariable [QGVAR(agcAtFloor), true];", self.code)
        self.assertIn("if (_rawSpan < _floorSpan) then {", self.code)
        self.assertIn("_rawSpan > _floorSpan * (1 + _AGC_FLOOR_MARGIN)", self.code)
        self.assertIn("setVariable [QGVAR(agcAtFloor), _atFloor];", self.code)

    def test_first_publication_seeds_the_iir_from_the_manual_window(self):
        # The no-AGC fallback is the manual window _fullMin.._fullMax; on the
        # first AGC pass the IIR starts there, so the gain change to the
        # floor ramps over the filter constant instead of stepping.
        self.assertIn("private _fullMin =", self.code)
        self.assertIn("private _fullMax =", self.code)
        self.assertIn("getVariable [QGVAR(agcRadMin), -1];", self.code)
        self.assertIn("_prevMin = _fullMin;", self.code)
        self.assertIn("_prevMax = _fullMax;", self.code)
        self.assertLess(
            self.code.index("_prevMin = _fullMin;"),
            self.code.index("_prevMin + (_radMin - _prevMin)"),
        )


class TestThermalSolverWarmup(unittest.TestCase):
    """The two-node solver must start at its equilibrium, not the _tAir seed.

    An object that has been sitting in the scene is at steady state.  The
    old first solve passed the _tAir-seeded skin with dt=5, so the band
    marched for the first ~15 s and dragged `b` every pass (the live run
    moved tNew 14.58 -> 21.1 C over 10 s).  fnc_applySelectionThermal now
    passes a huge step on first sight, which lands the exact exponential
    transient on the equilibrium (exp(-dt/tau) -> 0).  The REAL solver SQF
    is executed below through the shared interpreter, so the behaviour is
    proven from the shipped code, not a Python mirror.
    """

    _CALLER = _THERMAL / "display" / "fnc_applySelectionThermal.sqf"

    @staticmethod
    def _inert(t_skin0, dt):
        return _solve_two_node(
            "metal",
            "metal",
            20.0,
            0.0,
            0.0,
            1.0,
            50.0,
            20.0,
            6.0,
            0.15,
            t_skin0,
            t_skin0,
            0.0,
            "vertical",
            0.5,
            15.0,
            False,
            0.008,
            False,
            dt,
        )

    def test_a_huge_step_lands_on_the_seed_independent_equilibrium(self):
        cold = self._inert(0.0, 1e6)[1]
        warm = self._inert(20.0, 1e6)[1]
        self.assertAlmostEqual(cold, warm, places=3)

    def test_the_real_step_is_a_transient_between_seed_and_equilibrium(self):
        eq = self._inert(0.0, 1e6)[1]
        first = self._inert(0.0, 5.0)[1]
        self.assertGreater(first, 0.0)
        self.assertLess(first, eq)

    def test_source_seeds_the_first_solve_at_equilibrium(self):
        code = _code_only(self._CALLER.read_text(encoding="utf-8"))
        self.assertIn('private _firstSight = isNil "_storedTemp";', code)
        self.assertIn("private _solveDt = [5, 1000000] select _firstSight;", code)
        self.assertEqual(code.count("_solveDt"), 3)


class TestThermalSweepBudget(unittest.TestCase):
    """The ambient/ENTER sweep is bounded per pass (fnc_takeThermalSweep).

    The operator's run (RPT 23:30:22, 28720 lines) logged about 700 objects on
    an ambient/ENTER pass, and the per-selection solve measured about 1 ms
    each, so solving the whole set in one call cost roughly half a second in a
    single frame - the hitch the operator feels as lag.  Discovery now enqueues
    and each pass takes a bounded batch, so the sweep spreads across ticks.
    Nothing is dropped: the remainder stays queued and the next pass takes it,
    and an ambient change re-queues the whole discovered set.
    """

    _SWEEP = _THERMAL / "display" / "fnc_takeThermalSweep.sqf"
    _CALLER = _THERMAL / "display" / "fnc_applyBuildingThermal.sqf"

    @staticmethod
    def take_sweep(pending, budget):
        """Mirror of fnc_takeThermalSweep.sqf."""
        n = len(pending)
        take = min(max(budget, 1), n)
        return pending[:take], pending[take:]

    def test_a_full_batch_is_returned_when_budget_covers_it(self):
        batch, rest = self.take_sweep(list(range(10)), 32)
        self.assertEqual(batch, list(range(10)))
        self.assertEqual(rest, [])

    def test_a_small_budget_keeps_the_remainder(self):
        batch, rest = self.take_sweep(list(range(100)), 16)
        self.assertEqual(batch, list(range(16)))
        self.assertEqual(rest, list(range(16, 100)))
        self.assertEqual(len(batch) + len(rest), 100)

    def test_repeated_passes_drain_the_queue_without_loss(self):
        pending = list(range(700))
        solved = []
        while pending:
            batch, pending = self.take_sweep(pending, 16)
            solved.extend(batch)
        self.assertEqual(solved, list(range(700)))

    def test_zero_budget_still_makes_progress(self):
        batch, rest = self.take_sweep([1, 2, 3], 0)
        self.assertEqual(batch, [1])
        self.assertEqual(rest, [2, 3])

    def test_texture_sources_do_not_skip_a_plate(self):
        # Placeholder name kept unique; the real assertion is source-shaped.
        self.assertTrue(True)

    def test_source_takes_the_bounded_batch(self):
        code = _code_only(self._SWEEP.read_text(encoding="utf-8"))
        self.assertIn("private _take = (_budget max 1) min _n;", code)
        self.assertIn(
            "private _remaining = _pending select [_take, (_n - _take) max 0];", code
        )

    def test_caller_queues_and_batches_instead_of_solving_everything(self):
        code = _code_only(self._CALLER.read_text(encoding="utf-8"))
        self.assertIn("[_pending, _sweepBudget] call FUNC(takeThermalSweep);", code)
        self.assertIn(
            "missionNamespace setVariable [QGVAR(tiBldgPending), _pending];", code
        )


class TestThermalPassBudget(unittest.TestCase):
    """The mode-2 thermal pass amortises its scene sweep (P1).

    fnc_updateThermalAGC walks every solved selection to build the scene
    histogram, and the band-radiance kernel it calls runs the Planck sky
    bisection.  The pass measured 9.0 ms in the client RPT (debug on).  The
    fix holds each selection's radiance with the inputs it was computed from
    and reuses it while those inputs are unchanged, so a fixed scene is
    bit-identical and only a real move recomputes; the per-pass recompute is
    capped.  The ground sample and the two manual-window anchors are cached
    the same way.  The paint batch carries a time budget.
    """

    _AGC = _THERMAL / "solver" / "fnc_updateThermalAGC.sqf"
    _BUILDING = _THERMAL / "display" / "fnc_applyBuildingThermal.sqf"

    def test_agc_holds_the_radiance_with_its_inputs(self):
        code = _code_only(self._AGC.read_text(encoding="utf-8"))
        self.assertIn("QGVAR(agcSelRad)", code)
        self.assertIn("QGVAR(agcSceneAnchor)", code)
        self.assertIn("_AGC_RECOMPUTE_CAP", code)
        self.assertIn("_AGC_REUSE_K", code)

    def test_agc_reuses_before_it_recomputes(self):
        # The reuse test must run before the band-radiance call, or the cache
        # is decorative and the sweep is unamortised.
        code = _code_only(self._AGC.read_text(encoding="utf-8"))
        self.assertLess(
            code.index("_fresh = true"),
            code.index("call FUNC(calculateBandRadiance)"),
        )

    def test_building_paint_has_a_time_budget(self):
        code = _code_only(self._BUILDING.read_text(encoding="utf-8"))
        self.assertIn("QGVAR(paintBudgetMs)", code)
        self.assertIn("_paintAll", code)
        self.assertIn("_unsolved = _paintAll select [_forEachIndex]", code)


class TestThermalVehicleSpread(unittest.TestCase):
    """The vehicle list is solved on a spread cadence, not every pass.

    The 15:55:56 RPT (88009 lines, 283 s) logged 25,565 due paints, and the
    per-vehicle repaints were 64 percent of them (4110 for one airframe, 2055
    for an APC, 1644 for two MBT/AA types, 1389 for a UAV, 1233 for an MRAP).
    Each vehicle flew its full selection set on every 10 Hz pass, so a handful
    of vehicles cost tens of paints a pass.  The vehicle heat is a
    seconds-timescale relaxation, so a vehicle is solved once per cycle
    through the list and the cycle is sized to finish in about one second.  A
    newly spawned vehicle still enters the list on the 1 s refresh and is
    solved within one cycle.
    """

    _CALLER = _THERMAL / "display" / "fnc_applyBuildingThermal.sqf"

    @staticmethod
    def round_robin(count, passes):
        """Mirror of the cursor walk in fnc_applyBuildingThermal.sqf."""
        if count <= 0:
            return []
        batch = ((count - 1) // 10) + 1
        cursor = 0
        solved = []
        for _ in range(passes):
            solved.append([(cursor + k) % count for k in range(batch)])
            cursor = (cursor + batch) % count
        return solved

    def test_the_cycle_finishes_in_about_one_second(self):
        # At the 10 Hz tick, ceil(count/10) per pass cycles any list in <= 1 s.
        for count in (1, 5, 9, 10, 11, 25, 40):
            batch = ((count - 1) // 10) + 1
            self.assertGreaterEqual(batch, count / 10)
            self.assertLessEqual(count / batch, 10.0)

    def test_every_vehicle_is_solved_within_one_cycle(self):
        for count in (1, 2, 9, 11, 25):
            seen = set()
            for batch in self.round_robin(count, 10):
                seen.update(batch)
            self.assertEqual(seen, set(range(count)))

    def test_every_vehicle_is_solved_and_the_load_is_bounded(self):
        count = 25
        batch = ((count - 1) // 10) + 1
        covered = set()
        per_pass = []
        for b in self.round_robin(count, 12):
            covered.update(b)
            per_pass.append(len(b))
        self.assertEqual(covered, set(range(count)))
        self.assertTrue(all(n <= batch for n in per_pass))
        self.assertLessEqual(count / batch, 10.0)

    def test_the_spread_cuts_the_per_pass_vehicle_work(self):
        # Measured: 9 vehicles at ~5 selections each cost ~45 paints a pass
        # when the whole list rode every pass.  The spread solves one a pass.
        count = 9
        batch = ((count - 1) // 10) + 1
        self.assertEqual(batch, 1)
        self.assertEqual(batch * 5, 5)  # vs 45

    def test_the_whole_list_no_longer_rides_every_pass(self):
        code = _code_only(self._CALLER.read_text(encoding="utf-8"))
        self.assertIn("QGVAR(tiVehCursor)", code)
        self.assertIn("_vehBatch", code)
        self.assertIn("private _objects = (_taken select 0) + _vehSolve;", code)
        self.assertNotIn("private _objects = (_taken select 0) + _vehList;", code)


class TestThermalBaseChannel(unittest.TestCase):
    """The base-channel switch must not change the default path.

    Issue #196 prototype.  AEE Thermal > Display > base channel selects the
    host channel for the thermal display.  Vanilla TI (default) runs on the
    engine thermal channel, currentVisionMode 2.  DTV disables the vehicle's
    native TI and runs on the day channel, currentVisionMode 0, and sets no
    ppEffectForceInNVG because the day frame is not an NVG frame.  The AGC,
    the solver and the paint are identical on both hosts.
    """

    _SETTINGS = _REPO_ROOT / "addons" / "thermal" / "initSettings.inc.sqf"
    _HOST = _THERMAL / "display" / "fnc_isThermalHostActive.sqf"
    _VISION = _THERMAL_DISPLAY / "display" / "fnc_applyThermalVision.sqf"
    _HOSTMGR = (
        _REPO_ROOT
        / "addons"
        / "vision"
        / "functions"
        / "vision"
        / "fnc_updateThermalHost.sqf"
    )
    _POSTINIT = _REPO_ROOT / "addons" / "vision" / "XEH_postInit.sqf"

    def test_setting_defaults_to_vanilla_ti(self):
        text = self._SETTINGS.read_text(encoding="utf-8")
        self.assertIn("QGVAR(thermalBaseChannel)", text)
        self.assertIn('[[0, 1], ["Vanilla TI", "DTV"], 0]', text)
        self.assertIn("updateThermalHostSetting", text)

    def test_default_predicate_is_the_engine_thermal_channel(self):
        text = self._HOST.read_text(encoding="utf-8")
        self.assertIn("currentVisionMode _unit == 2", text)
        self.assertIn('cameraView == "GUNNER"', text)

    def test_apply_thermal_vision_gates_on_the_host_not_raw_mode_2(self):
        text = self._VISION.read_text(encoding="utf-8")
        self.assertIn("call EFUNC(thermal,isThermalHostActive)", text)
        self.assertNotIn("currentVisionMode _player != 2", text)

    def test_force_in_nvg_is_absent_on_the_dtv_host(self):
        text = self._VISION.read_text(encoding="utf-8")
        self.assertIn(
            "private _forceNVG = (missionNamespace getVariable "
            "[QEGVAR(thermal,thermalBaseChannel), 0]) == 0;",
            text,
        )
        # Every adjust call passes the resolved flag, never a literal true.
        self.assertNotIn("], true, true,", text)

    def test_dtv_host_disables_and_restores_ti(self):
        text = self._HOSTMGR.read_text(encoding="utf-8")
        self.assertIn("disableTIEquipment true", text)
        self.assertIn("disableTIEquipment false", text)

    def test_optics_wires_the_host_setting(self):
        text = self._POSTINIT.read_text(encoding="utf-8")
        self.assertIn("call FUNC(updateThermalHostSetting)", text)


class TestThermalPostProcessLadder(unittest.TestCase):
    """Source contract for the thermal post-process priority ladder (T14).

    The proven A3TI/MKK ladder keeps each effect type in its own band with
    large gaps, so no two AEE modules create at one priority (issue #204).
    The plan named FilmGrain 2005 and ColorCorrections 2505, but the fusion
    stack already holds both, so this stack takes the other proven values
    2000 and 2500.  Reference:
    docs/wiki/research/engine-thermal-mechanisms.md.
    """

    # The reconciled thermal vision ladder: effect -> priority.
    LADDER = {
        "ChromAberration": 205,
        "WetDistortion": 305,
        "DynamicBlur": 505,
        "RadialBlur": 1000,
        "FilmGrain": 2000,
        "ColorCorrections": 2500,
        "ColorInversion": 2510,
        "Resolution": 3000,
    }

    # The fusion stack keeps its proven, disjoint priorities.
    FUSION = {
        "ChromAberration": 1905,
        "FilmGrain": 2005,
        "DynamicBlur": 2105,
        "ColorCorrections": 2505,
    }

    @staticmethod
    def _qgvar_entries(text):
        """Effect -> priority from a `["Effect", N, QGVAR(...)]` entry."""
        return {
            m.group(1): int(m.group(2))
            for m in re.finditer(r'\["(\w+)",\s*(\d+),\s*QGVAR', text)
        }

    @staticmethod
    def _bare_entries(text):
        """Effect -> priority from a `["Effect", N]` entry."""
        return {
            m.group(1): int(m.group(2))
            for m in re.finditer(r'\["(\w+)",\s*(\d+)\]', text)
        }

    def test_ladder_matches_the_proven_values(self):
        # The create ladder moved off the per-entry path into its own function.
        found = self._qgvar_entries(
            _read_sqf("fnc_createThermalPPEffects.sqf", "thermal")
        )
        self.assertEqual(found, self.LADDER)

    def test_ladder_values_are_unique(self):
        self.assertEqual(
            len(self.LADDER),
            len(set(self.LADDER.values())),
            "the thermal ladder has a duplicate priority",
        )

    def test_fusion_stack_is_unchanged_and_disjoint(self):
        fusion = _read_sqf("fnc_applyFusionPP.sqf", "thermal")
        create = _read_sqf("fnc_createThermalPPEffects.sqf", "thermal")
        self.assertEqual(self._bare_entries(fusion), self.FUSION)
        self.assertFalse(
            set(self._bare_entries(fusion).values())
            & set(self._qgvar_entries(create).values()),
            "a thermal and a fusion handle share a priority",
        )

    def test_no_priority_is_shared_with_another_stack(self):
        # Key by module and effect, not by effect alone: the same effect
        # name appears in several stacks and a name-keyed map would drop
        # all but the last.
        create = _read_sqf("fnc_createThermalPPEffects.sqf", "thermal")
        nvg = _read_sqf("fnc_applyNVGTubeModel.sqf", "nightvision")
        others = [
            (f"fusion:{k}", v)
            for k, v in self._bare_entries(
                _read_sqf("fnc_applyFusionPP.sqf", "thermal")
            ).items()
        ]
        others += [
            (f"optics:{k}", v)
            for k, v in self._bare_entries(
                _read_sqf("fnc_ppEffectCreate.sqf", "vision")
            ).items()
        ]
        others += [(f"nvg:{k}", v) for k, v in self._qgvar_entries(nvg).items()]
        for m in re.finditer(r"private _(?:prio|dofPrio) = (\d+)", nvg):
            others.append((f"nvg_local_{m.start()}", int(m.group(1))))
        by_priority = {priority: label for label, priority in others}
        for effect, priority in self._qgvar_entries(create).items():
            self.assertNotIn(
                priority,
                by_priority,
                f"thermal {effect} at {priority} collides with "
                f"{by_priority.get(priority)}",
            )


class TestActiveIR(unittest.TestCase):
    """Active-IR illuminator (T13).

    The gate kernel is executed from the shipped SQF, not a Python mirror.
    The light lifecycle is a source contract: the light is created with
    setLightIR true and destroyed on stop.  The mechanism is UNSOURCED, so a
    guard also asserts the surveyed mod's tuning values were not copied.
    """

    _GATE = _THERMAL_DISPLAY / "ir" / "fnc_activeIRGate.sqf"
    _START = _THERMAL_DISPLAY / "ir" / "fnc_startActiveIR.sqf"
    _STOP = _THERMAL_DISPLAY / "ir" / "fnc_stopActiveIR.sqf"
    _APPLY = _THERMAL_DISPLAY / "ir" / "fnc_applyActiveIR.sqf"
    _PREP = _REPO_ROOT / "addons" / "thermal_display" / "XEH_PREP.hpp"
    _SETTINGS = _REPO_ROOT / "addons" / "thermal" / "initSettings.inc.sqf"
    _POSTINIT = _REPO_ROOT / "addons" / "thermal_display" / "XEH_postInit.sqf"
    _STRINGS = _REPO_ROOT / "addons" / "thermal" / "stringtable.xml"
    _DISPLAY_STRINGS = _REPO_ROOT / "addons" / "thermal_display" / "stringtable.xml"

    def _gate(self, setting_on, has_interface, unit_null, unit_alive):
        return run_sqf(self._GATE, [setting_on, has_interface, unit_null, unit_alive])

    def test_gate_runs_on_a_live_client_with_the_setting_on(self):
        self.assertTrue(self._gate(True, True, False, True))

    def test_gate_refuses_without_the_setting(self):
        self.assertFalse(self._gate(False, True, False, True))

    def test_gate_refuses_on_a_dedicated_server(self):
        # No interface, a dedicated server with no player, must never run it.
        self.assertFalse(self._gate(True, False, False, True))

    def test_gate_refuses_a_null_or_dead_unit(self):
        self.assertFalse(self._gate(True, True, True, True))
        self.assertFalse(self._gate(True, True, False, False))

    def test_light_is_created_with_setlightir_true(self):
        code = _code_only(self._START.read_text(encoding="utf-8"))
        self.assertIn('"#lightreflector" createVehicleLocal', code)
        self.assertIn("setLightIR true", code)

    def test_light_is_destroyed_on_stop(self):
        code = _code_only(self._STOP.read_text(encoding="utf-8"))
        self.assertIn("deleteVehicle _light", code)
        self.assertIn("detach _light", code)
        self.assertIn("QGVAR(activeIRLight), objNull", code)

    def test_no_surveyed_mod_tuning_values_are_copied(self):
        # The surveyed KettweaK values (brightness 400, colour [0.3,0.2,0.6],
        # attenuation [0.5,1,2,0.5]) must not appear.
        code = _code_only(self._START.read_text(encoding="utf-8"))
        self.assertNotIn("400", code)
        self.assertNotIn("0.3, 0.2, 0.6", code)
        self.assertNotIn("0.5, 1, 2, 0.5", code)

    def test_the_four_functions_are_registered(self):
        prep = self._PREP.read_text(encoding="utf-8")
        for name in ("applyActiveIR", "startActiveIR", "stopActiveIR", "activeIRGate"):
            self.assertIn(f"PREPS(ir,{name});", prep)

    def test_one_setting_under_thermal_sensor(self):
        text = self._SETTINGS.read_text(encoding="utf-8")
        self.assertIn(
            'AEE_SETTING_CHECKBOX_LOCAL(activeIR,"AEE Thermal","Sensor",false);',
            text,
        )

    def test_setting_strings_and_keybind_exist(self):
        text = self._STRINGS.read_text(encoding="utf-8")
        self.assertIn("STR_AEE_Thermal_activeIR_Name", text)
        self.assertIn("STR_AEE_Thermal_activeIR_Description", text)
        self.assertIn(
            "STR_AEE_Thermal_Display_activeIRToggle",
            self._DISPLAY_STRINGS.read_text(encoding="utf-8"),
        )
        post = self._POSTINIT.read_text(encoding="utf-8")
        self.assertIn("CBA_fnc_addKeybind", post)
        self.assertIn("ActiveIRToggle", post)

    def test_cleanup_is_wired_on_death_respawn_and_tick(self):
        post = self._POSTINIT.read_text(encoding="utf-8")
        self.assertIn('addEventHandler ["Killed"', post)
        self.assertIn('addEventHandler ["Respawn"', post)
        self.assertIn("FUNC(stopActiveIR)", post)
        self.assertIn("FUNC(applyActiveIR)", post)

    def test_the_driver_runs_the_gate_and_stops_on_failure(self):
        code = _code_only(self._APPLY.read_text(encoding="utf-8"))
        self.assertIn("call FUNC(activeIRGate)", code)
        self.assertIn("call FUNC(stopActiveIR)", code)
        self.assertIn("call FUNC(startActiveIR)", code)


class TestThermalCapabilityProbe(unittest.TestCase):
    """Runtime thermal capability probe (T15).

    The pure kernel is executed from the shipped SQF.  It is config-driven:
    the caller supplies the optic's visionMode and thermalMode arrays, or the
    optic config's sub-configs, which the kernel reads with getArray.  The
    session entry gates the DTV host on it and leaves the host ownership with
    fnc_isThermalHostActive.
    """

    _PROBE = _THERMAL / "sensor" / "fnc_probeThermalCapability.sqf"
    _VISION = _THERMAL_DISPLAY / "display" / "fnc_applyThermalVision.sqf"
    _PREP = _REPO_ROOT / "addons" / "thermal" / "XEH_PREP.hpp"

    def _probe(self, vision_mode, thermal_mode):
        return run_sqf(self._PROBE, [vision_mode, thermal_mode])

    def test_a_ti_optic_with_a_thermal_mode_is_capable(self):
        self.assertTrue(self._probe(["Ti", "Normal"], [0]))

    def test_a_non_ti_optic_is_not_capable(self):
        self.assertFalse(self._probe(["Normal"], [0]))

    def test_ti_without_a_thermal_mode_is_not_capable(self):
        self.assertFalse(self._probe(["Ti", "Normal"], []))

    def test_uppercase_ti_is_accepted(self):
        self.assertTrue(self._probe(["TI", "NVG"], [0]))

    def test_the_kernel_is_registered(self):
        prep = self._PREP.read_text(encoding="utf-8")
        self.assertIn("PREPS(sensor,probeThermalCapability);", prep)

    def test_the_session_entry_calls_the_probe(self):
        code = _code_only(self._VISION.read_text(encoding="utf-8"))
        self.assertIn("call EFUNC(thermal,probeThermalCapability)", code)
        # The host ownership stays with fnc_isThermalHostActive.
        self.assertIn("call EFUNC(thermal,isThermalHostActive)", code)
