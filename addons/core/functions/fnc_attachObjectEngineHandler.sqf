#include "..\script_component.hpp"
// Attaches one raw BIS engine event handler to one object, replacing any
// handler the same _key installed before. Shared by
// fnc_installObjectEngineHandler (objects that already exist) and by its
// class Init hook (objects created later).
//
// NO params TYPE SPECIFIER HERE, and that is deliberate. A type specifier
// array makes the engine demand a STRING type name, so [objNull] is rejected
// with "Error Params: Type Object, expected String". The first version of
// this file carried one and threw on every single call, 38 errors, and no
// handler ever attached. The guards below are explicit instead, so there is
// no type machinery to get wrong.
//
// Replacing rather than adding is deliberate too: the engine stacks duplicate
// handlers, so a second attach for the same key would run the work twice per
// event. That is the same defect the ppEffect registry fixed for handles.
params ["_object", "_eventName", "_eventCode", "_key"];

if (isNil "_object") exitWith {false};
if (isNull _object) exitWith {false};
if (_eventName isEqualTo "") exitWith {false};
if (_eventCode isEqualTo {}) exitWith {false};
if (_key isEqualTo "") exitWith {false};

private _idVar = format ["aee_core_ehId_%1", _key];
// The right-hand side of removeEventHandler must be an ARRAY. Passing the id
// bare gave "removeeventhandler: Type Number, expected Array" in the
// 2026-09-29 in-game RPT. The array is the [type, index] pair, which is the
// form CBA itself writes at cba_events/fnc_removeBISPlayerEventHandler.sqf:42
// and cba_diagnostic/fnc_removeUnitTrackProjectiles.sqf:37. The unary
// removeEventHandler [object, index] does not parse on this engine.
if (_object getVariable [_idVar, -1] >= 0) then {
    _object removeEventHandler [_eventName, _object getVariable _idVar];
};
_object setVariable [_idVar, _object addEventHandler [_eventName, _eventCode]];
true
