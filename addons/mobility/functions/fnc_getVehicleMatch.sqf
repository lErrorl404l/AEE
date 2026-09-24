#include "..\script_component.hpp"
/*
Vehicle identity matcher (issue #117).

Function: aee_mobility_fnc_getVehicleMatch.

This file is GENERATED. The generator tools/validation/gen_vehicle_data.py
writes it from the validated vehicle catalogue under data/vehicle/. Do not
edit it by hand. Edit the corpus and regenerate it.

The matcher resolves a game class to a real vehicle entry. It runs an
ordered ladder. The first layer that yields exactly one candidate wins. A
weaker layer runs only when every stronger layer yields none. A tie at any
layer returns an empty array.

  exact_class   the normalised class equals a mapped game class.      1
  alias         a classname or displayName token equals an alias.     2
  keyword       the query holds a keyword of 4 or more characters.    3
  inheritance   the class isKindOf the entry class token, and exactly
                one entry carries that token.                         4
  closest       the longest alias or keyword substring of the query,
                at least 4 characters, with a strictly lower
                runner-up score. A tie returns [].                    5

A row has nine columns:

  0 catalogue_id      string, the stable catalogue key
  1 variant_id        string, the variant key
  2 vehicle_type      string, "wheeled" or "tracked"
  3 class_token       string, the supported token or empty
  4 mapped_classes    string, "|" separated normalised game classes
  5 aliases           string, "|" separated normalised catalogue aliases
  6 keywords          string, "|" separated normalised catalogue keywords
  7 source_record_id  string, the source id of the operating weight value
  8 value_row         array of seven values, by vehicle type

value_row, wheeled  [operating_weight_kg, tyre_width_mm, tyre_diameter_mm,
                     ground_clearance_mm, net_power_kw, transmission_type,
                     grousers_state]
value_row, tracked  [operating_weight_kg, track_shoe_width_mm,
                     track_pitch_mm, ground_clearance_mm, net_power_kw,
                     transmission_type, grousers_state]

Column units: operating weight kg, widths and pitches mm, clearance mm,
net power kW, transmission_type enum (manual or automatic), grousers_state
enum (none, grousers or chains).

Returns [catalogue_id, variant_id, vehicle_type, confidence, matched_by,
source_record_id, valueRow], or []. The class displayName is identity text
only. The matcher reads no config value as a figure and no source registry.

Arguments:
  0: className (STRING, the CfgVehicles classname, default "")
*/
params [["_className", "", [""]]];
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

// Identity text only. The displayName broadens the query for the alias and
// keyword layers. It never carries a figure.
private _name = getText (configFile >> "CfgVehicles" >> _className >> "displayName");
private _query = [_className + " " + _name] call _normalise;
private _tokens = [];
{
    private _token = _x call _normalise;
    if (_token != "") then { _tokens pushBack _token; };
} forEach ((_className + " " + _name) splitString " _-.");

private _table = [
    ["cougar_4x4", "cougar_4x4", "wheeled", "", "", "cougar|cougar4x4|mrapcougar", "mrap|mineresistant|cougar|4x4", "gdls_cougar_4x4_datasheet", [15422, 395.0, 1179.5, 380, 246.080958, "automatic", ""]],
    ["hmmwv_m998", "hmmwv_m998", "wheeled", "", "", "m998|m998a1|hmmwv|humvee|m1038", "truck|utility|cargo|4x4|troopcarrier", "tm_9_2320_280_10", [2361, 0, 0, 410, 111.854981, "automatic", ""]],
    ["honda_civic_6gen_coupe", "honda_civic_6gen_coupe", "wheeled", "", "", "civiccoupe|hondaciviccoupe|civic2doorcoupe", "car|civilian|passengercar|coupe", "honda_civic_factory_service_manual_96_00", [1570, 0, 0, 150, 0, "", ""]],
    ["honda_civic_6gen_hatchback", "honda_civic_6gen_hatchback", "wheeled", "", "", "civichatchback|hondacivichatchback|civic2doorhatchback", "car|civilian|passengercar|hatchback", "honda_civic_factory_service_manual_96_00", [1495, 0, 0, 150, 0, "", ""]],
    ["honda_civic_6gen_sedan", "honda_civic_6gen_sedan", "wheeled", "", "car", "civic|hondacivic|hondacivicsedan|ej6|ej8", "car|civilian|passengercar|sedan", "honda_civic_factory_service_manual_96_00", [1540, 0, 0, 150, 0, "automatic", ""]],
    ["kawasaki_ninja_250r_ex250f", "kawasaki_ninja_250r_ex250f", "wheeled", "", "", "ninja250|ninja250r|ex250|ex250f|gpx250|gpx250r|kawasakininja250r", "motorcycle|ninja|sportbike", "kawasaki_ninja_250r_service_manual", [161, 0, 0, 155, 27.948831, "manual", "none"]],
    ["m1059", "m1059", "tracked", "", "", "m1059", "apc|carrier|tracked|smokegeneratorcarrier", "tm_9_2350_261_10", [11077, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m1064", "m1064", "tracked", "", "", "m1064", "apc|carrier|tracked|selfpropelled120mmmortarcarrier", "tm_9_2350_261_10", [12546, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m1068", "m1068", "tracked", "", "", "m1068", "apc|carrier|tracked|standardizedintegratedcommandpostsystem", "tm_9_2350_261_10", [12182, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m113a2", "m113a2", "tracked", "", "trackedapc", "m113|m113a2", "apc|carrier|tracked|armoredpersonnelcarrier", "tm_9_2350_261_10", [11353, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m1_abrams", "m1_abrams", "tracked", "", "", "m1|m1abrams|abrams|generalabrams", "tank|mbt|mainbattletank|105mm", "tm_9_2350_255_10", [54431, 0, 0, 483, 0, "automatic", ""]],
    ["m2_m3_bradley", "m2_m3_bradley", "tracked", "", "", "m2bradley|m3bradley|bradley|m2ifv|m3cfv", "ifv|cfv|infantryfightingvehicle|cavalryfightingvehicle|tracked|bradley", "tm_9_2350_252_10_1", [22285, 533, 152, 0, 372.849936, "automatic", "grousers"]],
    ["m577a2", "m577a2", "tracked", "", "", "m577a2", "apc|carrier|tracked|commandpostcarrier", "tm_9_2350_261_10", [11719, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m923", "m923", "wheeled", "", "", "m923", "truck|5ton|6x6|m939", "tm_9_2320_272_10", [9806, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m923a1", "m923a1", "wheeled", "", "", "m923a1", "truck|5ton|6x6|m939a1", "tm_9_2320_272_10", [10067, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m923a2", "m923a2", "wheeled", "", "truck", "m923|m923a2|m939|m939a2", "truck|cargo|5ton|6x6|dropside", "tm_9_2320_272_10", [9502, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m925", "m925", "wheeled", "", "", "m925", "truck|5ton|6x6|m939", "tm_9_2320_272_10", [10151, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m925a1", "m925a1", "wheeled", "", "", "m925a1", "truck|5ton|6x6|m939a1", "tm_9_2320_272_10", [10567, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m925a2", "m925a2", "wheeled", "", "", "m925a2", "truck|5ton|6x6|m939a2", "tm_9_2320_272_10", [10002, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m927", "m927", "wheeled", "", "", "m927", "truck|5ton|6x6|m939", "tm_9_2320_272_10", [12598, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m927a1", "m927a1", "wheeled", "", "", "m927a1", "truck|5ton|6x6|m939a1", "tm_9_2320_272_10", [11366, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m927a2", "m927a2", "wheeled", "", "", "m927a2", "truck|5ton|6x6|m939a2", "tm_9_2320_272_10", [10801, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m928", "m928", "wheeled", "", "", "m928", "truck|5ton|6x6|m939", "tm_9_2320_272_10", [12626, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m928a1", "m928a1", "wheeled", "", "", "m928a1", "truck|5ton|6x6|m939a1", "tm_9_2320_272_10", [11865, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m928a2", "m928a2", "wheeled", "", "", "m928a2", "truck|5ton|6x6|m939a2", "tm_9_2320_272_10", [11300, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m929", "m929", "wheeled", "", "", "m929", "truck|5ton|6x6|m939", "tm_9_2320_272_10", [11753, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m929a1", "m929a1", "wheeled", "", "", "m929a1", "truck|5ton|6x6|m939a1", "tm_9_2320_272_10", [11380, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m929a2", "m929a2", "wheeled", "", "", "m929a2", "truck|5ton|6x6|m939a2", "tm_9_2320_272_10", [10814, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m930", "m930", "wheeled", "", "", "m930", "truck|5ton|6x6|m939", "tm_9_2320_272_10", [12087, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m930a1", "m930a1", "wheeled", "", "", "m930a1", "truck|5ton|6x6|m939a1", "tm_9_2320_272_10", [11879, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m930a2", "m930a2", "wheeled", "", "", "m930a2", "truck|5ton|6x6|m939a2", "tm_9_2320_272_10", [11314, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m931", "m931", "wheeled", "", "", "m931", "truck|5ton|6x6|m939", "tm_9_2320_272_10", [10028, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m931a1", "m931a1", "wheeled", "", "", "m931a1", "truck|5ton|6x6|m939a1", "tm_9_2320_272_10", [9598, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m931a2", "m931a2", "wheeled", "", "", "m931a2", "truck|5ton|6x6|m939a2", "tm_9_2320_272_10", [9032, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m932", "m932", "wheeled", "", "", "m932", "truck|5ton|6x6|m939", "tm_9_2320_272_10", [10370, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m932a1", "m932a1", "wheeled", "", "", "m932a1", "truck|5ton|6x6|m939a1", "tm_9_2320_272_10", [10098, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m932a2", "m932a2", "wheeled", "", "", "m932a2", "truck|5ton|6x6|m939a2", "tm_9_2320_272_10", [9532, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m934", "m934", "wheeled", "", "", "m934", "truck|5ton|6x6|m939", "tm_9_2320_272_10", [13595, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m934a1", "m934a1", "wheeled", "", "", "m934a1", "truck|5ton|6x6|m939a1", "tm_9_2320_272_10", [13293, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m934a2", "m934a2", "wheeled", "", "", "m934a2", "truck|5ton|6x6|m939a2", "tm_9_2320_272_10", [12728, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m936", "m936", "wheeled", "", "", "m936", "truck|5ton|6x6|m939", "tm_9_2320_272_10", [17858, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m936a1", "m936a1", "wheeled", "", "", "m936a1", "truck|5ton|6x6|m939a1", "tm_9_2320_272_10", [17322, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m936a2", "m936a2", "wheeled", "", "", "m936a2", "truck|5ton|6x6|m939a2", "tm_9_2320_272_10", [16757, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m_atv_m1240", "m_atv_m1240", "wheeled", "", "mrap", "matv|m1240", "mrap|oshkosh|matv", "tm_9_2355_335_10", [11123, 395.0, 1179.5, 0, 275.908953, "automatic", ""]],
    ["m_atv_m1240a1", "m_atv_m1240a1", "wheeled", "", "", "matvm1240a1|m1240a1", "mrap|oshkosh|matv", "tm_9_2355_335_10", [12940, 0, 0, 0, 275.908953, "automatic", ""]],
    ["m_atv_m1245", "m_atv_m1245", "wheeled", "", "", "matvm1245|m1245", "mrap|oshkosh|matv", "tm_9_2355_335_10", [12325, 395.0, 1179.5, 0, 275.908953, "automatic", ""]],
    ["toyota_t100", "toyota_t100", "wheeled", "", "", "t100|toyotat100", "car|pickup|civilian|lighttruck", "toyota_t100_factory_service_manual_1996", [0, 0, 0, 0, 0, "manual", ""]]
];

// [catalogue_id, variant_id, vehicle_type, confidence, matched_by,
//  source_record_id, value_row]
private _result = {
    params ["_row", "_confidence", "_layer"];
    [_row select 0, _row select 1, _row select 2, _confidence, _layer,
     _row select 7, _row select 8]
};

private _candidates = [];

// Layer 1: exact class. The normalised class equals a mapped game class.
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    if (((_classes splitString "|") find _key) >= 0) then {
        _candidates pushBack _x;
    };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 1, "exact_class"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 2: alias. A query token equals a catalogue alias.
_candidates = [];
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
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
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _hit = false;
    {
        if ((count _x) >= 4 && {_query find _x >= 0}) then { _hit = true; };
    } forEach (_keywords splitString "|");
    if (_hit) then { _candidates pushBack _row; };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 3, "keyword"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 4: inheritance. The class isKindOf the entry class token.
_candidates = [];
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    if (_token != "" && {_className isKindOf _token}) then {
        _candidates pushBack _x;
    };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 4, "inheritance"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 5: closest. The longest alias or keyword substring of the query,
// at least four characters, with a strictly lower runner-up score.
private _bestRow = [];
private _bestScore = 0;
private _runnerUp = 0;
private _tie = false;
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
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
    [_bestRow, 5, "closest"] call _result
};
[]
