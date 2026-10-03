#include "..\..\script_component.hpp"
/*
 * Laser target marker per-frame lifecycle.
 *
 * Starts the beam worker when the controlled unit is in night vision and
 * stops it when the unit leaves.  The beam is an operator aid, so it runs
 * only while the operator looks through night vision.
 *
 * Ported from workshop 2041057379 A3TI/LTM/fn_pfhLTM.sqf.  The source starts
 * a per-frame handler that runs createLTM for allUnits and deletes the beams
 * of dead units.  The source sleeps to let a delete settle.  This port does
 * not sleep, because a sleep inside a per-frame handler stalls the engine.
 *
 * Params: none.  The worker resolves the current controlled unit itself.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};

private _unit = call CBA_fnc_currentUnit;
if (isNull _unit) exitWith {};

private _pfh = missionNamespace getVariable [QGVAR(ltmPFH), -1];
private _inNV = (currentVisionMode _unit isEqualTo 1);

// Left night vision: stop the handler and delete every stored beam.
if ((_pfh > -1) && !(_inNV)) exitWith {
    [_pfh] call CBA_fnc_removePerFrameHandler;
    missionNamespace setVariable [QGVAR(ltmPFH), -1];
    {
        [_x, true] call FUNC(ltmCreate);
    } forEach (missionNamespace getVariable [QGVAR(ltmPFHUnits), []]);
    missionNamespace setVariable [QGVAR(ltmPFHUnits), nil];
    AEE_LOG_DEBUG("LTM handler stopped");
};

if (_inNV && (_pfh < 0)) then {
    private _handle = [{
        // Drop the beams of units that died since the last tick.
        private _tracked = missionNamespace getVariable [QGVAR(ltmPFHUnits), []];
        if (_tracked isNotEqualTo []) then {
            {
                if (!alive _x) then {
                    [_x, true] call FUNC(ltmCreate);
                };
            } forEach _tracked;
        };

        // Build the beam for every unit that fires a laser.
        private _units = allUnits;
        {
            [_x] call FUNC(ltmCreate);
        } forEach _units;
        missionNamespace setVariable [QGVAR(ltmPFHUnits), _units];
    }] call CBA_fnc_addPerFrameHandler;
    missionNamespace setVariable [QGVAR(ltmPFH), _handle];
    AEE_LOG_INFO("LTM handler started");
};
