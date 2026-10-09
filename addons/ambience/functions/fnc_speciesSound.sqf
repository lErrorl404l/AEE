#include "..\script_component.hpp"

/*
Species-to-sound map (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It maps one species group to the vanilla media that exist for it, read from
the generated asset map (asset_map.sqf).  The group is the sound_group the
ecology corpus carries, not the retired sound-context key.

Media rules.  A raw file path (it contains a dot) is returned.  A CfgSFX class
is not: createSoundSourceLocal needs a CfgVehicles wrapper and vanilla ships
none for these classes, so a class entry is dropped.  An UNKNOWN recording is
never returned.

Platform gate.  A path under a3\sounds_f_enoch needs the Enoch platform.  The
caller passes the loaded platform tokens, for example ["enoch"]; an Enoch
path is dropped unless "enoch" is present.  A deer or wolf group with no
available media falls back to the base-game night bed and is reported as a
gap.  The water group has no confirmed non-silent recording, so it returns
no media and the gap is true.

Arguments:
  0: String - the species group (an asset-map sound group id)
  1: Array  - the loaded platform tokens, for example ["enoch"]
  2: Array  - the asset-map rows (see asset_map.sqf)

Returns:
  Array - [media, gap]; media is an array of vanilla .wss paths, gap is true
          when the group has no available media of its own.
*/

params [
    ["_group", "", [""]],
    ["_platforms", [], [[]]],
    ["_assetMap", [], [[]]]
];

private _contains = {
    params ["_haystack", "_needle"];
    private _h = toLower _haystack;
    private _n = toLower _needle;
    private _hl = count _h;
    private _nl = count _n;
    if (_nl > _hl) exitWith { false };
    private _found = false;
    for "_i" from 0 to (_hl - _nl) do {
        if ((_h select [_i, _nl]) == _n) then { _found = true; };
    };
    _found
};

private _enoch = false;
for "_p" from 0 to ((count _platforms) - 1) do {
    if (([_platforms select _p, "enoch"] call _contains)) then { _enoch = true; };
};

// Resolve one group's raw paths for the given platform state.  A CfgSFX
// entry has no dot and is dropped; an UNKNOWN recording is dropped whole.
private _resolve = {
    params ["_grp", "_withEnoch", "_map", "_has"];
    private _identity = "";
    private _media = [];
    for "_i" from 0 to ((count _map) - 1) do {
        private _row = _map select _i;
        if (((_row select 0) == "sound") && ((_row select 1) == _grp)) then {
            _identity = _row select 2;
            private _found = _row select 3;
            if (_found isEqualType []) then { _media = _found; };
        };
    };
    private _paths = [];
    if (_identity != "UNKNOWN") then {
        for "_i" from 0 to ((count _media) - 1) do {
            private _entry = _media select _i;
            if (_entry isEqualType "") then {
                if (([_entry, "."] call _has)) then {
                    if ((!([_entry, "sounds_f_enoch"] call _has)) || _withEnoch) then {
                        _paths pushBack _entry;
                    };
                };
            };
        };
    };
    _paths
};

private _media = [_group, _enoch, _assetMap, _contains] call _resolve;
private _gap = false;
if (_media isEqualTo []) then {
    _gap = true;
    // An Enoch-only mammal call with no own media falls back to the base
    // night bed.  The base set is not a deer or wolf voice, so the gap stays.
    if ((_group == "deer") || (_group == "wolf")) then {
        _media = ["night_insect", false, _assetMap, _contains] call _resolve;
    };
};

[_media, _gap]
