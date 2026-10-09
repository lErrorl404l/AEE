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
    ["a10a_thunderbolt_ii", "a10a", "fixed_wing", "Plane", "bplanecas01clusterf|bplanecas01f|bplanecas01dynamicloadoutf|plane", "a10|wipeout|thunderboltii", "cas|attack", "src_to_1a10a1", [12701, 0, 0, 0]],
    ["a10c_thunderbolt_ii", "a10c", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["a1h_skyraider", "a1h", "fixed_wing", "", "", "skyraider|spad", "attack", "", [0, 0, 0, 0]],
    ["a4e_skyhawk", "a4e", "fixed_wing", "", "", "skyhawk|scooter", "attack", "", [0, 0, 0, 0]],
    ["a6a_intruder", "a6a", "fixed_wing", "", "", "intruder", "attack", "", [0, 0, 0, 0]],
    ["a7d_corsair_ii", "a7d", "fixed_wing", "", "", "corsairii|sluf", "attack", "", [0, 0, 0, 0]],
    ["aermacchi_mb339", "mb339", "fixed_wing", "", "", "mb339", "trainer", "", [0, 0, 0, 0]],
    ["ah1g_cobra", "ah1g", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["ah64d_apache_longbow", "ah64d", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["alphajet_e", "alphajet_e", "fixed_wing", "", "", "alphajet", "trainer", "", [0, 0, 0, 0]],
    ["amx_gibli", "amx_gibli", "fixed_wing", "", "", "ghibli", "attack", "", [0, 0, 0, 0]],
    ["av8b_harrier_ii", "av8b", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["avro_lancaster_b1", "lancaster_b1", "fixed_wing", "", "", "lancaster", "bomber", "", [0, 0, 0, 0]],
    ["aw101_merlin", "aw101", "rotary_wing", "Helicopter", "cidaphelitransport02f|ihelitransport02f", "merlin|aw101", "transport|heavy", "src_leonardo_aw101", [15600, 5652000.0, 0, 271.716349]],
    ["aw159_wildcat", "aw159", "rotary_wing", "Helicopter", "iehelilight03dynamicloadoutf|iehelilight03unarmedf|ihelilight03f|ihelilight03dynamicloadoutf|ihelilight03unarmedf", "wildcat|aw159", "maritime|utility", "", [0, 0, 0, 0]],
    ["b17g_flying_fortress", "b17g", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["b24j_liberator", "b24j", "fixed_wing", "", "", "liberator", "bomber", "", [0, 0, 0, 0]],
    ["b29_superfortress", "b29", "fixed_wing", "", "", "superfortress", "bomber", "", [0, 0, 0, 0]],
    ["b52h_stratofortress", "b52h", "fixed_wing", "", "", "stratofortress|buff", "bomber", "", [0, 0, 0, 0]],
    ["bae_hawk_t1", "hawk_t1", "fixed_wing", "", "", "hawk", "trainer", "", [0, 0, 0, 0]],
    ["bf109g6", "bf109g6", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["cessna_172_skyhawk", "172s", "fixed_wing", "Plane", "cplanecivil01f|cplanecivil01racingf|icplanecivil01f", "skyhawk|c172", "civil|trainer", "src_faa_tcds_3a12", [1157, 134225.97696, 0, 0]],
    ["ch47_chinook", "ch47d", "rotary_wing", "Helicopter", "bhelitransport03f|bhelitransport03blackf|bhelitransport03unarmedf|bhelitransport03unarmedgreenf", "chinook|ch47", "heavy|transport", "src_tm_1_1520_240_10", [22680, 0, 0, 0]],
    ["ch47f_chinook", "ch47f", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["chengdu_j10a", "j10a", "fixed_wing", "", "", "vigorousdragon", "fighter", "", [0, 0, 0, 0]],
    ["chengdu_j7_ii", "j7_ii", "fixed_wing", "", "", "fishbed|mig21", "fighter", "", [0, 0, 0, 0]],
    ["dehavilland_mosquito_b", "mosquito_b", "fixed_wing", "", "", "mosquito|woodenwonder", "bomber", "", [0, 0, 0, 0]],
    ["ef2000_typhoon_fgr4", "ef2000_fgr4", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f100d_super_sabre", "f100d", "fixed_wing", "", "", "supersabre", "fighter", "", [0, 0, 0, 0]],
    ["f104g_starfighter", "f104g", "fixed_wing", "", "", "starfighter", "fighter", "", [0, 0, 0, 0]],
    ["f105d_thunderchief", "f105d", "fixed_wing", "", "", "thunderchief", "attack", "", [0, 0, 0, 0]],
    ["f111a_ardvark", "f111a", "fixed_wing", "", "", "aardvark", "attack", "", [0, 0, 0, 0]],
    ["f14a_tomcat", "f14a", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f14b_tomcat", "f14b", "fixed_wing", "", "", "tomcat", "fighter", "", [0, 0, 0, 0]],
    ["f15a_eagle", "f15a", "fixed_wing", "", "", "eagle", "fighter", "", [0, 0, 0, 0]],
    ["f15c_eagle", "f15c", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f15e_strike_eagle", "f15e", "fixed_wing", "", "", "strikeeagle", "fighter|attack", "", [0, 0, 0, 0]],
    ["f16a_block10", "f16a_block10", "fixed_wing", "", "", "falcon|viper", "fighter", "", [0, 0, 0, 0]],
    ["f16c_block50", "f16c_block50", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f16c_block52", "f16c_block52", "fixed_wing", "", "", "falcon", "fighter", "", [0, 0, 0, 0]],
    ["f22a_raptor", "f22a", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f35a_lightning_ii", "f35a", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f4c_phantom_ii", "f4c", "fixed_wing", "", "", "phantom", "fighter", "", [0, 0, 0, 0]],
    ["f4e_phantom_ii", "f4e", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f4j_phantom_ii", "f4j", "fixed_wing", "", "", "phantom", "fighter|naval", "", [0, 0, 0, 0]],
    ["f4u4_corsair", "f4u4", "fixed_wing", "", "", "corsair|whistlingdeath", "fighter", "", [0, 0, 0, 0]],
    ["f5e_tiger_ii", "f5e", "fixed_wing", "", "", "tiger", "fighter", "", [0, 0, 0, 0]],
    ["f6f5_hellcat", "f6f5", "fixed_wing", "", "", "hellcat", "fighter", "", [0, 0, 0, 0]],
    ["f80c_shooting_star", "f80c", "fixed_wing", "", "", "shootingstar", "fighter", "", [0, 0, 0, 0]],
    ["f84f_thunderstreak", "f84f", "fixed_wing", "", "", "thunderstreak", "fighter", "", [0, 0, 0, 0]],
    ["f86d_sabre", "f86d", "fixed_wing", "", "", "sabredog", "interceptor", "", [0, 0, 0, 0]],
    ["f86f_sabre", "f86f", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["f8e_crusader", "f8e", "fixed_wing", "", "", "crusader", "fighter", "", [0, 0, 0, 0]],
    ["fa18a_hornet", "fa18a", "fixed_wing", "", "", "hornet", "fighter", "", [0, 0, 0, 0]],
    ["fa18c_hornet", "fa18c", "fixed_wing", "", "", "hornet", "fighter", "", [0, 0, 0, 0]],
    ["fa18e_super_hornet", "fa18e", "fixed_wing", "Plane", "bplanefighter01clusterf|bplanefighter01f|bplanefighter01stealthf", "superhornet|fa18", "carrier|multirole", "src_fa18_natops", [14288, 66316756.798983, 0, 0]],
    ["fa18f_super_hornet", "fa18f", "fixed_wing", "", "", "superhornet", "fighter|carrier", "", [0, 0, 0, 0]],
    ["focke_wulf_fw190d", "fw190d", "fixed_wing", "", "", "dora", "fighter", "", [0, 0, 0, 0]],
    ["folland_gnat", "folland_gnat", "fixed_wing", "", "", "gnat", "trainer", "", [0, 0, 0, 0]],
    ["fw190a8", "fw190a8", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["harrier_gr9", "harrier_gr9", "fixed_wing", "", "", "harrier", "attack|vtol", "", [0, 0, 0, 0]],
    ["hawker_hurricane_mk_i", "hurricane_i", "fixed_wing", "", "", "hurricane", "fighter", "", [0, 0, 0, 0]],
    ["hawker_typhoon_mk_ib", "typhoon_ib", "fixed_wing", "", "", "typhoon|tiffy", "attack", "", [0, 0, 0, 0]],
    ["jas39c_gripen", "jas39c", "fixed_wing", "Plane", "iplanefighter04clusterf|iplanefighter04f", "gripen|jas39", "multirole|fighter", "src_saab_gripen_c", [14000, 31305555.5645, 0, 0]],
    ["junkers_ju87d_stuka", "ju87d", "fixed_wing", "", "", "stuka", "attack", "", [0, 0, 0, 0]],
    ["ka52_alligator", "ka52", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["l159_alca", "l159", "fixed_wing", "Plane", "iplanefighter03aaf|iplanefighter03casf|iplanefighter03clusterf|iplanefighter03dynamicloadoutf", "alca|l159", "trainer|lightattack", "", [0, 0, 0, 0]],
    ["light_utility_rotary", "mi2", "rotary_wing", "Helicopter", "ohelilight02f|ohelilight02dynamicloadoutf|ohelilight02unarmedf|ohelilight02v2f", "hoplite|mi2", "light|utility", "src_opfor_weg", [1076, 298279.9488, 0, 167.415473]],
    ["md500", "md500e", "rotary_wing", "Helicopter", "bhelilight01f|bhelilight01strippedf|chelilight01bluelinef|chelilight01bluef|chelilight01digitalf|chelilight01ellipticalf|chelilight01furiousf|chelilight01graywatcherf|chelilight01ionf|chelilight01jeansf|chelilight01lightf|chelilight01luxef|chelilight01redf|chelilight01shadowf|chelilight01sherifff|chelilight01speedyf|chelilight01strippedf|chelilight01sunsetf|chelilight01vranaf|chelilight01waspf|chelilight01wavef", "md500|hummingbird", "light|utility", "src_md500e_2023", [752, 313000.0, 0, 50.895764]],
    ["md500_civil", "md500_civil", "rotary_wing", "Helicopter", "chelilight01civilf|ichelilight01civilf", "md500civil", "civil|utility", "src_md500e_2023", [752, 313000.0, 0, 50.895764]],
    ["md530_defender", "md530f", "rotary_wing", "Helicopter", "bhelilight01armedf|bhelilight01dynamicloadoutf", "md530|pawnee|defender", "light|attack", "src_md530f_2023", [782, 478000.0, 0, 55.154115]],
    ["messerschmitt_bf109e", "bf109e", "fixed_wing", "", "", "bf109|emil", "fighter", "", [0, 0, 0, 0]],
    ["messerschmitt_me262a", "me262a", "fixed_wing", "", "", "schwalbe", "fighter", "", [0, 0, 0, 0]],
    ["mi24d_hind_d", "mi24d", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mi24v_hind_e", "mi24v", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mi26_halo", "mi26", "rotary_wing", "Helicopter", "", "halo|mi26", "heavy|transport", "src_opfor_weg", [12809, 8500978.5408, 0, 804.247719]],
    ["mi28_havoc", "mi28", "rotary_wing", "Helicopter", "oheliattack02f|oheliattack02blackf|oheliattack02dynamicloadoutf|oheliattack02dynamicloadoutblackf", "havoc|mi28", "attack|gunship", "src_opfor_weg", [3175, 1640539.7184, 0, 232.352193]],
    ["mi28n_havoc", "mi28n", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mi8t_hip", "mi8t", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mig15bis", "mig15bis", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mig17f_fresco", "mig17f", "fixed_wing", "", "", "fresco", "fighter", "", [0, 0, 0, 0]],
    ["mig19s_farmer", "mig19s", "fixed_wing", "", "", "farmer", "fighter", "", [0, 0, 0, 0]],
    ["mig21bis", "mig21bis", "fixed_wing", "", "", "fishbed", "fighter", "", [0, 0, 0, 0]],
    ["mig21f13", "mig21f13", "fixed_wing", "", "", "fishbed", "fighter", "", [0, 0, 0, 0]],
    ["mig21mf", "mig21mf", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mig23m_flogger", "mig23m", "fixed_wing", "", "", "flogger", "fighter", "", [0, 0, 0, 0]],
    ["mig23ml_flogger", "mig23ml", "fixed_wing", "", "", "flogger", "fighter", "", [0, 0, 0, 0]],
    ["mig25_foxbat", "mig25", "fixed_wing", "", "", "foxbat", "interceptor", "", [0, 0, 0, 0]],
    ["mig27_flogger_d", "mig27", "fixed_wing", "", "", "flogger", "attack", "", [0, 0, 0, 0]],
    ["mig29a_fulcrum", "mig29a", "fixed_wing", "", "", "fulcrum", "fighter", "", [0, 0, 0, 0]],
    ["mig29s_fulcrum_c", "mig29s", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mig31b_foxhound", "mig31b", "fixed_wing", "", "", "foxhound", "interceptor", "", [0, 0, 0, 0]],
    ["mig31bm_foxhound", "mig31bm", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["mig35_fulcrum_f", "mig35", "fixed_wing", "", "", "fulcrum", "fighter", "", [0, 0, 0, 0]],
    ["mirage_2000c", "mirage2000c", "fixed_wing", "", "", "mirage", "fighter", "", [0, 0, 0, 0]],
    ["mirage_f1_cr", "mirage_f1_cr", "fixed_wing", "", "", "mirage", "recon", "", [0, 0, 0, 0]],
    ["mirage_iii_e", "mirage3e", "fixed_wing", "", "", "mirage", "fighter", "", [0, 0, 0, 0]],
    ["mitsubishi_a6m2_zero", "a6m2", "fixed_wing", "", "", "zero|reisen", "fighter", "", [0, 0, 0, 0]],
    ["nh90_tth", "nh90_tth", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["p38j_lightning", "p38j", "fixed_wing", "", "", "lightning", "fighter", "", [0, 0, 0, 0]],
    ["p40e_warhawk", "p40e", "fixed_wing", "", "", "warhawk|kittyhawk", "fighter", "", [0, 0, 0, 0]],
    ["p47d_thunderbolt", "p47d", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["p51d_mustang", "p51d", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["p61b_black_widow", "p61b", "fixed_wing", "", "", "blackwidow", "interceptor", "", [0, 0, 0, 0]],
    ["panavia_tornado_gr4", "tornado_gr4", "fixed_wing", "", "", "tornado", "attack", "", [0, 0, 0, 0]],
    ["rafale_c", "rafale_c", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["rah66_comanche", "rah66", "rotary_wing", "Helicopter", "bheliattack01f|bheliattack01dynamicloadoutf|bheliattack01pylonsdynamicloadoutf", "comanche|rah66", "scout|recon", "src_rah66_case", [3526, 0, 0, 0]],
    ["saab_105", "saab_105", "fixed_wing", "", "", "saab105", "trainer", "", [0, 0, 0, 0]],
    ["saab_35_draken", "saab_35", "fixed_wing", "", "", "draken", "interceptor", "", [0, 0, 0, 0]],
    ["saab_37_viggen", "saab_37", "fixed_wing", "", "", "viggen", "fighter", "", [0, 0, 0, 0]],
    ["sepecat_jaguar_gr1", "jaguar_gr1", "fixed_wing", "", "", "jaguar", "attack", "", [0, 0, 0, 0]],
    ["shenyang_j8_ii", "j8_ii", "fixed_wing", "", "", "finback", "interceptor", "", [0, 0, 0, 0]],
    ["spitfire_mk_ix", "spitfire_ix", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["su17_fitter_c", "su17", "fixed_wing", "", "", "fitter", "attack", "", [0, 0, 0, 0]],
    ["su22_fitter_f", "su22", "fixed_wing", "", "", "fitter", "attack", "", [0, 0, 0, 0]],
    ["su24_fencer", "su24", "fixed_wing", "", "", "fencer", "attack", "", [0, 0, 0, 0]],
    ["su25_frogfoot", "su25", "fixed_wing", "Plane", "oplanecas02clusterf|oplanecas02f|oplanecas02dynamicloadoutf", "frogfoot|su25", "cas|attack", "src_opfor_weg", [4320, 0, 0, 0]],
    ["su25sm_frogfoot", "su25sm", "fixed_wing", "", "", "frogfoot|grach", "attack", "", [0, 0, 0, 0]],
    ["su25t_frogfoot", "su25t", "fixed_wing", "", "", "frogfoot", "attack", "", [0, 0, 0, 0]],
    ["su27s_flanker_b", "su27s", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["su27sk_flanker_b", "su27sk", "fixed_wing", "", "", "flanker", "fighter", "", [0, 0, 0, 0]],
    ["su30mki_flanker_h", "su30mki", "fixed_wing", "", "", "flanker", "fighter", "", [0, 0, 0, 0]],
    ["su33_flanker_d", "su33", "fixed_wing", "", "", "flanker", "fighter|carrier", "", [0, 0, 0, 0]],
    ["su34_fullback", "su34", "fixed_wing", "", "", "fullback", "attack", "", [0, 0, 0, 0]],
    ["su35s_flanker_e", "su35s", "fixed_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["su57_felon", "su57", "fixed_wing", "Plane", "oplanefighter02clusterf|oplanefighter02f|oplanefighter02stealthf", "felon|su57", "stealth|multirole", "src_odin_weg_2025", [18000, 0, 0, 0]],
    ["su7b_fitter", "su7b", "fixed_wing", "", "", "fitter", "attack", "", [0, 0, 0, 0]],
    ["t38a_talon", "t38a", "fixed_wing", "", "", "talon", "trainer", "", [0, 0, 0, 0]],
    ["uh1h_iroquois", "uh1h", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["uh60a_black_hawk", "uh60a", "rotary_wing", "Helicopter", "bctrghelitransport01sandf|bctrghelitransport01tropicf|bhelitransport01f|bhelitransport01camof|bhelitransport01pylonsf|helicopter", "blackhawk|uh60", "utility|transport", "src_tm_1_1520_237_10", [9185, 0, 0, 210.211504]],
    ["uh60m_black_hawk", "uh60m", "rotary_wing", "", "", "", "", "", [0, 0, 0, 0]],
    ["yak130_mitten", "yak130", "fixed_wing", "", "", "mitten", "trainer|attack", "", [0, 0, 0, 0]],
    ["yak38_forger", "yak38", "fixed_wing", "", "", "forger|vtol", "attack", "", [0, 0, 0, 0]]
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
