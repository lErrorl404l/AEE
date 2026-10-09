#include "..\script_component.hpp"

/*
Looping-source class resolver (wildlife ecology, task T27).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It maps a species sound group to the vanilla looping source class for that
group, if one exists.  A media entry without a dot is a CfgSFX or CfgVehicles
class, which is the only form createSoundSourceLocal accepts; a raw .wss path
with a dot is a one-shot and is not a looping source.  A group with no class
entry returns the empty string, so the caller creates no sustained emitter.

This keeps the emitter generic: the class comes from the data, never from a
per-species branch in SQF, so a custom animal that adds a looping class gets a
sustained emitter with no extra code.

Arguments:
  0: String - the species sound group (an asset-map sound key)
  1: Array  - the asset-map rows (see asset_map.sqf)

Returns:
  String - the looping source class, or "" when the group has none
*/

params [
    ["_group", "", [""]],
    ["_assetMap", [], [[]]]
];

if (_group == "") exitWith { "" };

private _source = "";
for "_i" from 0 to ((count _assetMap) - 1) do {
    if (_source == "") then {
        private _row = _assetMap select _i;
        if ((_row isEqualType []) && ((count _row) >= 4)) then {
            if (((_row select 0) == "sound") && ((_row select 1) == _group)) then {
                private _media = _row select 3;
                if (_media isEqualType []) then {
                    for "_m" from 0 to ((count _media) - 1) do {
                        private _entry = _media select _m;
                        if ((_source == "") && (_entry isEqualType "")) then {
                            // A class has no dot; a raw file path has one.
                            private _hasDot = false;
                            for "_c" from 0 to ((count _entry) - 1) do {
                                if ((_entry select [_c, 1]) == ".") then { _hasDot = true; };
                            };
                            if (!_hasDot) then { _source = _entry; };
                        };
                    };
                };
            };
        };
    };
};

_source
