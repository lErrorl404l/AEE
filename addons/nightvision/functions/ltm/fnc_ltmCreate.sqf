#include "..\..\script_component.hpp"
/*
 * Laser target marker beam state.
 *
 * Keeps the per-unit beam segment list current from the real laser geometry.
 * The laser target comes from laserTarget on the unit vehicle.  The segments
 * are stored on the unit and drawn by fnc_ltmDraw.  No object is created,
 * because the source p3d beam model cannot be shipped.
 *
 * Ported from workshop 2041057379 A3TI/LTM/fn_createLTM.sqf.  The source
 * builds 21 beam objects 500 m apart along the laser line, deletes them when
 * the laser target is null, and refreshes them at the blink cadence.  This
 * function keeps that structure with a segment list instead of objects.
 *
 * Params:
 *   0: _unit (OBJECT) - the operator or gunner whose vehicle fires the laser.
 *   1: _delete (BOOL) - force the beam away (default false).
 *
 * Returns: nothing.
 */
params [["_unit", objNull, [objNull]], ["_delete", false, [true]]];

if (isNull _unit) exitWith {};

private _target = laserTarget (vehicle _unit);

// Null laser target: the designator is off, delete the stored beam.
if (isNull _target) exitWith {
    if ((_unit getVariable [QGVAR(ltmSegments), []]) isNotEqualTo []) then {
        _unit setVariable [QGVAR(ltmSegments), nil, false];
    };
};

// The beam exists only while the operator has toggled it on.
private _active = !(isNil { _unit getVariable QGVAR(ltmStartTime) });
if (!_active || _delete) exitWith {
    _unit setVariable [QGVAR(ltmSegments), nil, false];
};

private _veh = vehicle _unit;
private _origin = getPosASL _veh;
private _targetPos = getPosASL _target;
if ((_targetPos select 2) < 0) then {
    _targetPos set [2, 0];
};

private _steady = ((_unit getVariable [QGVAR(ltmMode), LTM_MODE_BLINK]) isEqualTo LTM_MODE_STEADY);
private _built = _unit getVariable [QGVAR(ltmSegments), []];

// Steady mode tracks the laser every frame.  Blink mode rebuilds once per
// blink cycle and holds the geometry in between, as the source does.  The
// phase comes from time mod LTM_BLINK_INTERVAL, so the beam blinks in step
// on every machine.
private _phase = time mod LTM_BLINK_INTERVAL;
if (_steady || (_built isEqualTo []) || (_phase < 0.05)) then {
    private _segments = [_origin, _targetPos, LTM_SEGMENT_COUNT, LTM_SEGMENT_STEP] call FUNC(ltmBeamSegments);
    _unit setVariable [QGVAR(ltmSegments), _segments, false];
};
