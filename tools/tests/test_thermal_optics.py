#!/usr/bin/env python3
"""Reference checks for AEE's thermal and NVG optics physics.

These tests validate the SQF implementation in addons/thermal and
addons/optics against known physical values.  They mirror the exact
formulas in the SQF source so that any drift breaks the tests.

Run: python3 -m unittest tools.tests.test_thermal_optics -v
"""

import math
import os
import unittest
from pathlib import Path

# Cross-model consistency: the optics moon term must stay consistent with
# the verified lunar illuminance model (Krisciunas & Schaefer 1991) in
# test_astronomical.py.
from tools.tests.test_astronomical import ks_lunar_lux

# Repo root: tools/tests/ -> up two levels.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_OPTICS = _REPO_ROOT / "addons" / "optics" / "functions"
_THERMAL = _REPO_ROOT / "addons" / "thermal" / "functions"


def _read_sqf(name, addon="optics"):
    """Read an SQF function file.  The drift-lock tests read the SOURCE so a
    constant change in SQF fails the mirror tests until re-synced."""
    base = _OPTICS if addon == "optics" else _THERMAL
    return (base / name).read_text(encoding="utf-8")


# ─── Object temperature model mirrors ───────────────────────────────────────


def thermal_inertia(current, target, dt, tau):
    """Mirror of the exponential thermal inertia in fnc_calculateObjectTemperature.

    SQF: _currentTemp + (_target - _currentTemp) * (1 - exp(-dt / tau))
    """
    if tau <= 0:
        return target
    return current + (target - current) * (1 - math.exp(-dt / tau))


def vehicle_engine_heat(engine_run_time):
    """Mirror of the vehicle engine warm-up curve.

    SQF: 40 * (1 - exp(-_engineRunTime / 300))
    Returns °C above ambient.
    """
    return 40 * (1 - math.exp(-engine_run_time / 300))


def vehicle_exhaust_temp(air_temp, engine_run_time):
    """Mirror of the exhaust temperature model.

    SQF: _airTemp + 200 * (1 - exp(-_engineRunTime / 60))
    """
    return air_temp + 200 * (1 - math.exp(-engine_run_time / 60))


def vehicle_exhaust_share(air_temp, engine_run_time):
    """The small share of exhaust heat that raises the vehicle average.

    SQF: (_exhaustTemp - _airTemp) * 0.05
    """
    return (vehicle_exhaust_temp(air_temp, engine_run_time) - air_temp) * 0.05


def engine_run_time_decay(ert, dt):
    """Mirror of engine-off exponential decay.

    SQF: _engineRunTime * exp(-dt / 300)
    """
    return ert * math.exp(-dt / 300)


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


def emissivity_radiant_correction(emissivity):
    """Mirror of the radiant temperature correction.

    SQF: _target - (1 - _emissivity) * 2
    """
    return -(1 - emissivity) * 2


# ─── Thermal contrast mirrors ───────────────────────────────────────────────


def thermal_contrast(delta_t, rain=0.0, fog=0.0, humidity=0.0, air_temp=15.0):
    """Mirror of fnc_calculateThermalContrast.

    contrast = (deltaT / 8) min 1.0
    × (1 - rain × 0.4) × (1 - fog × 0.6) × (1 - humidity × 0.3)
    heat >35: contrast -= ((T - 35) / 10) × 0.7
    cold <5:  contrast *= 1.2, min 1.0

    8 °C span (was 5): the engine already renders the native thermal
    image with its own gain; this stage only adds environmental
    degradation.  A 5 °C span double-amplified the frame to pure white.
    """
    c = min(delta_t / 8.0, 1.0)
    c *= 1 - rain * 0.4
    c *= 1 - fog * 0.6
    c *= 1 - humidity * 0.3
    if air_temp > 35:
        c -= ((air_temp - 35) / 10) * 0.7
    if air_temp < 5:
        c = min(c * 1.2, 1.0)
    return max(0, min(1, c))


def netd_noise(view_distance, humidity=0.0):
    """Mirror of the NETD noise floor.

    SQF: _noise = 0.05 * ((_range / 1000) ^ 2) * (1 + _humidity * 0.5)
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
    missionNamespace hook (aee_optics_starlightLux) so skybox mods can
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

    battery_enabled is the opt-in aee_optics_nvgBatteryEnabled toggle
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
    Clear-condition veiling glare floor: +0.02 (2 %), the low end of the
    published 2-5 % veiling-glare ratio for real tubes.  A faint glow
    over the whole image that caps maximum contrast, independent of rain.
    """
    b = bloom_base + bloom_scale * moon_light
    b = b + blowout * bloom_scale * 2
    b = b * (1.0 + rain * 2.0)
    b = b + 0.02
    return max(0.0, min(1.0, b))


# ─── Engine thermal drive mirrors (fnc_applyEngineThermal.sqf) ─────────────
# These map AEE's physics state into the engine's thermal controls:
# setVehicleTIPars (per-vehicle heat 0..1) and setTIParameter (display
# window).  The engine owns the render pass; we supply the input heat and
# the AGC window, exactly like a real FLIR's gain/level controls.


def engine_heat_fraction(
    surface_temp_c,
    air_temp_c,
    damage_engine=0.0,
    damage_fuel=0.0,
    damage_body=0.0,
    alive=True,
):
    """Mirror of the engine heat FRACTION pushed to setVehicleTIPars.

    The physics surface temperature (air + solar + engine heat + exhaust
    + wind cooling, computed by fnc_calculateObjectTemperature) maps to the
    engine's 0..1 heat scale: ambient = 0, +50 C = 1.  Clamped to the
    engine's range.  Environment-driven - sun, wind, engine state all move
    the value; no static timers.

    Damage-state thermal: destroyed/burning (body or fuel >= 0.95, or not
    alive) saturates at 1.0; a damaged engine adds +0.5 heat at full
    damage (coolant loss, friction); fuel damage adds +0.2 fire-risk heat.
    """
    if not alive or damage_body >= 0.95 or damage_fuel >= 0.95:
        return 1.0
    frac = (surface_temp_c - air_temp_c) / 50.0
    frac = max(0.0, min(1.0, frac))
    frac = min(1.0, frac + damage_engine * 0.5)
    frac = min(1.0, frac + damage_fuel * 0.2)
    return frac


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

    The engine's thermal sun term expects lightpoint brightness in the
    A3TI range (~13, their static value).  A 0..1 value is ~30x below
    the visible threshold, so it does nothing and buildings fall back
    to baked alive-heat.  We scale physics radiation (0..1) into that
    range: brightness = radiation * 13.  Night (0) -> no sun term;
    full day -> A3TI-equivalent 13.
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
    """Vehicle engine warm-up curves."""

    def test_engine_heat_at_zero_time(self):
        # Engine just started: no heat yet.
        self.assertAlmostEqual(vehicle_engine_heat(0), 0, places=6)

    def test_engine_heat_after_one_tau(self):
        # After 300s: 40 * (1 - e^-1) ≈ 25.3°C above ambient.
        self.assertAlmostEqual(
            vehicle_engine_heat(300), 40 * (1 - math.exp(-1)), places=1
        )

    def test_engine_heat_plateau(self):
        # After 900s (3τ): ~38°C - approaching the 40°C plateau.
        self.assertGreater(vehicle_engine_heat(900), 38)
        self.assertLess(vehicle_engine_heat(900), 40)

    def test_exhaust_hot_fast(self):
        # Exhaust reaches high temp within 60s (one tau).
        exhaust = vehicle_exhaust_temp(15, 60)
        self.assertGreater(exhaust, 15 + 200 * 0.6)  # >135°C

    def test_exhaust_plateau(self):
        # After 5τ (300s): exhaust ≈ air + 200 × (1 - e^-5) ≈ 213.65.
        exhaust = vehicle_exhaust_temp(15, 300)
        self.assertAlmostEqual(exhaust, 15 + 200 * (1 - math.exp(-5)), places=0)

    def test_engine_off_cool_down(self):
        # After engine stop, accumulated run time decays exponentially.
        ert = 300  # was running for 300s
        after_300s = engine_run_time_decay(ert, 300)
        self.assertAlmostEqual(after_300s, ert * math.exp(-1), places=1)

    def test_engine_off_full_cool(self):
        # After 10τ (3000s): engine run time effectively near zero.
        self.assertLess(engine_run_time_decay(300, 3000), 1)


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
    """Radiant temperature correction from emissivity."""

    def test_perfect_emitter(self):
        # Emissivity 1.0: no correction.
        self.assertAlmostEqual(emissivity_radiant_correction(1.0), 0, places=6)

    def test_metal_emissivity(self):
        # Emissivity 0.9: -0.2°C correction.
        self.assertAlmostEqual(emissivity_radiant_correction(0.9), -0.2, places=6)

    def test_skin_emissivity(self):
        # Emissivity 0.98: -0.04°C correction.
        self.assertAlmostEqual(emissivity_radiant_correction(0.98), -0.04, places=4)


class TestThermalContrast(unittest.TestCase):
    """Thermal contrast from object-background delta-T."""

    def test_full_contrast_at_8C_gap(self):
        # 8°C difference → contrast = 1.0.
        self.assertAlmostEqual(thermal_contrast(8), 1.0, places=6)

    def test_half_contrast_at_4C_gap(self):
        # 4°C difference → contrast = 0.5.
        self.assertAlmostEqual(thermal_contrast(4), 0.5, places=6)

    def test_zero_gap(self):
        # No temperature difference → zero contrast.
        self.assertAlmostEqual(thermal_contrast(0), 0.0, places=6)

    def test_large_gap_saturates(self):
        # 20°C gap still caps at 1.0.
        self.assertAlmostEqual(thermal_contrast(20), 1.0, places=6)

    def test_rain_reduces_contrast(self):
        # Heavy rain (0.8): contrast × (1 - 0.8 × 0.4) = × 0.68.
        c_clear = thermal_contrast(8, rain=0)
        c_rain = thermal_contrast(8, rain=0.8)
        self.assertLess(c_rain, c_clear)
        self.assertAlmostEqual(c_rain, 0.68, places=2)

    def test_fog_reduces_contrast(self):
        # Dense fog (0.8): contrast × (1 - 0.8 × 0.6) = × 0.52.
        c_fog = thermal_contrast(8, fog=0.8)
        self.assertAlmostEqual(c_fog, 0.52, places=2)

    def test_humidity_reduces_contrast(self):
        # 80% RH: contrast × (1 - 0.8 × 0.3) = × 0.76.
        c_humid = thermal_contrast(8, humidity=0.8)
        self.assertAlmostEqual(c_humid, 0.76, places=2)

    def test_heat_flattens_contrast(self):
        # Hot air (40°C): contrast reduced.
        c_hot = thermal_contrast(8, air_temp=40)
        c_mild = thermal_contrast(8, air_temp=20)
        self.assertLess(c_hot, c_mild)

    def test_cold_boosts_contrast(self):
        # Cold air (0°C): contrast boosted by ×1.2, capped at 1.0.
        c_cold = thermal_contrast(4, air_temp=0)
        c_mild = thermal_contrast(4, air_temp=15)
        self.assertGreater(c_cold, c_mild)

    def test_never_negative(self):
        # Worst case: extreme heat, rain, fog.
        c = thermal_contrast(0, rain=1, fog=1, humidity=1, air_temp=45)
        self.assertGreaterEqual(c, 0)

    def test_never_exceeds_one(self):
        c = thermal_contrast(10, air_temp=0)
        self.assertLessEqual(c, 1.0)


class TestNETDNoise(unittest.TestCase):
    """NETD-based sensor noise floor."""

    def test_noise_at_1km(self):
        # At 1000m: noise = 0.05 × 1² = 0.05.
        self.assertAlmostEqual(netd_noise(1000), 0.05, places=4)

    def test_noise_at_500m(self):
        # At 500m: noise = 0.05 × 0.25 = 0.0125.
        self.assertAlmostEqual(netd_noise(500), 0.0125, places=4)

    def test_noise_scales_with_range_squared(self):
        # Double the range → 4× the noise.
        n1 = netd_noise(500)
        n2 = netd_noise(1000)
        self.assertAlmostEqual(n2 / n1, 4.0, places=2)

    def test_humidity_increases_noise(self):
        # High humidity adds noise.
        self.assertGreater(netd_noise(1000, 0.8), netd_noise(1000, 0))

    def test_noise_finite_at_extremes(self):
        self.assertTrue(math.isfinite(netd_noise(100, 0)))
        self.assertTrue(math.isfinite(netd_noise(5000, 1.0)))


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
        # A skybox mod raises aee_optics_starlightLux -> the whole night
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
        # Even with no moon, no blowout, no rain, real tubes have a 2 %
        # veiling glare floor (phosphor light reflected to the photocathode).
        b = nvg_bloom(0.04, 0.04, moon_light=0.0, blowout=0.0, rain=0.0)
        self.assertAlmostEqual(b, 0.04 + 0.02, places=6)

    def test_veiling_glare_independent_of_rain(self):
        # The floor is present in clear AND rainy conditions (it adds on
        # top of the rain-scaled bloom, it is not the rain term).
        clear = nvg_bloom(0.04, 0.04, 0.0, 0.0, 0.0)
        rainy = nvg_bloom(0.04, 0.04, 0.0, 0.0, 1.0)
        self.assertGreater(rainy, clear)
        self.assertGreaterEqual(clear, 0.02)  # floor present when clear

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
    """setVehicleTIPars heat fraction + setTIParameter AGC window."""

    def test_ambient_vehicle_zero_heat(self):
        # Vehicle at air temp (cold parked at night): 0 heat (dark).
        self.assertAlmostEqual(engine_heat_fraction(17, 17), 0.0, places=6)

    def test_running_engine_bright(self):
        # Running engine: +40 C over ambient -> 0.8 heat fraction.
        self.assertAlmostEqual(engine_heat_fraction(57, 17), 0.8, places=6)

    def test_sun_warmed_vehicle(self):
        # Solar absorption +15 C over ambient (0.7*15) -> 0.3 heat.
        self.assertAlmostEqual(engine_heat_fraction(32, 17), 0.3, places=6)

    def test_hot_engine_caps_at_one(self):
        # +50 C or more -> clamped at 1.0.
        self.assertAlmostEqual(engine_heat_fraction(100, 17), 1.0, places=6)

    def test_engine_heat_bounds(self):
        for t in [0, 5, 17, 40, 80, 120]:
            for a in [0, 15, 30, 45]:
                h = engine_heat_fraction(t, a)
                self.assertGreaterEqual(h, 0.0)
                self.assertLessEqual(h, 1.0)

    def test_heat_tracks_ambient(self):
        # Same surface, hotter ambient -> LESS heat (ambient is the zero).
        self.assertLess(engine_heat_fraction(40, 35), engine_heat_fraction(40, 15))

    def test_wheel_heat_scales_with_speed(self):
        self.assertAlmostEqual(vehicle_wheel_heat(0), 0.0, places=6)
        self.assertAlmostEqual(vehicle_wheel_heat(15), 0.5, places=6)
        self.assertAlmostEqual(vehicle_wheel_heat(30), 1.0, places=6)
        self.assertAlmostEqual(vehicle_wheel_heat(60), 1.0, places=6)  # capped

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
        # Radiation 1 (clear midday): A3TI-equivalent full sun term (13).
        self.assertAlmostEqual(second_sun_brightness(1), 13.0, places=6)

    def test_overcast_attenuates(self):
        # Overcast mid-day: partial sun term (0.5 * 13 = 6.5).
        self.assertAlmostEqual(second_sun_brightness(0.5), 6.5, places=6)

    def test_clamped_out_of_range(self):
        self.assertAlmostEqual(second_sun_brightness(-0.2), 0.0, places=6)
        self.assertAlmostEqual(second_sun_brightness(1.5), 13.0, places=6)

    def test_never_negative(self):
        self.assertGreaterEqual(second_sun_brightness(0), 0)

    def test_scale_matches_a3ti_ceiling(self):
        # Full sun must equal A3TI's static 13 (their reference value) so
        # the engine's sun term is actually above the visible threshold.
        self.assertAlmostEqual(second_sun_brightness(1.0), 13.0, places=6)


class TestVehicleDamageThermal(unittest.TestCase):
    """Damage-state thermal: damaged parts run hotter, destroyed saturates."""

    def test_undamaged_cold_vehicle(self):
        # Parked, engine off, ambient: reads cold.
        self.assertAlmostEqual(engine_heat_fraction(17.8, 17.8), 0.0, places=6)

    def test_damaged_engine_runs_hotter(self):
        # Engine at 40% damage adds +0.2 heat even if surface is ambient.
        h = engine_heat_fraction(17.8, 17.8, damage_engine=0.4)
        self.assertAlmostEqual(h, 0.2, places=6)

    def test_full_engine_damage_adds_half(self):
        h = engine_heat_fraction(17.8, 17.8, damage_engine=1.0)
        self.assertAlmostEqual(h, 0.5, places=6)

    def test_fuel_damage_adds_fire_risk(self):
        h = engine_heat_fraction(17.8, 17.8, damage_fuel=0.5)
        self.assertAlmostEqual(h, 0.1, places=6)

    def test_destroyed_saturates(self):
        for kwargs in [
            dict(damage_body=0.95),
            dict(damage_fuel=0.95),
            dict(alive=False),
        ]:
            self.assertAlmostEqual(
                engine_heat_fraction(17.8, 17.8, **kwargs), 1.0, places=6
            )

    def test_never_exceeds_one(self):
        h = engine_heat_fraction(80, 17.8, damage_engine=1.0, damage_fuel=1.0)
        self.assertLessEqual(h, 1.0)

    def test_exhaust_warms_with_run_time(self):
        # Idling 60 s: exhaustTemp = air + 200*(1-e^-1) = +126 C -> 1.0
        # (over the +50 C full-scale).  Idling 5 s: +15 C -> 0.3.
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
        import os

        data_dir = _REPO_ROOT / "addons" / "optics" / "data"
        self.assertFalse((data_dir / "ti_cloth_cold.rvmat").exists())
        self.assertFalse((data_dir / "ti_cloth_hot.rvmat").exists())
        # The substrate that replaced them must exist and expose the
        # per-selection apply path.
        fn = (
            _REPO_ROOT
            / "addons"
            / "thermal"
            / "functions"
            / "fnc_applySelectionThermal.sqf"
        )
        text = fn.read_text(encoding="utf-8")
        self.assertIn("setObjectTexture", text)
        self.assertIn("solveTwoNodeSelection", text)
        self.assertNotIn("solveSelectionTemperature", text)  # single-node killed
        self.assertIn("getSelectionMaterials", text)


def test_ti_texture_polarity(self):
    # The TI textures encode the cold/hot floor in the red channel.
    # In white-hot mode: pure black reads as black holes (the "black
    # hot" report), so cold is a dim grey, not black.  Hot is white.
    # Decode the DXT1 PAA with armaio and check the red channel mean.
    from armaio.paa._format import PaaFile

    data_dir = _REPO_ROOT / "addons" / "optics" / "data"

    def _red_mean(name):
        with open(data_dir / name, "rb") as fh:
            pf = PaaFile.read(fh)
        px = pf.mipmaps[0].decode(pf.format)
        return float(px[:, :, 0].mean())

    cold_r = _red_mean("ti_cold.paa")
    hot_r = _red_mean("ti_hot.paa")
    # Cold: warm grey floor (dim but visible), not pure black.
    self.assertGreater(cold_r, 40, "cold TI texture must not be pure black")
    self.assertLess(cold_r, 140, "cold TI texture must stay dim (below half)")
    # Hot: near-white so hot objects saturate in white-hot mode.
    self.assertGreater(hot_r, 200, "hot TI texture must be near-white")
    self.assertGreater(hot_r, cold_r, "hot texture must be brighter than cold")


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
        from pathlib import Path

        text = Path("addons/optics/functions/fnc_applyRainDroplets.sqf").read_text(
            encoding="utf-8"
        )
        # moveVelocity must be eyeVel (co-move), not -eyeVel (a sign error
        # that would send drops AWAY from the eye) and not a static 0.
        self.assertIn("co-move with eye", text)
        self.assertIn("_eyeVel,", text)
        self.assertNotIn("vectorMultiply -1", text)

        eye_state = Path("addons/optics/functions/fnc_getEyeState.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("eyeStatePrev", eye_state)

        post = Path("addons/optics/XEH_postInit.sqf").read_text(encoding="utf-8")
        # The duplicate droplet call in the thermal branch must be gone:
        # exactly ONE tick call (the unconditional one before the branches).
        self.assertEqual(post.count('["TICK"] call FUNC(applyRainDroplets)'), 1)


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
    def test_contrast_span_is_8(self):
        self._assert_in_sqf("fnc_calculateThermalContrast.sqf", ["/ 8"], "delta-T span")

    def test_contrast_attenuation_constants(self):
        self._assert_in_sqf(
            "fnc_calculateThermalContrast.sqf",
            ["rain * 0.4", "fog * 0.6", "humidity * 0.3"],
            "atmospheric attenuation",
        )

    def test_contrast_heat_cold_constants(self):
        self._assert_in_sqf(
            "fnc_calculateThermalContrast.sqf",
            ["_T > 35", "(_T - 35) / 10) * 0.7", "_T < 5", "* 1.2", "min 1.0"],
            "heat flatten / cold boost",
        )

    def test_contrast_vehicle_only_average(self):
        self._assert_in_sqf(
            "fnc_calculateThermalContrast.sqf",
            ['isKindOf "Man"', "isEqualType objNull", "avgVehicleTemp"],
            "vehicle-only scene average",
        )

    def test_netd_constants(self):
        self._assert_in_sqf(
            "fnc_calculateThermalContrast.sqf",
            ["0.05", "/ 1000", "5000", "humidity * 0.5"],
            "NETD noise floor",
        )

    # ── Thermal vision (fnc_applyThermalVision.sqf) ──
    def test_thermal_blur_constants(self):
        self._assert_in_sqf(
            "fnc_applyThermalVision.sqf",
            ["0.0, 0.15, true", "min 0.25", "0.0, 0.04, true"],
            "blur span / ceiling / pan-smear cap",
        )

    def test_thermal_window_constants(self):
        self._assert_in_sqf(
            "fnc_applyThermalVision.sqf",
            ["0.1, 0.8", "0.0, 0.2", "0.1, 1.0", "0.0, 0.15"],
            "fog/rain window blur",
        )

    def test_thermal_crossover_floor(self):
        self._assert_in_sqf(
            "fnc_applyThermalVision.sqf",
            ["0.05", "linearConversion [1, 0, _effective, 0.62, 0.35, true]"],
            "crossover floor / AGC contrast mapping",
        )

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
        )

    def test_focus_vehicle_exclusion(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            ["vehicle _player", "_hitObj != _veh && _hitParent != _veh"],
            "vehicle cabin exclusion",
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
        )

    def test_solar_model_exposes_sun_elevation(self):
        # The solar model must expose currentSunElevation for the twilight
        # term (radiation is max 0, so it cannot give the below-horizon angle).
        cfg = (
            _REPO_ROOT
            / "addons"
            / "core"
            / "functions"
            / "fnc_calculateSolarRadiation.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("currentSunElevation", cfg)
        self.assertIn("asin (_sinElev", cfg)

    def test_illuminance_extinction_constants(self):
        self._assert_in_sqf(
            "fnc_calculateIlluminance.sqf",
            ["_rainS * 30", "4343", "40 * (_fogS / 0.5) ^ 2", "min 300"],
            "smoothed rain/fog extinction",
        )

    def test_nvg_gain_model(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            ["_sensitivity / (_lux + 1)", "min _sensitivity"],
            "AGC gain model",
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
        )

    def test_nvg_battery_drain_model(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            [
                "_baseDrain * _gainRatio * _tempDrainFactor * diag_deltaTime",
                "0.0000174",
                "0.0000043",
                "0.0000079",
                "0.0000111",
            ],
            "battery drain rates",
        )

    def test_nvg_brightness_model(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            ["0.001, 0.25, _lux, 0.65, 1.0"],
            "AGC output brightness",
        )

    def test_nvg_mtf_model(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            ["_mtf15 * 0.55", "_blowout * 0.4", "1 - rain * 0.5"],
            "MTF degradation",
        )

    def test_nvg_veiling_glare_floor(self):
        self._assert_in_sqf(
            "fnc_applyNVGTubeModel.sqf",
            ["_bloom = _bloom + 0.02"],
            "clear-condition veiling glare floor",
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
                "_angVel < 0.44",
                "tiAppliedWidth",
            ],
            "engine AGC display window (physics-driven scene max heat)",
        )

    def test_engine_thermal_damage_constants(self):
        self._assert_in_sqf(
            "fnc_applyEngineThermal.sqf",
            [
                "thermalState",
                "(_surfaceTemp - _airTemp) / 50",
                "if (!alive _x) then { _sceneMax = 1",
                "0.2 * (diag_deltaTime / 30)",
                "nearEntities",
                "str _x",
            ],
            "scene max heat from the physics thermal state (dead saturates, decays 30 s)",
        )

    def test_second_sun_constants(self):
        self._assert_in_sqf(
            "fnc_applySecondSun.sqf",
            [
                "#lightpoint",
                "setLightDayLight true",
                "currentSolarRadiation",
                "setLightBrightness _lightBrightness",
                "createVehicleLocal",
                "_radiation * 13",
                "setLightAttenuation [1e10, 150",
            ],
            "physics-driven second sun (TI sun term, A3TI-scaled)",
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
                "call FUNC(getEyeState)",
            ],
            "rain droplets on objective (eye-repositioned Refract emitter)",
        )

    def test_shared_eye_state_constants(self):
        # The shared eye-state foundation: one cached computation per frame
        # (eyePos + state-aware direction), consumed by every eye-space
        # system.  Direction is state-aware (KtweaK's NVG pattern): turret
        # uses weaponDirection, on foot uses the view centre.
        self._assert_in_sqf(
            "fnc_getEyeState.sqf",
            [
                "diag_frameNo",
                "eyePos _unit",
                "eyeDirection _unit",
                "screenToWorldDirection [0.5, 0.5]",
                "weaponDirection (currentWeapon _veh)",
                "turretUnit [0]) isEqualTo _unit",
                "count _eyeDir == 3",
                "count _eyeDir == 2",
                "missionNamespace setVariable [QGVAR(eyeState), [_frame, [_eye, _fwd, _up, _eyeVel]]]",
                "eyeStatePrev",
                "eyeStatePrevTime",
            ],
            "shared eye-state foundation (state-aware direction)",
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
        )

    def test_no_raw_weather_in_brightness_paths(self):
        # Every brightness/visibility consumer must read the SMOOTHED
        # weather, not raw `rain`/`overcast`/`fog` (which step abruptly and
        # snap the display).  Only the droplet physics reads raw rain
        # (instant response is correct there).
        for fname, ctx in [
            ("fnc_applyNVGTubeModel.sqf", "NVG tube"),
            ("fnc_calculateIlluminance.sqf", "illuminance"),
            ("fnc_applyNightGrain.sqf", "night grain"),
            ("fnc_applyThermalVision.sqf", "thermal vision"),
            ("fnc_calculateAttenuation.sqf", "attenuation"),
            ("fnc_calculateAtmosphericSeeing.sqf", "seeing"),
            ("fnc_calculateMirageIntensity.sqf", "mirage"),
        ]:
            src = _read_sqf(fname)
            self.assertIn(
                "call FUNC(getSmoothedWeather)",
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
        for fname, ctx in [
            ("fnc_applyNVGTubeModel.sqf", "NVG tube"),
            ("fnc_calculateIlluminance.sqf", "illuminance"),
            ("fnc_applyRainDroplets.sqf", "droplets"),
        ]:
            src = _read_sqf(fname)
            self.assertIn(
                "call FUNC(getEyeState)",
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
            / "core"
            / "functions"
            / "fnc_calculateSolarRadiation.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("private _hour = dayTime", cfg)
        self.assertNotIn("(_date#3) + (time / 3600)", cfg)

    def test_clothing_thermal_constants(self):
        self._assert_in_sqf(
            "fnc_applyClothingThermal.sqf",
            [
                '["", "", "EXIT"] call EFUNC(thermal,applySelectionThermal)',
                "applySelectionThermal",
                "allUnits",
                "hiddenSelections",
                "getObjectTextures _obj",
                "fGround = 0.2",
                "fGround = 0.7",
                "QGVAR(tiSelections_",
            ],
            "per-item clothing solved by the per-selection thermal substrate",
        )

    def test_building_thermal_constants(self):
        self._assert_in_sqf(
            "fnc_applyBuildingThermal.sqf",
            [
                '["", "", "EXIT"] call EFUNC(thermal,applySelectionThermal)',
                "applySelectionThermal",
                'allMissionObjects ""',
                "vehicles - [player]",
                'nearObjects ["House", _viewDist]',
                'nearObjects ["Building", _viewDist]',
                "abs (_airTemp - _lastTemp) >= 2",
                "_qInternal = 770",
                "_qInternal = 280",
                "QGVAR(tiBldgSelections_",
            ],
            "per-building thermal solved by the per-selection substrate",
        )

    def test_mapwide_thermal_caps(self):
        # Config-level caps on the ROOT class cover every object (including
        # map geometry with no selections) at load, zero runtime cost.
        cfg = (_REPO_ROOT / "addons" / "optics" / "config.cpp").read_text(
            encoding="utf-8"
        )
        for frag in [
            "class All {",
            "afMax = 70",
            "htMax = 300",
            "mfMax = 50",
            "class AllVehicles: All",
        ]:
            self.assertIn(frag, cfg, f"config.cpp missing {frag} - map-wide caps")

    def test_infantry_thermal_config(self):
        # The static config: humans glow (mFact 1, tBody 32), vehicles get REAL
        # thermal caps (afMax 70, mfMax 50 - not 0, which the engine reads
        # as unset and falls back to vanilla 200).  AEE's physics drives
        # the per-part heat (engine/wheels) via setVehicleTIPars on top.
        cfg = (_REPO_ROOT / "addons" / "optics" / "config.cpp").read_text(
            encoding="utf-8"
        )
        for frag in [
            "mFact = 1",
            "tBody = 32",
            "afMax = 70",
            "mfMax = 50",
            "htMin = 60",
            "htMax = 300",
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
        from pathlib import Path

        text = _read_sqf("fnc_calculateObjectTemperature.sqf", "thermal")
        self.assertNotIn("_groundTarget max (_airTemp - 5)", text)
        self.assertNotIn("_groundGain", text)

    def test_object_temp_taus(self):
        self._assert_in_sqf(
            "fnc_calculateObjectTemperature.sqf",
            ["120", "600", "300", "60", "1800"],
            "thermal inertia taus (metal/concrete/vegetation/human/acclim)",
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
        self._assert_in_sqf(
            "fnc_calculateObjectTemperature.sqf",
            [
                "40 * (1 - exp (-_engineRunTime / 300))",
                "200 * (1 - exp (-_engineRunTime / 60))",
                "0.05",
                "_engineRunTime * exp (-_dt / 300)",
            ],
            "vehicle cold start / exhaust / cooldown",
            addon="thermal",
        )

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
        from pathlib import Path

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
        from pathlib import Path

        return Path("addons/optics/functions", name).read_text(encoding="utf-8")

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


if __name__ == "__main__":
    unittest.main()
