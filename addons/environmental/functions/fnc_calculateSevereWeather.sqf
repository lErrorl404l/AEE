#include "..\script_component.hpp"

/*
Severe weather event detection based on biome and conditions.

  Sandstorm     — Arid biome + high wind + dry air
  Blowing snow  — Snow-covered ground + cold temps + wind
  Dust devil    — Arid biome + hot clear day + wind in the 2-8 m/s band

Dust devils need the 2-8 m/s wind band: calm enough to not be
shredded, windy enough for vorticity. Strong wind (above the sandstorm
threshold) destroys them.

Each severity is 0-1 (0 = none, 1 = severe).
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

private _biome       = EGVAR(core,biome);
private _windSpd     = vectorMagnitude wind;
private _rain        = rain;
private _temp        = EGVAR(core,currentTemperature);
private _overcast    = overcast;
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];

if (isNil "_temp") then { _temp = 20; };

// ─── Sandstorm — arid + dry + wind above the threshold ──────────────────
private _sandstorm = 0;
if (!isNil "_biome"
    && _biome in ["BWh","BWk","BSh","BSk"]
    && (_windSpd > GVAR(SandstormWindThreshold))
    && (_rain < 0.01)
) then {
    _sandstorm = (_windSpd / 25) min 1.0;
};

// ─── Blowing snow / whiteout — snow state + cold + wind above threshold ──
private _blowingSnow = 0;
if (_groundState == "Snow" && (_windSpd > GVAR(BlowingSnowWindThreshold)) && (_temp < 0)) then {
    _blowingSnow = (_windSpd / 20) min 1.0;
};

// ─── Dust devil — arid + hot + clear + wind 2-8 m/s ─────────────────────
// Real dust devils form in the 2-8 m/s band; strong wind shreds them.
// More localised — lower severity cap reflects spot nature.
private _dustDevil = 0;
if (!isNil "_biome"
    && _biome in ["BWh","BWk","BSh","BSk"]
    && (_windSpd >= 2)
    && (_windSpd <= 8)
    && (_temp > GVAR(DustDevilTempThreshold))
    && (_overcast < 0.3)
) then {
    _dustDevil = (_windSpd / 15) min 0.8;
};

// ─── Output ──────────────────────────────────────────────────────────────
missionNamespace setVariable [QEGVAR(core,currentSandstorm),   _sandstorm];
missionNamespace setVariable [QEGVAR(core,currentBlowingSnow), _blowingSnow];
missionNamespace setVariable [QEGVAR(core,currentDustDevil),   _dustDevil];
