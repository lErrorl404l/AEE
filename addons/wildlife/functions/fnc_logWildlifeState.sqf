#include "..\script_component.hpp"

/*
Consolidated wildlife and AI state line.

One grep of "wildlife state" answers whether each gate is on, what the bed
and the field are, and what the force hooks hold.  The line carries the AI
agent count, the disturbance field, the wildlife tick state, the fauna and
sound counts, the gates and the force values.  It is emitted once at
AEE_LOG_INFO on the first tick, then at AEE_LOG_DEBUG every tick, so the
state is readable without the trace switch and cheap with it off.

The line never changes state and never broadcasts.  It reads the registries
that the tick and the AI substrate publish, with safe defaults so the first
line is valid before any agent, animal or sound exists.

Debug hooks, set on missionNamespace:
  - aee_wildlife_forceBiome    String, force the biome
  - aee_wildlife_forceNight    Bool or Number, force night
  - aee_wildlife_forceSilence  Number, 0..1 forced silence, -1 off
  - aee_wildlife_forceSpook    Array, a forced spook position
  - aee_wildlife_forceSpecies  String, force the species row

Arguments:
  0: Array - the wildlife tick state [bedKey, gain, disturbance, spook, range]

Returns:
  Nothing.
*/

// The wildlife tick runs every tickInterval and the line reads the AI
// registry, the disturbance field, the fauna list, the sound instances, the
// gates and the force hooks.  With tracing off, skip the whole build after
// the first call.  The first call still emits the INFO line.  Tracing on
// always rebuilds the line.
if (!(AEE_TRACE_ON || {missionNamespace getVariable ["aee_ai_logDebug", false]}) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

params [["_state", [], [[]]]];

_state params [
    ["_bedKey", ""],
    ["_gain", 0],
    ["_disturbance", 0],
    ["_spook", false],
    ["_spookRange", 0]
];

private _agents = missionNamespace getVariable [QEGVAR(ai,agents), []];
if !(_agents isEqualType []) then { _agents = []; };

// The field is [key, magnitude, time] per cell.  Count and largest decayed
// magnitude come from one walk.  The 45 s half-life matches the tick sample.
private _field = missionNamespace getVariable [QEGVAR(ai,disturbance), []];
if !(_field isEqualType []) then { _field = []; };
private _fieldCount = count _field;
private _fieldMax = 0;
private _now = CBA_missionTime;
{
    if (_x isEqualType []) then {
        if ((count _x) >= 3) then {
            private _decayed = [(_x select 1), _now - (_x select 2), 45] call EFUNC(ai,stimulusDecay);
            if (_decayed > _fieldMax) then { _fieldMax = _decayed; };
        };
    };
} forEach _field;

private _forceDecide = missionNamespace getVariable ["aee_ai_forceDecide", -1];
if !(_forceDecide isEqualType 0) then { _forceDecide = -1; };

private _fauna = missionNamespace getVariable [QGVAR(fauna), []];
if !(_fauna isEqualType []) then { _fauna = []; };
private _faunaLive = 0;
for "_i" from 0 to ((count _fauna) - 1) do {
    private _entry = _fauna select _i;
    if (_entry isEqualType []) then {
        if ((count _entry) >= 2) then {
            if (!isNull (_entry select 1)) then { _faunaLive = _faunaLive + 1; };
        };
    };
};
private _faunaCap = missionNamespace getVariable [QGVAR(maxAnimals), 16];
if !(_faunaCap isEqualType 0) then { _faunaCap = 16; };

private _instances = missionNamespace getVariable [QGVAR(soundInstances), []];
if !(_instances isEqualType []) then { _instances = []; };
private _soundLive = 0;
{
    if (_x isEqualType 0) then {
        if (_x > _now) then { _soundLive = _soundLive + 1; };
    };
} forEach _instances;

private _ambientSource = missionNamespace getVariable [QGVAR(ambientSource), objNull];
private _ambientPresent = !isNull _ambientSource;

private _enabled = missionNamespace getVariable [QGVAR(enabled), true];
if !(_enabled isEqualType true) then { _enabled = true; };
private _ambient = missionNamespace getVariable [QGVAR(ambientEnabled), true];
if !(_ambient isEqualType true) then { _ambient = true; };
private _animals = missionNamespace getVariable [QGVAR(animalsEnabled), false];
if !(_animals isEqualType true) then { _animals = false; };
private _density = missionNamespace getVariable [QGVAR(density), 1.0];
if !(_density isEqualType 0) then { _density = 1.0; };
// The interval is read with the gates so the on-demand monitor reports one value.
private _tickInterval = missionNamespace getVariable [QGVAR(tickInterval), 1.0];
if !(_tickInterval isEqualType 0) then { _tickInterval = 1.0; };

private _forceBiome = missionNamespace getVariable ["aee_wildlife_forceBiome", ""];
if !(_forceBiome isEqualType "") then { _forceBiome = ""; };
private _forceNight = missionNamespace getVariable ["aee_wildlife_forceNight", 0];
if !((_forceNight isEqualType 0) || {_forceNight isEqualType false}) then { _forceNight = 0; };
private _forceSilence = missionNamespace getVariable ["aee_wildlife_forceSilence", -1];
if !(_forceSilence isEqualType 0) then { _forceSilence = -1; };
private _forceSpook = missionNamespace getVariable ["aee_wildlife_forceSpook", []];
if !(_forceSpook isEqualType []) then { _forceSpook = []; };
private _forceSpecies = missionNamespace getVariable ["aee_wildlife_forceSpecies", ""];
if !(_forceSpecies isEqualType "") then { _forceSpecies = ""; };

// The tick duration is written by fnc_wildlifeTick only inside the trace
// gate, so the line shows the last recorded tick and "-" when tracing is off.
private _tickField = "-";
if (AEE_TRACE_ON) then {
    private _lastTickMs = missionNamespace getVariable [QGVAR(lastTickMs), -1];
    if (_lastTickMs isEqualType 0) then {
        if (_lastTickMs >= 0) then { _tickField = round _lastTickMs; };
    };
};

private _logMsg = format [
    "wildlife state | ai=agents:%1 field=%2 max=%3 decide=%4 | bed=%5 gain=%6 disturbance=%7 spook=%8 range=%9 | fauna=%10/%11 sound=%12/%13 ambient=%14 | gates=on=%15 ambient=%16 animals=%17 density=%18 | forces=biome=%19 night=%20 silence=%21 spook=%22 species=%23 | tick=%24ms",
    count _agents, _fieldCount, round (_fieldMax * 100) / 100, round _forceDecide,
    _bedKey, round (_gain * 100) / 100, round (_disturbance * 100) / 100, _spook, round _spookRange,
    _faunaLive, _faunaCap, _soundLive, WILDLIFE_SOUND_INSTANCE_CAP, _ambientPresent,
    _enabled, _ambient, _animals, round (_density * 100) / 100,
    _forceBiome, _forceNight, round (_forceSilence * 100) / 100, _forceSpook, _forceSpecies,
    _tickField
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
