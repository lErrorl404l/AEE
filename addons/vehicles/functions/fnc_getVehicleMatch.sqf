#include "..\script_component.hpp"
/*
Vehicle identity matcher (issue #117).

Function: aee_vehicles_fnc_getVehicleMatch.

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
  2 vehicle_type      string, "wheeled", "tracked", "air" or "sea"
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
value_row, air      [operating_weight_kg, length_mm, width_mm, height_mm]
value_row, sea      [operating_weight_kg, length_mm, width_mm, height_mm]

The ground row carries the NRMM inputs. The air and sea row carries the
identity geometry only, because the ground couplings are land-specific.

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
    ["2s19_msta_s", "2s19_msta_s", "tracked", "", "", "2s19mstas", "2s19", "wikipedia_2s19_msta_s", [42000, 0, 0, 0, 0, "", ""]],
    ["2s1_gvozdika", "2s1_gvozdika", "tracked", "", "", "2s1|2s1gvozdika|gvozdika", "", "2s1_gvozdika", [16000, 0, 0, 0, 223.709962, "", ""]],
    ["2s25_sprut_sd", "2s25_sprut_sd", "tracked", "", "", "2s25sprutsd", "2s25", "wikipedia_2s25_sprut_sd", [18000, 0, 0, 0, 0, "", ""]],
    ["2s3_akatsiya_2s3m1", "2s3_akatsiya_2s3m1", "tracked", "", "", "2s3akatsiya2s3m1", "2s3|2s3m1|2s3akatsiya|akatsiya2s3m1", "wikipedia_2s3_akatsiya", [28000, 0, 0, 0, 0, "", ""]],
    ["2s9_nona_s", "2s9_nona_s", "tracked", "", "", "2s9|nona|nonas|sochor", "2s9nonas", "wikipedia_2s9_nona_s", [8700, 0, 0, 0, 180.0, "", ""]],
    ["9k79_tochka_9p129_1m_tel", "9k79_tochka_9p129_1m_tel", "wheeled", "", "", "9k79tochka9p1291mtel", "9k79|9p1291m|9p1291|9k79tochka|tochka9p1291m|9p1291mtel", "ru_wikipedia_d0_a2_d0_be_d1_87_d0_ba_d0_b0_d1_82_d0_b0_d0_ba_d1_82_d0_b8_d1_87_d0_b5_d1_81_d0_ba_d0_b8_d0_b9_d1_80_d0_b0_d0_ba_d0_b5_d1_82_d0_bd_d1_8b_d0_b9_d0_ba_d0_be_d0_bc_d0_bf_d0_bb_d0_b5_d0_ba_d1_81", [18145, 0, 0, 0, 0, "", ""]],
    ["achzarit", "achzarit", "tracked", "", "", "achzarit", "israeliapc|idfapc", "achzarit", [44000, 0, 0, 0, 484.704917, "automatic", ""]],
    ["ahs_krab", "ahs_krab", "tracked", "", "", "krab|ahskrab", "polishhowitzer|155mmspg", "ahs_krab", [48000, 0, 0, 0, 745.699872, "automatic", ""]],
    ["al_fahd", "al_fahd", "wheeled", "", "", "alfahd|af4082", "8x8|saudiarabia", "wikipedia_al_fahd", [16300, 0, 0, 405, 410.13493, "", ""]],
    ["al_khalid", "al_khalid", "tracked", "", "", "alkhalid", "pakistanitank|alkhalidmbt", "al_khalid", [46000, 0, 0, 0, 894.839846, "automatic", ""]],
    ["altay", "altay", "tracked", "", "", "altay|altaymbt", "", "wikipedia_altay", [65000, 0, 0, 0, 1118.549808, "", ""]],
    ["anoa", "anoa", "wheeled", "", "", "anoa|pindadanoa", "6x6|indonesia", "pindad_anoa_6x6_product_page", [14500, 0, 0, 400, 238.623959, "automatic", ""]],
    ["arjun", "arjun", "tracked", "", "", "arjun|arjunmk1|arjunmbt", "india", "wikipedia_arjun", [58500, 0, 0, 450, 1043.979821, "", ""]],
    ["aslav", "aslav", "wheeled", "", "", "aslav", "reconnaissance", "wikipedia_aslav", [13200, 0, 0, 0, 205, "", ""]],
    ["astros_ii", "astros_ii", "wheeled", "", "bmbt01mlrsbasef|mbt01mlrsbasef", "astrosii|astros2|astros", "mlrs|rocketartillery|6x6|brazil|astrosiimlrs|iimlrs", "wikipedia_astros_ii", [10000, 0, 0, 0, 208.795964, "", ""]],
    ["at105_saxon", "at105_saxon", "wheeled", "", "", "at105saxon", "at105|at105saxo", "wikipedia_saxon", [11660, 0, 0, 0, 0, "", ""]],
    ["atf_dingo", "atf_dingo", "wheeled", "", "", "atfdingo", "", "wikipedia_atf_dingo", [11900, 0, 0, 0, 0, "", ""]],
    ["bae_systems_caiman_xm1220_xm1230_caiman_plus", "bae_systems_caiman_xm1220_xm1230_caiman_plus", "wheeled", "", "", "baesystemscaimanxm1220xm1230caimanplus|m1220|m1230|xm1220|xm1230|caiman", "baesystemscaimanxm1220|systemscaiman|caimanxm1220|xm1230caimanplus|xm1230caiman|caimanplus|baesystemscaiman|baesystemscaimanxm1220xm1230", "globalsecurity_caiman_specs", [13835, 0, 0, 0, 0, "", ""]],
    ["bae_systems_rg_33_4x4", "bae_systems_rg_33_4x4", "wheeled", "", "", "baesystemsrg334x4", "rg33|4x4|systemsrg33|rg334x4|baesystemsrg33", "armyrecognition_rg33_4x4", [14000, 0, 0, 0, 0, "", ""]],
    ["bae_systems_rg_33_4x4_socom_m1238", "bae_systems_rg_33_4x4_socom_m1238", "wheeled", "", "", "baesystemsrg334x4socomm1238|m1238|rg33socom", "rg33|4x4|systemsrg33|rg334x4|4x4socom|socomm1238|baesystemsrg334x4socom|rg33soco", "warwheels_rg33_4x4_socom", [14000, 0, 0, 0, 0, "", ""]],
    ["bae_systems_rg_33l_6x6", "bae_systems_rg_33l_6x6", "wheeled", "", "", "baesystemsrg33l6x6|m1232|m1237|rg33l", "rg33|6x6|systemsrg33l|rg33l6x6|baesystemsrg33l", "armyrecognition_rg33_4x4", [24000, 0, 0, 0, 0, "", ""]],
    ["bae_systems_rg_33l_socom_armored_utility_vehicle_auv", "bae_systems_rg_33l_socom_armored_utility_vehicle_auv", "wheeled", "", "", "baesystemsrg33lsocomarmoredutilityvehicleauv|m1239|rg33lsocom|socomauv", "rg33l|rg33|systemsrg33l|socomarmored|armoredutility|utilityvehicle|vehicleauv|baesystemsrg33lsocomarmoredutilityvehicle|baesystemsrg33lsocomarmoredutilityvehicleau|rg33lsoco", "bae_rg33l_auv_brochure", [26473, 0, 0, 0, 0, "", ""]],
    ["bionix", "bionix", "tracked", "", "", "bionix|bionixafv", "singapore", "wikipedia_bionix", [23000, 0, 0, 0, 354.207439, "", ""]],
    ["bm_21_grad", "bm_21_grad", "wheeled", "", "", "bm21grad", "bm21|bm21gra", "wikipedia_bm_21_grad", [13710, 0, 0, 0, 0, "", ""]],
    ["bmc_kirpi", "bmc_kirpi", "wheeled", "", "", "kirpi|bmckirpi", "mineresistant", "wikipedia_bmc_kirpi", [20000, 355.6, 1219.2, 400, 275, "automatic", ""]],
    ["bmd_1", "bmd_1", "tracked", "", "", "bmd1", "", "wikipedia_bmd_1", [7500, 0, 0, 0, 0, "", ""]],
    ["bmd_1k", "bmd_1k", "tracked", "", "", "bmd1k", "", "wikipedia_bmd_1", [7500, 0, 0, 0, 0, "", ""]],
    ["bmd_1p", "bmd_1p", "tracked", "", "", "bmd1p", "", "wikipedia_bmd_1", [7500, 0, 0, 0, 0, "", ""]],
    ["bmd_1pk", "bmd_1pk", "tracked", "", "", "bmd1pk", "", "wikipedia_bmd_1", [7500, 0, 0, 0, 0, "", ""]],
    ["bmd_1r", "bmd_1r", "tracked", "", "", "bmd1r", "", "wikipedia_bmd_1", [7500, 0, 0, 0, 0, "", ""]],
    ["bmd_2", "bmd_2", "tracked", "", "", "bmd2", "", "wikipedia_bmd_2", [11500, 0, 0, 0, 0, "", ""]],
    ["bmd_2k", "bmd_2k", "tracked", "", "", "bmd2k", "", "wikipedia_bmd_2", [11500, 0, 0, 0, 0, "", ""]],
    ["bmd_2m", "bmd_2m", "tracked", "", "", "bmd2m", "", "wikipedia_bmd_2", [11500, 0, 0, 0, 0, "", ""]],
    ["bmd_4", "bmd_4", "tracked", "", "", "bmd4", "", "wikipedia_bmd_4", [13600, 0, 0, 0, 0, "", ""]],
    ["bmd_4m", "bmd_4m", "tracked", "", "", "bmd4m", "", "armyrecognition_bmd_4m", [13500, 0, 0, 0, 0, "", ""]],
    ["bmp_1", "bmp_1", "tracked", "", "", "bmp1", "", "bmp_1", [13200, 0, 0, 370, 223.709962, "", ""]],
    ["bmp_1d", "bmp_1d", "tracked", "", "", "bmp1d", "", "bmp_1", [13200, 0, 0, 0, 0, "", ""]],
    ["bmp_1k", "bmp_1k", "tracked", "", "", "bmp1k", "", "bmp_1", [13200, 0, 0, 0, 0, "", ""]],
    ["bmp_1p", "bmp_1p", "tracked", "", "", "bmp1p", "", "wikipedia_list_of_bmp_1_variants", [13400, 0, 0, 0, 0, "", ""]],
    ["bmp_2", "bmp_2", "tracked", "", "", "bmp2", "", "wikipedia_bmp_2", [14300, 0, 0, 0, 0, "", ""]],
    ["bmp_2d", "bmp_2d", "tracked", "", "", "bmp2d", "", "wikipedia_bmp_2", [14300, 0, 0, 0, 0, "", ""]],
    ["bmp_2k", "bmp_2k", "tracked", "", "", "bmp2k", "", "wikipedia_bmp_2", [14300, 0, 0, 0, 0, "", ""]],
    ["bmp_3", "bmp_3", "tracked", "", "", "bmp3", "", "wikipedia_bmp_3", [18700, 0, 0, 0, 0, "", ""]],
    ["bmpt_terminator", "bmpt_terminator", "tracked", "", "", "bmptterminator", "", "wikipedia_bmpt_terminator", [48000, 0, 0, 0, 0, "", ""]],
    ["bmw_r75", "bmw_r75", "wheeled", "", "", "bmwr75", "sidecarmotorcycle|germanmotorcycle|r75", "bmw_r75", [420, 0, 0, 0, 19.388197, "", ""]],
    ["bmw_x6_concept", "bmw_x6_concept", "wheeled", "", "", "bmwx6|suv|x6conceptcar", "bmwx6conceptcar|x6concept|conceptcar|x6conceptca", "", [0, 0, 0, 0, 0, "", ""]],
    ["boragh", "boragh", "tracked", "", "", "boragh", "iranianapc|boraghapc", "boragh", [13000, 0, 0, 0, 246.080958, "", ""]],
    ["boxer_apc", "boxer_apc", "wheeled", "", "", "boxer|boxerapc|gtkboxer", "8x8", "artec_boxer_apc_datasheet", [38500, 0, 0, 500, 608.491096, "", ""]],
    ["brdm_2", "brdm_2", "wheeled", "", "", "brdm2", "4x4|armoredreconnaissance|armouredcar|brdm", "brdm_2_technical_manual_en", [7000, 330.2, 1117.6, 330, 104.397982, "manual", ""]],
    ["brm_1k", "brm_1k", "tracked", "", "", "brm1k", "brm1", "weaponsystems_346_brm_1k", [13200, 0, 0, 0, 0, "", ""]],
    ["bsa_m20", "bsa_m20", "wheeled", "", "", "bsam20|bsam21", "british|wwii|500cc|sidevalve|wm20|despatchrider|m20", "bsa_m20", [167, 0, 0, 0, 9.694098, "manual", ""]],
    ["btr_4", "btr_4", "wheeled", "", "", "btr4", "8x8|ukraine", "btr4_manual_2010", [21900, 0, 0, 475, 372.849936, "automatic", ""]],
    ["btr_60", "btr_60", "wheeled", "", "", "btr60", "", "wikipedia_btr_60", [10300, 0, 0, 0, 0, "", ""]],
    ["btr_70", "btr_70", "wheeled", "", "", "btr70", "8x8|armoredpersonnelcarrier|btr", "btr_70", [11500, 0, 0, 0, 178.967969, "", ""]],
    ["btr_80", "btr_80", "wheeled", "", "wheeledapc", "btr80", "8x8|armoredpersonnelcarrier|btr", "btr_80_technical_description_2001", [13600, 0, 0, 475, 193.881967, "manual", ""]],
    ["btr_80a", "btr_80a", "wheeled", "", "", "btr80a", "", "weaponsystems_122_btr_80a", [14500, 0, 0, 0, 0, "", ""]],
    ["btr_90", "btr_90", "wheeled", "", "", "btr90", "", "wikipedia_btr_90", [20900, 0, 0, 0, 0, "", ""]],
    ["bushmaster_pmv", "bushmaster_pmv", "wheeled", "", "", "bushmaster|bushmasterpmv", "infantrymobility", "thales_bushmaster_troop_carrier_datasheet", [11400, 0, 0, 430, 223.709962, "", ""]],
    ["c1_ariete", "c1_ariete", "tracked", "", "", "ariete|c1ariete|c1", "c1ariet", "wikipedia_ariete", [54000, 0, 0, 440, 947.038837, "", ""]],
    ["caterpillar_789d", "caterpillar_789d", "wheeled", "", "", "cat789d|caterpillar789d|789d", "caterpillar789|cat789", "wikipedia_caterpillar_789", [0, 0, 3657.6, 0, 1319.888773, "", ""]],
    ["centauro", "centauro", "wheeled", "", "", "centauro|b1centauro|centauro1", "tankdestroyer|8x8|b1centaur", "wikipedia_centauro", [24000, 0, 0, 0, 387.763933, "automatic", ""]],
    ["challenger_1", "challenger_1", "tracked", "", "", "challenger|challenger1|fv4030", "", "challenger_1_aesp_230_p_100_201", [62000, 650, 0, 500, 894.839846, "automatic", ""]],
    ["challenger_2", "challenger_2", "tracked", "", "", "challenger2|challengerii|fv4034", "challenger", "wikipedia_challenger_2", [64000, 0, 0, 500, 894.839846, "", ""]],
    ["chevrolet_suburban_gmt900", "chevrolet_suburban_gmt900", "wheeled", "", "", "suburban|chevroletsuburban", "chevroletsuburbangmt900|gmt900|suburbangmt900", "wikipedia_chevrolet_suburban", [2540, 0, 0, 0, 0, "", ""]],
    ["chevrolet_tahoe_gmt900", "chevrolet_tahoe_gmt900", "wheeled", "", "", "chevrolettahoe|tahoe", "chevrolettahoegmt900|gmt900|tahoegmt900", "wikipedia_chevrolet_tahoe", [0, 0, 0, 0, 0, "automatic", ""]],
    ["cougar_4x4", "cougar_4x4", "wheeled", "", "", "cougar|cougar4x4|mrapcougar|cgrcat1a2|cat1a2", "mineresistant|4x4", "gdls_cougar_4x4_datasheet", [15422, 395.0, 1179.5, 380, 246.080958, "automatic", ""]],
    ["cv90", "cv90", "tracked", "", "", "cv90|combatvehicle90|stridsfordon90", "combatvehicle|vehicle90", "wikipedia_cv90", [23000, 0, 0, 0, 0, "", ""]],
    ["cv90_denmark", "cv90_denmark", "tracked", "", "", "cv9035dk|cv90denmark|combatvehicle90denmark", "cv90|combatvehicle|vehicle90|90denmark|cv9035d|cv90denmar|combatvehicle90denmar", "wikipedia_cv90", [23000, 0, 0, 0, 0, "", ""]],
    ["cv90_norway", "cv90_norway", "tracked", "", "", "cv9030n|cv90norway|combatvehicle90norway", "cv90|combatvehicle|vehicle90|90norway|cv9030|cv90norwa|combatvehicle90norwa", "wikipedia_cv90", [23000, 0, 0, 0, 0, "", ""]],
    ["dardo", "dardo", "tracked", "", "", "dardo|dardoifv|vcc80", "", "wikipedia_dardo", [23400, 0, 0, 0, 381.798334, "", ""]],
    ["eitan", "eitan", "wheeled", "", "", "eitan|eitanafv", "armouredfightingvehicle", "wikipedia_eitan", [50000, 0, 0, 0, 559.274904, "", ""]],
    ["fahd", "fahd", "wheeled", "", "", "fahd|fahdapc", "4x4|egypt", "wikipedia_fahd", [12500, 0, 0, 370, 205.067465, "", ""]],
    ["freccia", "freccia", "wheeled", "", "", "freccia|vbmfreccia|frecciaifv", "8x8", "wikipedia_freccia", [22000, 0, 0, 0, 0, "", ""]],
    ["fv101_scorpion", "fv101_scorpion", "tracked", "", "", "fv101scorpion", "fv101|fv101scorpio", "wikipedia_fv101_scorpion", [8074, 0, 0, 0, 0, "", ""]],
    ["fv107_scimitar", "fv107_scimitar", "tracked", "", "", "fv107scimitar", "fv107|fv107scimita", "wikipedia_fv107_scimitar", [7800, 0, 0, 0, 0, "", ""]],
    ["fv4201_chieftain", "fv4201_chieftain", "tracked", "", "", "fv4201chieftain", "fv4201|fv4201chieftai", "wikipedia_chieftain", [56000, 0, 0, 0, 0, "", ""]],
    ["fv510_warrior", "fv510_warrior", "tracked", "", "iapctracked03cannonf", "warrior|fv510|fv510warrior|warriortrackedarmouredvehicle|mora|fv720", "fv510warrio", "wikipedia_fv510_warrior", [25400, 0, 0, 0, 410.13493, "", ""]],
    ["gaz_233011_gaz_tigr", "gaz_233011_gaz_tigr", "wheeled", "", "", "gaz233011gaztigr", "gaz233011|gaz233011gaz|gaztigr|gaz233011gaztig", "wikipedia_tigr_military_vehicle", [7200, 0, 0, 0, 0, "", ""]],
    ["gaz_233014_tigr_with_arbalet_turret", "gaz_233014_tigr_with_arbalet_turret", "wheeled", "", "", "gaz233014tigrwitharbaletturret", "gaz233014|gaz233014tigr|tigrwith|witharbalet|arbaletturret|gaz233014tigrwitharbaletturre", "ru_wikipedia_", [5300, 0, 0, 0, 0, "", ""]],
    ["gaz_233114_tigr_m", "gaz_233114_tigr_m", "wheeled", "", "", "gaz233114tigrm", "gaz233114|gaz233114tigr", "ru_wikipedia_", [8980, 0, 0, 0, 0, "", ""]],
    ["gaz_66", "gaz_66", "wheeled", "", "", "gaz66", "soviettruck", "gaz_66", [3440, 0, 0, 315, 0, "manual", ""]],
    ["gaz_66_ap_2", "gaz_66_ap_2", "wheeled", "", "", "gaz66ap2", "ap2", "gaz_66", [3440, 0, 0, 0, 0, "", ""]],
    ["gaz_66_esb_8im", "gaz_66_esb_8im", "wheeled", "", "", "gaz66esb8im", "esb8im|esb8i|gaz66esb8", "gaz_66", [3440, 0, 0, 0, 0, "", ""]],
    ["guarani", "guarani", "wheeled", "", "", "guarani|vbtpmrguarani|vbtpmr", "6x6|brazil", "guarani_eb70_ci_11412", [17500, 0, 0, 0, 0, "", ""]],
    ["harley_wla", "harley_wla", "wheeled", "", "", "wla|harleywla", "militarymotorcycle|vtwin|harleydavidsonwla", "harley_wla_tm_9_879", [245, 101.6, 660.4, 102, 18.642497, "manual", ""]],
    ["hmmwv_m1025", "hmmwv_m1025", "wheeled", "", "", "m1025|m1025a1|m1025a2|m1026", "m1025hmmwv", "tm_9_2320_280_10", [2706, 0, 0, 0, 0, "", ""]],
    ["hmmwv_m998", "hmmwv_m998", "wheeled", "", "", "m998|m998a1|hmmwv|humvee|m1038", "4x4|troopcarrier|m998hmmwv", "tm_9_2320_280_10", [2361, 0, 0, 410, 111.854981, "automatic", ""]],
    ["honda_cb750", "honda_cb750", "wheeled", "", "", "cb750|hondacb750|cb750four", "superbike|aircooledfour|classicmotorcycle|cb750fou", "honda_cb750", [232.7, 0, 0, 0, 50.707591, "manual", ""]],
    ["honda_cg125", "honda_cg125", "wheeled", "", "", "cg125|hondacg125", "motorbike|commuter|125|japan", "wikipedia_honda_cg125", [105, 0, 0, 0, 7.829849, "manual", ""]],
    ["honda_civic_6gen_coupe", "honda_civic_6gen_coupe", "wheeled", "", "", "civiccoupe|hondaciviccoupe|civic2doorcoupe", "passengercar|hondaciviccoupe6thgeneration|6th|hondacivic|coupe6th|6thgeneration|civic|civic2doorcoup", "honda_civic_factory_service_manual_96_00", [1570, 0, 0, 150, 0, "", ""]],
    ["honda_civic_6gen_hatchback", "honda_civic_6gen_hatchback", "wheeled", "", "chatchback01f|chatchback01sportf|hatchback01basef", "civichatchback|hondacivichatchback|civic2doorhatchback", "passengercar|hondacivichatchback6thgeneration|6th|hondacivic|hatchback6th|6thgeneration|civic|civic2doorhatchbac", "honda_civic_factory_service_manual_96_00", [1495, 0, 0, 150, 0, "", ""]],
    ["honda_civic_6gen_sedan", "honda_civic_6gen_sedan", "wheeled", "", "car", "civic|hondacivic|hondacivicsedan|ej6|ej8", "passengercar|hondacivicsedan6thgeneration|6th|civicsedan|sedan6th|6thgeneration", "honda_civic_factory_service_manual_96_00", [1540, 0, 0, 150, 0, "automatic", ""]],
    ["hyundai_iblue_concept", "hyundai_iblue_concept", "wheeled", "", "", "hatchback|hyundaiiblue|iblue", "hyundaiiblueconceptcar|iblueconcept|conceptcar", "", [0, 0, 0, 0, 0, "", ""]],
    ["k21_ifv", "k21_ifv", "tracked", "", "", "k21|k21ifv", "koreanifv|k21if", "k21_ifv", [25600, 0, 0, 0, 559.274904, "", ""]],
    ["k2_black_panther", "k2_black_panther", "tracked", "", "", "k2|k2blackpanther|blackpanther", "k2black|k2blackpanthe", "wikipedia_k2_black_panther", [56000, 0, 0, 0, 0, "", ""]],
    ["k808_white_tiger", "k808_white_tiger", "wheeled", "", "", "k808|whitetiger|k806", "koreanapc|k808whitetiger|k808white", "k808_white_tiger", [20000, 0, 0, 0, 313.193946, "", ""]],
    ["k9_thunder", "k9_thunder", "tracked", "", "", "k9|k9thunder|k9a1", "selfpropelledhowitzer|sph|k9thunde", "wikipedia_k9_thunder", [47000, 0, 0, 410, 745.699872, "", ""]],
    ["kamaz_4310", "kamaz_4310", "wheeled", "", "", "kamaz4310", "", "ru_wikipedia_kamaz_4310", [7080, 400, 1220, 365, 156.596973, "manual", ""]],
    ["kamaz_5350_mustang", "kamaz_5350_mustang", "wheeled", "", "", "kamaz5350mustang", "kamaz5350|kamaz5350mustan", "de_wikipedia_kamaz_5350", [9600, 0, 0, 0, 0, "", ""]],
    ["kamaz_63968_typhoon_k", "kamaz_63968_typhoon_k", "wheeled", "", "", "kamaz63968typhoonk|typhoon", "kamaz63968|kamaz63968typhoon", "wikipedia_kamaz_typhoon", [21000, 0, 0, 0, 0, "", ""]],
    ["karrar_tank", "karrar_tank", "tracked", "", "", "karrar", "iraniantank|karrarmbt", "karrar_tank", [51000, 0, 0, 0, 0, "", ""]],
    ["kawasaki_ninja_250r_ex250f", "kawasaki_ninja_250r_ex250f", "wheeled", "", "", "ninja250|ninja250r|ex250|ex250f|gpx250|gpx250r|kawasakininja250r", "motorcycle|ninja|sportbike|kawasakininja250rex250f|250r|kawasakininja|250rex250f|kawasakininja250", "kawasaki_ninja_250r_service_manual", [161, 130.0, 614.4, 155, 27.948831, "manual", "none"]],
    ["komatsu_lav", "komatsu_lav", "wheeled", "", "", "komatsulav|jgsdflav", "japaneselav", "komatsu_lav", [4500, 0, 0, 0, 119.31198, "automatic", ""]],
    ["kraz_255b1", "kraz_255b1", "wheeled", "", "", "kraz255b1", "", "wikipedia_kraz_255", [11950, 0, 0, 0, 0, "", ""]],
    ["land_rover_wolf_xd_110", "land_rover_wolf_xd_110", "wheeled", "", "", "landroverwolfxd110", "landrover|roverwolf|wolfxd|xd110|landroverwolf", "elite_uk_forces_land_rover_wolf", [1600, 0, 0, 0, 0, "", ""]],
    ["lav25", "lav25", "wheeled", "", "", "lav25", "", "wikipedia_lav25", [12800, 0, 0, 0, 205.0, "", ""]],
    ["lav_6", "lav_6", "wheeled", "", "", "lav6|lav60", "8x8|lav", "wikipedia_lav6", [20638, 0, 0, 0, 335.564942, "", ""]],
    ["leclerc", "leclerc", "tracked", "", "", "leclerc|charleclerc", "", "wikipedia_leclerc", [54500, 0, 0, 500, 1118.549808, "automatic", ""]],
    ["leopard_1", "leopard_1", "tracked", "", "", "leopard1", "", "wikipedia_leopard_1", [42200, 0, 0, 0, 0, "", ""]],
    ["leopard_2a6", "leopard_2a6", "tracked", "", "", "leopard2|leopard2a6|2a6|leopard", "", "wikipedia_leopard_2", [62300, 0, 0, 540, 1118.549808, "", ""]],
    ["leopard_2a6_finland", "leopard_2a6_finland", "tracked", "", "", "leopard2a6finland|leopard2finland", "2a6|2a6finland|leopard2|leopard2finlan", "wikipedia_leopard_2", [62300, 0, 0, 540, 1118.549808, "", ""]],
    ["leopard_2a6_hel", "leopard_2a6_hel", "tracked", "", "", "leopard2a6hel|leopard2hel|leopard2greece", "2a6|2a6hel|leopard2|leopard2he|leopard2greec", "wikipedia_leopard_2", [62300, 0, 0, 540, 1118.549808, "", ""]],
    ["leopard_2a7_hungary", "leopard_2a7_hungary", "tracked", "", "", "leopard2a7hungary|leopard2a7|leopard2hungary", "2a7|2a7hungary|leopard2|leopard2hungar", "wikipedia_leopard_2", [66500, 0, 0, 540, 1118.549808, "", ""]],
    ["m1059", "m1059", "tracked", "", "", "m1059", "smokegeneratorcarrier", "tm_9_2350_261_10", [11077, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m1064", "m1064", "tracked", "", "", "m1064", "selfpropelled120mmmortarcarrier", "tm_9_2350_261_10", [12546, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m1068", "m1068", "tracked", "", "", "m1068", "standardizedintegratedcommandpostsystem", "tm_9_2350_261_10", [12182, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m1078a1p2", "m1078a1p2", "wheeled", "", "", "m1078a1p2", "", "wikipedia_family_of_medium_tactical_vehicles", [10390, 0, 0, 0, 0, "", ""]],
    ["m1078a1r_socom_sov", "m1078a1r_socom_sov", "wheeled", "", "", "m1078a1rsocomsov", "m1078a1r|m1078a1|m1078a1rsocom|socomsov", "fmtv_a1r_m1078_cargo_datasheet", [7808, 0, 0, 0, 0, "", ""]],
    ["m1083a1p2", "m1083a1p2", "wheeled", "", "", "m1083a1p2", "", "wikipedia_family_of_medium_tactical_vehicles", [11280, 0, 0, 0, 0, "", ""]],
    ["m1084a1p2", "m1084a1p2", "wheeled", "", "", "m1084a1p2", "", "globalsecurity_m1084", [10740, 0, 0, 0, 0, "", ""]],
    ["m1084a1r_socom_sov", "m1084a1r_socom_sov", "wheeled", "", "", "m1084a1rsocomsov", "m1084a1r|m1084a1|m1084a1rsocom|socomsov", "fmtv_a1r_m1084_cargo_datasheet", [11184, 0, 0, 0, 0, "", ""]],
    ["m1085a1p2", "m1085a1p2", "wheeled", "", "", "m1085a1p2", "", "globalsecurity_m1085", [9451, 0, 0, 0, 0, "", ""]],
    ["m109a6_paladin", "m109a6_paladin", "tracked", "", "", "m109a6paladin", "m109a6", "inetres_m109", [28849, 0, 0, 0, 0, "", ""]],
    ["m1117_guardian_asv", "m1117_guardian_asv", "wheeled", "", "", "m1117guardianasv", "m1117|m1117guardian|guardianasv|m1117guardianas", "wikipedia_m1117_armored_security_vehicle", [13410, 0, 0, 0, 0, "", ""]],
    ["m113a2", "m113a2", "tracked", "", "trackedapc", "m113|m113a2", "armoredpersonnelcarrier", "tm_9_2350_261_10", [11353, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m113a3", "m113a3", "tracked", "", "", "m113a3", "", "inetres_m113", [12250, 0, 0, 0, 0, "", ""]],
    ["m1151a1", "m1151a1", "wheeled", "", "", "m1151a1", "", "globalsecurity_m1151_specs", [3697, 0, 0, 0, 0, "", ""]],
    ["m1152a1", "m1152a1", "wheeled", "", "", "m1152a1", "", "globalsecurity_m1152", [3221, 0, 0, 0, 0, "", ""]],
    ["m1165a1", "m1165a1", "wheeled", "", "", "m1165a1", "", "globalsecurity_m1165_specs", [3279, 0, 0, 0, 0, "", ""]],
    ["m142_himars", "m142_himars", "wheeled", "", "", "m142himars", "m142|m142himar", "wikipedia_m142_himars", [13500, 0, 0, 0, 0, "", ""]],
    ["m1_abrams", "m1_abrams", "tracked", "", "tank", "m1|m1abrams|abrams|generalabrams", "105mm|m1abram", "tm_9_2350_255_10", [54431, 0, 0, 483, 0, "automatic", ""]],
    ["m1a1_aim", "m1a1_aim", "tracked", "", "", "m1a1aim", "m1a1", "wikipedia_m1_abrams", [61300, 0, 0, 0, 0, "", ""]],
    ["m1a1_fep", "m1a1_fep", "tracked", "", "", "m1a1fep", "m1a1", "wikipedia_m1_abrams", [57153, 0, 0, 0, 0, "", ""]],
    ["m1a1_hc", "m1a1_hc", "tracked", "", "", "m1a1hc", "m1a1", "wikipedia_m1_abrams", [57153, 0, 0, 0, 0, "", ""]],
    ["m1a2_sep_v1", "m1a2_sep_v1", "tracked", "", "", "m1a2sepv1", "m1a2|m1a2sep|sepv1", "wikipedia_m1_abrams", [63000, 0, 0, 0, 0, "", ""]],
    ["m1a2_sep_v2", "m1a2_sep_v2", "tracked", "", "", "m1a2sepv2", "m1a2|m1a2sep|sepv2", "wikipedia_m1_abrams", [64600, 0, 0, 0, 0, "", ""]],
    ["m270_mlrs", "m270_mlrs", "tracked", "", "", "m270mlrs", "m270|m270mlr", "wikipedia_m270_mlrs", [24035, 0, 0, 0, 0, "", ""]],
    ["m2_m3_bradley", "m2_m3_bradley", "tracked", "", "", "m2bradley|m3bradley|bradley|m2ifv|m3cfv", "cfv|cavalryfightingvehicle|m2bradle|m3bradle|m2if|m3cf", "tm_9_2350_252_10_1", [22285, 533, 152, 0, 372.849936, "automatic", "grousers"]],
    ["m2a2_bradley", "m2a2_bradley", "tracked", "", "", "m2a2bradley", "m2a2", "inetres_m2", [29000, 0, 0, 0, 0, "", ""]],
    ["m2a3_bradley", "m2a3_bradley", "tracked", "", "", "m2a3bradley", "m2a3", "inetres_m2", [30000, 0, 0, 0, 0, "", ""]],
    ["m3_bradley", "m3_bradley", "tracked", "", "", "m3bradley", "m3bradle", "wikipedia_m3_bradley", [27669, 0, 0, 0, 0, "", ""]],
    ["m48_patton", "m48_patton", "tracked", "", "", "m48patton", "m48|m48patto", "wikipedia_m48_patton", [44996, 0, 0, 0, 0, "", ""]],
    ["m577a2", "m577a2", "tracked", "", "", "m577a2", "commandpostcarrier", "tm_9_2350_261_10", [11719, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m60_patton", "m60_patton", "tracked", "", "", "m60patton", "m60|m60patto", "wikipedia_m60_tank", [47718, 0, 0, 0, 0, "", ""]],
    ["m6_linebacker", "m6_linebacker", "tracked", "", "", "m6|m6a2|linebacker", "m6linebacker", "wikipedia_m6_linebacker", [27600, 0, 0, 0, 450.0, "", ""]],
    ["m88_recovery_vehicle", "m88_recovery_vehicle", "tracked", "", "", "m88recoveryvehicle", "m88|m88recovery|recoveryvehicle|m88recoveryvehicl", "wikipedia_m88_recovery_vehicle", [50800, 0, 0, 0, 0, "", ""]],
    ["m923", "m923", "wheeled", "", "", "m923", "5ton|6x6|m939", "tm_9_2320_272_10", [9806, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m923a1", "m923a1", "wheeled", "", "", "m923a1", "5ton|6x6|m939a1", "tm_9_2320_272_10", [10067, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m923a2", "m923a2", "wheeled", "", "truck", "m923|m923a2|m939|m939a2", "5ton|6x6|dropside", "tm_9_2320_272_10", [9502, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m925", "m925", "wheeled", "", "", "m925", "5ton|6x6|m939", "tm_9_2320_272_10", [10151, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m925a1", "m925a1", "wheeled", "", "", "m925a1", "5ton|6x6|m939a1", "tm_9_2320_272_10", [10567, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m925a2", "m925a2", "wheeled", "", "", "m925a2", "5ton|6x6|m939a2", "tm_9_2320_272_10", [10002, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m927", "m927", "wheeled", "", "", "m927", "5ton|6x6|m939", "tm_9_2320_272_10", [12598, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m927a1", "m927a1", "wheeled", "", "", "m927a1", "5ton|6x6|m939a1", "tm_9_2320_272_10", [11366, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m927a2", "m927a2", "wheeled", "", "", "m927a2", "5ton|6x6|m939a2", "tm_9_2320_272_10", [10801, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m928", "m928", "wheeled", "", "", "m928", "5ton|6x6|m939", "tm_9_2320_272_10", [12626, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m928a1", "m928a1", "wheeled", "", "", "m928a1", "5ton|6x6|m939a1", "tm_9_2320_272_10", [11865, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m928a2", "m928a2", "wheeled", "", "", "m928a2", "5ton|6x6|m939a2", "tm_9_2320_272_10", [11300, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m929", "m929", "wheeled", "", "", "m929", "5ton|6x6|m939", "tm_9_2320_272_10", [11753, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m929a1", "m929a1", "wheeled", "", "", "m929a1", "5ton|6x6|m939a1", "tm_9_2320_272_10", [11380, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m929a2", "m929a2", "wheeled", "", "", "m929a2", "5ton|6x6|m939a2", "tm_9_2320_272_10", [10814, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m930", "m930", "wheeled", "", "", "m930", "5ton|6x6|m939", "tm_9_2320_272_10", [12087, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m930a1", "m930a1", "wheeled", "", "", "m930a1", "5ton|6x6|m939a1", "tm_9_2320_272_10", [11879, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m930a2", "m930a2", "wheeled", "", "", "m930a2", "5ton|6x6|m939a2", "tm_9_2320_272_10", [11314, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m931", "m931", "wheeled", "", "", "m931", "5ton|6x6|m939", "tm_9_2320_272_10", [10028, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m931a1", "m931a1", "wheeled", "", "", "m931a1", "5ton|6x6|m939a1", "tm_9_2320_272_10", [9598, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m931a2", "m931a2", "wheeled", "", "", "m931a2", "5ton|6x6|m939a2", "tm_9_2320_272_10", [9032, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m932", "m932", "wheeled", "", "", "m932", "5ton|6x6|m939", "tm_9_2320_272_10", [10370, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m932a1", "m932a1", "wheeled", "", "", "m932a1", "5ton|6x6|m939a1", "tm_9_2320_272_10", [10098, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m932a2", "m932a2", "wheeled", "", "", "m932a2", "5ton|6x6|m939a2", "tm_9_2320_272_10", [9532, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m934", "m934", "wheeled", "", "", "m934", "5ton|6x6|m939", "tm_9_2320_272_10", [13595, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m934a1", "m934a1", "wheeled", "", "", "m934a1", "5ton|6x6|m939a1", "tm_9_2320_272_10", [13293, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m934a2", "m934a2", "wheeled", "", "", "m934a2", "5ton|6x6|m939a2", "tm_9_2320_272_10", [12728, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m936", "m936", "wheeled", "", "", "m936", "5ton|6x6|m939", "tm_9_2320_272_10", [17858, 279.4, 1066.8, 292, 186.424968, "automatic", ""]],
    ["m936a1", "m936a1", "wheeled", "", "", "m936a1", "5ton|6x6|m939a1", "tm_9_2320_272_10", [17322, 355.6, 1219.2, 353, 186.424968, "automatic", ""]],
    ["m936a2", "m936a2", "wheeled", "", "", "m936a2", "5ton|6x6|m939a2", "tm_9_2320_272_10", [16757, 355.6, 1219.2, 353, 178.967969, "automatic", ""]],
    ["m977_hemtt", "m977_hemtt", "wheeled", "", "", "m977|hemtt|m977hemtt|heavyexpandedmobilitytacticaltruck", "8x8|m977hemt", "tm_9_2320_279_10_1", [17600, 406.4, 1320.8, 609.6, 331.836443, "automatic", ""]],
    ["m977a4", "m977a4", "wheeled", "", "", "m977a4", "", "wikipedia_heavy_expanded_mobility_tactical_truck", [19278, 0, 0, 0, 0, "", ""]],
    ["m978a4_hemtt", "m978a4_hemtt", "wheeled", "", "", "m978a4hemtt", "m978a4", "oshkosh_hemtt_a4_fuel_servicing_datasheet", [19119, 0, 0, 0, 0, "", ""]],
    ["m_atv_m1240", "m_atv_m1240", "wheeled", "", "mrap", "matv|m1240", "oshkosh|matvm1240", "tm_9_2355_335_10", [11123, 395.0, 1179.5, 0, 275.908953, "automatic", ""]],
    ["m_atv_m1240a1", "m_atv_m1240a1", "wheeled", "", "", "matvm1240a1|m1240a1", "oshkosh|matv", "tm_9_2355_335_10", [12940, 0, 0, 0, 275.908953, "automatic", ""]],
    ["m_atv_m1245", "m_atv_m1245", "wheeled", "", "", "matvm1245|m1245", "oshkosh|matv", "tm_9_2355_335_10", [12325, 395.0, 1179.5, 0, 275.908953, "automatic", ""]],
    ["marder_1a3", "marder_1a3", "tracked", "", "", "marder|marder1a3|spzmarder|schutzenpanzermarder", "germany|1a3", "thyssen_henschel_marder_1a3", [28600, 0, 0, 0, 439.962924, "automatic", ""]],
    ["maxxpro", "maxxpro", "wheeled", "", "", "maxxpro|internationalmaxxpro", "4x4|unitedstates", "tm_9_2355_106_10", [17168, 395.0, 1179.5, 260, 246.080958, "automatic", ""]],
    ["mercedes_benz_sprinter", "mercedes_benz_sprinter", "wheeled", "", "", "mercedesbenzsprinter|sprinter|van", "", "", [0, 0, 0, 0, 0, "", ""]],
    ["merkava_mk4", "merkava_mk4", "tracked", "", "bmbt01tuskf|btmbt01tuskf", "merkava|merkavamk4|slammer|m2a1|m2a4", "merkavamk", "wikipedia_merkava", [65000, 0, 0, 450, 1119, "", ""]],
    ["mowag_piranha", "mowag_piranha", "wheeled", "", "", "piranha|mowagpiranha", "armouredfightingvehicle", "wikipedia_mowag_piranha", [0, 0, 0, 0, 202, "automatic", ""]],
    ["mt_lb", "mt_lb", "tracked", "", "", "mtlb", "", "wikipedia_mt_lb", [11900, 0, 0, 0, 0, "", ""]],
    ["namer", "namer", "tracked", "", "bapctracked01aaf|bapctracked01crvf|bapctracked01rcwsf|btapctracked01crvf", "namer|namerapc|panther|cheetah|bobcat", "", "wikipedia_namer", [60000, 0, 0, 0, 894.839846, "", ""]],
    ["object_681", "object_681", "tracked", "", "", "object681|obyekt681", "", "ru_wikipedia_object_681", [13600, 0, 0, 420, 223.709962, "", ""]],
    ["offroad_q7_l200_composite", "offroad_q7_l200_composite", "wheeled", "", "bgoffroad01atf|coffroad01repairf|igoffroad01atf|ogoffroad01atf|offroad01atbasef|offroad01basef|offroad01repairbasef|offroad01unarmedbasef|rhsgreftlagoffroadat|rhsgreftlaoffroadat", "audiq7pickupconcept|q7pickupconcept|mitsubishil200", "audiq7pickupconceptfrontandmitsubishil200rearcomposite|l200|audiq7|q7pickup|pickupconcept|conceptfront|frontand|andmitsubishi|l200rear|rearcomposite|q7pickupconceptandl200|conceptand|andl200|audiq7pickupconcep|q7pickupconcep", "", [0, 0, 0, 0, 0, "", ""]],
    ["olifant", "olifant", "tracked", "", "", "olifant|olifantmk1|olifantmk2", "", "wikipedia_olifant", [58000, 0, 0, 508, 775.527867, "automatic", ""]],
    ["oshkosh_m_atv_m1277", "oshkosh_m_atv_m1277", "wheeled", "", "", "oshkoshmatvm1277", "m1277|oshkoshmatv|matvm1277", "wikipedia_oshkosh_m_atv", [12500, 0, 0, 0, 0, "", ""]],
    ["oshkosh_mtvr_mk23", "oshkosh_mtvr_mk23", "wheeled", "", "", "oshkoshmtvrmk23|oshkoshmtvr|mtvr", "mk23|mtvrmk23", "wikipedia_mtvr", [13200, 0, 0, 0, 0, "", ""]],
    ["pandur_ii", "pandur_ii", "wheeled", "", "", "pandurii|pandur2|pandur", "", "wikipedia_pandur_ii", [17300, 0, 0, 0, 335, "automatic", ""]],
    ["patria_amv", "patria_amv", "wheeled", "", "", "patriaamv|amv|patria", "", "wikipedia_patria_amv", [16000, 0, 0, 0, 450, "automatic", ""]],
    ["peugeot_p4", "peugeot_p4", "wheeled", "", "", "peugeotp4", "lightutility|vltt|xn8|legere|frencharmy", "peugeot_p4", [1750, 0, 0, 0, 58.16459, "", ""]],
    ["piranha_v", "piranha_v", "wheeled", "", "", "piranhav|piranha5|piranha", "", "wikipedia_piranha_v", [0, 0, 0, 0, 437, "", ""]],
    ["pizarro", "pizarro", "tracked", "", "", "pizarro|ascod|ascodpizarro", "", "wikipedia_ascod", [26300, 0, 0, 0, 447.419923, "", ""]],
    ["polaris_mrzr_4", "polaris_mrzr_4", "wheeled", "", "", "polarismrzr4|mrzr4", "polarismrzr", "utv_guide_mrzr_4", [0, 0, 0, 0, 65.621589, "", ""]],
    ["prp_3", "prp_3", "tracked", "", "", "prp3", "", "weaponsystems_623_prp_3_val", [13000, 0, 0, 0, 0, "", ""]],
    ["pt91_twardy", "pt91_twardy", "tracked", "", "", "pt91|pt91twardy|twardy", "pt91tward", "wikipedia_pt91", [45900, 0, 0, 395, 633.844891, "manual", ""]],
    ["pts_m", "pts_m", "tracked", "", "", "ptsm", "", "ru_wikipedia_d0_9f_d0_a2_d0_a1_d0_9c", [17800, 0, 0, 0, 0, "", ""]],
    ["puma_cev", "puma_cev", "tracked", "", "", "pumacev|idfpuma", "israeliengineeringvehicle|puma", "puma_cev", [50000, 0, 0, 0, 671.129885, "", ""]],
    ["puma_ifv", "puma_ifv", "tracked", "", "", "pumagermanifv", "pumagerman|germanifv", "wikipedia_puma_ifv", [31400, 0, 0, 0, 0, "", ""]],
    ["ratel", "ratel", "wheeled", "", "", "ratel|ratel20", "6x6", "wikipedia_ratel", [18500, 0, 0, 340, 205.067465, "", ""]],
    ["rg_31", "rg_31", "wheeled", "", "", "rg31|rg31nyala|nyala", "4x4|rg31nyal", "gdls_rg31_mk5_datasheet", [14000, 395.0, 1179.5, 492, 223.709962, "automatic", ""]],
    ["rooikat", "rooikat", "wheeled", "", "", "rooikat", "8x8", "wikipedia_rooikat", [28000, 0, 0, 0, 413.863429, "", ""]],
    ["rosomak", "rosomak", "wheeled", "", "", "rosomak|ktorosomak", "8x8|patriaamv", "wikipedia_rosomak", [22000, 0, 0, 0, 404.91503, "", ""]],
    ["sd_kfz_251", "sd_kfz_251", "tracked", "", "", "sdkfz251", "", "wikipedia_sd_kfz_251", [7810, 0, 0, 0, 0, "", ""]],
    ["snatch_land_rover", "snatch_land_rover", "wheeled", "", "", "snatchlandrover", "snatchland|landrover", "wikipedia_snatch_land_rover", [4050, 0, 0, 0, 0, "", ""]],
    ["strv_122", "strv_122", "tracked", "", "", "stridsvagn122|strv122", "leopard2", "wikipedia_strv_122", [62500, 0, 0, 540, 1102.890111, "", ""]],
    ["stryker_m1126_icv", "m1126_stryker_icv", "wheeled", "", "", "stryker|m1126|m1126strykericv|m1126icv", "8x8|icv|m1126stryker|strykericv|m1126strykeric|m1126ic", "wikipedia_stryker", [16470, 0, 0, 0, 260.994955, "", ""]],
    ["t_14_armata", "t_14_armata", "tracked", "", "", "t14armata", "t14|t14armat", "wikipedia_t14_armata", [55000, 0, 0, 0, 0, "", ""]],
    ["t_15_armata", "t_15_armata", "tracked", "", "", "t15armata", "t15|t15armat", "wikipedia_t15_armata", [50000, 0, 0, 0, 0, "", ""]],
    ["t_34", "t_34", "tracked", "", "", "t34", "", "wikipedia_t_34", [32400, 0, 0, 0, 0, "", ""]],
    ["t_54_t_55", "t_54_t_55", "tracked", "", "", "t54t55", "t54|t55", "wikipedia_t_54_t_55", [36000, 0, 0, 0, 0, "", ""]],
    ["t_62", "t_62", "tracked", "", "", "t62", "", "wikipedia_t_62", [37000, 0, 0, 0, 0, "", ""]],
    ["t_64", "t_64", "tracked", "", "", "t64", "", "t64a_technical_manual_1984", [38500, 0, 0, 500, 521.98991, "", ""]],
    ["t_72b3_obr_2012g", "t_72b3_obr_2012g", "tracked", "", "", "t72b3obr2012g", "t72b3|2012g|t72b3obr|obr2012g", "ru_wikipedia_d0_a2_72_d0_913", [46500, 0, 0, 0, 0, "", ""]],
    ["t_72b_obr_1984g", "t_72b_obr_1984g", "tracked", "", "", "t72bobr1984g", "t72b|t72|1984g|t72bobr|obr1984g|t72bobr1984", "wikipedia_t_72", [44500, 0, 0, 0, 0, "", ""]],
    ["t_72m4cz", "t_72m4cz", "tracked", "", "", "t72m4cz|t72", "t72m4", "wikipedia_t_72m4cz", [48000, 0, 0, 0, 746, "", ""]],
    ["t_72ms", "t_72ms", "tracked", "", "", "t72ms", "t72m", "wikipedia_t_72", [44500, 0, 0, 0, 0, "", ""]],
    ["t_80", "t_80", "tracked", "", "", "t80", "", "ru_wikipedia_d0_a2_80", [42000, 0, 0, 0, 0, "", ""]],
    ["t_80a", "t_80a", "tracked", "", "", "t80a", "", "ru_wikipedia_d0_a2_80_d0_90", [45200, 0, 0, 0, 0, "", ""]],
    ["t_80b", "t_80b", "tracked", "", "", "t80b", "", "wikipedia_t_80", [42500, 0, 0, 0, 0, "", ""]],
    ["t_80bk", "t_80bk", "tracked", "", "", "t80bk", "", "wikipedia_t_80", [42500, 0, 0, 0, 0, "", ""]],
    ["t_80bv", "t_80bv", "tracked", "", "", "t80bv", "", "wikipedia_t_80", [42500, 0, 0, 0, 0, "", ""]],
    ["t_80bvk", "t_80bvk", "tracked", "", "", "t80bvk", "", "wikipedia_t_80", [42500, 0, 0, 0, 0, "", ""]],
    ["t_80u", "t_80u", "tracked", "", "", "t80u", "", "ru_wikipedia_d0_a2_80_d0_a3", [46500, 0, 0, 0, 0, "", ""]],
    ["t_80ue_1", "t_80ue_1", "tracked", "", "", "t80ue1", "", "wikipedia_t_80_models", [46500, 0, 0, 0, 0, "", ""]],
    ["t_80um", "t_80um", "tracked", "", "", "t80um", "", "ru_wikipedia_d0_a2_80_d0_a3", [46500, 0, 0, 0, 0, "", ""]],
    ["t_90", "t_90", "tracked", "", "", "t90|t90a|t90s", "russia", "wikipedia_t_90", [46000, 0, 0, 0, 626.387892, "", ""]],
    ["t_90am", "t_90am", "tracked", "", "", "t90am", "t90a", "ru_wikipedia_d0_a2_90_d0_90_d0_9c", [48000, 0, 0, 0, 0, "", ""]],
    ["t_90sa", "t_90sa", "tracked", "", "", "t90sa", "t90s", "wikipedia_t_90", [46500, 0, 0, 0, 0, "", ""]],
    ["t_90sm", "t_90sm", "tracked", "", "", "t90sm", "t90s", "wikipedia_t_90", [48000, 0, 0, 0, 0, "", ""]],
    ["terrex", "terrex", "wheeled", "", "", "terrex|terrexicv", "8x8|singapore", "stengg_terrex_family_datasheet", [24000, 0, 0, 0, 335.564942, "automatic", ""]],
    ["toyota_hilux_technical", "toyota_hilux_technical", "wheeled", "", "", "toyotahiluxtechnical", "toyotahilux|hiluxtechnical", "wikipedia_toyota_hilux", [2286, 0, 0, 0, 0, "", ""]],
    ["toyota_land_cruiser_70", "toyota_land_cruiser_70", "wheeled", "", "", "landcruiser70|landcruiserj70|lc70", "japan|toyotalandcruiserj70|j70|toyotaland|landcruiser|cruiserj70", "wikipedia_toyota_land_cruiser_70", [0, 0, 0, 0, 0, "manual", ""]],
    ["toyota_t100", "toyota_t100", "wheeled", "", "", "t100|toyotat100", "pickup|lighttruck", "toyota_t100_factory_service_manual_1996", [0, 0, 0, 0, 0, "manual", ""]],
    ["tpz_fuchs", "tpz_fuchs", "wheeled", "", "", "tpzfuchs", "", "wikipedia_tpz_fuchs", [23500, 0, 0, 0, 0, "", ""]],
    ["type_10", "type_10", "tracked", "", "", "type10|hitomaru", "", "wikipedia_type_10_tank", [48000, 0, 0, 0, 894.839846, "", ""]],
    ["type_16_mcv", "type_16_mcv", "wheeled", "", "", "type16|type16mcv|mcv", "maneuvercombatvehicle|16mcv|type16mc", "wikipedia_type_16_mcv", [26000, 0, 0, 0, 425.048927, "", ""]],
    ["type_89_ifv", "type_89_ifv", "tracked", "", "", "type89|type89ifv", "89ifv|type89if", "wikipedia_type_89_ifv", [26500, 0, 0, 0, 447.419923, "", ""]],
    ["type_96_apc", "type_96_apc", "wheeled", "", "", "type96apc|jgsdftype96", "jgsdfapc|komatsuapc|96apc|type96ap", "type_96_apc", [14600, 0, 0, 0, 268.451954, "", ""]],
    ["type_96_tank", "type_96_tank", "tracked", "", "", "type96|ztz96", "type96tank|chinesetank", "type_96_tank", [41000, 0, 0, 0, 544.360907, "", ""]],
    ["type_99_tank", "type_99_tank", "tracked", "", "", "type99|ztz99", "type99tank|chinesembt", "type_99_tank", [55000, 0, 0, 0, 1118.549808, "", ""]],
    ["uaz_3151", "uaz_3151", "wheeled", "", "", "uaz3151", "", "uaz_469", [1700, 0, 0, 0, 0, "", ""]],
    ["uaz_469", "uaz_469", "wheeled", "", "", "uaz469", "sovietlightutility", "uaz_469", [1700, 213.36, 807.72, 220, 53.690391, "manual", ""]],
    ["ural_375d", "ural_375d", "wheeled", "", "", "ural375d", "ural375", "wikipedia_ural_375", [8400, 0, 0, 0, 0, "", ""]],
    ["ural_4320", "ural_4320", "wheeled", "", "", "ural4320", "6x6|russia", "ural_4320_02_service_manual", [8445, 355.6, 1219.2, 0, 156.596973, "manual", ""]],
    ["vbci", "vbci", "wheeled", "", "", "vbci|vehiculeblindedecombatdinfanterie|vbci8x8", "8x8|france", "nexter_vbci_sales_brochure", [19000, 0, 0, 0, 447.419923, "automatic", ""]],
    ["wiesel_awc", "wiesel_awc", "tracked", "", "", "wieselawc", "", "wikipedia_wiesel_awc", [2750, 0, 0, 0, 0, "", ""]],
    ["willys_m38", "willys_m38", "wheeled", "", "", "m38|willysm38|m38jeep", "lightutilitytruck|m38jee", "willys_m38_tm_9_8012", [1247, 177.8, 762.0, 235, 0, "manual", ""]],
    ["willys_mb", "willys_mb", "wheeled", "", "", "willysmb|willys|jeep", "willysjeep|godevil", "tm_9_803_willys_mb", [1113, 406.4, 965.2, 222, 44.741992, "manual", ""]],
    ["yamaha_grizzly_450", "yamaha_grizzly_450", "wheeled", "", "", "grizzly450|quadbike|yamahagrizzly450", "yamahagrizzly", "", [0, 0, 0, 0, 0, "", ""]],
    ["zbd_04", "zbd_04", "tracked", "", "", "zbd04", "chineseifv|type04ifv", "zbd_04", [20000, 0, 0, 0, 440, "", ""]],
    ["zil_131", "zil_131", "wheeled", "", "", "zil131", "", "wikipedia_zil_131", [6700, 0, 0, 0, 0, "", ""]],
    ["zsu_23_4_shilka", "zsu_23_4_shilka", "tracked", "", "", "zsu234shilka", "zsu234|zsu234shilk", "wikipedia_zsu_23_4_shilka", [19000, 0, 0, 0, 0, "", ""]]
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
        if ((count _x) >= 3 && {_query find _x >= 0}) then { _hit = true; };
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
private _bestCount = 0;
private _bestName = 0;
private _tie = false;
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    // Score by the TOTAL of every distinct designation of this entry that
    // the query holds, not by the longest one alone. A reporting name is
    // shared across the marks of a type ("Frogfoot" names every Su-25), so
    // the longest single match would let any mark answer for the type;
    // summing makes the entry whose type number AND name both appear win.
    private _score = 0;
    private _count = 0;
    private _longest = 0;
    {
        _count = _count + 1;
        if ((count _x) >= 3 && {_query find _x >= 0}) then {
            // A designation carrying a TYPE NUMBER identifies the thing;
            // a plain word only describes it ("gunship" fits every gunship).
            // So a type number is worth double, and a described match can
            // no longer outvote the designation that names the aircraft.
            private _hasDigit = false;
            {
                if (_x >= 48 && _x <= 57) exitWith { _hasDigit = true; };
            } forEach (toArray _x);
            _score = _score + (count _x) * ([1, 2] select _hasDigit);
        };
        if ((count _x) > _longest) then { _longest = count _x; };
    } forEach ((_aliases + "|" + _keywords) splitString "|");
    if (_score >= 3) then {
        if (_score > _bestScore) then {
            _runnerUp = _bestScore;
            _bestScore = _score;
            _bestRow = _row;
            _bestCount = _count;
            _bestName = _longest;
            _tie = false;
        } else {
            if (_score == _bestScore) then {
                // Equal evidence. Two rules separate sibling marks, in
                // order: the entry advertising FEWER designations is the
                // less qualified one, and failing that the entry whose own
                // longest designation is SHORTER carries the less qualified
                // name ("AW101 Merlin" before "AW101 HM2 Merlin"). When a
                // query names the type but not the mark, the base mark is
                // the right answer. A true draw still stays a draw.
                if (_count < _bestCount) then {
                    _bestRow = _row;
                    _bestCount = _count;
                    _bestName = _longest;
                    _tie = false;
                } else {
                    if (_count == _bestCount) then {
                        if (_longest < _bestName) then {
                            _bestRow = _row;
                            _bestName = _longest;
                            _tie = false;
                        } else {
                            if (_longest == _bestName) then { _tie = true; };
                        };
                    };
                };
            };
            if (_score < _bestScore && _score > _runnerUp) then {
                _runnerUp = _score;
            };
        };
    };
} forEach _table;
if ((_bestRow isNotEqualTo []) && {!_tie} && _bestScore > _runnerUp) exitWith {
    [_bestRow, 5, "closest"] call _result
};
[]
