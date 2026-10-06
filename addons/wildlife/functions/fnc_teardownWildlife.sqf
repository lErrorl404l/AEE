#include "..\script_component.hpp"

/*
Stop the wildlife client tick and release its sound source.

Arguments: none.

Returns:
  Nothing.
*/

if (!isNil QGVAR(ambientPFH)) then {
    [GVAR(ambientPFH)] call CBA_fnc_removePerFrameHandler;
    GVAR(ambientPFH) = nil;
};

private _source = missionNamespace getVariable [QGVAR(ambientSource), objNull];
if (!isNull _source) then {
    deleteVehicle _source;
    missionNamespace setVariable [QGVAR(ambientSource), objNull];
};

// Release every attached fauna emitter, so a teardown leaves no looping
// source behind.
private _emitters = missionNamespace getVariable [QGVAR(emitters), []];
if (_emitters isEqualType []) then {
    for "_i" from 0 to ((count _emitters) - 1) do {
        private _row = _emitters select _i;
        if ((_row isEqualType []) && ((count _row) >= 3)) then {
            private _emitter = _row select 2;
            if (!isNull _emitter) then { deleteVehicle _emitter; };
        };
    };
};
missionNamespace setVariable [QGVAR(emitters), []];

AEE_LOG_INFO("wildlife client tick stopped")
