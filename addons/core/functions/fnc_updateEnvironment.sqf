#include "..\script_component.hpp"

params [["_posASL", [], [[]]]];

// Normalise the position: accept both [x, y, z] and a single-element
// wrapper [[x, y, z]] (the docker test edge-case phase passes the
// wrapped form).  Downstream callers expect a bare 3-element array.
if ((count _posASL) == 1 && {(_posASL select 0) isEqualType []}) then {
    _posASL = _posASL select 0;
};

if (!GVAR(enabled)) exitWith {};

// Multiplayer note: core atmospheric state (temperature, pressure, humidity,
// wind, density) is a deterministic function of position, mission time and
// engine weather — no randomness — so every machine computes identical
// values without publicVariable broadcast. Event state and visual FX
// (lightning direction, microburst gust, space-weather flares) use per-
// machine random rolls; divergence there is cosmetic only.
missionNamespace setVariable [QEGVAR(core,overcast), overcast];

// Real Weather mode: when aee_core_realWeatherActive is set (by the
// RealWeather compat layer from weather.json), the simulation must NOT
// recompute temperature/pressure/humidity — it would overwrite the real
// data. Derived effects (ground, fog, foliage, FX) still run below.
private _realWeather = missionNamespace getVariable [QEGVAR(core,realWeatherActive), false];

if (!_realWeather) then {
    // Deterministic weather progression seed — drives slow weather-quality drift
    [] call FUNC(calculateSeededWeatherProgression);

    private _month = date select 1;

    // Per-position biome detection — updates aee_core_biome based on
    // surface type, latitude, and elevation at the player's position.
    [_posASL] call EFUNC(environmental,updateBiomePosition);
    private _biome = GVAR(biome);

    // Pass explicit position to update functions so they use the same
    // location rather than each independently querying CBA_fnc_currentUnit.
    [_biome, _month, _posASL] call EFUNC(thermal,updateTemperature);
    [_biome, _month, _posASL] call EFUNC(atmos,updatePressure);
    [] call EFUNC(environmental,calculateQNH);
    [] call EFUNC(physiology,calculateHypoxia);
    [_biome, _month, _posASL] call EFUNC(atmos,updateHumidity);
    [] call FUNC(updateSoilMoisture);
    [] call EFUNC(atmos,calculatePrecipitationPhase);
    [] call EFUNC(atmos,calculateHaze);
    [] call EFUNC(environmental,calculateSurfaceWetness);

    [] call EFUNC(ballistics,calculateAirDensity);
};

// Wind runs in BOTH modes.  updateWind reads the engine wind command and
// publishes the computed vector and gusts to the shared state and the
// engine (setWind).  Real-weather mode replaces temperature/pressure/
// humidity but must not freeze the wind field, so it is not gated.
[] call EFUNC(atmos,updateWind);
if (GVAR(fxEnabled)) then {
    [] call EFUNC(fx,applyWindNoise);
};

// ─── Derived effects (ground, foliage, sound, fog) ─────────────────────────
[_posASL] call EFUNC(mobility,updateGroundState);

// Apply module precipitation bias — scale rain contribution to accumulation
private _modulePrecip = missionNamespace getVariable [QGVAR(modulePrecipBias), 1];
if (_modulePrecip != 1) then {
    private _rainAccum = missionNamespace getVariable [QGVAR(rainAccum), 0];
    // updateGroundState applied: rainAccum = rainAccum*0.97 + rain*0.03
    // Adjust by adding the scaled delta: rain*0.03*(bias-1)
    _rainAccum = _rainAccum + (rain * 0.03 * (_modulePrecip - 1));
    missionNamespace setVariable [QGVAR(rainAccum), _rainAccum];
};

[] call EFUNC(environmental,updateSeasonalFoliage);
if (GVAR(hydrologyEnabled)) then { call EFUNC(environmental,calculateFreezeThawCycling); };
[] call EFUNC(environmental,updateSoundPropagation);
[] call EFUNC(atmos,updateFog);
[] call EFUNC(environmental,calculateFogBaseAltitude);

// ─── Thermal / Physiological ───────────────────────────────────────────────
[] call EFUNC(thermal,calculateWBGT);
[] call EFUNC(thermal,calculateHeatIndex);
[] call EFUNC(thermal,calculateHypothermiaRisk);
[] call EFUNC(thermal,calculateClothingInsulation);
[] call EFUNC(thermal,calculateFreezingRain);
    [] call EFUNC(thermal,calculateWaterTemperature);
    [] call EFUNC(environmental,calculateFrostOnWindscreens);
[] call EFUNC(thermal,calculateObjectTemperature);
if (GVAR(physiologyEnabled)) then {
    [] call EFUNC(physiology,calculateUVIndex);
    [] call EFUNC(physiology,calculateBatteryTemperatureDerating);
    [] call EFUNC(physiology,calculateDehydrationRisk);
    [] call EFUNC(physiology,calculateAltitudeAcclimatization);
    // Cross-sensitivity runs after both accumulators have their current
    // values.  calculateHypoxia runs earlier in this tick (line 44), so
    // both raw risks are fresh here.  Neither accumulator reads its own
    // output risk, so writing the amplified value back is safe.
    [] call EFUNC(physiology,applyCrossSensitivity);
    // Fatigue/sleep state (Borbely two-process model) accumulates on the
    // same tick cadence.  Guards on fatigueEnabled internally.
    if (missionNamespace getVariable [QEGVAR(physiology,fatigueEnabled), true]) then {
        [] call EFUNC(physiology,updateFatigueState);
    };
};

// ─── Sensor / Optics ───────────────────────────────────────────────────────
// Shared illuminance layer: the engine's real scene light (getLightingAt)
// sampled at the player position.  Runs unconditionally so NVG, thermal,
// glare, and ballistics all consume one authoritative lux value.
[_posASL] call EFUNC(optics,calculateIlluminance);
[] call EFUNC(optics,calculateThermalContrast);
[] call EFUNC(optics,calculateAttenuation);
if (GVAR(opticsEnabled)) then {
    [] call EFUNC(optics,calculateMirageIntensity);
    [] call EFUNC(optics,calculateSmokePersistence);
    [] call EFUNC(optics,calculatePrecipitationVisibility);
    [] call EFUNC(optics,calculateSolarGlare);
    [] call EFUNC(thermal,calculateThermalCrossover);
    [] call EFUNC(optics,calculateDewOnOptics);
    [] call EFUNC(optics,calculateSnowBlindness);
};

// ─── Mobility / Operations ─────────────────────────────────────────────────
[] call EFUNC(mobility,calculateTraction);
[] call EFUNC(mobility,calculateHelicopterLift);
[] call EFUNC(environmental,calculateFireSpreadRisk);
if (GVAR(enginePowerDegradationEnabled)) then {
    [_posASL] call EFUNC(mobility,calculateEnginePower);
};

// ─── Ballistics ─────────────────────────────────────────────────────────────
    [] call EFUNC(ballistics,calculateCrosswindBallistics);
    [_posASL] call EFUNC(ballistics,calculateCoriolisDeflection);
// Ammo temp is per-weapon per-unit in ACE3 — stub retained for future

// ─── Radio / Comms ──────────────────────────────────────────────────────────
if (GVAR(radioPropagationEnabled)) then {
    [] call EFUNC(radio,calculateRadioPropagation);
};

// ─── Surface Hydrology ──────────────────────────────────────────────────────
if (GVAR(hydrologyEnabled)) then {
    [] call EFUNC(environmental,calculateSnowAccumulation);
    [] call EFUNC(environmental,calculateFlashFloodRisk);
    [] call EFUNC(environmental,calculateDustSuppression);
};
[] call EFUNC(mobility,calculateRouteDegradation);
[] call EFUNC(mobility,calculateSoilBearingStrength);
if (GVAR(fxEnabled)) then {
    [] call EFUNC(fx,applyVehicleDust);
    [] call EFUNC(fx,applyAtmosphericDust);
};

// ─── Atmospheric events ────────────────────────────────────────────────────
if (GVAR(atmosphericEventsEnabled)) then {
    [] call EFUNC(atmos,calculateLightning);
    [] call EFUNC(environmental,calculateSevereWeather);
    [] call EFUNC(atmos,calculateMicroburst);
    [] call EFUNC(atmos,calculateTurbulence);
    [_posASL] call EFUNC(environmental,calculateAvalancheRisk);
    [] call EFUNC(atmos,calculateAirframeIcing);
    [] call EFUNC(optics,calculateAtmosphericSeeing);

    // ── FX triggers (visual/audio events also require FX enabled) ───────
    if (GVAR(fxEnabled)) then {
        [] call EFUNC(fx,calculateLightningStrikeEffects);
        [] call EFUNC(fx,triggerLightning);
        [] call EFUNC(fx,triggerSevereWeatherFX);
    };
};

// ─── Environmental / Seasonal ──────────────────────────────────────────────
[] call EFUNC(mobility,calculateRiverWaterLevel);
[] call EFUNC(environmental,calculateCropState);
[] call EFUNC(atmos,calculateCloudDevelopment);
[] call EFUNC(atmos,calculatePressureTrend);
[] call EFUNC(environmental,calculateLunarIllumination);

// ─── Night classification & star visibility (after lunar phase computed) ──
// DEF Stan 61-027 night zones depend on sun elevation and moon phase.
// calculateLunarIllumination stores moonPhase; sunElevation is set by
// the solar model.  classifyNight must run after both are available.
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), -90];
private _moonPhase = missionNamespace getVariable [QEGVAR(environmental,lunarPhase), 0];
[_sunElev, _moonPhase] call EFUNC(optics,classifyNight);
private _ambientLux = missionNamespace getVariable [QEGVAR(optics,ambientLux), 0.001];
private _seeing = missionNamespace getVariable [QEGVAR(optics,atmosphericSeeing), 0.5];
[_ambientLux, _seeing] call EFUNC(optics,calculateLimitingMagnitude);
private _posASL2D = if (count _posASL >= 3) then { [_posASL select 0, _posASL select 1, 0] } else { [0, 0, 0] };
[_posASL2D, date] call EFUNC(optics,getStarCatalog);
if (GVAR(maritimeEnabled)) then {
    [] call EFUNC(maritime,calculateTidalPrediction);
};
[] call EFUNC(atmos,calculateCloudCeiling);
[] call EFUNC(environmental,calculateSpaceWeather);
[] call EFUNC(radio,calculateIonosphericAbsorption);
if (GVAR(environmentalEnabled)) then {
    [] call EFUNC(environmental,calculateBiologicalAmbient);
    [] call EFUNC(environmental,calculateCBRNPersistence);
};
if (GVAR(physiologyEnabled)) then {
    [] call EFUNC(physiology,calculateScentDispersion);
};
if (GVAR(maritimeEnabled)) then {
    [] call EFUNC(maritime,calculateSeaState);
    [] call EFUNC(maritime,calculateCompassDeviation);
};

// ─── Visual / Gameplay ────────────────────────────────────────────────────
if (GVAR(opticsEnabled)) then {
    [] call EFUNC(optics,calculateRainOnOptics);
    [] call EFUNC(optics,calculateVehicleHeatShimmer);
};
[] call EFUNC(mobility,calculateMudAccretion);

// ─── Post-Process Effects & HUD ─────────────────────────────────────────
[] call EFUNC(optics,applyRainOnOpticsFX);
[] call EFUNC(optics,applyHeatShimmerFX);
[] call EFUNC(optics,applyNightGrain);
[] call EFUNC(optics,applyMirageFX);
[] call EFUNC(optics,applySolarGlareFX);
[] call EFUNC(optics,applySnowBlindnessFX);
[] call EFUNC(optics,applyDewOnOpticsFX);
[] call EFUNC(optics,applyAtmosphericSeeingFX);
[] call EFUNC(optics,managePostProcess);
if (GVAR(physiologyEnabled)) then {
    [] call EFUNC(physiology,applyHeatStressHUD);
};

// ─── Breath condensation ───────────────────────────────────────────────────
if (GVAR(fxEnabled)) then {
    [] call EFUNC(fx,applyBreathCondensation);
    [] call EFUNC(fx,applyRainVehicleSound);
    [] call EFUNC(fx,applyRainSurfaceDrops);
};

if (GVAR(diagnostic)) then {
    [] call FUNC(diagnostic);
};

// Notify CBA local event subscribers that the environment state refreshed.
// Subscribers read the aee_core_* mission variables rather than receiving
// state in the event payload (the tick publishes ~50 variables).
["AEE_WeatherUpdated"] call CBA_fnc_localEvent;
