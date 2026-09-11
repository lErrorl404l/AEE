#include "..\script_component.hpp"

/*
Low-level turbulence index (0-1) for aircraft and helicopter handling.

Two components:
  Mechanical   — wind interacting with terrain roughness
  Convective   — thermal activity from hot surfaces and daytime heating

Sets QGVAR(currentTurbulence).
*/

// ─── Mechanical (terrain-driven) ────────────────────────────────────────
private _windSpd = vectorMagnitude wind;
private _mechanical = 0;

if (_windSpd > 5) then {
    // Resolve surface roughness from ground type
    private _roughness = 0.4;    // default
    private _player = call CBA_fnc_currentUnit;
    if (!isNil "_player") then {
        private _pos2D = getPos _player;
        private _type = toLower (surfaceType _pos2D);
        _roughness = switch (true) do {
            case (_type in ["#gdtconiferous","#gdtforest"]):         { 0.8 };
            case (_type in ["#gdturban","#gdtstratis","#gdtconcrete","#gdtruins"]): { 1.0 };
            case (_type in ["#gdtdesert","#gdtsand"]):               { 0.2 };
            case (_type in ["#gdtwater","#gdtsea","#gdtpond"]):      { 0.1 };
            default                                                  { 0.4 };
        };
    };
    _mechanical = _roughness * (_windSpd / 15) min 1.0;
};

// ─── Convective (thermal-driven) ────────────────────────────────────────
private _convective = 0;
private _temp = EGVAR(core,currentTemperature);
if (isNil "_temp") then { _temp = 20; };

// Hot surface + clear skies — strong thermals
if (_temp > 30 && overcast < 0.3) then {
    _convective = _convective + 0.3;
};

// Daytime heating gradient
private _hour = dayTime;
if (_hour > 8 && _hour < 18 && _temp > 25) then {
    _convective = _convective + (0.1 + ((_temp - 25) / 50) * 0.1);   // 0.1-0.2
};

// ─── Sum & clamp ───────────────────────────────────────────────────────
private _turbulence = (_mechanical + _convective) min 1.0;

missionNamespace setVariable [QGVAR(currentTurbulence), _turbulence];
