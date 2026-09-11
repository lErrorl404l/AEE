#include "..\script_component.hpp"

/*
Severe weather event detection based on biome and conditions.

  Sandstorm     — Arid biome + high wind + dry air
  Blowing snow  — Snow-covered ground + cold temps + wind
  Dust devil    — Arid biome + hot clear day + light wind

Each severity is 0-1 (0 = none, 1 = severe).
Sets QGVAR(currentSandstorm), QGVAR(currentBlowingSnow), QGVAR(currentDustDevil).
*/

// ─── Inputs ──────────────────────────────────────────────────────────────
private _biome       = GVAR(biome);
private _windSpd     = vectorMagnitude wind;
private _rain        = rain;
private _temp        = EGVAR(core,currentTemperature);
private _overcast    = overcast;
private _groundState = missionNamespace getVariable [QGVAR(groundState), "Normal"];

if (isNil "_temp") then { _temp = 20; };

// ─── Sandstorm — arid + dry + wind > 10 m/s ─────────────────────────────
private _sandstorm = 0;
if (!isNil "_biome"
    && _biome in ["BWh","BWk","BSh","BSk"]
    && (_windSpd > 10)
    && (_rain < 0.01)
) then {
    _sandstorm = (_windSpd / 25) min 1.0;
};

// ─── Blowing snow / whiteout — snow state + cold + wind > 8 m/s ─────────
private _blowingSnow = 0;
if (_groundState == "Snow" && (_windSpd > 8) && (_temp < 0)) then {
    _blowingSnow = (_windSpd / 20) min 1.0;
};

// ─── Dust devil — arid + hot + clear + light wind ───────────────────────
// More localised — lower severity cap reflects spot nature.
private _dustDevil = 0;
if (!isNil "_biome"
    && _biome in ["BWh","BWk","BSh","BSk"]
    && (_windSpd > 5)
    && (_temp > 30)
    && (_overcast < 0.3)
) then {
    _dustDevil = (_windSpd / 15) min 0.8;
};

// ─── Output ──────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(currentSandstorm),   _sandstorm];
missionNamespace setVariable [QGVAR(currentBlowingSnow), _blowingSnow];
missionNamespace setVariable [QGVAR(currentDustDevil),   _dustDevil];
