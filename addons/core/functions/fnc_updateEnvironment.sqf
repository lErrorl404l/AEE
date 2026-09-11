#include "..\script_component.hpp"

params [["_posASL", [], [[]]]];

if (!GVAR(enabled)) exitWith {};

// Multiplayer note: core atmospheric state (temperature, pressure, humidity,
// wind, density) is a deterministic function of position, mission time and
// engine weather — no randomness — so every machine computes identical
// values without publicVariable broadcast. Event state and visual FX
// (lightning direction, microburst gust, space-weather flares) use per-
// machine random rolls; divergence there is cosmetic only.
missionNamespace setVariable [QEGVAR(core,overcast), overcast];

private _month = date select 1;

private _biome = GVAR(biome);
if (isNil "_biome" || _biome == "") then {
    [] call EFUNC(environmental,getBiome);
    _biome = GVAR(biome);
};

// Pass explicit position to update functions so they use the same
// location rather than each independently querying CBA_fnc_currentUnit.
[_biome, _month, _posASL] call EFUNC(thermal,updateTemperature);
[_biome, _month, _posASL] call EFUNC(atmos,updatePressure);
[_biome, _month, _posASL] call EFUNC(atmos,updateHumidity);
[] call EFUNC(atmos,updateWind);
[] call EFUNC(fx,applyWindNoise);

[] call EFUNC(ballistics,calculateAirDensity);

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

// ─── Thermal / Physiological ───────────────────────────────────────────────
[] call EFUNC(thermal,calculateHeatIndex);
[] call EFUNC(thermal,calculateHypothermiaRisk);
[] call EFUNC(thermal,calculateFreezingRain);
    [] call EFUNC(thermal,calculateWaterTemperature);
    [] call EFUNC(environmental,calculateFrostOnWindscreens);
[] call EFUNC(physiology,calculateUVIndex);
[] call EFUNC(physiology,calculateBatteryTemperatureDerating);
[] call EFUNC(physiology,calculateDehydrationRisk);
[] call EFUNC(physiology,calculateAltitudeAcclimatization);

// ─── Sensor / Optics ───────────────────────────────────────────────────────
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
[] call EFUNC(fx,applyVehicleDust);

// ─── Atmospheric events ────────────────────────────────────────────────────
if (GVAR(atmosphericEventsEnabled)) then {
    [] call EFUNC(atmos,calculateLightning);
    [] call EFUNC(environmental,calculateSevereWeather);
    [] call EFUNC(atmos,calculateMicroburst);
    [] call EFUNC(atmos,calculateTurbulence);
    [_posASL] call EFUNC(environmental,calculateAvalancheRisk);
    [] call EFUNC(atmos,calculateAirframeIcing);
    [] call EFUNC(optics,calculateAtmosphericSeeing);

    // ── FX triggers ────────────────────────────────────────────────────
    [] call EFUNC(fx,triggerLightning);
    [] call EFUNC(fx,triggerSevereWeatherFX);
};

// ─── Environmental / Seasonal ──────────────────────────────────────────────
[] call EFUNC(mobility,calculateRiverWaterLevel);
[] call EFUNC(environmental,calculateCropState);
[] call EFUNC(atmos,calculateCloudDevelopment);
[] call EFUNC(atmos,calculatePressureTrend);
[] call EFUNC(environmental,calculateLunarIllumination);
[] call EFUNC(maritime,calculateTidalPrediction);
[] call EFUNC(atmos,calculateCloudCeiling);
[] call EFUNC(environmental,calculateSpaceWeather);
if (GVAR(environmentalEnabled)) then {
    [] call EFUNC(environmental,calculateBiologicalAmbient);
    [] call EFUNC(physiology,calculateScentDispersion);
    [] call EFUNC(maritime,calculateSeaState);
    [] call EFUNC(maritime,calculateCompassDeviation);
    [] call EFUNC(environmental,calculateCBRNPersistence);
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
[] call EFUNC(physiology,applyHeatStressHUD);

// ─── Breath condensation ───────────────────────────────────────────────────
[] call EFUNC(fx,applyBreathCondensation);
[] call EFUNC(fx,applyRainVehicleSound);

if (GVAR(diagnostic)) then {
    [] call FUNC(diagnostic);
};
