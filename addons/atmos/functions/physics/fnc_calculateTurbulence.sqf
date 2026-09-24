#include "..\..\script_component.hpp"

/*
Low-level turbulence index (0-1) for aircraft and helicopter handling.

Two components:
  Mechanical   — wind interacting with terrain roughness
  Convective   — thermal activity from hot surfaces and daytime heating

The raw 0-1 index converts to an ICAO eddy dissipation rate (EDR) proxy
in m^(2/3)/s, the standard turbulence metric of ICAO Annex 3 / Doc 10064.
Intensity classes follow the ICAO EDR bands:
  LIGHT < 0.1, MODERATE 0.1-0.3, SEVERE 0.3-0.5, EXTREME > 0.5.

Sets QEGVAR(core,currentTurbulence), GVAR(edrValue), GVAR(turbulenceClass).
*/

// ─── Mechanical (terrain-driven) ────────────────────────────────────────
// Local wind (issue #136): the spatial field at the player's position —
// building wake, terrain lee recirculation, canyon suppression, crest
// acceleration — replaces the single global vector for the mechanical
// term.  A lee-side recirculation (0.2-0.4x global) is calmer; a ridge
// crest speed-up (up to 1.4x) is rougher.
private _player = call CBA_fnc_currentUnit;
private _posASL = [0, 0, 0];
// isNull, not isNil: CBA_fnc_currentUnit returns objNull on a dedicated
// server rather than nil, so the isNil test let the body run and the
// server published position-derived turbulence for the map origin.
if (!isNil "_player" && {!isNull _player}) then { _posASL = getPosASL _player; };
private _localWind = [_posASL, _posASL param [2, 0]] call FUNC(getLocalWind);
private _windSpd = vectorMagnitude _localWind;
private _mechanical = 0;

if (_windSpd > 5) then {
    // Surface roughness: the engine's own CfgSurfaces `rough` coefficient
    // for the ground under the player.  This is the map's data, so no
    // map-specific surface name is compared here.  CfgSurfaces is
    // read-only at runtime, but readable.
    private _roughness = 0.4;    // fallback: open ground
    // isNull, not isNil: a dedicated server's CBA_fnc_currentUnit is
    // objNull, not nil, so this once ran at the map origin.
    if (!isNull _player) then {
        private _pos2D = getPos _player;
        // surfaceType returns the bare class name (GdtSnow);
        // normalise the token before the config lookup.
        private _raw = surfaceType _pos2D;
        private _type = toLower _raw;
        if (_type find "#gdt" == 0) then { _type = _type select [4]; }
        else { if (_type find "gdt" == 0) then { _type = _type select [3]; }; };
        // Keep the engine class case (GdtSnow) for the lookup; the bare
        // stripped name misses the CfgSurfaces class.
        private _cls = _raw;
        if (_cls find "#" == 0) then { _cls = _cls select [1]; };
        private _cfg = configFile >> "CfgSurfaces" >> _cls;
        if (!isClass _cfg && {_type != ""}) then {
            _cfg = configFile >> "CfgSurfaces" >> _type;
        };
        if (isClass _cfg) then {
            private _r = getNumber (_cfg >> "rough");
            if (_r > 0) then { _roughness = _r min 1.0; };
        };
    };
    _mechanical = _roughness * (_windSpd / 15) min 1.0;
};

// ─── Convective (thermal-driven) ────────────────────────────────────────
private _convective = 0;
private _temp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if (isNil "_temp") then { _temp = 20; };

// Hot surface + clear skies — strong thermals
if (_temp > 30 && overcast < 0.3) then {
    _convective = _convective + 0.3;
};

// Daytime heating gradient
private _hour = dayTime;
if (_hour > 8 && (_hour < 18) && (_temp > 25)) then {
    _convective = _convective + (0.1 + ((_temp - 25) / 50) * 0.1);   // 0.1-0.2
};

// ─── Sum & clamp ───────────────────────────────────────────────────────
private _turbulence = (_mechanical + _convective) min 1.0;

// ─── ICAO EDR conversion ────────────────────────────────────────────────
// EDR (m^(2/3)/s) is the ICAO Annex 3 turbulence metric.  The raw 0-1
// index maps to the typical light-moderate EDR range (0.1-0.7).
private _edr = _turbulence * 0.7;

private _turbulenceClass = switch (true) do {
    case (_edr > 0.5):  { "EXTREME" };
    case (_edr > 0.3):  { "SEVERE" };
    case (_edr >= 0.1): { "MODERATE" };
    default             { "LIGHT" };
};

missionNamespace setVariable [QEGVAR(core,currentTurbulence), _turbulence];
missionNamespace setVariable [QGVAR(edrValue), _edr];
missionNamespace setVariable [QGVAR(turbulenceClass), _turbulenceClass];
