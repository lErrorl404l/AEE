#include "..\script_component.hpp"

/*
Attach a looping emitter to each active animal near the listener (task T27).

Client-only wiring.  It keeps the sustained emitters attached and bounded.  For
each live animal inside the emitter radius it resolves the animal's looping
source class, then fnc_emitterPlan decides which emitters to create, keep and
release.  An emitter is created once with createSoundSourceLocal and attached
to the animal, so a sustained call tracks the animal as it moves.  It is
recreated only when the class changes, and deleted when the animal despawns,
leaves the radius or falls over the cap, so an emitter cannot leak.

There is no per-species branch here.  The class comes from the asset map
through fnc_emitterClass, so a custom animal that supplies a looping class
gets a sustained emitter with no extra code.  The create budget bounds the
attachments made in one tick, and the plan bounds the live total.

Arguments:
  0: Array  - the listener position
  1: Number - the per-tick create budget

Returns:
  Number - the number of live attached emitters
*/

params [
    ["_position", [0, 0, 0], [[]]],
    ["_budget", WILDLIFE_EMITTER_CAP, [0]]
];

if (!hasInterface) exitWith { 0 };

private _fauna = missionNamespace getVariable [QGVAR(fauna), []];
if !(_fauna isEqualType []) then { _fauna = []; };

private _registry = missionNamespace getVariable [QGVAR(emitters), []];
if !(_registry isEqualType []) then { _registry = []; };

private _assetMap = missionNamespace getVariable [QGVAR(assetMap), []];
if !(_assetMap isEqualType []) then { _assetMap = []; };

// The active list is [id, class, distance] for each live animal inside the
// radius whose species resolves to a looping class.
private _active = [];
for "_i" from 0 to ((count _fauna) - 1) do {
    private _entry = _fauna select _i;
    if ((_entry isEqualType []) && ((count _entry) >= 2)) then {
        private _id = _entry select 0;
        private _agent = _entry select 1;
        if (!isNull _agent) then {
            private _distance = (getPos _agent) distance _position;
            if (_distance <= WILDLIFE_EMITTER_RADIUS) then {
                private _group = _agent getVariable [QGVAR(soundGroup), ""];
                if !(_group isEqualType "") then { _group = ""; };
                private _class = [_group, _assetMap] call FUNC(emitterClass);
                if (_class != "") then {
                    _active pushBack [_id, _class, _distance];
                };
            };
        };
    };
};

// The registry rows reduce to the plan's [id, key] shape.
private _keys = [];
for "_i" from 0 to ((count _registry) - 1) do {
    private _row = _registry select _i;
    if ((_row isEqualType []) && ((count _row) >= 3)) then {
        _keys pushBack [(_row select 0), (_row select 1)];
    };
};

private _plan = [
    _keys, _active, WILDLIFE_EMITTER_CAP, WILDLIFE_EMITTER_RADIUS
] call FUNC(emitterPlan);
private _create = _plan select 0;
private _release = _plan select 2;

// Release first, so a changed class or a despawn frees its source before a
// new one is created.  The kept rows stay attached and untouched.
private _kept = [];
for "_i" from 0 to ((count _registry) - 1) do {
    private _row = _registry select _i;
    private _drop = false;
    for "_r" from 0 to ((count _release) - 1) do {
        if ((_release select _r) == (_row select 0)) then { _drop = true; };
    };
    if (_drop) then {
        private _source = _row select 2;
        if (!isNull _source) then { deleteVehicle _source; };
    } else {
        _kept pushBack _row;
    };
};

// Create the missing emitters, bounded by the per-tick budget.  The source
// class is generic: it is whatever the asset map supplied for the group.
private _created = 0;
for "_i" from 0 to ((count _create) - 1) do {
    if (_created < _budget) then {
        private _spec = _create select _i;
        private _id = _spec select 0;
        private _class = _spec select 1;

        private _agent = objNull;
        for "_f" from 0 to ((count _fauna) - 1) do {
            private _entry = _fauna select _f;
            if ((_entry isEqualType []) && ((count _entry) >= 2)) then {
                if (((_entry select 0) == _id) && (isNull _agent)) then {
                    _agent = _entry select 1;
                };
            };
        };

        if (!isNull _agent) then {
            private _source = createSoundSourceLocal [_class, getPosASL _agent, [], 0];
            if (!isNull _source) then {
                _source attachTo [_agent, [0, 0, 0]];
                _kept pushBack [_id, _class, _source];
                _created = _created + 1;
            };
        };
    };
};

missionNamespace setVariable [QGVAR(emitters), _kept];
count _kept
