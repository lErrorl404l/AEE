#include "..\script_component.hpp"
/*
Device identity matcher (night vision, thermal and optic).

Function: aee_nightvision_fnc_getDeviceMatch.

This file is GENERATED. The generator tools/validation/gen_device_data.py
writes it from the validated device catalogue under data/device/. Do not
edit it by hand. Edit the corpus and regenerate it.

The matcher resolves a device class to a real device entry. It runs an
ordered ladder. The first layer that yields exactly one candidate wins. A
weaker layer runs only when every stronger layer yields none. A tie at any
layer returns an empty array.

  exact_class   the normalised class equals a mapped class name.        1
  alias         a classname token equals a catalogue alias.             2
  keyword       the query holds a keyword of 4 or more characters.      3
  closest       the longest alias or keyword substring of the query,
                at least 4 characters, with a strictly lower
                runner-up score. A tie returns [].                    4

The vehicle matcher runs a fifth inheritance layer. A device row names no
supported game class token, so that layer has no meaning here and is
absent. The order and the tie rule of the remaining layers are the same.

The table is filtered by family before the ladder runs, so one class cannot
tie across two families. The ENVG-B is both a night vision device and a
thermal device, and a caller states which one it wants.

A row has seven columns:

  0 device_id         string, the stable catalogue key
  1 family            string, "nvg", "thermal" or "optic"
  2 class_names       string, "|" separated normalised class names
  3 aliases           string, "|" separated normalised catalogue aliases
  4 keywords          string, "|" separated normalised catalogue keywords
  5 source_record_id  string, the source id of the first held value
  6 value_row         array of values, by family

value_row, nvg      [output_colour, resolution_lpmm, snr, halo_mm]
value_row, thermal  [netd_c, resolution_x, resolution_y, refresh_hz,
                     cooled, weight_kg, band]
value_row, optic    [magnification, objective_mm, fov_deg, weight_kg,
                     exit_pupil_mm, active]

A missing value is a labelled zero for a number or an empty string for a
word, never a refusal of the record. The grade of every field is in the
corpus and in the coverage artefact.

Returns [device_id, family, confidence, matched_by, source_record_id,
valueRow], or []. The class displayName is identity text only. The matcher
reads no config value as a figure and no source registry.

Arguments:
  0: className (STRING, the device classname, default "")
  1: family (STRING, the optional family filter, default "")
*/
params [["_className", "", [""]], ["_family", "", [""]]];
if (_className == "") exitWith { [] };

private _normalise = {
    params ["_text"];
    private _out = "";
    {
        if ((_x >= 48 && _x <= 57) || (_x >= 97 && _x <= 122)) then {
            _out = _out + toString [_x];
        };
    } forEach (toArray (toLower _text));
    _out
};

private _key = [_className] call _normalise;
if (_key == "") exitWith { [] };

// Identity text only: the class name, the raw display name and its
// localised stringtable text. A class stores a $STR key in displayName,
// so all three are needed. None carries a figure.
private _rawName = "";
{
    private _cfg = configFile >> _x >> _className;
    if (isClass _cfg) exitWith {
        _rawName = getText (_cfg >> "displayName");
    };
} forEach ["CfgWeapons", "CfgVehicles"];
private _localName = if ((_rawName select [0,1]) == "$") then { localize _rawName } else { _rawName };
private _identity = _className + " " + _rawName + " " + _localName;
private _query = [_identity] call _normalise;
private _tokens = [];
{
    private _token = _x call _normalise;
    if (_token != "") then { _tokens pushBack _token; };
} forEach (_identity splitString " _-.");

private _tableAll = [
    ["active_nv", "optic", "1pn51|1pn93|1pn120|nvs", "1pn51|1pn93|1pn120|nvs|nvg|thermal", "1pn51|1pn93|1pn120|nvs|nvg|thermal", "aee_sensor_device_library", [3.5, 50, 5, 2.0, 14, "active"]],
    ["anvis9", "nvg", "anavs9|anvis|avs9", "anvis|avs9", "anvis|avs9", "elbit_anvis9", ["", 64, 0, 0.5533]],
    ["catherine", "thermal", "catherinemp|catherine", "catherine", "catherine", "aee_sensor_device_library", [0.025, 1280, 1024, 50, "cooled", 7.9, "lwir"]],
    ["coti", "thermal", "anpas29coti|coti|pas29", "coti|pas29", "coti|pas29", "aee_sensor_device_library", [0.05, 320, 240, 30, "uncooled", 0.15, "lwir"]],
    ["ecoti", "thermal", "ecoti", "ecoti", "ecoti", "safran_ecoti_datasheet", [0, 640, 480, 0, "uncooled", 0.125, "lwir"]],
    ["envg_thermal", "thermal", "envgb|anpsq42", "envg|envgb", "envg|psq42", "aee_sensor_device_library", [0.04, 640, 480, 30, "uncooled", 1.133, "lwir"]],
    ["envgb", "nvg", "envgb|envg|anpsq42|anpsq44|nvgogglesb", "envg|envgb|psq42|psq44|nvgogglesb", "envg|psq42|psq44|nvgogglesb", "l3harris_envgb", ["white", 72, 32, 0.5533]],
    ["fixed_10x", "optic", "leupoldmark4|mark4|10x", "mark4|10x", "mark4|10x", "aee_sensor_device_library", [10, 40, 3.5, 0.68, 4, "passive"]],
    ["flir_recon", "thermal", "flirreconv|recon", "recon", "recon", "aee_sensor_device_library", [0.025, 640, 480, 50, "cooled", 1.9, "mwir"]],
    ["flir_scout", "thermal", "flirscoutiii640|scout", "scout", "scout", "aee_sensor_device_library", [0.05, 640, 512, 30, "uncooled", 0.34, "lwir"]],
    ["gpnvg18", "nvg", "gpnvg18|panogoggles|nvwide", "gpnvg|pano|nvwide", "gpnvg|nvwide|panoramic", "l3harris_gpnvg18", ["white", 64, 0, 0.5533]],
    ["helion", "thermal", "pulsarhelion|helion", "helion", "helion", "aee_sensor_device_library", [0.04, 384, 288, 50, "uncooled", 0.5, "lwir"]],
    ["holographic", "optic", "eotechexps3|exps|553", "eotech|exps|553", "eotech|exps|553", "aee_sensor_device_library", [1, 0, 0, 0.32, 0, "passive"]],
    ["jim_lr", "thermal", "jimlr|jim", "jim", "jimlr|safranjim", "aee_sensor_device_library", [0.025, 384, 288, 50, "cooled", 2.8, "mwir"]],
    ["m145_class", "optic", "m145mgo|c79|mgo", "m145|c79|mgo", "m145|c79|mgo", "aee_sensor_device_library", [3.4, 28, 8.5, 0.68, 8.2, "passive"]],
    ["mowgli", "thermal", "1pn97|mowgli", "mowgli|1pn97", "mowgli|1pn97", "aee_sensor_device_library", [0.05, 320, 240, 50, "uncooled", 1.5, "lwir"]],
    ["pas13_base", "thermal", "anpas13|pas13", "", "", "aee_sensor_device_library", [0.05, 640, 480, 30, "uncooled", 1.134, "lwir"]],
    ["pas13_v1", "thermal", "anpas13ev1|pas13v1", "pas13v1", "pas13v1|pas13gv1", "aee_sensor_device_library", [0.05, 320, 240, 30, "uncooled", 0.885, "lwir"]],
    ["pas13_v2", "thermal", "anpas13ev2|pas13v2", "pas13v2", "pas13v2|pas13gv2", "aee_sensor_device_library", [0.05, 640, 480, 30, "uncooled", 1.134, "lwir"]],
    ["pas13_v3", "thermal", "anpas13ev3|pas13v3", "pas13v3", "pas13v3|pas13gv3", "aee_sensor_device_library", [0.05, 640, 480, 30, "uncooled", 1.497, "lwir"]],
    ["prism_4x", "optic", "acog|ta31|ta11|m150rco|susat|zf|4x", "acog|ta31|ta11|rco|susat|zf|4x", "acog|ta31|ta11|rco|susat|4x", "aee_sensor_device_library", [4, 32, 7, 0.42, 8, "passive"]],
    ["pso_class", "optic", "pso1|posp|1p78|kashtan|1p69|hyperon", "pso|posp|1p78|kashtan|1p69|hyperon", "pso|posp|1p78|kashtan|1p69|hyperon", "aee_sensor_device_library", [4, 24, 6, 0.6, 6, "passive"]],
    ["pvs14", "nvg", "anpvs14|pvs14", "pvs14", "pvs14", "elbit_pvs14", ["", 64, 31, 0.5533]],
    ["pvs15", "nvg", "anpvs15|pvs15", "pvs15", "pvs15", "l3harris_pvs15", ["", 64, 0, 0.5533]],
    ["pvs31", "nvg", "anpvs31|pvs31|pvs31a|pvs31c|nvgw", "pvs31|nvgw", "pvs31|nvgw", "l3harris_pvs31c", ["white", 72, 33, 0.5533]],
    ["pvs5", "nvg", "anpvs5|pvs5", "pvs5", "pvs5", "aee_sensor_device_library", ["", 28, 0, 0.2388]],
    ["pvs7", "nvg", "anpvs7|pvs7", "pvs7", "pvs7", "anvs_pvs7", ["", 0, 12, 0.2388]],
    ["red_dot", "optic", "compm4|m68|t2|1p87|reddot|reflex", "compm|t2|m68|1p87|reddot|reflex", "compm|m68|1p87|reddot|reflex", "aee_sensor_device_library", [1, 23, 0, 0.27, 0, "passive"]],
    ["russian_1pn138", "nvg", "1pn138|1pn97", "1pn138|1pn97", "1pn138|1pn97", "", ["", 0, 0, 0]],
    ["russian_1pn63", "nvg", "1pn63|1pn58", "1pn63|1pn58", "1pn63|1pn58", "aee_sensor_device_library", ["", 30, 0, 0]],
    ["russian_1pn93", "nvg", "1pn93", "1pn93", "1pn93", "", ["", 0, 0, 0]],
    ["shakhin", "thermal", "1pn139|1pn140|shakhin", "shakhin|1pn139|1pn140", "shakhin|1pn139|1pn140", "aee_sensor_device_library", [0.05, 640, 480, 50, "uncooled", 2.2, "lwir"]],
    ["sophie", "thermal", "thalessophie|sophie", "sophie", "sophie", "aee_sensor_device_library", [0.05, 384, 288, 50, "uncooled", 2.0, "lwir"]],
    ["sophie_ultima", "thermal", "sophieultima|ultima", "ultima", "ultima", "aee_sensor_device_library", [0.025, 640, 512, 50, "cooled", 2.5, "mwir"]],
    ["thermion", "thermal", "pulsarthermionxp50|thermion", "thermion", "thermion", "aee_sensor_device_library", [0.025, 640, 480, 50, "uncooled", 0.9, "lwir"]],
    ["vanilla_gen2", "nvg", "nvgogglesopfor|nvgen2", "", "nvgen2|nvgogglesopfor", "cui_2012_halo", ["", 0, 0, 0.2388]],
    ["vanilla_gen3", "nvg", "nvgoggles|nvgogglesindep|nvgen3", "", "nvgen3|nvgogglesindep", "cui_2012_halo", ["", 0, 0, 0.5533]],
    ["variable_1_4x", "optic", "specterdr|14x|16x|lds", "specterdr|14|16|1x4|1x6|lds", "specterdr|14x|16x|lds", "aee_sensor_device_library", [4, 30, 8, 0.6, 7.5, "passive"]],
    ["variable_sniper", "optic", "atacr|pmii|mark5|525x56", "atacr|pmii|pm2|mark5|525", "atacr|pmii|mark5|525", "aee_sensor_device_library", [10, 56, 3, 1.05, 5.6, "passive"]]
];

// Filter by family so a class two families share cannot tie.
private _table = if (_family == "") then { _tableAll } else {
    _tableAll select {(_x select 1) == _family}
};

// [device_id, family, confidence, matched_by, source_record_id, value_row]
private _result = {
    params ["_row", "_confidence", "_layer"];
    [_row select 0, _row select 1, _confidence, _layer,
     _row select 5, _row select 6]
};

private _candidates = [];

// Layer 1: exact class. The normalised class equals a mapped class name.
{
    _x params ["_device", "_devFamily", "_classes", "_aliases", "_keywords", "_source", "_values"];
    if (((_classes splitString "|") find _key) >= 0) then {
        _candidates pushBack _x;
    };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 1, "exact_class"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 2: alias. A query token equals a catalogue alias.
_candidates = [];
{
    _x params ["_device", "_devFamily", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _hit = false;
    {
        if (_x in _tokens) then { _hit = true; };
    } forEach (_aliases splitString "|");
    if (_hit) then { _candidates pushBack _row; };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 2, "alias"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 3: keyword. The query holds a keyword of at least four characters.
_candidates = [];
{
    _x params ["_device", "_devFamily", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _hit = false;
    {
        if ((count _x) >= 4 && {_query find _x >= 0}) then { _hit = true; };
    } forEach (_keywords splitString "|");
    if (_hit) then { _candidates pushBack _row; };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 3, "keyword"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 4: closest. The longest alias or keyword substring of the query,
// at least four characters, with a strictly lower runner-up score.
private _bestRow = [];
private _bestScore = 0;
private _runnerUp = 0;
private _tie = false;
{
    _x params ["_device", "_devFamily", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _score = 0;
    {
        if ((count _x) >= 4 && {count _x > _score} && {_query find _x >= 0}) then {
            _score = count _x;
        };
    } forEach ((_aliases + "|" + _keywords) splitString "|");
    if (_score >= 4) then {
        if (_score > _bestScore) then {
            _runnerUp = _bestScore;
            _bestScore = _score;
            _bestRow = _row;
            _tie = false;
        } else {
            if (_score == _bestScore) then { _tie = true; };
            if (_score > _runnerUp) then { _runnerUp = _score; };
        };
    };
} forEach _table;
if ((_bestRow isNotEqualTo []) && {!_tie} && _bestScore > _runnerUp) exitWith {
    [_bestRow, 4, "closest"] call _result
};
[]
