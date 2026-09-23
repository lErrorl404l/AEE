#include "..\..\script_component.hpp"

/*
Particle emission model (issue #149) — a PURE function of AEE state.

Given an effect name it returns the emission parameters the pipeline needs:
[intensity, colourRGBA, rate].  There are no side effects and no
randomness: every value is a function of the arguments and the published
AEE state (position, mission time, engine weather), so every machine
computes the same numbers.  The only per-machine variation in the particle
engine is the cosmetic spawn itself, which the pipeline applies with
setParticleRandom (a billboard sprite, not simulation state).

The gate functions hold the object context (who is driving, which aircraft)
and pass the measured strength in _context.  This function holds the
physics mapping, so a gate change cannot change the physics and a physics
change is tested in one place.

Arguments:
  0: effect (STRING)
  1: position (ARRAY, PositionASL, optional)
  2: context (ARRAY, optional).  Surface effects pass
     [strength, lift, colour]; other effects pass [].

Returns [intensity 0..1, colourRGBA, rate particles/s].
*/

params [
    ["_effect", "atmosphericDust", [""]],
    ["_pos", [], [[]]],
    ["_context", [], [[]]]
];

private _cfg = (call FUNC(particleEffectConfig)) getOrDefault [_effect, createHashMap];
private _baseRate = _cfg getOrDefault ["baseRate", 5];

// Shared state.  The moisture proxy is dust suppression (1 = dry, 0 = wet).
private _suppression = missionNamespace getVariable [QEGVAR(core,dustSuppression), 0.6];
if !(_suppression isEqualType 0) then { _suppression = 0.6; };
private _wind = missionNamespace getVariable [QEGVAR(core,currentWindStr), 0];
if !(_wind isEqualType 0) then { _wind = 0; };

// Biome dust palette — the existing atmospheric-dust colours (warm tan
// for desert, grey-brown for temperate, pale for polar).
private _biome = missionNamespace getVariable [QEGVAR(core,biome), "Cfb"];
private _biomeDustColour = [0.7, 0.6, 0.4];
switch (true) do {
    case (_biome in ["BWh", "BSh", "BWk"]): { _biomeDustColour = [0.8, 0.7, 0.5]; };
    case (_biome in ["Dfb", "Dfc"]):        { _biomeDustColour = [0.5, 0.45, 0.35]; };
    case (_biome in ["ET", "EF"]):           { _biomeDustColour = [0.85, 0.85, 0.8]; };
};

private _intensity = 0;
private _colour = [0.62, 0.58, 0.48, 1];

switch (true) do {
    // ─── Surface effects: strength comes from the gate ───────────────────
    case (_effect in ["vehicleDust", "footfallDust", "rotorWash"]): {
        _context params [["_strength", 0, [0]], ["_lift", 0.6, [0]], ["_col", [], [[]]]];
        _intensity = _strength * _suppression * _lift;
        if (_col isNotEqualTo []) then { _colour = _col; };
    };
    // ─── Wind-blown atmospheric dust ─────────────────────────────────────
    case (_effect == "atmosphericDust"): {
        // Wind speed -> density factor (0 at 5 m/s, 1 at 20 m/s), the
        // existing atmospheric-dust gate.
        private _windFactor = (((_wind - 5) / 15) min 1) max 0;
        private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
        private _surfaceMultiplier = 1;
        switch (_groundState) do {
            case "Dusty": { _surfaceMultiplier = 2.0; };
            case "Mud":   { _surfaceMultiplier = 0.2; };
            case "Snow":  { _surfaceMultiplier = 0.1; };
            case "Dry":   { _surfaceMultiplier = 1.5; };
        };
        _intensity = _windFactor * _suppression * _surfaceMultiplier;
        _colour = [_biomeDustColour select 0, _biomeDustColour select 1, _biomeDustColour select 2, 1];
    };
    // ─── Weather effects: physics state is the gate ──────────────────────
    case (_effect == "snowfall"): {
        private _phase = missionNamespace getVariable [QEGVAR(core,precipitationPhase), "rain"];
        private _rate = missionNamespace getVariable [QEGVAR(core,snowfallRate), 0];
        if !(_rate isEqualType 0) then { _rate = 0; };
        if (_phase == "snow") then { _intensity = _rate min 1; };
        _colour = [1, 1, 1, 1];
    };
    case (_effect == "blowingSnow"): {
        private _blowing = missionNamespace getVariable [QEGVAR(core,currentBlowingSnow), 0];
        if !(_blowing isEqualType 0) then { _blowing = 0; };
        _intensity = _blowing min 1;
        _colour = [1, 1, 1, 1];
    };
    case (_effect == "hail"): {
        // Hail falls only when the phase model's convective gate is set
        // (fnc_calculatePrecipitationPhase).  The gate is the physics.
        if (missionNamespace getVariable [QEGVAR(core,hailActive), false]) then { _intensity = 1; };
        _colour = [0.92, 0.95, 1.00, 1];
    };
    case (_effect == "haboob"): {
        // Severe dust: the #106 sandstorm intensity, and the wind must be
        // above the haboob threshold (15 m/s) to carry it.
        private _sand = missionNamespace getVariable [QEGVAR(core,currentSandstorm), 0];
        if !(_sand isEqualType 0) then { _sand = 0; };
        if (_wind > 15) then { _intensity = _sand min 1; };
        _colour = [_biomeDustColour select 0, _biomeDustColour select 1, _biomeDustColour select 2, 1];
    };
    case (_effect in ["hurricane", "hurricaneSpray", "hurricaneDebris"]): {
        // The composite above the hurricane threshold (33 m/s, the
        // Saffir-Simpson Category 1 boundary).  Intensity ramps to 1 by
        // 45 m/s.
        if (_wind > 33) then { _intensity = ((_wind - 33) / 12) min 1; };
        if (_effect == "hurricaneSpray") then { _colour = [0.72, 0.78, 0.82, 1]; };
        if (_effect == "hurricaneDebris") then { _colour = [0.30, 0.28, 0.22, 1]; };
        if (_effect == "hurricane") then { _colour = [0.70, 0.78, 0.88, 1]; };
    };
};

// ─── Existing FX settings still scale their effects ──────────────────────
// The migration keeps the vehicle-dust and atmospheric-dust settings
// meaningful.  The defaults reproduce the pre-pipeline behaviour exactly.
private _rateScale = 1;
if (_effect == "vehicleDust") then {
    _intensity = _intensity * (missionNamespace getVariable [QGVAR(vehicleDustIntensity), 1.0]);
    _rateScale = (missionNamespace getVariable [QGVAR(vehicleDustDensity), 0.08]) / 0.08;
} else {
    if (_effect == "atmosphericDust") then {
        _intensity = _intensity * ((missionNamespace getVariable [QGVAR(atmosphericDustIntensity), 0.08]) / 0.08);
    };
};

if ((count _colour) == 3) then { _colour pushBack 1; };

[_intensity, _colour, _baseRate * _intensity * _rateScale]
