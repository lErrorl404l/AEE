#include "..\..\script_component.hpp"

/*
DTV base-channel per-frame driver.

Registered by fnc_dtvHostStart and runs only while the base channel setting
is DTV.  Each tick it asks fnc_updateThermalHost for the host state and, when
the host is active, runs the SAME thermal pass as the engine thermal channel
(fnc_runThermalPass).  The AGC, the solver and the paint are identical - only
the host channel and the engine's native TI state differ.
*/
private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || {!alive _player}) exitWith {
    [] call FUNC(updateThermalHost);
};

private _active = [_player] call FUNC(updateThermalHost);
if (_active) then {
    [] call FUNC(runThermalPass);
};
