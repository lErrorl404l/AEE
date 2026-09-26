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
    ["achzarit", "achzarit", "tracked", "", "", "achzarit", "achzarit|israeliapc|idfapc", "achzarit", [44000, 0, 0, 0, 484.704917, "automatic", ""]],
    ["ahs_krab", "ahs_krab", "tracked", "", "", "krab|ahskrab", "krab|polishhowitzer|155mmspg", "ahs_krab", [48000, 0, 0, 0, 745.699872, "automatic", ""]],
    ["al_fahd", "al_fahd", "wheeled", "", "", "alfahd|af4082", "afv|wheeled|8x8|saudiarabia", "wikipedia_al_fahd", [16300, 0, 0, 405, 410.13493, "", ""]],
    ["al_khalid", "al_khalid", "tracked", "", "", "alkhalid", "alkhalid|pakistanitank|alkhalidmbt", "al_khalid", [46000, 0, 0, 0, 894.839846, "automatic", ""]],
    ["altay", "altay", "tracked", "", "", "altay|altaymbt", "mbt|mainbattletank|tracked|altay", "wikipedia_altay", [65000, 0, 0, 0, 1118.549808, "", ""]],
    ["anoa", "anoa", "wheeled", "", "", "anoa|pindadanoa", "apc|wheeled|6x6|indonesia", "wikipedia_anoa", [12500, 0, 0, 400, 0, "automatic", ""]],
    ["arjun", "arjun", "tracked", "", "", "arjun|arjunmk1|arjunmbt", "mbt|mainbattletank|tracked|india", "wikipedia_arjun", [58500, 0, 0, 450, 1043.979821, "", ""]],
    ["aslav", "aslav", "wheeled", "", "", "aslav", "reconnaissance|wheeled|aslav", "wikipedia_aslav", [13200, 0, 0, 0, 205, "", ""]],
    ["astros_ii", "astros_ii", "wheeled", "", "", "astrosii|astros2|astros", "mlrs|rocketartillery|wheeled|6x6|brazil", "wikipedia_astros_ii", [10000, 0, 0, 0, 208.795964, "", ""]],
    ["bionix", "bionix", "tracked", "", "", "bionix|bionixafv", "ifv|tracked|infantryfightingvehicle|singapore", "wikipedia_bionix", [23000, 0, 0, 0, 354.207439, "", ""]],
    ["bmc_kirpi", "bmc_kirpi", "wheeled", "", "", "kirpi|bmckirpi", "mrap|mineresistant|wheeled|kirpi", "wikipedia_bmc_kirpi", [20000, 0, 0, 345, 257, "", ""]],
    ["bmp_2", "bmp_2", "tracked", "", "", "bmp2", "ifv|tracked|infantryfightingvehicle|sovietunion", "wikipedia_bmp_2", [14300, 0, 0, 0, 0, "", ""]],
    ["bmw_r75", "bmw_r75", "wheeled", "", "", "bmwr75", "bmwr75|sidecarmotorcycle|germanmotorcycle", "bmw_r75", [420, 0, 0, 0, 19.388197, "", ""]],
    ["boragh", "boragh", "tracked", "", "", "boragh", "boragh|iranianapc|boraghapc", "boragh", [13000, 0, 0, 0, 246.080958, "", ""]],
    ["boxer_apc", "boxer_apc", "wheeled", "", "", "boxer|boxerapc|gtkboxer", "apc|wheeled|8x8|boxer", "artec_boxer_apc_datasheet", [38500, 0, 0, 500, 608.491096, "", ""]],
    ["brdm_2", "brdm_2", "wheeled", "", "", "brdm2", "amphibious|4x4|armoredreconnaissance|armouredcar|brdm", "brdm_2_technical_manual_en", [7000, 330.2, 1117.6, 330, 104.397982, "manual", ""]],
    ["btr_4", "btr_4", "wheeled", "", "", "btr4", "apc|wheeled|8x8|ukraine", "wikipedia_btr_4", [20500, 0, 0, 0, 364.647237, "", ""]],
    ["btr_80", "btr_80", "wheeled", "", "wheeledapc", "btr80", "apc|amphibious|8x8|armoredpersonnelcarrier|btr", "btr_80_technical_description_2001", [13600, 0, 0, 475, 193.881967, "manual", ""]],
    ["bushmaster_pmv", "bushmaster_pmv", "wheeled", "", "", "bushmaster|bushmasterpmv", "mrap|infantrymobility|wheeled|bushmaster", "wikipedia_bushmaster_pmv", [11400, 0, 0, 0, 224, "", ""]],
    ["c1_ariete", "c1_ariete", "tracked", "", "", "ariete|c1ariete|c1", "mbt|mainbattletank|ariete|tracked", "wikipedia_ariete", [54000, 0, 0, 440, 947.038837, "", ""]],
    ["centauro", "centauro", "wheeled", "", "", "centauro|b1centauro|centauro1", "tankdestroyer|wheeled|8x8|centauro", "wikipedia_centauro", [24000, 0, 0, 0, 387.763933, "automatic", ""]],
    ["challenger_1", "challenger_1", "tracked", "", "", "challenger|challenger1|fv4030", "mbt|mainbattletank|challenger|tracked", "challenger_1_aesp_230_p_100_201", [62000, 650, 0, 500, 894.839846, "automatic", ""]],
    ["challenger_2", "challenger_2", "tracked", "", "", "challenger2|challengerii|fv4034", "mbt|mainbattletank|challenger|tracked", "wikipedia_challenger_2", [64000, 0, 0, 500, 894.839846, "", ""]],
    ["cougar_4x4", "cougar_4x4", "wheeled", "", "", "cougar|cougar4x4|mrapcougar", "mrap|mineresistant|cougar|4x4", "gdls_cougar_4x4_datasheet", [15422, 395.0, 1179.5, 380, 246.080958, "automatic", ""]],
    ["cv90", "cv90", "tracked", "", "", "cv90|combatvehicle90|stridsfordon90", "ifv|infantryfightingvehicle|tracked|cv90", "wikipedia_cv90", [23000, 0, 0, 0, 0, "", ""]],
    ["cv90_denmark", "cv90_denmark", "tracked", "", "", "cv9035dk|cv90denmark|combatvehicle90denmark", "ifv|infantryfightingvehicle|tracked|cv90", "wikipedia_cv90", [23000, 0, 0, 0, 0, "", ""]],
    ["cv90_norway", "cv90_norway", "tracked", "", "", "cv9030n|cv90norway|combatvehicle90norway", "ifv|infantryfightingvehicle|tracked|cv90", "wikipedia_cv90", [23000, 0, 0, 0, 0, "", ""]],
    ["dardo", "dardo", "tracked", "", "", "dardo|dardoifv|vcc80", "ifv|infantryfightingvehicle|tracked|dardo", "wikipedia_dardo", [23400, 0, 0, 0, 381.798334, "", ""]],
    ["eitan", "eitan", "wheeled", "", "", "eitan|eitanafv", "afv|armouredfightingvehicle|wheeled|eitan", "wikipedia_eitan", [50000, 0, 0, 0, 559.274904, "", ""]],
    ["fahd", "fahd", "wheeled", "", "", "fahd|fahdapc", "apc|wheeled|4x4|egypt", "wikipedia_fahd", [12500, 0, 0, 370, 205.067465, "", ""]],
    ["freccia", "freccia", "wheeled", "", "", "freccia|vbmfreccia|frecciaifv", "ifv|infantryfightingvehicle|wheeled|8x8|freccia", "wikipedia_freccia", [22000, 0, 0, 0, 0, "", ""]],
    ["fv510_warrior", "fv510_warrior", "tracked", "", "", "warrior|fv510|fv510warrior|warriortrackedarmouredvehicle", "ifv|tracked|warrior|infantryfightingvehicle", "wikipedia_fv510_warrior", [25400, 0, 0, 0, 410.13493, "", ""]],
    ["gaz_66", "gaz_66", "wheeled", "", "", "gaz66", "gaz66|soviettruck", "gaz_66", [3440, 0, 0, 315, 0, "manual", ""]],
    ["guarani", "guarani", "wheeled", "", "", "guarani|vbtpmrguarani|vbtpmr", "apc|wheeled|6x6|amphibious|brazil", "wikipedia_guarani", [16700, 0, 0, 0, 0, "", ""]],
    ["harley_wla", "harley_wla", "wheeled", "", "", "wla|harleywla", "harleywla|militarymotorcycle|vtwin", "harley_wla", [245, 101.6, 660.4, 0, 18.642497, "manual", ""]],
    ["hmmwv_m998", "hmmwv_m998", "wheeled", "", "", "m998|m998a1|hmmwv|humvee|m1038", "truck|utility|cargo|4x4|troopcarrier", "tm_9_2320_280_10", [2361, 0, 0, 410, 111.854981, "automatic", ""]],
    ["honda_cb750", "honda_cb750", "wheeled", "", "", "cb750|hondacb750|cb750four", "superbike|aircooledfour|classicmotorcycle", "honda_cb750", [232.7, 0, 0, 0, 50.707591, "manual", ""]],
    ["honda_cg125", "honda_cg125", "wheeled", "", "", "cg125|hondacg125", "motorbike|commuter|125|japan", "wikipedia_honda_cg125", [105, 0, 0, 0, 7.829849, "manual", ""]],
    ["honda_civic_6gen_coupe", "honda_civic_6gen_coupe", "wheeled", "", "", "civiccoupe|hondaciviccoupe|civic2doorcoupe", "car|civilian|passengercar|coupe", "honda_civic_factory_service_manual_96_00", [1570, 0, 0, 150, 0, "", ""]],
    ["honda_civic_6gen_hatchback", "honda_civic_6gen_hatchback", "wheeled", "", "", "civichatchback|hondacivichatchback|civic2doorhatchback", "car|civilian|passengercar|hatchback", "honda_civic_factory_service_manual_96_00", [1495, 0, 0, 150, 0, "", ""]],
    ["honda_civic_6gen_sedan", "honda_civic_6gen_sedan", "wheeled", "", "car", "civic|hondacivic|hondacivicsedan|ej6|ej8", "car|civilian|passengercar|sedan", "honda_civic_factory_service_manual_96_00", [1540, 0, 0, 150, 0, "automatic", ""]],
    ["k21_ifv", "k21_ifv", "tracked", "", "", "k21|k21ifv", "k21|koreanifv|k21ifv", "k21_ifv", [25600, 0, 0, 0, 559.274904, "", ""]],
    ["k2_black_panther", "k2_black_panther", "tracked", "", "", "k2|k2blackpanther|blackpanther", "mbt|mainbattletank|tracked|k2", "wikipedia_k2_black_panther", [56000, 0, 0, 0, 0, "", ""]],
    ["k808_white_tiger", "k808_white_tiger", "wheeled", "", "", "k808|whitetiger|k806", "k808|whitetiger|koreanapc", "k808_white_tiger", [20000, 0, 0, 0, 313.193946, "", ""]],
    ["k9_thunder", "k9_thunder", "tracked", "", "", "k9|k9thunder|k9a1", "selfpropelledhowitzer|sph|tracked|k9", "wikipedia_k9_thunder", [47000, 0, 0, 410, 745.699872, "", ""]],
    ["karrar_tank", "karrar_tank", "tracked", "", "", "karrar", "karrar|iraniantank|karrarmbt", "karrar_tank", [51000, 0, 0, 0, 0, "", ""]],
    ["kawasaki_ninja_250r_ex250f", "kawasaki_ninja_250r_ex250f", "wheeled", "", "", "ninja250|ninja250r|ex250|ex250f|gpx250|gpx250r|kawasakininja250r", "motorcycle|ninja|sportbike", "kawasaki_ninja_250r_service_manual", [161, 130.0, 614.4, 155, 27.948831, "manual", "none"]],
    ["komatsu_lav", "komatsu_lav", "wheeled", "", "", "komatsulav|jgsdflav", "komatsulav|jgsdflav|japaneselav", "komatsu_lav", [4500, 0, 0, 0, 119.31198, "automatic", ""]],
    ["lav_6", "lav_6", "wheeled", "", "", "lav6|lav60", "ifv|infantryfightingvehicle|wheeled|8x8|lav", "wikipedia_lav6", [20638, 0, 0, 0, 335.564942, "", ""]],
    ["leclerc", "leclerc", "tracked", "", "", "leclerc|charleclerc", "mbt|mainbattletank|leclerc|tracked", "wikipedia_leclerc", [54500, 0, 0, 500, 1118.549808, "automatic", ""]],
    ["leopard_2a6", "leopard_2a6", "tracked", "", "", "leopard2|leopard2a6|2a6|leopard", "mbt|mainbattletank|leopard|tracked", "wikipedia_leopard_2", [62300, 0, 0, 540, 1118.549808, "", ""]],
    ["leopard_2a6_finland", "leopard_2a6_finland", "tracked", "", "", "leopard2a6finland|leopard2finland", "mbt|mainbattletank|tracked|leopard", "wikipedia_leopard_2", [62300, 0, 0, 540, 1118.549808, "", ""]],
    ["leopard_2a6_hel", "leopard_2a6_hel", "tracked", "", "", "leopard2a6hel|leopard2hel|leopard2greece", "mbt|mainbattletank|tracked|leopard", "wikipedia_leopard_2", [62300, 0, 0, 540, 1118.549808, "", ""]],
    ["leopard_2a7_hungary", "leopard_2a7_hungary", "tracked", "", "", "leopard2a7hungary|leopard2a7|leopard2hungary", "mbt|mainbattletank|tracked|leopard", "wikipedia_leopard_2", [66500, 0, 0, 540, 1118.549808, "", ""]],
    ["m1059", "m1059", "tracked", "", "", "m1059", "apc|carrier|tracked|smokegeneratorcarrier", "tm_9_2350_261_10", [11077, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m1064", "m1064", "tracked", "", "", "m1064", "apc|carrier|tracked|selfpropelled120mmmortarcarrier", "tm_9_2350_261_10", [12546, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m1068", "m1068", "tracked", "", "", "m1068", "apc|carrier|tracked|standardizedintegratedcommandpostsystem", "tm_9_2350_261_10", [12182, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m113a2", "m113a2", "tracked", "", "trackedapc", "m113|m113a2", "apc|carrier|tracked|armoredpersonnelcarrier", "tm_9_2350_261_10", [11353, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m1_abrams", "m1_abrams", "tracked", "", "tank", "m1|m1abrams|abrams|generalabrams", "tank|mbt|mainbattletank|105mm", "tm_9_2350_255_10", [54431, 0, 0, 483, 0, "automatic", ""]],
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
    ["m977_hemtt", "m977_hemtt", "wheeled", "", "", "m977|hemtt|m977hemtt|heavyexpandedmobilitytacticaltruck", "truck|cargo|8x8|hemtt|heavyexpandedmobilitytacticaltruck", "tm_9_2320_279_10_1", [17600, 406.4, 1320.8, 609.6, 331.836443, "automatic", ""]],
    ["m_atv_m1240", "m_atv_m1240", "wheeled", "", "mrap", "matv|m1240", "mrap|oshkosh|matv", "tm_9_2355_335_10", [11123, 395.0, 1179.5, 0, 275.908953, "automatic", ""]],
    ["m_atv_m1240a1", "m_atv_m1240a1", "wheeled", "", "", "matvm1240a1|m1240a1", "mrap|oshkosh|matv", "tm_9_2355_335_10", [12940, 0, 0, 0, 275.908953, "automatic", ""]],
    ["m_atv_m1245", "m_atv_m1245", "wheeled", "", "", "matvm1245|m1245", "mrap|oshkosh|matv", "tm_9_2355_335_10", [12325, 395.0, 1179.5, 0, 275.908953, "automatic", ""]],
    ["marder_1a3", "marder_1a3", "tracked", "", "", "marder|marder1a3|spzmarder|schutzenpanzermarder", "ifv|tracked|infantryfightingvehicle|germany", "thyssen_henschel_marder_1a3", [28600, 0, 0, 0, 439.962924, "automatic", ""]],
    ["maxxpro", "maxxpro", "wheeled", "", "", "maxxpro|internationalmaxxpro", "mrap|wheeled|4x4|unitedstates", "wikipedia_maxxpro", [21000, 0, 0, 350, 246.080958, "automatic", ""]],
    ["merkava_mk4", "merkava_mk4", "tracked", "", "", "merkava|merkavamk4", "mbt|mainbattletank|tracked|merkava", "wikipedia_merkava", [65000, 0, 0, 450, 1119, "", ""]],
    ["mowag_piranha", "mowag_piranha", "wheeled", "", "", "piranha|mowagpiranha", "afv|armouredfightingvehicle|wheeled|piranha", "wikipedia_mowag_piranha", [0, 0, 0, 0, 202, "automatic", ""]],
    ["namer", "namer", "tracked", "", "", "namer|namerapc", "apc|armouredpersonnelcarrier|tracked|namer", "wikipedia_namer", [60000, 0, 0, 0, 894.839846, "", ""]],
    ["olifant", "olifant", "tracked", "", "", "olifant|olifantmk1|olifantmk2", "mbt|mainbattletank|tracked|southafrica", "wikipedia_olifant", [58000, 0, 0, 508, 775.527867, "automatic", ""]],
    ["pandur_ii", "pandur_ii", "wheeled", "", "", "pandurii|pandur2|pandur", "apc|armouredpersonnelcarrier|wheeled|pandur", "wikipedia_pandur_ii", [17300, 0, 0, 0, 335, "", ""]],
    ["patria_amv", "patria_amv", "wheeled", "", "", "patriaamv|amv|patria", "apc|armouredpersonnelcarrier|wheeled|patria", "wikipedia_patria_amv", [16000, 0, 0, 0, 450, "", ""]],
    ["piranha_v", "piranha_v", "wheeled", "", "", "piranhav|piranha5|piranha", "apc|armouredpersonnelcarrier|wheeled|piranha", "wikipedia_piranha_v", [0, 0, 0, 0, 437, "", ""]],
    ["pizarro", "pizarro", "tracked", "", "", "pizarro|ascod|ascodpizarro", "ifv|infantryfightingvehicle|tracked|pizarro|ascod", "wikipedia_ascod", [26300, 0, 0, 0, 447.419923, "", ""]],
    ["pt91_twardy", "pt91_twardy", "tracked", "", "", "pt91|pt91twardy|twardy", "mbt|mainbattletank|tracked|twardy", "wikipedia_pt91", [45900, 0, 0, 395, 633.844891, "manual", ""]],
    ["puma_cev", "puma_cev", "tracked", "", "", "pumacev|idfpuma", "idfpuma|pumacev|israeliengineeringvehicle", "puma_cev", [50000, 0, 0, 0, 671.129885, "", ""]],
    ["ratel", "ratel", "wheeled", "", "", "ratel|ratel20", "ifv|wheeled|6x6|southafrica", "wikipedia_ratel", [18500, 0, 0, 340, 205.067465, "", ""]],
    ["rg_31", "rg_31", "wheeled", "", "", "rg31|rg31nyala|nyala", "mrap|wheeled|4x4|southafrica", "wikipedia_rg_31", [7280, 0, 0, 0, 91.721084, "", ""]],
    ["rooikat", "rooikat", "wheeled", "", "", "rooikat", "afv|wheeled|8x8|southafrica", "wikipedia_rooikat", [28000, 0, 0, 0, 413.863429, "", ""]],
    ["rosomak", "rosomak", "wheeled", "", "", "rosomak|ktorosomak", "apc|wheeled|8x8|rosomak|patriaamv", "wikipedia_rosomak", [22000, 0, 0, 0, 404.91503, "", ""]],
    ["strv_122", "strv_122", "tracked", "", "", "stridsvagn122|strv122", "mbt|mainbattletank|tracked|leopard2", "wikipedia_strv_122", [62500, 0, 0, 540, 1102.890111, "", ""]],
    ["stryker_m1126_icv", "m1126_stryker_icv", "wheeled", "", "", "stryker|m1126|m1126strykericv|m1126icv", "apc|ifv|8x8|stryker|icv|armouredpersonnelcarrier", "wikipedia_stryker", [16470, 0, 0, 0, 260.994955, "", ""]],
    ["t_64", "t_64", "tracked", "", "", "t64", "mbt|mainbattletank|tracked|sovietunion", "wikipedia_t_64", [38000, 0, 0, 0, 521.98991, "", ""]],
    ["t_72m4cz", "t_72m4cz", "tracked", "", "", "t72m4cz|t72", "mbt|mainbattletank|tracked|t72", "wikipedia_t_72m4cz", [48000, 0, 0, 0, 746, "", ""]],
    ["t_90", "t_90", "tracked", "", "", "t90|t90a|t90s", "mbt|mainbattletank|tracked|russia", "wikipedia_t_90", [46000, 0, 0, 0, 626.387892, "", ""]],
    ["terrex", "terrex", "wheeled", "", "", "terrex|terrexicv", "apc|wheeled|8x8|singapore", "wikipedia_terrex", [24000, 0, 0, 0, 298.279949, "", ""]],
    ["toyota_land_cruiser_70", "toyota_land_cruiser_70", "wheeled", "", "", "landcruiser70|landcruiserj70|lc70", "car|truck|offroad|utility|japan", "wikipedia_toyota_land_cruiser_70", [0, 0, 0, 0, 0, "manual", ""]],
    ["toyota_t100", "toyota_t100", "wheeled", "", "", "t100|toyotat100", "car|pickup|civilian|lighttruck", "toyota_t100_factory_service_manual_1996", [0, 0, 0, 0, 0, "manual", ""]],
    ["type_10", "type_10", "tracked", "", "", "type10|hitomaru", "mbt|mainbattletank|tracked|type10", "wikipedia_type_10_tank", [48000, 0, 0, 0, 894.839846, "", ""]],
    ["type_16_mcv", "type_16_mcv", "wheeled", "", "", "type16|type16mcv|mcv", "mcv|maneuvercombatvehicle|wheeled|type16", "wikipedia_type_16_mcv", [26000, 0, 0, 0, 425.048927, "", ""]],
    ["type_89_ifv", "type_89_ifv", "tracked", "", "", "type89|type89ifv", "ifv|infantryfightingvehicle|tracked|type89", "wikipedia_type_89_ifv", [26500, 0, 0, 0, 447.419923, "", ""]],
    ["type_96_apc", "type_96_apc", "wheeled", "", "", "type96apc|jgsdftype96", "type96apc|jgsdfapc|komatsuapc", "type_96_apc", [14600, 0, 0, 0, 268.451954, "", ""]],
    ["type_96_tank", "type_96_tank", "tracked", "", "", "type96|ztz96", "ztz96|type96tank|chinesetank", "type_96_tank", [41000, 0, 0, 0, 544.360907, "", ""]],
    ["type_99_tank", "type_99_tank", "tracked", "", "", "type99|ztz99", "ztz99|type99tank|chinesembt", "type_99_tank", [55000, 0, 0, 0, 1118.549808, "", ""]],
    ["uaz_469", "uaz_469", "wheeled", "", "", "uaz469", "uaz469|sovietlightutility", "uaz_469", [1700, 0, 0, 220, 0, "manual", ""]],
    ["ural_4320", "ural_4320", "wheeled", "", "", "ural4320", "truck|wheeled|6x6|russia|cargo", "wikipedia_ural_4320", [15300, 0, 0, 0, 0, "manual", ""]],
    ["vbci", "vbci", "wheeled", "", "", "vbci|vehiculeblindedecombatdinfanterie|vbci8x8", "ifv|8x8|armoured|infantryfightingvehicle|france", "nexter_vbci_sales_brochure", [19000, 0, 0, 0, 447.419923, "automatic", ""]],
    ["willys_mb", "willys_mb", "wheeled", "", "", "willysmb|willys|jeep", "willysmb|willysjeep|godevil", "willys_mb", [1113, 0, 0, 222, 44.741992, "manual", ""]],
    ["zbd_04", "zbd_04", "tracked", "", "", "zbd04", "zbd04|chineseifv|type04ifv", "zbd_04", [20000, 0, 0, 0, 440, "", ""]]
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
