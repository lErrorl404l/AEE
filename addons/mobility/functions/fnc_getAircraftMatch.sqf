#include "..\script_component.hpp"
/*
Aircraft identity matcher (issue #117).

Function: aee_mobility_fnc_getAircraftMatch.

This file is GENERATED. The generator tools/validation/gen_aircraft_data.py
writes it from the validated aircraft catalogue under data/aircraft/. Do not
edit it by hand. Edit the corpus and regenerate it.

The matcher resolves a game class to a real aircraft entry. It runs an
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
  2 vehicle_type      string, "fixed_wing" or "rotary_wing"
  3 class_token       string, the supported token or empty
  4 mapped_classes    string, "|" separated normalised game classes
  5 aliases           string, "|" separated normalised catalogue aliases
  6 keywords          string, "|" separated normalised catalogue keywords
  7 source_record_id  string, the source id of the operating weight value
  8 value_row         array of four values, in fixed order

value_row  [operating_weight_kg, rated_power_w, drag_area_m2,
            rotor_disc_area_m2]

The value row carries the four flight-model inputs. A field no held value
and no derivation reaches is a labelled absent zero. The matcher reads no
config value as a figure and no source registry.

Column units: operating weight kg, rated power W, drag area m^2, rotor disc
area m^2.

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

// Identity text only: the class name, the raw display name and its
// localised stringtable text. A vanilla class stores a $STR key in
// displayName, so all three are needed. None carries a figure.
private _rawName = getText (configFile >> "CfgVehicles" >> _className >> "displayName");
private _localName = if ((_rawName select [0,1]) == "$") then { localize _rawName } else { _rawName };
private _identity = _className + " " + _rawName + " " + _localName;
private _query = [_identity] call _normalise;
private _tokens = [];
{
    private _token = _x call _normalise;
    if (_token != "") then { _tokens pushBack _token; };
} forEach (_identity splitString " _-.");

private _table = [
    ["a10a_thunderbolt_ii", "a10a", "fixed_wing", "Plane", "bplanecas01f|plane", "a10|wipeout|thunderboltii", "cas|attack", "src_to_1a10a1", [12701, 0, 0, 0]],
    ["a10c_thunderbolt_ii", "a10c", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["ah1g_cobra", "ah1g", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["ah64d_apache_longbow", "ah64d", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["av8b_harrier_ii", "av8b", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["aw101_merlin", "aw101", "rotary_wing", "Helicopter", "ihelitransport02f", "merlin|aw101", "transport|heavy", "src_leonardo_aw101", [15600, 5652000.0, 0, 271.716349]],
    ["aw159_wildcat", "aw159", "rotary_wing", "Helicopter", "ihelilight03f", "wildcat|aw159", "maritime|utility", "", [0, 0, 0, 0]],
    ["b17g_flying_fortress", "b17g", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["bf109g6", "bf109g6", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["cessna_172_skyhawk", "172s", "fixed_wing", "Plane", "cplanecivil01f", "skyhawk|c172", "civil|trainer", "src_faa_tcds_3a12", [1157, 134225.97696, 0, 0]],
    ["ch47_chinook", "ch47d", "rotary_wing", "Helicopter", "bhelitransport03f", "chinook|ch47", "heavy|transport", "src_tm_1_1520_240_10", [22680, 0, 0, 0]],
    ["ch47f_chinook", "ch47f", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["ef2000_typhoon_fgr4", "ef2000_fgr4", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f14a_tomcat", "f14a", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f15c_eagle", "f15c", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f16c_block50", "f16c_block50", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f22a_raptor", "f22a", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f35a_lightning_ii", "f35a", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f4e_phantom_ii", "f4e", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f86f_sabre", "f86f", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["fa18e_super_hornet", "fa18e", "fixed_wing", "Plane", "bplanefighter01f", "superhornet|fa18", "carrier|multirole", "src_fa18_natops", [14288, 66316756.798983, 0, 0]],
    ["fw190a8", "fw190a8", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["jas39c_gripen", "jas39c", "fixed_wing", "Plane", "iplanefighter04f", "gripen|jas39", "multirole|fighter", "src_saab_gripen_c", [14000, 31305555.5645, 0, 0]],
    ["ka52_alligator", "ka52", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["l159_alca", "l159", "fixed_wing", "Plane", "iplanefighter03aaf|iplanefighter03casf|iplanefighter03dynamicloadoutf", "alca|l159", "trainer|lightattack", "", [0, 0, 0, 0]],
    ["light_utility_rotary", "mi2", "rotary_wing", "Helicopter", "ohelilight02f", "hoplite|mi2", "light|utility", "src_opfor_weg", [1076, 298279.9488, 0, 167.415473]],
    ["md500", "md500e", "rotary_wing", "Helicopter", "bhelilight01f", "md500|hummingbird", "light|utility", "src_md500e_2023", [752, 313000.0, 0, 50.895764]],
    ["md500_civil", "md500_civil", "rotary_wing", "Helicopter", "chelilight01civilf", "md500civil", "civil|utility", "src_md500e_2023", [752, 313000.0, 0, 50.895764]],
    ["md530_defender", "md530f", "rotary_wing", "Helicopter", "bhelilight01armedf", "md530|pawnee|defender", "light|attack", "src_md530f_2023", [782, 478000.0, 0, 55.154115]],
    ["mi24d_hind_d", "mi24d", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mi24v_hind_e", "mi24v", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mi26_halo", "mi26", "rotary_wing", "Helicopter", "", "halo|mi26", "heavy|transport", "src_opfor_weg", [12809, 8500978.5408, 0, 804.247719]],
    ["mi28_havoc", "mi28", "rotary_wing", "Helicopter", "oheliattack02f", "havoc|mi28", "attack|gunship", "src_opfor_weg", [3175, 1640539.7184, 0, 232.352193]],
    ["mi28n_havoc", "mi28n", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mi8t_hip", "mi8t", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mig15bis", "mig15bis", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mig21mf", "mig21mf", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mig29s_fulcrum_c", "mig29s", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mig31bm_foxhound", "mig31bm", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["nh90_tth", "nh90_tth", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["p47d_thunderbolt", "p47d", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["p51d_mustang", "p51d", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["rafale_c", "rafale_c", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["rah66_comanche", "rah66", "rotary_wing", "Helicopter", "bheliattack01f", "comanche|rah66", "scout|recon", "src_rah66_case", [3526, 0, 0, 0]],
    ["spitfire_mk_ix", "spitfire_ix", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["su25_frogfoot", "su25", "fixed_wing", "Plane", "oplanecas02f", "frogfoot|su25", "cas|attack", "src_opfor_weg", [4320, 0, 0, 0]],
    ["su27s_flanker_b", "su27s", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["su35s_flanker_e", "su35s", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["su57_felon", "su57", "fixed_wing", "Plane", "oplanefighter02f", "felon|su57", "stealth|multirole", "src_odin_weg_2025", [18000, 0, 0, 0]],
    ["uh1h_iroquois", "uh1h", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["uh60a_black_hawk", "uh60a", "rotary_wing", "Helicopter", "bhelitransport01f|helicopter", "blackhawk|uh60", "utility|transport", "src_tm_1_1520_237_10", [9185, 0, 0, 210.211504]],
    ["uh60m_black_hawk", "uh60m", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]]
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
