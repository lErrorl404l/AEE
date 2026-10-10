#include "..\script_component.hpp"
// Attaches a raw BIS engine event handler to every object of a class: the
// ones that already exist, and the ones created later.
//
// WHY AEE INSTALLS ITS OWN, measured on CBA v3.19.0 build 260808 on 2026-09-29:
//   - CBA_fnc_addEventHandler received 0 of the 3 real engine Init events a
//     probe raised, and fired once only when the bus was driven by hand, so
//     the bus is sound but nothing emits engine event names onto it.
//   - HandleDamage is absent from XEH_EVENTS and
//     Extended_HandleDamage_EventHandlers is commented out in cba_xeh, so
//     CBA_fnc_addClassEventHandler returns false for it. Measured.
//   - A raw BIS addEventHandler cannot be attached to a class name. The engine
//     rejects it: "addeventhandler: Type String, expected Object,Group".
// Init is in XEH_EVENTS, so a class Init handler is the one mechanism that
// reaches a specific object. This mirrors CBA's own XEH shape.
//
// The spec list is FLAT and self-describing, [class, eventName, eventCode,
// key], so the Init handler never needs the class name: it matches each spec
// by isKindOf against the object it was handed. The first version keyed the
// list by class and read the class back out of _this select 1, which is out of
// range because CBA hands an Init handler an array of the object.
params ["_class", "_eventName", "_eventCode", "_key"];

if (_class isEqualTo "") exitWith {false};
if (_eventName isEqualTo "") exitWith {false};
if (_eventCode isEqualTo {}) exitWith {false};
if (_key isEqualTo "") exitWith {false};

// Keyed on _key, so two addons can install the same event on the same class
// without removing each other, and so a second call replaces rather than
// stacks.
private _specs = missionNamespace getVariable [QGVAR(objectEngineHandlerSpecs), []];

private _replaced = false;
private _kept = [];
{
    if (_x select 3 isEqualTo _key) then {
        _kept pushBack [_class, _eventName, _eventCode, _key];
        _replaced = true;
    } else {
        _kept pushBack _x;
    };
} forEach _specs;
if (!_replaced) then {
    _kept pushBack [_class, _eventName, _eventCode, _key];
};
missionNamespace setVariable [QGVAR(objectEngineHandlerSpecs), _kept];

// Objects that already exist, so a module that initialises late still covers
// the whole map rather than only what spawns after it.
{
    if (_x isKindOf _class) then {
        [_x, _eventName, _eventCode, _key] call EFUNC(lib,attachObjectEngineHandler);
    };
} forEach (entities [[], [], true, false]);

// Objects created later. The retroactive flag makes CBA run Init for the
// existing ones too, so one registration covers both cases.
if !(missionNamespace getVariable [QGVAR(objectEngineHandlersHooked), false]) then {
    missionNamespace setVariable [QGVAR(objectEngineHandlersHooked), true];
    ["AllVehicles", "Init", {
        params ["_object"];
        if (isNil "_object") exitWith {};
        if (isNull _object) exitWith {};
        {
            if (_object isKindOf (_x select 0)) then {
                [_object, _x select 1, _x select 2, _x select 3] call EFUNC(lib,attachObjectEngineHandler);
            };
        } forEach (missionNamespace getVariable [QGVAR(objectEngineHandlerSpecs), []]);
    }, true, [], true] call CBA_fnc_addClassEventHandler;
};

true
