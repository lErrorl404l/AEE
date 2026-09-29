#include "..\script_component.hpp"
// Attaches a raw BIS engine event handler to the local unit, and re-attaches
// it when that unit is replaced.
//
// WHY AEE INSTALLS ITS OWN, measured on CBA v3.19.0 build 260808 on 2026-09-29.
// Every route previously used for an engine event is dead, wrong, or the wrong
// granularity:
//   - CBA_fnc_addEventHandler received 0 of the 3 real engine Init events a
//     probe raised, and fired exactly once when the bus was driven by hand, so
//     the bus is sound but nothing emits engine event names onto it.
//   - CBA_fnc_addClassEventHandler accepts Init, Explosion, HitPart and
//     Dammaged, but REJECTS FiredBIS and accepts only legacy "Fired", which
//     cba_xeh rebinds as _this = [0,1,2,3,4,6,5]. That swaps the magazine and
//     the projectile, and it emits a deprecation WARNING_4 which
//     tools/docker/verify.py counts as a failure. Measured.
//   - A class EH also fires for every unit in the world, while every AEE
//     engine handler filters to the local player, so it is the wrong
//     granularity as well as the wrong argument order.
// A raw BIS "Fired" event carries the BIS argument order natively, is silent,
// and can be scoped to exactly the unit AEE cares about. That is the only
// route that is correct, cheap and quiet.
//
// No params type specifier: the engine demands a string type name there and
// rejects [objNull] outright, which aborted every call in the first version.
// The guards are explicit instead.
//
// Re-attachment rides CBA's "unit" player event, a real CBA event, so respawn
// costs nothing rather than a per-frame poll.
//
// _key is the caller's own name, NOT the event name. Four addons each own a
// Fired handler on the same unit, so keying on the event would let one call
// remove another's handler.
params ["_eventName", "_eventCode", "_key"];

if (_eventName isEqualTo "") exitWith {false};
if (_eventCode isEqualTo {}) exitWith {false};
if (_key isEqualTo "") exitWith {false};

private _attachers = missionNamespace getVariable [QGVAR(playerEngineHandlers), []];

private _replaced = false;
private _kept = [];
{
    if (_x select 2 isEqualTo _key) then {
        _kept pushBack [_eventName, _eventCode, _key];
        _replaced = true;
    } else {
        _kept pushBack _x;
    };
} forEach _attachers;
if (!_replaced) then {
    _kept pushBack [_eventName, _eventCode, _key];
};
missionNamespace setVariable [QGVAR(playerEngineHandlers), _kept];

private _unit = call CBA_fnc_currentUnit;
if (!isNull _unit) then {
    [_unit, _eventName, _eventCode, _key] call EFUNC(core,attachObjectEngineHandler);
};

// One hook for every handler, so N handlers still cost a single player event.
if !(missionNamespace getVariable [QGVAR(playerEngineHandlersHooked), false]) then {
    missionNamespace setVariable [QGVAR(playerEngineHandlersHooked), true];
    ["unit", {
        private _unit = call CBA_fnc_currentUnit;
        if (isNull _unit) exitWith {};
        {
            [_unit, _x select 0, _x select 1, _x select 2] call EFUNC(core,attachObjectEngineHandler);
        } forEach (missionNamespace getVariable [QEGVAR(core,playerEngineHandlers), []]);
    }] call CBA_fnc_addPlayerEventHandler;
};

true
