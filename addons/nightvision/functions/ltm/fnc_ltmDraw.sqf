#include "..\..\script_component.hpp"
/*
 * Laser target marker Draw3D worker.
 *
 * Draws the stored beam segments with drawLine3D.  This replaces the source
 * p3d beam model, which cannot be shipped.  The beam is real geometry drawn
 * from the laser line.  The colour follows the source intent: green for the
 * blinking marker and white for the steady marker.
 *
 * Registered once on the mission Draw3D event by fnc_ltmInit.  One pass per
 * frame, and a no-op when the beam is off.
 *
 * Params: none.  The worker resolves the current controlled unit itself.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};

private _on = missionNamespace getVariable [QGVAR(ltmEnabled), false];
if !(_on isEqualType true) then { _on = false; };
if (!_on) exitWith {};

private _unit = call CBA_fnc_currentUnit;
if (isNull _unit) exitWith {};

private _segments = _unit getVariable [QGVAR(ltmSegments), []];
if (_segments isEqualTo []) exitWith {};

private _steady = ((_unit getVariable [QGVAR(ltmMode), LTM_MODE_BLINK]) isEqualTo LTM_MODE_STEADY);

// Blink mode shows the beam for the first half of every cycle.  The phase
// comes from time mod LTM_BLINK_INTERVAL, the source's blink cadence.
private _visible = _steady || ((time mod LTM_BLINK_INTERVAL) < (LTM_BLINK_INTERVAL * 0.5));
if (!_visible) exitWith {};

private _colour = [0.10, 1.00, 0.20, 1.00];
if (_steady) then {
    _colour = [1.00, 1.00, 1.00, 1.00];
};

{
    drawLine3D [_x select 0, _x select 1, _colour];
} forEach _segments;
