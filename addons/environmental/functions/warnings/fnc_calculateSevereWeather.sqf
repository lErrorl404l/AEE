#include "..\..\script_component.hpp"

/*
Severe weather event detection based on biome and conditions.

  Sandstorm     — Arid biome + high wind + dry air
  Blowing snow  — Snow-covered ground + cold temps + wind
  Dust devil    — Arid biome + hot clear day + wind in the 2-8 m/s band

Dust devils need the 2-8 m/s wind band: calm enough to not be
shredded, windy enough for vorticity. Strong wind (above the sandstorm
threshold) destroys them.

Each severity is 0-1 (0 = none, 1 = severe).  The sandstorm and
blowing-snow intensities come from the dust and snow visibility models
(issue #106), so each scalar rises as the visibility falls.
Sets QEGVAR(core,currentSandstorm), QEGVAR(core,currentBlowingSnow), QEGVAR(core,currentDustDevil).
*/

// ─── Inputs ──────────────────────────────────────────────────────────────
// Zeus storm override: while active, force the severe-weather state
// instead of the natural detection. "clear" forces everything to 0.
private _overrideType     = missionNamespace getVariable [QEGVAR(core,stormOverrideType), ""];
private _overrideUntil    = missionNamespace getVariable [QEGVAR(core,stormOverrideUntil), 0];
private _overridden       = false;
if ((_overrideType != "") && (time < _overrideUntil)) then {
    private _intensity = missionNamespace getVariable [QEGVAR(core,stormOverrideIntensity), 0.5];
    _intensity = _intensity max 0 min 1;
    private _forcedSand = 0;
    private _forcedSnow = 0;
    if (_overrideType == "sandstorm") then { _forcedSand = _intensity; };
    if (_overrideType == "snowstorm") then { _forcedSnow = _intensity; };
    missionNamespace setVariable [QEGVAR(core,currentSandstorm),   _forcedSand];
    missionNamespace setVariable [QEGVAR(core,currentBlowingSnow), _forcedSnow];
    missionNamespace setVariable [QEGVAR(core,currentDustDevil),   0];
    _overridden = true;
};
if (_overridden) exitWith {};

private _biome       = missionNamespace getVariable [QEGVAR(core,biome), "Cfb"];
private _windSpd     = vectorMagnitude wind;
private _rain        = rain;
private _temp        = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _overcast    = overcast;
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];

if (isNil "_temp") then { _temp = 20; };

// ─── Sandstorm / haboob — arid + dry + wind above the threshold ─────────
// The intensity comes from the dust visibility (Baddock 2014), not from a
// wind scalar.  The airborne concentration is a MODELLING CHOICE: the mod
// has no dust sensor, so the concentration ramps from 1 mg/m3 at the wind
// threshold to 10 mg/m3 ten m/s above it.  That spans the issue's severe
// band (1 to 10 mg/m3, 500 to 50 m visibility) over the 10 to 20 m/s wind
// range the issue gives for typical to crusted sand.
private _sandThreshold = missionNamespace getVariable [QGVAR(SandstormWindThreshold), 10];
private _sandstorm = 0;
if (!isNil "_biome"
    && _biome in ["BWh","BWk","BSh","BSk"]
    && (_windSpd > _sandThreshold)
    && (_rain < 0.01)
) then {
    private _concentration = 1 + ((_windSpd - _sandThreshold) * 0.9);
    _sandstorm = ([_concentration] call FUNC(calculateDustVisibility)) get "intensity";
};

// ─── Blowing snow / whiteout — snow state + cold + wind above threshold ──
// The intensity comes from the suspended-snow visibility (Li and Pomeroy
// 1997b), not from a wind scalar.  Air density is passed in so the
// saltation flux uses the current atmosphere.
private _blowingSnow = 0;
if (_groundState == "Snow" && (_windSpd > missionNamespace getVariable [QGVAR(BlowingSnowWindThreshold), 8]) && (_temp < 0)) then {
    private _rhoA = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];
    if !(_rhoA isEqualType 0) then { _rhoA = 1.225; };
    _blowingSnow = ([_windSpd, _temp, 0.001, _rhoA, 0.20] call FUNC(calculateBlowingSnowVisibility)) get "intensity";
};

// ─── Dust devil — arid + hot + clear + wind 2-8 m/s ─────────────────────
// Real dust devils form in the 2-8 m/s band; strong wind shreds them.
// More localised — lower severity cap reflects spot nature.
private _dustDevil = 0;
if (!isNil "_biome"
    && _biome in ["BWh","BWk","BSh","BSk"]
    && (_windSpd >= 2)
    && (_windSpd <= 8)
    && (_temp > missionNamespace getVariable [QGVAR(DustDevilTempThreshold), 30])
    && (_overcast < 0.3)
) then {
    _dustDevil = (_windSpd / 15) min 0.8;
};

// ─── Output ──────────────────────────────────────────────────────────────
missionNamespace setVariable [QEGVAR(core,currentSandstorm),   _sandstorm];
missionNamespace setVariable [QEGVAR(core,currentBlowingSnow), _blowingSnow];
missionNamespace setVariable [QEGVAR(core,currentDustDevil),   _dustDevil];
