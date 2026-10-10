#include "..\..\script_component.hpp"

/*
Register a scalar-field emitter (issue #116).  This is the public source API:
fire, grenade, CBRN and gas emitters all push their emission into one engine
through this function instead of each modelling its own plume.

The source is queued on the shared registry and consumed by
FUNC(updateScalarFields) on the next tick, which deposits it into the field's
grid over the given radius.  An emitter that fires between ticks is not lost:
the source carries a time-to-live and is injected on the next tick that runs
inside that window.

Arguments:
  0: key       (STRING) field to feed ("smoke", "dust", or a field the engine
               does not yet own, for a later emitter)
  1: position  (ARRAY)  emission position, world coordinates, [x, y] or
               [x, y, z]; only x and y are used by the 2D grid
  2: strength  (NUMBER) emission strength in field units; added to each cell
               inside the radius, scaled by a linear falloff
  3: radiusM   (NUMBER) emission radius, metres
  4: ttlTicks  (NUMBER, optional) ticks the source stays live, default 1

Return:
  BOOL - true when the source was queued.
*/

params [
    ["_key", "", [""]],
    ["_position", [0, 0], [[]]],
    ["_strength", 1, [0]],
    ["_radiusM", 100, [0]],
    ["_ttlTicks", 1, [0]]
];

if (_key isEqualTo "") exitWith { false };
if (count _position < 2) exitWith { false };
if !(GVAR(scalarFieldsEnabled)) exitWith { false };

private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
if !(_interval isEqualType 0) then { _interval = 5; };

private _sources = missionNamespace getVariable [QGVAR(scalarSources), []];
_sources pushBack [
    _key,
    _position select 0,
    _position select 1,
    _strength,
    _radiusM max 0,
    diag_tickTime + (_ttlTicks max 0) * (_interval max 1)
];
missionNamespace setVariable [QGVAR(scalarSources), _sources];

true
