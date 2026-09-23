#include "..\script_component.hpp"

/*
Author: AEE
Description:
Per-frame atmospheric turbulence and wind-shear forces for aircraft.

Reads the shared weather state (aee_core_currentTurbulence, currentGusts,
currentWind, currentWindDir, currentAirDensity) and applies a smoothed gust
vector to every airborne, moving aircraft within range of a player or the
mission centre.

Simple Flight Model (SFM) aircraft receive the gust as a velocity delta via
setVelocity. Advanced Flight Model (ASM) aircraft receive it as a force via
addForce, scaled by mass.

Wind shear: when gusts exceed 15 m/s, a deterministic horizontal impulse is
added on a fixed roll so all clients agree.

Arguments:
None

Return Value:
None

Example:
[] call aee_mobility_fnc_applyFlightTurbulence;

Public: No
*/

if (!GVAR(flightTurbulence)) exitWith {};
if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith {};

private _turbulence = missionNamespace getVariable [QEGVAR(core,currentTurbulence), 0];
private _gusts = missionNamespace getVariable [QEGVAR(core,currentGusts), 0];

// Cheap gate — calm air needs no forces
if ((_turbulence < 0.05) && (_gusts < 3)) exitWith {};

private _windDir = missionNamespace getVariable [QEGVAR(core,currentWindDir), -1];
if (_windDir < 0) then {
    private _wind = missionNamespace getVariable [QEGVAR(core,currentWind), wind];
    _windDir = ((_wind select 0) atan2 (_wind select 1)) + 180;
    if (_windDir >= 360) then { _windDir = _windDir - 360; };
};

private _density = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];
private _densityFactor = _density / 1.225;
private _scale = GVAR(turbulenceScale);
private _radius = GVAR(turbulenceRadius);

// ─── Reference position — player or mission centre ─────────────────────
private _refPos = [worldSize / 2, worldSize / 2, 0];
private _player = call CBA_fnc_currentUnit;
if (!isNil "_player" && {!isNull _player}) then {
    _refPos = getPosATL _player;
};

// ─── Cached aircraft list (refresh every 5 s) ──────────────────────────
private _aircraft = missionNamespace getVariable [QGVAR(turbulenceAircraft), []];
private _lastRefresh = missionNamespace getVariable [QGVAR(turbulenceRefresh), -1];
if ((_aircraft isEqualTo []) || ((time - _lastRefresh) > 5)) then {
    _aircraft = vehicles select { (_x isKindOf "Air") && (alive _x) };
    missionNamespace setVariable [QGVAR(turbulenceAircraft), _aircraft];
    missionNamespace setVariable [QGVAR(turbulenceRefresh), time];
};

if (_aircraft isEqualTo []) exitWith {};

// ─── Wind-shear event — deterministic roll, salt 701 ───────────────────
private _shearVec = [0, 0, 0];
if (_gusts > 15) then {
    private _roll = [round (time * 10), 701] call EFUNC(core,deterministicRandom);
    private _lastShear = missionNamespace getVariable [QGVAR(turbulenceShearTime), -999];
    if ((_roll > 0.9) && ((time - _lastShear) > 10)) then {
        missionNamespace setVariable [QGVAR(turbulenceShearTime), time];
        private _shearDir = _windDir + 90;
        _shearVec = [sin _shearDir, cos _shearDir, 0] vectorMultiply (_gusts * 0.5);
    };
};

// ─── Per-aircraft smoothing state ──────────────────────────────────────
private _state = missionNamespace getVariable [QGVAR(turbulenceState), []];
private _newState = [];

private _candidates = _aircraft select {
    (!isNull _x) &&
    (alive _x) &&
    (((getPosATL _x) select 2) > 3) &&
    (speed _x > 10) &&
    ((_x distance _refPos) < _radius)
};

{
    private _veh = _x;

    // Stored smooth gust for this aircraft
    private _smooth = [0, 0, 0];
    {
        if ((_x select 0) == _veh) exitWith { _smooth = _x select 1; };
    } forEach _state;

    // Target gust — wind direction plus random sway, scaled by weather.
    // Density scales the FORCE (ASM path only): a thin-air force produces
    // a smaller acceleration, but a velocity delta (SFM) already is a
    // velocity — density must not enter it, or thin air would push the
    // aircraft harder in SFM than in ASM.
    private _sway = (_turbulence * 40) - 20;
    private _dir = _windDir + 180 + _sway;
    private _dirVec = [sin _dir, cos _dir, 0];
    _dirVec set [2, ((random 0.5) - 0.25) * _turbulence];
    private _mag = _turbulence * _gusts * _scale * (0.6 + random 0.8);
    private _target = _dirVec vectorMultiply _mag;

    // Smooth transition — no jitter
    private _newSmooth = _smooth vectorAdd ((_target vectorDiff _smooth) vectorMultiply 0.1);
    _newState pushBack [_veh, _newSmooth];

    // Apply — SFM via velocity delta, ASM via force
    // ponytail: addVectorUp does not exist in Arma 3; addForce is the
    // engine command for external forces on ASM aircraft (reference mod).
    private _isASM = isClass (configOf _veh >> "AdvancedFlightModel");
    if (_isASM) then {
        private _mass = getMass _veh;
        _veh addForce [(_newSmooth vectorMultiply (_densityFactor * _mass / 100)), [0, 0, 0]];
    } else {
        _veh setVelocity ((velocity _veh) vectorAdd _newSmooth);
    };

    // Wind-shear kick
    if (_shearVec isNotEqualTo [0, 0, 0]) then {
        if (_isASM) then {
            private _mass = getMass _veh;
            _veh addForce [_shearVec vectorMultiply (_mass / 100), [0, 0, 0]];
        } else {
            _veh setVelocity ((velocity _veh) vectorAdd _shearVec);
        };
    };
} forEach _candidates;

missionNamespace setVariable [QGVAR(turbulenceState), _newState];
