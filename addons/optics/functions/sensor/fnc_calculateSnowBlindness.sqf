#include "..\..\script_component.hpp"

/*
Snow blindness / photokeratitis visual impairment (0–1) from bright snow.

Returns a visual impairment factor where 0 = no impairment, 1 = fully
impaired (squinting, tearing, dazzled).

High-albedo snow reflects UV and visible light upward into the eyes:
  • Snow on ground (snowDepth_m > 0)
  • Daytime (sun above horizon)
  • Low overcast (unfiltered sunlight)
  • Player outside (not in enclosed vehicle / building)

Mitigated by:
  • Sunglasses / tinted goggles (factor 0.1)
  • HMD / NVG (face shaded — factor 0.15)
  • Weapon optic (eye already shaded — factor 0.05)
  • High overcast (diffuse light reduces glare)

Also simulates glare flicker from variable lighting under partial cloud.

Stored in GVAR(snowBlindness).
*/

params [["_unit", objNull, [objNull]]];
if (isNull _unit) exitWith { 0 };  // no unit on dedicated server

// ─── Night guard ───────────────────────────────────────────────────────────
if (sunOrMoon <= 0) exitWith {
    missionNamespace setVariable [QGVAR(snowBlindness), 0];
    0
};

// ─── Inputs ────────────────────────────────────────────────────────────────
private _snowDepth = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];
private _overcast  = overcast;
private _daytime   = dayTime;

// No snow → no snow blindness
if (_snowDepth <= 0) exitWith {
    missionNamespace setVariable [QGVAR(snowBlindness), 0];
    0
};

// ─── Base blindness from snow reflectivity ─────────────────────────────────
// Snow contributes up to the base setting at full depth
private _baseMax = missionNamespace getVariable [QGVAR(snowBlindnessBase), 0.1];
private _baseBlindness = (_snowDepth min _baseMax) * (1 - _overcast);

// ─── Solar elevation factor (peak at noon, zero at horizon) ────────────────
private _dayFraction    = _daytime / 24;
private _solarElevation = sin ((_dayFraction - 0.25) * 360) * 90 max 0;
_baseBlindness = _baseBlindness * (_solarElevation / 90);

// ─── Eye protection adaption factor ────────────────────────────────────────
// 1.0 = fully exposed, lower values = better protected
private _adaption = 1;

// Check goggles for sun protection
private _goggleClass = goggles _unit;
if (_goggleClass != "") then {
    private _goggleLower = toLower _goggleClass;
    if (_goggleLower find "shades" >= 0 ||
        {_goggleLower find "aviator" >= 0} ||
        {_goggleLower find "goggle" >= 0} ||
        {_goggleLower find "tinted" >= 0} ||
        {_goggleLower find "dark" >= 0}) then {
        _adaption = 0.1;
    };
};

// Check HMD (NVGs, ballistic visors — also block ambient light)
if (_adaption > 0.1) then {
    private _hmdClass = hmd _unit;
    if (_hmdClass != "") then {
        _adaption = 0.15;
    };
};

// Check weapon optic (eye already shaded against ambient light)
if (_adaption > 0.05) then {
    private _weapon = currentWeapon _unit;
    if (_weapon != "") then {
        private _optic = (primaryWeaponItems _unit) param [2, ""];
        if (_optic != "") then {
            _adaption = 0.05;
        };
    };
};

// ─── Glare flicker under partial cloud ─────────────────────────────────────
// Variable lighting from moving clouds creates intermittent brightening
private _glareFlicker = 0;
if (_overcast > 0.2 && (_overcast < 0.5) && (_baseBlindness > 0)) then {
    _glareFlicker = sin (time * 8) * 0.1 max 0;
};

// ─── Combine ───────────────────────────────────────────────────────────────
private _blindness = (_baseBlindness * _adaption + _glareFlicker) min 1;

missionNamespace setVariable [QGVAR(snowBlindness), _blindness];

_blindness
