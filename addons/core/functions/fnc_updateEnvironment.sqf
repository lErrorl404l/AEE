#include "..\script_component.hpp"
#include "\z\aee\addons\main\script_debug.hpp"

params [["_posASL", [], [[]]]];

// Normalise the position: accept both [x, y, z] and a single-element
// wrapper [[x, y, z]] (the docker test edge-case phase passes the
// wrapped form).  Downstream callers expect a bare 3-element array.
if ((count _posASL) == 1 && {(_posASL select 0) isEqualType []}) then {
    _posASL = _posASL select 0;
};

if (!GVAR(enabled)) exitWith {};

BEGIN_COUNTER(updateEnvironment);

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

// The ICAO reference altitude is the standard-atmosphere datum the
// derived models use.  Five consumers read EGVAR(core,referenceAltitude)
// (pressure, temperature lapse, helicopter lift, UV index, freezing rain)
// and nothing produced it: each read an undefined variable and fell back to
// its own default.  The setting is the producer, and 0 keeps the live
// terrain height, which is the behaviour those consumers expect.
if (GVAR(icaoReferenceAlt) != 0) then {
    missionNamespace setVariable [QEGVAR(core,referenceAltitude), GVAR(icaoReferenceAlt)];
} else {
    missionNamespace setVariable [
        QEGVAR(core,referenceAltitude),
        getTerrainHeightASL (_posASL select [0, 2])
    ];
};

if (!_realWeather) then {
    // Deterministic weather progression seed — drives slow weather-quality drift
    BEGIN_COUNTER(weatherProgression);
    [] call FUNC(calculateSeededWeatherProgression);
    END_COUNTER(weatherProgression);

    private _month = date select 1;

    // Per-position biome detection — updates aee_core_biome based on
    // surface type, latitude, and elevation at the player's position.
    BEGIN_COUNTER(biomePosition);
    if (GVAR(biomeEnabled)) then {
        [_posASL] call EFUNC(environmental,updateBiomePosition);
    };
    END_COUNTER(biomePosition);
    private _biome = GVAR(biome);

    // Pass explicit position to update functions so they use the same
    // location rather than each independently querying CBA_fnc_currentUnit.
    BEGIN_COUNTER(thermoAtmos);
    if (GVAR(tempLapseRateEnabled) || GVAR(tempDiurnalEnabled)) then {
        [_biome, _month, _posASL] call EFUNC(thermal,updateTemperature);
    };
    [_biome, _month, _posASL] call EFUNC(atmos,updatePressure);
    [] call EFUNC(environmental,calculateQNH);
    [] call EFUNC(physiology,calculateHypoxia);
    if (GVAR(humidityEnabled)) then {
        [_biome, _month, _posASL] call EFUNC(atmos,updateHumidity);
    };
    [] call FUNC(updateSoilMoisture);
    [] call EFUNC(atmos,calculatePrecipitationPhase);
    [] call EFUNC(atmos,calculateHaze);
    [] call EFUNC(environmental,calculateSurfaceWetness);
    END_COUNTER(thermoAtmos);

    if (GVAR(airDensityEnabled)) then {
        BEGIN_COUNTER(airDensity);
        [] call EFUNC(ballistics,calculateAirDensity);
        END_COUNTER(airDensity);
    };
};

// Wind runs in BOTH modes.  updateWind reads the engine wind command and
// publishes the computed vector and gusts to the shared state and the
// engine (setWind).  Real-weather mode replaces temperature/pressure/
// humidity but must not freeze the wind field, so it is not gated by
// realWeather, only by the wind switch itself.
if (GVAR(windEnabled)) then {
    [] call EFUNC(atmos,updateWind);
};
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
    BEGIN_COUNTER(physiology);
    if (missionNamespace getVariable [QEGVAR(physiology,fatigueEnabled), true]) then {
        [] call EFUNC(physiology,updateFatigueState);
    };
    // Shooter stability index from cold/heat/fatigue.  Reads the fatigue
    // state set above, so it runs after updateFatigueState on this tick.
    // Crosswind is NOT a stability factor: it deflects the round, not the
    // shooter (handled by the ballistics module).  Stored for the ACE3
    // sway factor and for external consumers.
    if (missionNamespace getVariable [QEGVAR(physiology,fatigueEnabled), true]
        && {missionNamespace getVariable [QEGVAR(physiology,stabilityEnabled), true]}) then {
        [] call EFUNC(physiology,calculateShooterStability);
    };
    // Cold-weather human performance (wind chill -> dexterity, frostbite
    // time, TB MED 508 category).  Reads the temperature + wind published
    // above, publishes the shared cold state the movement coupling and
    // weather report consume.  Gated internally by coldWeatherEnabled.
    [] call EFUNC(physiology,calculateColdWeatherPerformance);
    END_COUNTER(physiology);
};

// ─── Sensor / Optics ───────────────────────────────────────────────────────
// Shared illuminance layer: the engine's real scene light (getLightingAt)
// sampled at the player position.  Runs unconditionally so NVG, thermal,
// glare, and ballistics all consume one authoritative lux value.
// Space weather must run BEFORE the illuminance layer: the aurora
// intensity feeds the ambient lux the NVG chain consumes (issue #112).
BEGIN_COUNTER(optics);
[] call EFUNC(environmental,calculateSpaceWeather);
[_posASL] call EFUNC(core,calculateIlluminance);
// Engine camera aperture follows the illuminance model (issue #141).
[] call EFUNC(atmos,updateAperture);
[] call EFUNC(thermal,calculateThermalContrast);
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
END_COUNTER(optics);

// Vision-driven view distance (issue #138): client-only, applies the
// physics visibility state to the local view distance.  Runs at the tick
// cadence with a 500 m deadband + ramp, so 5 s is smooth.
if (missionNamespace getVariable [QEGVAR(optics,viewDistanceEnabled), true]) then {
    [] call EFUNC(optics,calculateViewDistance);
};

// ─── Mobility / Operations ─────────────────────────────────────────────────
BEGIN_COUNTER(mobility);
[] call EFUNC(mobility,calculateTraction);
[] call EFUNC(mobility,calculateHelicopterLift);
[] call EFUNC(environmental,calculateFireSpreadRisk);
if (GVAR(enginePowerDegradationEnabled)) then {
    [_posASL] call EFUNC(mobility,calculateEnginePower);
};
END_COUNTER(mobility);

// ─── Ballistics ─────────────────────────────────────────────────────────────
BEGIN_COUNTER(ballistics);
    [] call EFUNC(ballistics,calculateCrosswindBallistics);
    [_posASL] call EFUNC(ballistics,calculateCoriolisDeflection);
END_COUNTER(ballistics);

// ─── Radio / Comms ──────────────────────────────────────────────────────────
// Sea-surface temperature feeds the evaporation-duct model (issue #37);
// compute it before the propagation index reads it.
BEGIN_COUNTER(radio);
if (GVAR(radioPropagationEnabled)) then {
    if (GVAR(maritimeEnabled)) then {
        [] call EFUNC(maritime,calculateSeaSurfaceTemperature);
    };
    [] call EFUNC(radio,calculateRadioPropagation);
};
END_COUNTER(radio);

// ─── Surface Hydrology ──────────────────────────────────────────────────────
// Tidal prediction must run before river water level and flash flood,
// because those functions read the tide offset set here.
BEGIN_COUNTER(hydrology);
if (GVAR(maritimeEnabled)) then {
    [] call EFUNC(maritime,calculateTidalPrediction);
};
if (GVAR(hydrologyEnabled)) then {
    [] call EFUNC(environmental,calculateSnowAccumulation);
    [] call EFUNC(environmental,calculateFlashFloodRisk);
    [] call EFUNC(environmental,calculateDustSuppression);
};
[] call EFUNC(mobility,calculateRouteDegradation);
[] call EFUNC(mobility,calculateSoilBearingStrength);
// Particle effects are driven by the ONE pipeline after the severe-weather
// block below, so the weather gates read the current sandstorm and
// blowing-snow state rather than the previous tick's.
END_COUNTER(hydrology);

// ─── Atmospheric events ────────────────────────────────────────────────────
BEGIN_COUNTER(atmosEvents);
if (GVAR(atmosphericEventsEnabled)) then {
    [] call EFUNC(atmos,calculateLightning);
    // Engine lightning rendering follows the strike risk (issue #141).
    [] call EFUNC(atmos,updateEngineLightnings);
    [] call EFUNC(environmental,calculateSevereWeather);
    [] call EFUNC(atmos,calculateMicroburst);
    [] call EFUNC(atmos,calculateTurbulence);
    [_posASL] call EFUNC(environmental,calculateAvalancheRisk);
    // Seasonal concealment: foliage/crop/snow -> concealment factor,
    // published for the future camo (#119) and AI-detection (#74) links.
    [_posASL, "STAND"] call EFUNC(environmental,calculateConcealment);
    [_posASL] call EFUNC(environmental,calculateIceLoad);
    [] call EFUNC(atmos,calculateAirframeIcing);
    [] call EFUNC(optics,calculateAtmosphericSeeing);

    // ── FX triggers (visual/audio events also require FX enabled) ───────
    if (GVAR(fxEnabled)) then {
        [] call EFUNC(fx,calculateLightningStrikeEffects);
        [] call EFUNC(fx,triggerLightning);
        [] call EFUNC(fx,triggerSevereWeatherFX);
    };
};
END_COUNTER(atmosEvents);

// ─── Particle pipeline (issues #149, #151) ─────────────────────────────────
// ONE handler for every AEE particle effect: the four surface/dust effects
// and the weather set.  It runs after the severe-weather block so the
// weather gates read the current sandstorm and blowing-snow state, and
// after the phase model so snowfall sees the current phase.
if (GVAR(fxEnabled)) then {
    [] call EFUNC(fx,particlePipeline);
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
private _ambientLux = missionNamespace getVariable [QEGVAR(core,ambientLux), 0.001];
private _seeing = missionNamespace getVariable [QEGVAR(optics,atmosphericSeeing), 0.5];
[_ambientLux, _seeing] call EFUNC(optics,calculateLimitingMagnitude);
private _posASL2D = if (count _posASL >= 3) then { [_posASL select 0, _posASL select 1, 0] } else { [0, 0, 0] };
[_posASL2D, date] call EFUNC(optics,getStarCatalog);
[] call EFUNC(atmos,calculateCloudCeiling);
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
    // Engine wave rendering follows the sea state (issue #141).
    [] call EFUNC(atmos,updateEngineWaves);
    [] call EFUNC(maritime,calculateCompassDeviation);
};

// ─── Visual / Gameplay ────────────────────────────────────────────────────
if (GVAR(opticsEnabled)) then {
    [] call EFUNC(optics,calculateRainOnOptics);
    [] call EFUNC(optics,calculateVehicleHeatShimmer);
};
[] call EFUNC(mobility,calculateMudAccretion);

// ─── Engine environment bridges (issue #141) ─────────────────────────────
// Local renderer bridges; each function self-gates on hasInterface.
[] call EFUNC(atmos,updateRainbow);
[] call EFUNC(atmos,updateLocalWindParams);

// ─── Post-Process Effects & HUD ─────────────────────────────────────────
[] call EFUNC(optics,applyRainOnOpticsFX);
[] call EFUNC(optics,applyHeatShimmerFX);
[] call EFUNC(nightvision,applyNightGrain);
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

END_COUNTER(updateEnvironment);
