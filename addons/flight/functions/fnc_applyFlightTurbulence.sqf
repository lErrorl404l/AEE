#include "..\script_component.hpp"

/*
Author: AEE
Description:
Per-frame atmospheric turbulence and wind-shear forces for aircraft.

Reads the shared weather state (aee_core_currentTurbulence, currentGusts,
currentWind, currentWindDir, currentAirDensity) and applies a smoothed gust
vector to every airborne, moving aircraft within range of a player or the
mission centre.

The gust is a relative wind.  Its force is aerodynamic drag, the dynamic
pressure times the airframe's effective drag area (F = 0.5 rho v^2 Cd S),
read from the aircraft corpus record.  The force does not carry the mass, so
the acceleration it realises is force / mass: a heavy airframe resists a gust
and a light one is nudged.  The advanced flight model (the scenario-global
flag difficultyEnabledRTD) and any rotor-lib airframe (the
RotorLibHelicopterProperties class) receive the force via addForce, with a
bounded addTorque attitude nudge for a rotary airframe.  The simple model
cannot integrate a PhysX force, so it receives the same acceleration as a
local velocity delta.  Every application is gated to the machine that owns
the object, so a remote client or a dedicated server never writes another
machine's velocity state.

The engine has no "AdvancedFlightModel" class.  The old gate tested for it,
matched nothing, and left the addForce branch dead.  The correct gate is the
difficulty flag and the rotor-lib property above.

Wind shear: when gusts exceed 15 m/s, a deterministic horizontal gust is
added on a fixed roll so all clients agree.  It joins the gust vector and
takes the same aerodynamic, mass-aware force.

Arguments:
None

Return Value:
None

Example:
[] call aee_flight_fnc_applyFlightTurbulence;

Public: No
*/

if (!GVAR(flightTurbulence)) exitWith {};
if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith {};

// One clock (Pillar 1): this handler runs at 0.05 s, so the integration step
// is the real elapsed clock time since the last pass, not the frame delta.
// diag_deltaTime is the previous RENDERED frame - reading it here would make
// the time constant depend on the frame rate (the P79 defect class).  The
// first pass, and any zero-width pass, integrates nothing.
private _nowSim = missionNamespace getVariable [QEGVAR(core,simTime), diag_tickTime];
private _lastSim = missionNamespace getVariable [QGVAR(turbulenceSimTime), _nowSim];
private _dt = (_nowSim - _lastSim) max 0;
missionNamespace setVariable [QGVAR(turbulenceSimTime), _nowSim];

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

private _density = missionNamespace getVariable [QEGVAR(core,currentAirDensity), AERO_ISA_SEA_LEVEL_DENSITY];
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
// The radius test belongs in the cache, not in the per-frame candidate
// select below.  The speed, height and liveness tests stay per frame,
// because those are physics conditions that must react as they change.
if ((_aircraft isEqualTo []) || ((time - _lastRefresh) > 1)) then {
    _aircraft = vehicles select {
        (_x isKindOf "Air") && (alive _x) && {(_x distance _refPos) < _radius}
    };
    missionNamespace setVariable [QGVAR(turbulenceAircraft), _aircraft];
    missionNamespace setVariable [QGVAR(turbulenceRefresh), time];
};

if (_aircraft isEqualTo []) exitWith {};

// ─── Wind-shear event — deterministic roll, salt 701 ───────────────────
private _shearVec = [0, 0, 0];
if (_gusts > 15) then {
    private _roll = [round (time * 10), 701] call EFUNC(lib,deterministicRandom);
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

// The advanced model is a scenario-global flag, so read it once per call.
private _rtd = difficultyEnabledRTD;

private _candidates = _aircraft select {
    (!isNull _x) &&
    (alive _x) &&
    (local _x) &&
    (((getPosATL _x) select 2) > 3) &&
    (speed _x > 10)
};

{
    private _veh = _x;

    // Stored smooth gust for this aircraft
    private _smooth = [0, 0, 0];
    {
        if ((_x select 0) == _veh) exitWith { _smooth = _x select 1; };
    } forEach _state;

    // Target gust — wind direction plus random sway, scaled by weather.
    private _sway = (_turbulence * 40) - 20;
    private _dir = _windDir + 180 + _sway;
    private _dirVec = [sin _dir, cos _dir, 0];
    _dirVec set [2, ((random 0.5) - 0.25) * _turbulence];
    private _mag = _turbulence * _gusts * _scale * (0.6 + random 0.8);
    private _target = _dirVec vectorMultiply _mag;

    // Smooth transition — no jitter
    private _newSmooth = _smooth vectorAdd ((_target vectorDiff _smooth) vectorMultiply 0.1);
    _newState pushBack [_veh, _newSmooth];

    // ─── Apply ─────────────────────────────────────────────────────────
    // The advanced model is the global difficulty flag and a rotor-lib
    // airframe is identified by its own property class.  The old test for an
    // "AdvancedFlightModel" class matched nothing, so this branch never ran.
    private _rotorLib = isClass (configOf _veh >> "RotorLibHelicopterProperties");
    private _physical = ([_rtd, _rotorLib] call FUNC(resolveFlightModel)) == 1;

    private _mass = getMass _veh;
    if (_mass <= 0) then { _mass = AERO_DEFAULT_AIRCRAFT_MASS_KG; };

    // The airframe's drag reference area, from the aircraft corpus record.
    private _row = [typeOf _veh] call FUNC(getAircraftData);
    private _dragArea = [_row] call FUNC(resolveTurbulenceArea);

    // The gust is a relative wind.  Its force is the dynamic pressure times
    // the drag area, so it does not carry the mass and the acceleration it
    // realises is force / mass: a heavy airframe resists and a light one is
    // nudged.  The wind-shear kick is the same kind of perturbation, so it
    // joins the gust vector.
    private _gustVec = _newSmooth vectorAdd _shearVec;
    private _gustMag = vectorMagnitude _gustVec;

    if (_gustMag > 0) then {
        private _forceN = [_gustMag, _density, _dragArea, _mass] call FUNC(calculateTurbulenceForce);
        if (_forceN > 0) then {
            private _forceDir = vectorNormalized _gustVec;
            if (_physical) then {
                _veh addForce [_forceDir vectorMultiply _forceN, [0, 0, 0]];
                // A rotary airframe also takes a bounded attitude nudge, so
                // the gust rolls and yaws it and not only translates it.
                if (_rotorLib) then {
                    private _torque = (_forceDir vectorCrossProduct [0, 0, 1]) vectorMultiply (_forceN * TURBULENCE_TORQUE_FRACTION);
                    _veh addTorque [_torque, false];
                };
            } else {
                // The simple model does not integrate a PhysX force, so apply
                // the same acceleration over the real clock delta as a local
                // velocity delta.  The delta carries the mass through
                // force / mass, so the simple model is weight-aware too.
                private _deltaV = (_forceN / _mass) * _dt;
                _veh setVelocity ((velocity _veh) vectorAdd (_forceDir vectorMultiply _deltaV));
            };
        };
    };
} forEach _candidates;

missionNamespace setVariable [QGVAR(turbulenceState), _newState];
