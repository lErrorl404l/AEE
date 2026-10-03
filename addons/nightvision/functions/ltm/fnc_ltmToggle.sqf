#include "..\..\script_component.hpp"
/*
 * Laser target marker on and off switch.
 *
 * Turns the marker on for the controlled unit, but only in a plane, a UAV or
 * a helicopter that is not also a land vehicle.  A second call turns it off.
 *
 * Ported from workshop 2041057379 A3TI/LTM/fn_toggleLTM.sqf.  The source also
 * stores the turret config, so the mode resets when the operator changes
 * seat.  This port omits that bookkeeping, because aee has no turret
 * resolver and the mode change is not part of the requirement.
 *
 * Params:
 *   0: _unit (OBJECT) - the operator (default objNull).
 *
 * Returns: nothing.
 */
params [["_unit", objNull, [objNull]]];

if (isNull _unit) exitWith {};

if (isNil { _unit getVariable QGVAR(ltmStartTime) }) then {
    private _veh = vehicle _unit;
    if (((_veh isKindOf "Plane") || (_veh isKindOf "UAV") || (_veh isKindOf "Helicopter")) && !(_veh isKindOf "LandVehicle")) then {
        _unit setVariable [QGVAR(ltmStartTime), time, true];
        _unit setVariable [QGVAR(ltmMode), LTM_MODE_BLINK, true];
        AEE_LOG_INFO("LTM enabled");
    };
} else {
    _unit setVariable [QGVAR(ltmStartTime), nil, true];
    _unit setVariable [QGVAR(ltmMode), nil, true];
    _unit setVariable [QGVAR(ltmSegments), nil, false];
    AEE_LOG_INFO("LTM disabled");
};
