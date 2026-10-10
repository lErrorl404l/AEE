#include "..\..\script_component.hpp"
/*
 * Laser target marker postInit wiring.
 *
 * Registers the Draw3D worker and the vision-mode trigger.  The Draw3D worker
 * is one cheap pass per frame.  The vision-mode player event starts and stops
 * the beam handler.  The handler is called once now, for a player who is
 * already in night vision at mission start.
 *
 * Ported from workshop 2041057379 A3TI/LTM wiring (A3TI/fn_init.sqf spawns
 * fn_pfhLTM, A3TI/fn_CBA_Keybinds.sqf binds the keys).
 *
 * Params: none.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};

addMissionEventHandler ["Draw3D", {
    [] call FUNC(ltmDraw);
}];

["visionMode", {
    params ["_unit", "_visionMode"];
    if (_unit != (call CBA_fnc_currentUnit)) exitWith {};
    [] call FUNC(ltmPFH);
}, false] call CBA_fnc_addPlayerEventHandler;

[] call FUNC(ltmPFH);
