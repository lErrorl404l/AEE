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

// Identity text only: the class name, the raw display name and its
// localised stringtable text. A vanilla class stores a $STR key in
// displayName, so all three are needed. None carries a figure.
private _rawName = getText (configFile >> "CfgVehicles" >> _className >> "displayName");
private _localName = if (_rawName == "") then { "" } else { localize _rawName };
private _identity = _className + " " + _rawName + " " + _localName;
private _query = [_identity] call _normalise;
private _tokens = [];
{
    private _token = _x call _normalise;
    if (_token != "") then { _tokens pushBack _token; };
} forEach (_identity splitString " _-.");

private _table = [
    ["2s19_msta_s", "2s19_msta_s", "tracked", "", "", "2s19mstas", "", "wikipedia_2s19_msta_s", [42000, 0, 0, 0, 0, "", ""]],
    ["2s1_gvozdika", "2s1_gvozdika", "tracked", "", "", "2s1|2s1gvozdika|gvozdika", "selfpropelledartillery|tracked|howitzer|sovietunion", "2s1_gvozdika", [16000, 0, 0, 0, 223.709962, "", ""]],
    ["2s25_sprut_sd", "2s25_sprut_sd", "tracked", "", "rhsa3spruttankbase|rhssprutvdv", "2s25sprutsd", "", "wikipedia_2s25_sprut_sd", [18000, 0, 0, 0, 0, "", ""]],
    ["2s3_akatsiya_2s3m1", "2s3_akatsiya_2s3m1", "tracked", "", "rhs2s3tv|rhs2s3tankbase", "2s3akatsiya2s3m1", "", "wikipedia_2s3_akatsiya", [28000, 0, 0, 0, 0, "", ""]],
    ["9k79_tochka_9p129_1m_tel", "9k79_tochka_9p129_1m_tel", "wheeled", "", "otr21base|rhs9k79|rhs9k79b|rhs9k79k", "9k79tochka9p1291mtel", "", "ru_wikipedia_d0_a2_d0_be_d1_87_d0_ba_d0_b0_d1_82_d0_b0_d0_ba_d1_82_d0_b8_d1_87_d0_b5_d1_81_d0_ba_d0_b8_d0_b9_d1_80_d0_b0_d0_ba_d0_b5_d1_82_d0_bd_d1_8b_d0_b9_d0_ba_d0_be_d0_bc_d0_bf_d0_bb_d0_b5_d0_ba_d1_81", [18145, 0, 0, 0, 0, "", ""]],
    ["achzarit", "achzarit", "tracked", "", "", "achzarit", "achzarit|israeliapc|idfapc", "achzarit", [44000, 0, 0, 0, 484.704917, "automatic", ""]],
    ["ahs_krab", "ahs_krab", "tracked", "", "", "krab|ahskrab", "krab|polishhowitzer|155mmspg", "ahs_krab", [48000, 0, 0, 0, 745.699872, "automatic", ""]],
    ["al_fahd", "al_fahd", "wheeled", "", "", "alfahd|af4082", "afv|wheeled|8x8|saudiarabia", "wikipedia_al_fahd", [16300, 0, 0, 405, 410.13493, "", ""]],
    ["al_khalid", "al_khalid", "tracked", "", "", "alkhalid", "alkhalid|pakistanitank|alkhalidmbt", "al_khalid", [46000, 0, 0, 0, 894.839846, "automatic", ""]],
    ["altay", "altay", "tracked", "", "", "altay|altaymbt", "mbt|mainbattletank|tracked|altay", "wikipedia_altay", [65000, 0, 0, 0, 1118.549808, "", ""]],
    ["anoa", "anoa", "wheeled", "", "", "anoa|pindadanoa", "apc|wheeled|6x6|indonesia", "pindad_anoa_6x6_product_page", [14500, 0, 0, 400, 238.623959, "automatic", ""]],
    ["arjun", "arjun", "tracked", "", "", "arjun|arjunmk1|arjunmbt", "mbt|mainbattletank|tracked|india", "wikipedia_arjun", [58500, 0, 0, 450, 1043.979821, "", ""]],
    ["aslav", "aslav", "wheeled", "", "", "aslav", "reconnaissance|wheeled|aslav", "wikipedia_aslav", [13200, 0, 0, 0, 205, "", ""]],
    ["astros_ii", "astros_ii", "wheeled", "", "bmbt01mlrsbasef|mbt01mlrsbasef", "astrosii|astros2|astros", "mlrs|rocketartillery|wheeled|6x6|brazil", "wikipedia_astros_ii", [10000, 0, 0, 0, 208.795964, "", ""]],
    ["at105_saxon", "at105_saxon", "wheeled", "", "", "at105saxon", "", "wikipedia_saxon", [11660, 0, 0, 0, 0, "", ""]],
    ["atf_dingo", "atf_dingo", "wheeled", "", "", "atfdingo", "", "wikipedia_atf_dingo", [11900, 0, 0, 0, 0, "", ""]],
    ["bae_systems_caiman_xm1220_xm1230_caiman_plus", "bae_systems_caiman_xm1220_xm1230_caiman_plus", "wheeled", "", "rhsusfm1220m153m2usarmyd|rhsusfm1220m153m2usarmywd|rhsusfm1220m153mk19usarmyd|rhsusfm1220m153mk19usarmywd|rhsusfm1220m2usarmyd|rhsusfm1220m2usarmywd|rhsusfm1220mk19usarmyd|rhsusfm1220mk19usarmywd|rhsusfm1220usarmyd|rhsusfm1220usarmywd|rhsusfm1230m2usarmyd|rhsusfm1230m2usarmywd|rhsusfm1230mk19usarmyd|rhsusfm1230mk19usarmywd", "baesystemscaimanxm1220xm1230caimanplus", "", "globalsecurity_caiman_specs", [13835, 0, 0, 0, 0, "", ""]],
    ["bae_systems_rg_33_4x4", "bae_systems_rg_33_4x4", "wheeled", "", "rhsusfrg33d|rhsusfrg33m2d|rhsusfrg33m2usmcd|rhsusfrg33m2usmcwd|rhsusfrg33m2wd|rhsusfrg33usmcd|rhsusfrg33usmcwd|rhsusfrg33wd", "baesystemsrg334x4", "", "armyrecognition_rg33_4x4", [14000, 0, 0, 0, 0, "", ""]],
    ["bae_systems_rg_33_4x4_socom_m1238", "bae_systems_rg_33_4x4_socom_m1238", "wheeled", "", "rhsrg33socom", "baesystemsrg334x4socomm1238", "", "warwheels_rg33_4x4_socom", [14000, 0, 0, 0, 0, "", ""]],
    ["bae_systems_rg_33l_6x6", "bae_systems_rg_33l_6x6", "wheeled", "", "rhsusfm1232m2usarmyd|rhsusfm1232m2usarmywd|rhsusfm1232mcm2usmcd|rhsusfm1232mcm2usmcwd|rhsusfm1232mcmk19usmcd|rhsusfm1232mcmk19usmcwd|rhsusfm1232mk19usarmyd|rhsusfm1232mk19usarmywd|rhsusfm1232usarmyd|rhsusfm1232usarmywd|rhsusfm1237m2usarmyd|rhsusfm1237m2usarmywd|rhsusfm1237mk19usarmyd|rhsusfm1237mk19usarmywd", "baesystemsrg33l6x6", "", "armyrecognition_rg33_4x4", [24000, 0, 0, 0, 0, "", ""]],
    ["bae_systems_rg_33l_socom_armored_utility_vehicle_auv", "bae_systems_rg_33l_socom_armored_utility_vehicle_auv", "wheeled", "", "rhsusfm1239m2deploysocomd|rhsusfm1239m2deploysocomwd|rhsusfm1239m2socomd|rhsusfm1239m2socomwd|rhsusfm1239mk19deploysocomd|rhsusfm1239mk19deploysocomwd|rhsusfm1239mk19socomd|rhsusfm1239mk19socomwd|rhsusfm1239socomd|rhsusfm1239socomwd", "baesystemsrg33lsocomarmoredutilityvehicleauv", "", "bae_rg33l_auv_brochure", [26473, 0, 0, 0, 0, "", ""]],
    ["bionix", "bionix", "tracked", "", "", "bionix|bionixafv", "ifv|tracked|infantryfightingvehicle|singapore", "wikipedia_bionix", [23000, 0, 0, 0, 354.207439, "", ""]],
    ["bm_21_grad", "bm_21_grad", "wheeled", "", "rhsbm21msv01|rhsbm21vdv01|rhsbm21vmf01|rhsbm21vv01|rhsgrefcdfbregbm21|rhsgrefcdfregbm21|rhsgrefinsbm21|rhsgrefinsgbm21", "bm21grad", "", "wikipedia_bm_21_grad", [13710, 0, 0, 0, 0, "", ""]],
    ["bmc_kirpi", "bmc_kirpi", "wheeled", "", "", "kirpi|bmckirpi", "mrap|mineresistant|wheeled|kirpi", "wikipedia_bmc_kirpi", [20000, 355.6, 1219.2, 400, 275, "automatic", ""]],
    ["bmd_1", "bmd_1", "tracked", "", "rhsbmd1|rhsbmd1base|rhsgrefcdfbbmd1|rhsgrefcdfbmd1|rhsgrefinsbmd1|rhsgrefinsgbmd1", "bmd1", "", "wikipedia_bmd_1", [7500, 0, 0, 0, 0, "", ""]],
    ["bmd_1k", "bmd_1k", "tracked", "", "rhsbmd1k|rhsgrefcdfbbmd1k|rhsgrefcdfbmd1k", "bmd1k", "", "wikipedia_bmd_1", [7500, 0, 0, 0, 0, "", ""]],
    ["bmd_1p", "bmd_1p", "tracked", "", "rhsbmd1p|rhsgrefcdfbbmd1p|rhsgrefcdfbmd1p|rhsgrefinsbmd1p|rhsgrefinsgbmd1p", "bmd1p", "", "wikipedia_bmd_1", [7500, 0, 0, 0, 0, "", ""]],
    ["bmd_1pk", "bmd_1pk", "tracked", "", "rhsbmd1pk|rhsgrefcdfbbmd1pk|rhsgrefcdfbmd1pk", "bmd1pk", "", "wikipedia_bmd_1", [7500, 0, 0, 0, 0, "", ""]],
    ["bmd_1r", "bmd_1r", "tracked", "", "rhsbmd1r", "bmd1r", "", "wikipedia_bmd_1", [7500, 0, 0, 0, 0, "", ""]],
    ["bmd_2", "bmd_2", "tracked", "", "rhsbmdbase", "bmd2", "", "wikipedia_bmd_2", [11500, 0, 0, 0, 0, "", ""]],
    ["bmd_2k", "bmd_2k", "tracked", "", "rhsbmd2k|rhsgrefcdfbbmd2k|rhsgrefcdfbmd2k", "bmd2k", "", "wikipedia_bmd_2", [11500, 0, 0, 0, 0, "", ""]],
    ["bmd_2m", "bmd_2m", "tracked", "", "rhsbmd2m|rhsbmd2mmsv", "bmd2m", "", "wikipedia_bmd_2", [11500, 0, 0, 0, 0, "", ""]],
    ["bmd_4", "bmd_4", "tracked", "", "rhsbmd4vdv", "bmd4", "", "wikipedia_bmd_4", [13600, 0, 0, 0, 0, "", ""]],
    ["bmd_4m", "bmd_4m", "tracked", "", "rhsbmd4mvdv|rhsbmd4mavdv", "bmd4m", "", "armyrecognition_bmd_4m", [13500, 0, 0, 0, 0, "", ""]],
    ["bmp_1", "bmp_1", "tracked", "", "rhsbmp1msv|rhsbmp1tv|rhsbmp1vdv|rhsbmp1vmf|rhsbmp1vv|rhsbmp1tankbase|rhsbmpbase|rhsgrefcdfbbmp1|rhsgrefcdfbmp1|rhsgrefinsbmp1|rhsgrefinsgbmp1", "bmp1", "ifv|tracked|infantryfightingvehicle|sovietunion", "bmp_1", [13200, 0, 0, 370, 223.709962, "", ""]],
    ["bmp_1d", "bmp_1d", "tracked", "", "rhsbmp1dmsv|rhsbmp1dtv|rhsbmp1dvdv|rhsbmp1dvmf|rhsbmp1dvv|rhsgrefcdfbbmp1d|rhsgrefcdfbmp1d|rhsgrefinsbmp1d|rhsgrefinsgbmp1d", "bmp1d", "", "bmp_1", [13200, 0, 0, 0, 0, "", ""]],
    ["bmp_1k", "bmp_1k", "tracked", "", "rhsbmp1kmsv|rhsbmp1ktv|rhsbmp1kvdv|rhsbmp1kvmf|rhsbmp1kvv|rhsgrefcdfbbmp1k|rhsgrefcdfbmp1k|rhsgrefinsbmp1k|rhsgrefinsgbmp1k", "bmp1k", "", "bmp_1", [13200, 0, 0, 0, 0, "", ""]],
    ["bmp_1p", "bmp_1p", "tracked", "", "rhsbmp1pmsv|rhsbmp1ptv|rhsbmp1pvdv|rhsbmp1pvmf|rhsbmp1pvv|rhsgrefcdfbbmp1p|rhsgrefcdfbmp1p|rhsgrefinsbmp1p|rhsgrefinsgbmp1p", "bmp1p", "", "wikipedia_list_of_bmp_1_variants", [13400, 0, 0, 0, 0, "", ""]],
    ["bmp_2", "bmp_2", "tracked", "", "rhsbmp2msv|rhsbmp2tv|rhsbmp2vdv|rhsbmp2vmf|rhsbmp2vv|rhsbmp2emsv|rhsbmp2etv|rhsbmp2evdv|rhsbmp2evmf|rhsbmp2evv|rhsgrefcdfbbmp2|rhsgrefcdfbbmp2e|rhsgrefcdfbmp2|rhsgrefcdfbmp2e|rhsgrefinsbmp2|rhsgrefinsbmp2e|rhsgrefinsgbmp2|rhsgrefinsgbmp2e", "bmp2", "ifv|tracked|infantryfightingvehicle|sovietunion", "wikipedia_bmp_2", [14300, 0, 0, 0, 0, "", ""]],
    ["bmp_2d", "bmp_2d", "tracked", "", "rhsbmp2dmsv|rhsbmp2dtv|rhsbmp2dvdv|rhsbmp2dvmf|rhsbmp2dvv|rhsgrefcdfbbmp2d|rhsgrefcdfbmp2d|rhsgrefinsbmp2d|rhsgrefinsgbmp2d", "bmp2d", "", "wikipedia_bmp_2", [14300, 0, 0, 0, 0, "", ""]],
    ["bmp_2k", "bmp_2k", "tracked", "", "rhsbmp2kmsv|rhsbmp2ktv|rhsbmp2kvdv|rhsbmp2kvmf|rhsbmp2kvv|rhsgrefcdfbbmp2k|rhsgrefcdfbmp2k|rhsgrefinsbmp2k|rhsgrefinsgbmp2k", "bmp2k", "", "wikipedia_bmp_2", [14300, 0, 0, 0, 0, "", ""]],
    ["bmp_3", "bmp_3", "tracked", "", "rhsbmp3latemsv|rhsbmp3msv|rhsbmp3mmsv|rhsbmp3meramsv|rhsbmp3tankbase", "bmp3", "", "wikipedia_bmp_3", [18700, 0, 0, 0, 0, "", ""]],
    ["bmpt_terminator", "bmpt_terminator", "tracked", "", "", "bmptterminator", "", "wikipedia_bmpt_terminator", [48000, 0, 0, 0, 0, "", ""]],
    ["bmw_r75", "bmw_r75", "wheeled", "", "", "bmwr75", "bmwr75|sidecarmotorcycle|germanmotorcycle", "bmw_r75", [420, 0, 0, 0, 19.388197, "", ""]],
    ["boragh", "boragh", "tracked", "", "", "boragh", "boragh|iranianapc|boraghapc", "boragh", [13000, 0, 0, 0, 246.080958, "", ""]],
    ["boxer_apc", "boxer_apc", "wheeled", "", "", "boxer|boxerapc|gtkboxer", "apc|wheeled|8x8|boxer", "artec_boxer_apc_datasheet", [38500, 0, 0, 500, 608.491096, "", ""]],
    ["brdm_2", "brdm_2", "wheeled", "", "", "brdm2", "amphibious|4x4|armoredreconnaissance|armouredcar|brdm", "brdm_2_technical_manual_en", [7000, 330.2, 1117.6, 330, 104.397982, "manual", ""]],
    ["brm_1k", "brm_1k", "tracked", "", "rhsbrm1kbase|rhsbrm1kmsv|rhsbrm1ktv|rhsbrm1kvdv|rhsbrm1kvmf|rhsbrm1kvv", "brm1k", "", "weaponsystems_346_brm_1k", [13200, 0, 0, 0, 0, "", ""]],
    ["bsa_m20", "bsa_m20", "wheeled", "", "", "bsam20|bsam21", "british|wwii|500cc|sidevalve|wm20|despatchrider", "bsa_m20", [167, 0, 0, 0, 9.694098, "manual", ""]],
    ["btr_4", "btr_4", "wheeled", "", "", "btr4", "apc|wheeled|8x8|ukraine", "btr4_manual_2010", [21900, 0, 0, 475, 372.849936, "automatic", ""]],
    ["btr_60", "btr_60", "wheeled", "", "", "btr60", "", "wikipedia_btr_60", [10300, 0, 0, 0, 0, "", ""]],
    ["btr_70", "btr_70", "wheeled", "", "rhsbtr70msv|rhsbtr70vdv|rhsbtr70vmf|rhsbtr70vv|rhsgrefcdfbbtr70|rhsgrefcdfbtr70|rhsgrefinsbtr70|rhsgrefinsgbtr70|rhsgrefnatbtr70|rhsgrefunbtr70", "btr70", "apc|amphibious|8x8|armoredpersonnelcarrier|btr", "btr_70", [11500, 0, 0, 0, 178.967969, "", ""]],
    ["btr_80", "btr_80", "wheeled", "", "wheeledapc|rhsbtr80msv|rhsbtr80vdv|rhsbtr80vmf|rhsbtr80vv|rhsgrefcdfbbtr80|rhsgrefcdfbtr80", "btr80", "apc|amphibious|8x8|armoredpersonnelcarrier|btr", "btr_80_technical_description_2001", [13600, 0, 0, 475, 193.881967, "manual", ""]],
    ["btr_80a", "btr_80a", "wheeled", "", "rhsbtr80amsv|rhsbtr80avdv|rhsbtr80avmf|rhsbtr80avv", "btr80a", "", "weaponsystems_122_btr_80a", [14500, 0, 0, 0, 0, "", ""]],
    ["btr_90", "btr_90", "wheeled", "", "", "btr90", "", "wikipedia_btr_90", [20900, 0, 0, 0, 0, "", ""]],
    ["bushmaster_pmv", "bushmaster_pmv", "wheeled", "", "", "bushmaster|bushmasterpmv", "mrap|infantrymobility|wheeled|bushmaster", "thales_bushmaster_troop_carrier_datasheet", [11400, 0, 0, 430, 223.709962, "", ""]],
    ["c1_ariete", "c1_ariete", "tracked", "", "", "ariete|c1ariete|c1", "mbt|mainbattletank|ariete|tracked", "wikipedia_ariete", [54000, 0, 0, 440, 947.038837, "", ""]],
    ["centauro", "centauro", "wheeled", "", "", "centauro|b1centauro|centauro1", "tankdestroyer|wheeled|8x8|centauro", "wikipedia_centauro", [24000, 0, 0, 0, 387.763933, "automatic", ""]],
    ["challenger_1", "challenger_1", "tracked", "", "", "challenger|challenger1|fv4030", "mbt|mainbattletank|challenger|tracked", "challenger_1_aesp_230_p_100_201", [62000, 650, 0, 500, 894.839846, "automatic", ""]],
    ["challenger_2", "challenger_2", "tracked", "", "", "challenger2|challengerii|fv4034", "mbt|mainbattletank|challenger|tracked", "wikipedia_challenger_2", [64000, 0, 0, 500, 894.839846, "", ""]],
    ["cougar_4x4", "cougar_4x4", "wheeled", "", "rhsusfcgrcat1a2m2usmcd|rhsusfcgrcat1a2m2usmcwd|rhsusfcgrcat1a2mk19usmcd|rhsusfcgrcat1a2mk19usmcwd|rhsusfcgrcat1a2usmcd|rhsusfcgrcat1a2usmcwd", "cougar|cougar4x4|mrapcougar", "mrap|mineresistant|cougar|4x4", "gdls_cougar_4x4_datasheet", [15422, 395.0, 1179.5, 380, 246.080958, "automatic", ""]],
    ["cv90", "cv90", "tracked", "", "", "cv90|combatvehicle90|stridsfordon90", "ifv|infantryfightingvehicle|tracked|cv90", "wikipedia_cv90", [23000, 0, 0, 0, 0, "", ""]],
    ["cv90_denmark", "cv90_denmark", "tracked", "", "", "cv9035dk|cv90denmark|combatvehicle90denmark", "ifv|infantryfightingvehicle|tracked|cv90", "wikipedia_cv90", [23000, 0, 0, 0, 0, "", ""]],
    ["cv90_norway", "cv90_norway", "tracked", "", "", "cv9030n|cv90norway|combatvehicle90norway", "ifv|infantryfightingvehicle|tracked|cv90", "wikipedia_cv90", [23000, 0, 0, 0, 0, "", ""]],
    ["dardo", "dardo", "tracked", "", "", "dardo|dardoifv|vcc80", "ifv|infantryfightingvehicle|tracked|dardo", "wikipedia_dardo", [23400, 0, 0, 0, 381.798334, "", ""]],
    ["eitan", "eitan", "wheeled", "", "", "eitan|eitanafv", "afv|armouredfightingvehicle|wheeled|eitan", "wikipedia_eitan", [50000, 0, 0, 0, 559.274904, "", ""]],
    ["fahd", "fahd", "wheeled", "", "", "fahd|fahdapc", "apc|wheeled|4x4|egypt", "wikipedia_fahd", [12500, 0, 0, 370, 205.067465, "", ""]],
    ["freccia", "freccia", "wheeled", "", "", "freccia|vbmfreccia|frecciaifv", "ifv|infantryfightingvehicle|wheeled|8x8|freccia", "wikipedia_freccia", [22000, 0, 0, 0, 0, "", ""]],
    ["fv101_scorpion", "fv101_scorpion", "tracked", "", "", "fv101scorpion", "", "wikipedia_fv101_scorpion", [8074, 0, 0, 0, 0, "", ""]],
    ["fv107_scimitar", "fv107_scimitar", "tracked", "", "", "fv107scimitar", "", "wikipedia_fv107_scimitar", [7800, 0, 0, 0, 0, "", ""]],
    ["fv4201_chieftain", "fv4201_chieftain", "tracked", "", "", "fv4201chieftain", "", "wikipedia_chieftain", [56000, 0, 0, 0, 0, "", ""]],
    ["fv510_warrior", "fv510_warrior", "tracked", "", "iapctracked03cannonf", "warrior|fv510|fv510warrior|warriortrackedarmouredvehicle|mora|fv720", "ifv|tracked|warrior|infantryfightingvehicle", "wikipedia_fv510_warrior", [25400, 0, 0, 0, 410.13493, "", ""]],
    ["gaz_233011_gaz_tigr", "gaz_233011_gaz_tigr", "wheeled", "", "rhstigr3camomsv|rhstigr3camovdv|rhstigr3camovmf|rhstigr3camovv|rhstigrffv3camomsv|rhstigrffv3camovdv|rhstigrffv3camovmf|rhstigrffv3camovv|rhstigrffvmsv|rhstigrffvvdv|rhstigrffvvmf|rhstigrffvvv", "gaz233011gaztigr", "", "wikipedia_tigr_military_vehicle", [7200, 0, 0, 0, 0, "", ""]],
    ["gaz_233014_tigr_with_arbalet_turret", "gaz_233014_tigr_with_arbalet_turret", "wheeled", "", "rhstigrsts3camomsv|rhstigrsts3camovdv|rhstigrsts3camovmf|rhstigrsts3camovv|rhstigrstsmsv|rhstigrstsvdv|rhstigrstsvmf|rhstigrstsvv", "gaz233014tigrwitharbaletturret", "", "ru_wikipedia_", [5300, 0, 0, 0, 0, "", ""]],
    ["gaz_233114_tigr_m", "gaz_233114_tigr_m", "wheeled", "", "rhstigrm3camomsv|rhstigrm3camovdv|rhstigrm3camovmf|rhstigrm3camovv|rhstigrmmsv|rhstigrmvdv|rhstigrmvmf|rhstigrmvv", "gaz233114tigrm", "", "ru_wikipedia_", [8980, 0, 0, 0, 0, "", ""]],
    ["gaz_66", "gaz_66", "wheeled", "", "rhsgaz66ammobase|rhsgaz66ammomsv|rhsgaz66ammovdv|rhsgaz66ammovmf|rhsgaz66ammovv|rhsgaz66flatmsv|rhsgaz66flatvdv|rhsgaz66flatvmf|rhsgaz66flatvv|rhsgaz66msv|rhsgaz66r142base|rhsgaz66r142msv|rhsgaz66r142vdv|rhsgaz66r142vmf|rhsgaz66r142vv|rhsgaz66vdv|rhsgaz66vmf|rhsgaz66vv|rhsgaz66zu23base|rhsgaz66zu23msv|rhsgaz66zu23vdv|rhsgaz66zu23vmf|rhsgaz66zu23vv|rhsgaz66omsv|rhsgaz66ovdv|rhsgaz66ovmf|rhsgaz66ovv|rhstruck|rhsgrefcdfbgaz66|rhsgrefcdfbgaz66ammo|rhsgrefcdfbgaz66flat|rhsgrefcdfbgaz66r142|rhsgrefcdfbgaz66zu23|rhsgrefcdfbgaz66o|rhsgrefcdfgaz66|rhsgrefcdfgaz66ammo|rhsgrefcdfgaz66flat|rhsgrefcdfgaz66r142|rhsgrefcdfgaz66zu23|rhsgrefcdfgaz66o|rhsgrefinsggaz66|rhsgrefinsggaz66ammo|rhsgrefinsggaz66flat|rhsgrefinsggaz66r142|rhsgrefinsggaz66zu23|rhsgrefinsggaz66o|rhsgrefinsgaz66|rhsgrefinsgaz66ammo|rhsgrefinsgaz66flat|rhsgrefinsgaz66r142|rhsgrefinsgaz66zu23|rhsgrefinsgaz66o", "gaz66", "gaz66|soviettruck", "gaz_66", [3440, 0, 0, 315, 0, "manual", ""]],
    ["gaz_66_ap_2", "gaz_66_ap_2", "wheeled", "", "rhsgaz66ap2base|rhsgaz66ap2msv|rhsgaz66ap2vdv|rhsgaz66ap2vmf|rhsgaz66ap2vv|rhsgrefcdfbgaz66ap2|rhsgrefcdfgaz66ap2|rhsgrefinsggaz66ap2|rhsgrefinsgaz66ap2", "gaz66ap2", "", "gaz_66", [3440, 0, 0, 0, 0, "", ""]],
    ["gaz_66_esb_8im", "gaz_66_esb_8im", "wheeled", "", "rhsgaz66repairbase|rhsgaz66repairmsv|rhsgaz66repairvdv|rhsgaz66repairvmf|rhsgaz66repairvv|rhsgrefcdfbgaz66repair|rhsgrefcdfgaz66repair|rhsgrefinsggaz66repair|rhsgrefinsgaz66repair", "gaz66esb8im", "", "gaz_66", [3440, 0, 0, 0, 0, "", ""]],
    ["guarani", "guarani", "wheeled", "", "", "guarani|vbtpmrguarani|vbtpmr", "apc|wheeled|6x6|amphibious|brazil", "guarani_eb70_ci_11412", [17500, 0, 0, 0, 0, "", ""]],
    ["harley_wla", "harley_wla", "wheeled", "", "", "wla|harleywla", "harleywla|militarymotorcycle|vtwin", "harley_wla_tm_9_879", [245, 101.6, 660.4, 102, 18.642497, "manual", ""]],
    ["hmmwv_m998", "hmmwv_m998", "wheeled", "", "rhsgrefhidfm9982dr|rhsgrefhidfm9982drfulltop|rhsgrefhidfm9982drhalftop|rhsgrefhidfm9984drfulltop|rhsgrefhidfm9984drhalftop|rhsgrefhidfm9984dr|rhssafarmyom998olive2drfulltop|rhssafarmyom998olive2drhalftop|rhssafm998olive2drfulltop|rhssafm998olive2drhalftop|rhsusfm998d2dr|rhsusfm998d2drfulltop|rhsusfm998d2drhalftop|rhsusfm998d4dr|rhsusfm998d4drfulltop|rhsusfm998d4drhalftop|rhsusfm998ds2dr|rhsusfm998ds2drfulltop|rhsusfm998ds2drhalftop|rhsusfm998ds4dr|rhsusfm998ds4drfulltop|rhsusfm998ds4drhalftop|rhsusfm998w2dr|rhsusfm998w2drfulltop|rhsusfm998w2drhalftop|rhsusfm998w4dr|rhsusfm998w4drfulltop|rhsusfm998w4drhalftop|rhsusfm998ws2dr|rhsusfm998ws2drfulltop|rhsusfm998ws2drhalftop|rhsusfm998ws4dr|rhsusfm998ws4drfulltop|rhsusfm998ws4drhalftop", "m998|m998a1|hmmwv|humvee|m1038", "truck|utility|cargo|4x4|troopcarrier", "tm_9_2320_280_10", [2361, 0, 0, 410, 111.854981, "automatic", ""]],
    ["honda_cb750", "honda_cb750", "wheeled", "", "", "cb750|hondacb750|cb750four", "superbike|aircooledfour|classicmotorcycle", "honda_cb750", [232.7, 0, 0, 0, 50.707591, "manual", ""]],
    ["honda_cg125", "honda_cg125", "wheeled", "", "", "cg125|hondacg125", "motorbike|commuter|125|japan", "wikipedia_honda_cg125", [105, 0, 0, 0, 7.829849, "manual", ""]],
    ["honda_civic_6gen_coupe", "honda_civic_6gen_coupe", "wheeled", "", "", "civiccoupe|hondaciviccoupe|civic2doorcoupe", "car|civilian|passengercar|coupe", "honda_civic_factory_service_manual_96_00", [1570, 0, 0, 150, 0, "", ""]],
    ["honda_civic_6gen_hatchback", "honda_civic_6gen_hatchback", "wheeled", "", "chatchback01f|chatchback01sportf|hatchback01basef", "civichatchback|hondacivichatchback|civic2doorhatchback", "car|civilian|passengercar|hatchback", "honda_civic_factory_service_manual_96_00", [1495, 0, 0, 150, 0, "", ""]],
    ["honda_civic_6gen_sedan", "honda_civic_6gen_sedan", "wheeled", "", "car", "civic|hondacivic|hondacivicsedan|ej6|ej8", "car|civilian|passengercar|sedan", "honda_civic_factory_service_manual_96_00", [1540, 0, 0, 150, 0, "automatic", ""]],
    ["k21_ifv", "k21_ifv", "tracked", "", "", "k21|k21ifv", "k21|koreanifv|k21ifv", "k21_ifv", [25600, 0, 0, 0, 559.274904, "", ""]],
    ["k2_black_panther", "k2_black_panther", "tracked", "", "", "k2|k2blackpanther|blackpanther", "mbt|mainbattletank|tracked|k2", "wikipedia_k2_black_panther", [56000, 0, 0, 0, 0, "", ""]],
    ["k808_white_tiger", "k808_white_tiger", "wheeled", "", "", "k808|whitetiger|k806", "k808|whitetiger|koreanapc", "k808_white_tiger", [20000, 0, 0, 0, 313.193946, "", ""]],
    ["k9_thunder", "k9_thunder", "tracked", "", "", "k9|k9thunder|k9a1", "selfpropelledhowitzer|sph|tracked|k9", "wikipedia_k9_thunder", [47000, 0, 0, 410, 745.699872, "", ""]],
    ["kamaz_5350_mustang", "kamaz_5350_mustang", "wheeled", "", "rhskamaz5350|rhskamaz5350ammobase|rhskamaz5350ammomsv|rhskamaz5350ammovdv|rhskamaz5350ammovmf|rhskamaz5350ammovv|rhskamaz5350flatbed|rhskamaz5350flatbedcover|rhskamaz5350flatbedcovermsv|rhskamaz5350flatbedcovervdv|rhskamaz5350flatbedcovervmf|rhskamaz5350flatbedcovervv|rhskamaz5350flatbedmsv|rhskamaz5350flatbedvdv|rhskamaz5350flatbedvmf|rhskamaz5350flatbedvv|rhskamaz5350msv|rhskamaz5350open|rhskamaz5350openmsv|rhskamaz5350openvdv|rhskamaz5350openvmf|rhskamaz5350openvv|rhskamaz5350vdv|rhskamaz5350vmf|rhskamaz5350vv", "kamaz5350mustang", "", "de_wikipedia_kamaz_5350", [9600, 0, 0, 0, 0, "", ""]],
    ["kamaz_63968_typhoon_k", "kamaz_63968_typhoon_k", "wheeled", "", "rhstyphoonbase|rhstyphoonvdv", "kamaz63968typhoonk", "", "wikipedia_kamaz_typhoon", [21000, 0, 0, 0, 0, "", ""]],
    ["karrar_tank", "karrar_tank", "tracked", "", "", "karrar", "karrar|iraniantank|karrarmbt", "karrar_tank", [51000, 0, 0, 0, 0, "", ""]],
    ["kawasaki_ninja_250r_ex250f", "kawasaki_ninja_250r_ex250f", "wheeled", "", "", "ninja250|ninja250r|ex250|ex250f|gpx250|gpx250r|kawasakininja250r", "motorcycle|ninja|sportbike", "kawasaki_ninja_250r_service_manual", [161, 130.0, 614.4, 155, 27.948831, "manual", "none"]],
    ["komatsu_lav", "komatsu_lav", "wheeled", "", "", "komatsulav|jgsdflav", "komatsulav|jgsdflav|japaneselav", "komatsu_lav", [4500, 0, 0, 0, 119.31198, "automatic", ""]],
    ["land_rover_wolf_xd_110", "land_rover_wolf_xd_110", "wheeled", "", "", "landroverwolfxd110", "", "elite_uk_forces_land_rover_wolf", [1600, 0, 0, 0, 0, "", ""]],
    ["lav_6", "lav_6", "wheeled", "", "", "lav6|lav60", "ifv|infantryfightingvehicle|wheeled|8x8|lav", "wikipedia_lav6", [20638, 0, 0, 0, 335.564942, "", ""]],
    ["leclerc", "leclerc", "tracked", "", "", "leclerc|charleclerc", "mbt|mainbattletank|leclerc|tracked", "wikipedia_leclerc", [54500, 0, 0, 500, 1118.549808, "automatic", ""]],
    ["leopard_1", "leopard_1", "tracked", "", "", "leopard1", "", "wikipedia_leopard_1", [42200, 0, 0, 0, 0, "", ""]],
    ["leopard_2a6", "leopard_2a6", "tracked", "", "", "leopard2|leopard2a6|2a6|leopard", "mbt|mainbattletank|leopard|tracked", "wikipedia_leopard_2", [62300, 0, 0, 540, 1118.549808, "", ""]],
    ["leopard_2a6_finland", "leopard_2a6_finland", "tracked", "", "", "leopard2a6finland|leopard2finland", "mbt|mainbattletank|tracked|leopard", "wikipedia_leopard_2", [62300, 0, 0, 540, 1118.549808, "", ""]],
    ["leopard_2a6_hel", "leopard_2a6_hel", "tracked", "", "", "leopard2a6hel|leopard2hel|leopard2greece", "mbt|mainbattletank|tracked|leopard", "wikipedia_leopard_2", [62300, 0, 0, 540, 1118.549808, "", ""]],
    ["leopard_2a7_hungary", "leopard_2a7_hungary", "tracked", "", "", "leopard2a7hungary|leopard2a7|leopard2hungary", "mbt|mainbattletank|tracked|leopard", "wikipedia_leopard_2", [66500, 0, 0, 540, 1118.549808, "", ""]],
    ["m1059", "m1059", "tracked", "", "", "m1059", "apc|carrier|tracked|smokegeneratorcarrier", "tm_9_2350_261_10", [11077, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m1064", "m1064", "tracked", "", "", "m1064", "apc|carrier|tracked|selfpropelled120mmmortarcarrier", "tm_9_2350_261_10", [12546, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m1068", "m1068", "tracked", "", "", "m1068", "apc|carrier|tracked|standardizedintegratedcommandpostsystem", "tm_9_2350_261_10", [12182, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m1078a1p2", "m1078a1p2", "wheeled", "", "rhsusfm1078a1p2bcpfmtvusarmy|rhsusfm1078a1p2bdcpfmtvusarmy|rhsusfm1078a1p2bdflatbedfmtvusarmy|rhsusfm1078a1p2bdfmtvusarmy|rhsusfm1078a1p2bdopenfmtvusarmy|rhsusfm1078a1p2bm2dflatbedfmtvusarmy|rhsusfm1078a1p2bm2dfmtvusarmy|rhsusfm1078a1p2bm2dopenfmtvusarmy|rhsusfm1078a1p2bm2wdflatbedfmtvusarmy|rhsusfm1078a1p2bm2wdfmtvusarmy|rhsusfm1078a1p2bm2wdopenfmtvusarmy|rhsusfm1078a1p2bm2flatbedfmtvusarmy|rhsusfm1078a1p2bm2fmtvusarmy|rhsusfm1078a1p2bm2openfmtvusarmy|rhsusfm1078a1p2bwdcpfmtvusarmy|rhsusfm1078a1p2bwdflatbedfmtvusarmy|rhsusfm1078a1p2bwdfmtvusarmy|rhsusfm1078a1p2bwdopenfmtvusarmy|rhsusfm1078a1p2bflatbedfmtvusarmy|rhsusfm1078a1p2bfmtvusarmy|rhsusfm1078a1p2bopenfmtvusarmy|rhsusfm1078a1p2dflatbedfmtvusarmy|rhsusfm1078a1p2dfmtvusarmy|rhsusfm1078a1p2dopenfmtvusarmy|rhsusfm1078a1p2wdflatbedfmtvusarmy|rhsusfm1078a1p2wdfmtvusarmy|rhsusfm1078a1p2wdopenfmtvusarmy|rhsusfm1078a1p2flatbedfmtvusarmy|rhsusfm1078a1p2fmtvusarmy|rhsusfm1078a1p2openfmtvusarmy|rhsusfm1083a1p2bm2dmhqfmtvusarmy|rhsusfm1083a1p2bm2wdmhqfmtvusarmy", "m1078a1p2", "", "wikipedia_family_of_medium_tactical_vehicles", [10390, 0, 0, 0, 0, "", ""]],
    ["m1078a1r_socom_sov", "m1078a1r_socom_sov", "wheeled", "", "rhsm1078a1rsov", "m1078a1rsocomsov", "", "fmtv_a1r_m1078_cargo_datasheet", [7808, 0, 0, 0, 0, "", ""]],
    ["m1083a1p2", "m1083a1p2", "wheeled", "", "rhsusfm1083a1p2bdflatbedfmtvusarmy|rhsusfm1083a1p2bdfmtvusarmy|rhsusfm1083a1p2bdopenfmtvusarmy|rhsusfm1083a1p2bm2dflatbedfmtvusarmy|rhsusfm1083a1p2bm2dfmtvusarmy|rhsusfm1083a1p2bm2dopenfmtvusarmy|rhsusfm1083a1p2bm2wdflatbedfmtvusarmy|rhsusfm1083a1p2bm2wdfmtvusarmy|rhsusfm1083a1p2bm2wdopenfmtvusarmy|rhsusfm1083a1p2bm2flatbedfmtvusarmy|rhsusfm1083a1p2bm2fmtvusarmy|rhsusfm1083a1p2bm2openfmtvusarmy|rhsusfm1083a1p2bwdflatbedfmtvusarmy|rhsusfm1083a1p2bwdfmtvusarmy|rhsusfm1083a1p2bwdopenfmtvusarmy|rhsusfm1083a1p2bflatbedfmtvusarmy|rhsusfm1083a1p2bfmtvusarmy|rhsusfm1083a1p2bopenfmtvusarmy|rhsusfm1083a1p2dflatbedfmtvusarmy|rhsusfm1083a1p2dfmtvusarmy|rhsusfm1083a1p2dopenfmtvusarmy|rhsusfm1083a1p2wdflatbedfmtvusarmy|rhsusfm1083a1p2wdfmtvusarmy|rhsusfm1083a1p2wdopenfmtvusarmy|rhsusfm1083a1p2flatbedfmtvusarmy|rhsusfm1083a1p2fmtvusarmy|rhsusfm1083a1p2openfmtvusarmy", "m1083a1p2", "", "wikipedia_family_of_medium_tactical_vehicles", [11280, 0, 0, 0, 0, "", ""]],
    ["m1084a1p2", "m1084a1p2", "wheeled", "", "rhsusfm1084a1p2bdfmtvusarmy|rhsusfm1084a1p2bm2dfmtvusarmy|rhsusfm1084a1p2bm2wdfmtvusarmy|rhsusfm1084a1p2bm2fmtvusarmy|rhsusfm1084a1p2bwdfmtvusarmy|rhsusfm1084a1p2bfmtvusarmy|rhsusfm1084a1p2dfmtvusarmy|rhsusfm1084a1p2wdfmtvusarmy|rhsusfm1084a1p2fmtvusarmy", "m1084a1p2", "", "globalsecurity_m1084", [10740, 0, 0, 0, 0, "", ""]],
    ["m1084a1r_socom_sov", "m1084a1r_socom_sov", "wheeled", "", "rhsm1084a1rsov", "m1084a1rsocomsov", "", "fmtv_a1r_m1084_cargo_datasheet", [11184, 0, 0, 0, 0, "", ""]],
    ["m1085a1p2", "m1085a1p2", "wheeled", "", "rhsusfm1083a1p2bm2dmedicalfmtvusarmy|rhsusfm1083a1p2bm2wdmedicalfmtvusarmy|rhsusfm1085a1p2bdmedicalfmtvusarmy|rhsusfm1085a1p2bmedicalfmtvusarmy|rhsusfm1085a1p2bwdmedicalfmtvusarmy", "m1085a1p2", "", "globalsecurity_m1085", [9451, 0, 0, 0, 0, "", ""]],
    ["m109a6_paladin", "m109a6_paladin", "tracked", "", "rhsusfm109usarmy|rhsusfm109dusarmy|rhsusfm109tankbase", "m109a6paladin", "", "inetres_m109", [28849, 0, 0, 0, 0, "", ""]],
    ["m1117_guardian_asv", "m1117_guardian_asv", "wheeled", "", "rhsusfm1117d|rhsusfm1117o|rhsusfm1117w|rhsusfm1117base", "m1117guardianasv", "", "wikipedia_m1117_armored_security_vehicle", [13410, 0, 0, 0, 0, "", ""]],
    ["m113a2", "m113a2", "tracked", "", "trackedapc", "m113|m113a2", "apc|carrier|tracked|armoredpersonnelcarrier", "tm_9_2350_261_10", [11353, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m113a3", "m113a3", "tracked", "", "rhsgrefhidfm113a3m2|rhsgrefhidfm113a3unarmed|rhsusfm113usarmy|rhsusfm113usarmym240|rhsusfm113usarmymk19|rhsusfm113usarmymedical|rhsusfm113usarmysupply|rhsusfm113usarmyunarmed|rhsusfm113dusarmy|rhsusfm113dusarmym240|rhsusfm113dusarmymk19|rhsusfm113dusarmymedical|rhsusfm113dusarmysupply|rhsusfm113dusarmyunarmed|rhsusfm113tankbase", "m113a3", "", "inetres_m113", [12250, 0, 0, 0, 0, "", ""]],
    ["m1151a1", "m1151a1", "wheeled", "", "rhssafarmyom1151olive|rhssafarmyom1151olivepkm|rhssafm1151olive|rhssafm1151olivepkm|rhsusfm1151crowsm2base|rhsusfm1151crowsmk19base|rhsusfm1151gpkm240base|rhsusfm1151gpkm2base|rhsusfm1151gpkmk19base|rhsusfm1151gpkpkmbase|rhsusfm1151m2lras3base|rhsusfm1151mctagsm240base|rhsusfm1151mctagsm2base|rhsusfm1151mctagsmk19base|rhsusfm1151ogpkm240base|rhsusfm1151ogpkm2base|rhsusfm1151ogpkmk19base|rhsusfm1151base|rhsusfm1151m240v1usarmyd|rhsusfm1151m240v1usarmywd|rhsusfm1151m240v2usarmyd|rhsusfm1151m240v2usarmywd|rhsusfm1151m240v3usmcd|rhsusfm1151m240v3usmcwd|rhsusfm1151m2lras3v1usarmyd|rhsusfm1151m2lras3v1usarmywd|rhsusfm1151m2v1usarmyd|rhsusfm1151m2v1usarmywd|rhsusfm1151m2v2usarmyd|rhsusfm1151m2v2usarmywd|rhsusfm1151m2v3usmcd|rhsusfm1151m2v3usmcwd|rhsusfm1151m2crowsusarmyd|rhsusfm1151m2crowsusarmywd|rhsusfm1151m2crowsusmcd|rhsusfm1151m2crowsusmcwd|rhsusfm1151mk19v1usarmyd|rhsusfm1151mk19v1usarmywd|rhsusfm1151mk19v2usarmyd|rhsusfm1151mk19v2usarmywd|rhsusfm1151mk19v3usmcd|rhsusfm1151mk19v3usmcwd|rhsusfm1151mk19crowsusarmyd|rhsusfm1151mk19crowsusarmywd|rhsusfm1151mk19crowsusmcd|rhsusfm1151mk19crowsusmcwd|rhsusfm1151usarmyd|rhsusfm1151usarmywd|rhsusfm1151usmcd|rhsusfm1151usmcwd", "m1151a1", "", "globalsecurity_m1151_specs", [3697, 0, 0, 0, 0, "", ""]],
    ["m1152a1", "m1152a1", "wheeled", "", "rhssafarmyom1152olive|rhssafarmyom1152rsvolive|rhssafm1152olive|rhssafm1152rsvolive|rhsusfm1152base|rhsusfm1152rsvusarmyd|rhsusfm1152rsvusarmywd|rhsusfm1152rsvusmcd|rhsusfm1152rsvusmcwd|rhsusfm1152sicpsbase|rhsusfm1152sicpsusarmyd|rhsusfm1152sicpsusarmywd|rhsusfm1152tcvbase|rhsusfm1152usarmyd|rhsusfm1152usarmywd|rhsusfm1152usmcd|rhsusfm1152usmcwd", "m1152a1", "", "globalsecurity_m1152", [3221, 0, 0, 0, 0, "", ""]],
    ["m1165a1", "m1165a1", "wheeled", "", "rhsusfm1165a1gmvsag2m134dm240base|rhsusfm1165a1gmvsag2m2m240base|rhsusfm1165a1gmvsag2mk19m240base|rhsusfm1165asvogpkm240base|rhsusfm1165asvm240usafd|rhsusfm1165asvm240usafwd|rhsusfm1165base|rhsusfm1165usarmyd|rhsusfm1165usarmywd|rhsusfm1165usmcd|rhsusfm1165usmcwd|rhsusfm1165a1gmvm134dm240socomd|rhsusfm1165a1gmvm2m240socomd|rhsusfm1165a1gmvmk19m240socomd", "m1165a1", "", "globalsecurity_m1165_specs", [3279, 0, 0, 0, 0, "", ""]],
    ["m142_himars", "m142_himars", "wheeled", "", "", "m142himars", "", "wikipedia_m142_himars", [13500, 0, 0, 0, 0, "", ""]],
    ["m1_abrams", "m1_abrams", "tracked", "", "tank", "m1|m1abrams|abrams|generalabrams", "tank|mbt|mainbattletank|105mm", "tm_9_2350_255_10", [54431, 0, 0, 483, 0, "automatic", ""]],
    ["m1a1_aim", "m1a1_aim", "tracked", "", "rhsusfm1a1aimtuskid|rhsusfm1a1aimtuskiwd|rhsusfm1a1aimdusarmy|rhsusfm1a1aimwdusarmy|rhsusfm1a1tankbase", "m1a1aim", "", "wikipedia_m1_abrams", [61300, 0, 0, 0, 0, "", ""]],
    ["m1a1_fep", "m1a1_fep", "tracked", "", "rhsm1a1fep|rhsusfm1a1fepd|rhsusfm1a1fepod|rhsusfm1a1fepwd", "m1a1fep", "", "wikipedia_m1_abrams", [57153, 0, 0, 0, 0, "", ""]],
    ["m1a1_hc", "m1a1_hc", "tracked", "", "rhsm1a1hc|rhsusfm1a1hcwd", "m1a1hc", "", "wikipedia_m1_abrams", [57153, 0, 0, 0, 0, "", ""]],
    ["m1a2_sep_v1", "m1a2_sep_v1", "tracked", "", "rhsusfm1a2sep1dusarmy|rhsusfm1a2sep1tuskidusarmy|rhsusfm1a2sep1tuskiidusarmy|rhsusfm1a2sep1tuskiiwdusarmy|rhsusfm1a2sep1tuskiwdusarmy|rhsusfm1a2sep1wdusarmy|rhsusfm1a2tankbase", "m1a2sepv1", "", "wikipedia_m1_abrams", [63000, 0, 0, 0, 0, "", ""]],
    ["m1a2_sep_v2", "m1a2_sep_v2", "tracked", "", "rhsusfm1a2sep2base|rhsusfm1a2sep2dusarmy|rhsusfm1a2sep2wdusarmy", "m1a2sepv2", "", "wikipedia_m1_abrams", [64600, 0, 0, 0, 0, "", ""]],
    ["m270_mlrs", "m270_mlrs", "tracked", "", "", "m270mlrs", "", "wikipedia_m270_mlrs", [24035, 0, 0, 0, 0, "", ""]],
    ["m2_m3_bradley", "m2_m3_bradley", "tracked", "", "", "m2bradley|m3bradley|bradley|m2ifv|m3cfv", "ifv|cfv|infantryfightingvehicle|cavalryfightingvehicle|tracked|bradley", "tm_9_2350_252_10_1", [22285, 533, 152, 0, 372.849936, "automatic", "grousers"]],
    ["m2a2_bradley", "m2a2_bradley", "tracked", "", "rhsm2a2|rhsm2a2buski|rhsm2a2buskiwd|rhsm2a2base|rhsm2a2early|rhsm2a2wd", "m2a2bradley", "", "inetres_m2", [29000, 0, 0, 0, 0, "", ""]],
    ["m2a3_bradley", "m2a3_bradley", "tracked", "", "rhsm2a3|rhsm2a3buski|rhsm2a3buskiii|rhsm2a3buskiiiwd|rhsm2a3buskiwd|rhsm2a3wd", "m2a3bradley", "", "inetres_m2", [30000, 0, 0, 0, 0, "", ""]],
    ["m3_bradley", "m3_bradley", "tracked", "", "", "m3bradley", "", "wikipedia_m3_bradley", [27669, 0, 0, 0, 0, "", ""]],
    ["m48_patton", "m48_patton", "tracked", "", "", "m48patton", "", "wikipedia_m48_patton", [44996, 0, 0, 0, 0, "", ""]],
    ["m577a2", "m577a2", "tracked", "", "", "m577a2", "apc|carrier|tracked|commandpostcarrier", "tm_9_2350_261_10", [11719, 0, 0, 434.8, 156.596973, "automatic", "grousers"]],
    ["m60_patton", "m60_patton", "tracked", "", "", "m60patton", "", "wikipedia_m60_tank", [47718, 0, 0, 0, 0, "", ""]],
    ["m88_recovery_vehicle", "m88_recovery_vehicle", "tracked", "", "", "m88recoveryvehicle", "", "wikipedia_m88_recovery_vehicle", [50800, 0, 0, 0, 0, "", ""]],
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
    ["m977a4", "m977a4", "wheeled", "", "rhsusfm977a4ammobkitm2usarmyd|rhsusfm977a4ammobkitm2usarmywd|rhsusfm977a4ammobkitusarmyd|rhsusfm977a4ammobkitusarmywd|rhsusfm977a4ammousarmyd|rhsusfm977a4ammousarmywd|rhsusfm977a4bkitm2usarmyd|rhsusfm977a4bkitm2usarmywd|rhsusfm977a4bkitusarmyd|rhsusfm977a4bkitusarmywd|rhsusfm977a4repairbkitm2usarmyd|rhsusfm977a4repairbkitm2usarmywd|rhsusfm977a4repairbkitusarmyd|rhsusfm977a4repairbkitusarmywd|rhsusfm977a4repairusarmyd|rhsusfm977a4repairusarmywd|rhsusfm977a4usarmyd|rhsusfm977a4usarmywd", "m977a4", "", "wikipedia_heavy_expanded_mobility_tactical_truck", [19278, 0, 0, 0, 0, "", ""]],
    ["m978a4_hemtt", "m978a4_hemtt", "wheeled", "", "rhsm978a4", "m978a4hemtt", "", "oshkosh_hemtt_a4_fuel_servicing_datasheet", [19119, 0, 0, 0, 0, "", ""]],
    ["m_atv_m1240", "m_atv_m1240", "wheeled", "", "mrap|rhsusfm1240a1m240usarmyd|rhsusfm1240a1m240usarmywd|rhsusfm1240a1m240usmcd|rhsusfm1240a1m240usmcwd|rhsusfm1240a1m2usarmyd|rhsusfm1240a1m2usarmywd|rhsusfm1240a1m2usmcd|rhsusfm1240a1m2usmcwd|rhsusfm1240a1mk19usarmyd|rhsusfm1240a1mk19usarmywd|rhsusfm1240a1mk19usmcd|rhsusfm1240a1mk19usmcwd|rhsusfm1240a1usarmyd|rhsusfm1240a1usarmywd|rhsusfm1240a1usmcd|rhsusfm1240a1usmcwd", "matv|m1240", "mrap|oshkosh|matv", "tm_9_2355_335_10", [11123, 395.0, 1179.5, 0, 275.908953, "automatic", ""]],
    ["m_atv_m1240a1", "m_atv_m1240a1", "wheeled", "", "rhsusfm1240a1m240uikusarmyd|rhsusfm1240a1m240uikusarmywd|rhsusfm1240a1m2uikusarmyd|rhsusfm1240a1m2uikusarmywd|rhsusfm1240a1mk19uikusarmyd|rhsusfm1240a1mk19uikusarmywd", "matvm1240a1|m1240a1", "mrap|oshkosh|matv", "tm_9_2355_335_10", [12940, 0, 0, 0, 275.908953, "automatic", ""]],
    ["m_atv_m1245", "m_atv_m1245", "wheeled", "", "rhsusfm1245m2crowssocomd|rhsusfm1245m2crowssocomdeploy|rhsusfm1245mk19crowssocomd|rhsusfm1245mk19crowssocomdeploy", "matvm1245|m1245", "mrap|oshkosh|matv", "tm_9_2355_335_10", [12325, 395.0, 1179.5, 0, 275.908953, "automatic", ""]],
    ["marder_1a3", "marder_1a3", "tracked", "", "", "marder|marder1a3|spzmarder|schutzenpanzermarder", "ifv|tracked|infantryfightingvehicle|germany", "thyssen_henschel_marder_1a3", [28600, 0, 0, 0, 439.962924, "automatic", ""]],
    ["maxxpro", "maxxpro", "wheeled", "", "", "maxxpro|internationalmaxxpro", "mrap|wheeled|4x4|unitedstates", "tm_9_2355_106_10", [17168, 395.0, 1179.5, 260, 246.080958, "automatic", ""]],
    ["merkava_mk4", "merkava_mk4", "tracked", "", "bmbt01tuskf|btmbt01tuskf", "merkava|merkavamk4|slammer|m2a1|m2a4", "mbt|mainbattletank|tracked|merkava", "wikipedia_merkava", [65000, 0, 0, 450, 1119, "", ""]],
    ["mowag_piranha", "mowag_piranha", "wheeled", "", "", "piranha|mowagpiranha", "afv|armouredfightingvehicle|wheeled|piranha", "wikipedia_mowag_piranha", [0, 0, 0, 0, 202, "automatic", ""]],
    ["mt_lb", "mt_lb", "tracked", "", "", "mtlb", "", "wikipedia_mt_lb", [11900, 0, 0, 0, 0, "", ""]],
    ["namer", "namer", "tracked", "", "bapctracked01aaf|bapctracked01crvf|bapctracked01rcwsf|btapctracked01crvf", "namer|namerapc|panther|cheetah|bobcat", "apc|armouredpersonnelcarrier|tracked|namer", "wikipedia_namer", [60000, 0, 0, 0, 894.839846, "", ""]],
    ["olifant", "olifant", "tracked", "", "", "olifant|olifantmk1|olifantmk2", "mbt|mainbattletank|tracked|southafrica", "wikipedia_olifant", [58000, 0, 0, 508, 775.527867, "automatic", ""]],
    ["oshkosh_m_atv_m1277", "oshkosh_m_atv_m1277", "wheeled", "", "rhsusfm1240a1m2crowsusarmyd|rhsusfm1240a1m2crowsusarmywd|rhsusfm1240a1m2crowsusmcd|rhsusfm1240a1m2crowsusmcwd|rhsusfm1240a1mk19crowsusarmyd|rhsusfm1240a1mk19crowsusarmywd|rhsusfm1240a1mk19crowsusmcd|rhsusfm1240a1mk19crowsusmcwd", "oshkoshmatvm1277", "", "wikipedia_oshkosh_m_atv", [12500, 0, 0, 0, 0, "", ""]],
    ["pandur_ii", "pandur_ii", "wheeled", "", "", "pandurii|pandur2|pandur", "apc|armouredpersonnelcarrier|wheeled|pandur", "wikipedia_pandur_ii", [17300, 0, 0, 0, 335, "automatic", ""]],
    ["patria_amv", "patria_amv", "wheeled", "", "", "patriaamv|amv|patria", "apc|armouredpersonnelcarrier|wheeled|patria", "wikipedia_patria_amv", [16000, 0, 0, 0, 450, "automatic", ""]],
    ["peugeot_p4", "peugeot_p4", "wheeled", "", "", "peugeotp4", "lightutility|vltt|xn8|legere|frencharmy", "peugeot_p4", [1750, 0, 0, 0, 58.16459, "", ""]],
    ["piranha_v", "piranha_v", "wheeled", "", "", "piranhav|piranha5|piranha", "apc|armouredpersonnelcarrier|wheeled|piranha", "wikipedia_piranha_v", [0, 0, 0, 0, 437, "", ""]],
    ["pizarro", "pizarro", "tracked", "", "", "pizarro|ascod|ascodpizarro", "ifv|infantryfightingvehicle|tracked|pizarro|ascod", "wikipedia_ascod", [26300, 0, 0, 0, 447.419923, "", ""]],
    ["prp_3", "prp_3", "tracked", "", "rhsprp3msv|rhsprp3tv|rhsprp3vdv|rhsprp3vmf|rhsprp3vv", "prp3", "", "weaponsystems_623_prp_3_val", [13000, 0, 0, 0, 0, "", ""]],
    ["pt91_twardy", "pt91_twardy", "tracked", "", "", "pt91|pt91twardy|twardy", "mbt|mainbattletank|tracked|twardy", "wikipedia_pt91", [45900, 0, 0, 395, 633.844891, "manual", ""]],
    ["pts_m", "pts_m", "tracked", "", "rhssafarmyopts|rhssafarmypts", "ptsm", "", "ru_wikipedia_d0_9f_d0_a2_d0_a1_d0_9c", [17800, 0, 0, 0, 0, "", ""]],
    ["puma_cev", "puma_cev", "tracked", "", "", "pumacev|idfpuma", "idfpuma|pumacev|israeliengineeringvehicle", "puma_cev", [50000, 0, 0, 0, 671.129885, "", ""]],
    ["puma_ifv", "puma_ifv", "tracked", "", "", "pumagermanifv", "", "wikipedia_puma_ifv", [31400, 0, 0, 0, 0, "", ""]],
    ["ratel", "ratel", "wheeled", "", "", "ratel|ratel20", "ifv|wheeled|6x6|southafrica", "wikipedia_ratel", [18500, 0, 0, 340, 205.067465, "", ""]],
    ["rg_31", "rg_31", "wheeled", "", "", "rg31|rg31nyala|nyala", "mrap|wheeled|4x4|southafrica", "gdls_rg31_mk5_datasheet", [14000, 395.0, 1179.5, 492, 223.709962, "automatic", ""]],
    ["rooikat", "rooikat", "wheeled", "", "", "rooikat", "afv|wheeled|8x8|southafrica", "wikipedia_rooikat", [28000, 0, 0, 0, 413.863429, "", ""]],
    ["rosomak", "rosomak", "wheeled", "", "", "rosomak|ktorosomak", "apc|wheeled|8x8|rosomak|patriaamv", "wikipedia_rosomak", [22000, 0, 0, 0, 404.91503, "", ""]],
    ["sd_kfz_251", "sd_kfz_251", "tracked", "", "", "sdkfz251", "", "wikipedia_sd_kfz_251", [7810, 0, 0, 0, 0, "", ""]],
    ["snatch_land_rover", "snatch_land_rover", "wheeled", "", "", "snatchlandrover", "", "wikipedia_snatch_land_rover", [4050, 0, 0, 0, 0, "", ""]],
    ["strv_122", "strv_122", "tracked", "", "", "stridsvagn122|strv122", "mbt|mainbattletank|tracked|leopard2", "wikipedia_strv_122", [62500, 0, 0, 540, 1102.890111, "", ""]],
    ["stryker_m1126_icv", "m1126_stryker_icv", "wheeled", "", "", "stryker|m1126|m1126strykericv|m1126icv", "apc|ifv|8x8|stryker|icv|armouredpersonnelcarrier", "wikipedia_stryker", [16470, 0, 0, 0, 260.994955, "", ""]],
    ["t_34", "t_34", "tracked", "", "", "t34", "", "wikipedia_t_34", [32400, 0, 0, 0, 0, "", ""]],
    ["t_54_t_55", "t_54_t_55", "tracked", "", "", "t54t55", "", "wikipedia_t_54_t_55", [36000, 0, 0, 0, 0, "", ""]],
    ["t_62", "t_62", "tracked", "", "", "t62", "", "wikipedia_t_62", [37000, 0, 0, 0, 0, "", ""]],
    ["t_64", "t_64", "tracked", "", "", "t64", "mbt|mainbattletank|tracked|sovietunion", "t64a_technical_manual_1984", [38500, 0, 0, 500, 521.98991, "", ""]],
    ["t_72b3_obr_2012g", "t_72b3_obr_2012g", "tracked", "", "rhst72bdtv|rhst72betv", "t72b3obr2012g", "", "ru_wikipedia_d0_a2_72_d0_913", [46500, 0, 0, 0, 0, "", ""]],
    ["t_72b_obr_1984g", "t_72b_obr_1984g", "tracked", "", "rhsa3t72tankbase|rhst72batv|rhst72bbtv|rhst72bctv|rhsgrefcdfbt72batv|rhsgrefcdfbt72bbtv|rhsgrefcdft72batv|rhsgrefcdft72bbtv", "t72bobr1984g", "", "wikipedia_t_72", [44500, 0, 0, 0, 0, "", ""]],
    ["t_72m4cz", "t_72m4cz", "tracked", "", "", "t72m4cz|t72", "mbt|mainbattletank|tracked|t72", "wikipedia_t_72m4cz", [48000, 0, 0, 0, 746, "", ""]],
    ["t_72ms", "t_72ms", "tracked", "", "rhssafarmyot72s|rhssafarmyt72s", "t72ms", "", "wikipedia_t_72", [44500, 0, 0, 0, 0, "", ""]],
    ["t_80", "t_80", "tracked", "", "rhst80", "t80", "", "ru_wikipedia_d0_a2_80", [42000, 0, 0, 0, 0, "", ""]],
    ["t_80a", "t_80a", "tracked", "", "rhst80a", "t80a", "", "ru_wikipedia_d0_a2_80_d0_90", [45200, 0, 0, 0, 0, "", ""]],
    ["t_80b", "t_80b", "tracked", "", "rhstankbase", "t80b", "", "wikipedia_t_80", [42500, 0, 0, 0, 0, "", ""]],
    ["t_80bk", "t_80bk", "tracked", "", "rhst80bk", "t80bk", "", "wikipedia_t_80", [42500, 0, 0, 0, 0, "", ""]],
    ["t_80bv", "t_80bv", "tracked", "", "rhst80bv|rhsgrefcdfbt80bvtv|rhsgrefcdft80bvtv", "t80bv", "", "wikipedia_t_80", [42500, 0, 0, 0, 0, "", ""]],
    ["t_80bvk", "t_80bvk", "tracked", "", "rhst80bvk", "t80bvk", "", "wikipedia_t_80", [42500, 0, 0, 0, 0, "", ""]],
    ["t_80u", "t_80u", "tracked", "", "rhst80u|rhst80u45m|rhsgrefcdfbt80utv|rhsgrefcdft80utv", "t80u", "", "ru_wikipedia_d0_a2_80_d0_a3", [46500, 0, 0, 0, 0, "", ""]],
    ["t_80ue_1", "t_80ue_1", "tracked", "", "rhst80ue1", "t80ue1", "", "wikipedia_t_80_models", [46500, 0, 0, 0, 0, "", ""]],
    ["t_80um", "t_80um", "tracked", "", "rhst80um", "t80um", "", "ru_wikipedia_d0_a2_80_d0_a3", [46500, 0, 0, 0, 0, "", ""]],
    ["t_90", "t_90", "tracked", "", "rhst90atv", "t90|t90a|t90s", "mbt|mainbattletank|tracked|russia", "wikipedia_t_90", [46000, 0, 0, 0, 626.387892, "", ""]],
    ["t_90am", "t_90am", "tracked", "", "rhst90amtv", "t90am", "", "ru_wikipedia_d0_a2_90_d0_90_d0_9c", [48000, 0, 0, 0, 0, "", ""]],
    ["t_90sa", "t_90sa", "tracked", "", "rhst90saatv|rhst90sabtv", "t90sa", "", "wikipedia_t_90", [46500, 0, 0, 0, 0, "", ""]],
    ["t_90sm", "t_90sm", "tracked", "", "rhst90smtv", "t90sm", "", "wikipedia_t_90", [48000, 0, 0, 0, 0, "", ""]],
    ["terrex", "terrex", "wheeled", "", "", "terrex|terrexicv", "apc|wheeled|8x8|singapore", "stengg_terrex_family_datasheet", [24000, 0, 0, 0, 335.564942, "automatic", ""]],
    ["toyota_hilux_technical", "toyota_hilux_technical", "wheeled", "", "", "toyotahiluxtechnical", "", "wikipedia_toyota_hilux", [2286, 0, 0, 0, 0, "", ""]],
    ["toyota_land_cruiser_70", "toyota_land_cruiser_70", "wheeled", "", "bgenoffroad01genf|bgoffroad01atf|cidapoffroad01f|coffroad01repairf|igoffroad01atf|ogoffroad01atf|offroad01atbasef|offroad01basef|offroad01repairbasef|offroad01unarmedbasef|rhsgreftlagoffroadat|rhsgreftlaoffroadat", "landcruiser70|landcruiserj70|lc70", "car|truck|offroad|utility|japan", "wikipedia_toyota_land_cruiser_70", [0, 0, 0, 0, 0, "manual", ""]],
    ["toyota_t100", "toyota_t100", "wheeled", "", "", "t100|toyotat100", "car|pickup|civilian|lighttruck", "toyota_t100_factory_service_manual_1996", [0, 0, 0, 0, 0, "manual", ""]],
    ["tpz_fuchs", "tpz_fuchs", "wheeled", "", "", "tpzfuchs", "", "wikipedia_tpz_fuchs", [23500, 0, 0, 0, 0, "", ""]],
    ["type_10", "type_10", "tracked", "", "", "type10|hitomaru", "mbt|mainbattletank|tracked|type10", "wikipedia_type_10_tank", [48000, 0, 0, 0, 894.839846, "", ""]],
    ["type_16_mcv", "type_16_mcv", "wheeled", "", "", "type16|type16mcv|mcv", "mcv|maneuvercombatvehicle|wheeled|type16", "wikipedia_type_16_mcv", [26000, 0, 0, 0, 425.048927, "", ""]],
    ["type_89_ifv", "type_89_ifv", "tracked", "", "", "type89|type89ifv", "ifv|infantryfightingvehicle|tracked|type89", "wikipedia_type_89_ifv", [26500, 0, 0, 0, 447.419923, "", ""]],
    ["type_96_apc", "type_96_apc", "wheeled", "", "", "type96apc|jgsdftype96", "type96apc|jgsdfapc|komatsuapc", "type_96_apc", [14600, 0, 0, 0, 268.451954, "", ""]],
    ["type_96_tank", "type_96_tank", "tracked", "", "", "type96|ztz96", "ztz96|type96tank|chinesetank", "type_96_tank", [41000, 0, 0, 0, 544.360907, "", ""]],
    ["type_99_tank", "type_99_tank", "tracked", "", "", "type99|ztz99", "ztz99|type99tank|chinesembt", "type_99_tank", [55000, 0, 0, 0, 1118.549808, "", ""]],
    ["uaz_3151", "uaz_3151", "wheeled", "", "rhsuazbase|rhsuazmsv01|rhsuazmsvbase|rhsuazopenbase|rhsuazopenmsv01|rhsuazopenmsvbase|rhsuazopenvdv|rhsuazopenvmf|rhsuazopenvv|rhsuazvdv|rhsuazvmf|rhsuazvv|rhsgrefcdfbreguaz|rhsgrefcdfbreguazopen|rhsgrefcdfreguaz|rhsgrefcdfreguazopen|rhsgrefunuaz|rhssafunuaz|rhssafunuazopen", "uaz3151", "", "uaz_469", [1700, 0, 0, 0, 0, "", ""]],
    ["uaz_469", "uaz_469", "wheeled", "", "", "uaz469", "uaz469|sovietlightutility", "uaz_469", [1700, 213.36, 807.72, 220, 53.690391, "manual", ""]],
    ["ural_375d", "ural_375d", "wheeled", "", "rhssafarmyoural|rhssafarmyouralfuel|rhssafarmyouralopen|rhssafarmyural|rhssafarmyuralfuel|rhssafarmyuralopen|rhssafunural", "ural375d", "", "wikipedia_ural_375", [8400, 0, 0, 0, 0, "", ""]],
    ["ural_4320", "ural_4320", "wheeled", "", "rhsuralbase|rhsuralbaseturret|rhsuralciv01|rhsuralciv02|rhsuralciv03|rhsuralcivbase|rhsuralfuelmsv01|rhsuralfuelvdv01|rhsuralfuelvmf01|rhsuralfuelvv01|rhsuralmsv01|rhsuralmsvbase|rhsuralopenciv01|rhsuralopenciv02|rhsuralopenciv03|rhsuralopenmsv01|rhsuralopenvdv01|rhsuralopenvmf01|rhsuralopenvv01|rhsuralrepairmsv01|rhsuralrepairvdv01|rhsuralrepairvmf01|rhsuralrepairvv01|rhsuralsupportmsvbase01|rhsuralvdv01|rhsuralvmf01|rhsuralvv01|rhsuralzu23base|rhsuralzu23msv01|rhsuralzu23vdv01|rhsuralzu23vmf01|rhsuralzu23vv01|rhsgrefcdfbural|rhsgrefcdfburalzu23|rhsgrefcdfburalfuel|rhsgrefcdfburalopen|rhsgrefcdfburalrepair|rhsgrefcdfural|rhsgrefcdfuralzu23|rhsgrefcdfuralfuel|rhsgrefcdfuralopen|rhsgrefcdfuralrepair|rhsgrefinsgural|rhsgrefinsguralopen|rhsgrefinsguralrepair|rhsgrefinsguralwork|rhsgrefinsguralworkopen|rhsgrefinsural|rhsgrefinsuralopen|rhsgrefinsuralrepair|rhsgrefinsuralwork|rhsgrefinsuralworkopen|rhsgrefnatural|rhsgrefnaturalzu23|rhsgrefnaturalopen|rhsgrefnaturalwork|rhsgrefnaturalworkopen|rhsgrefunural", "ural4320", "truck|wheeled|6x6|russia|cargo", "ural_4320_02_service_manual", [8445, 355.6, 1219.2, 0, 156.596973, "manual", ""]],
    ["vbci", "vbci", "wheeled", "", "", "vbci|vehiculeblindedecombatdinfanterie|vbci8x8", "ifv|8x8|armoured|infantryfightingvehicle|france", "nexter_vbci_sales_brochure", [19000, 0, 0, 0, 447.419923, "automatic", ""]],
    ["wiesel_awc", "wiesel_awc", "tracked", "", "", "wieselawc", "", "wikipedia_wiesel_awc", [2750, 0, 0, 0, 0, "", ""]],
    ["willys_m38", "willys_m38", "wheeled", "", "", "m38|willysm38|m38jeep", "willysm38|m38jeep|lightutilitytruck", "willys_m38_tm_9_8012", [1247, 177.8, 762.0, 235, 0, "manual", ""]],
    ["willys_mb", "willys_mb", "wheeled", "", "", "willysmb|willys|jeep", "willysmb|willysjeep|godevil", "tm_9_803_willys_mb", [1113, 406.4, 965.2, 222, 44.741992, "manual", ""]],
    ["zbd_04", "zbd_04", "tracked", "", "", "zbd04", "zbd04|chineseifv|type04ifv", "zbd_04", [20000, 0, 0, 0, 440, "", ""]],
    ["zsu_23_4_shilka", "zsu_23_4_shilka", "tracked", "", "rhszsu234aa|rhszsutankbase|rhsgrefcdfbzsu234|rhsgrefcdfzsu234|rhsgrefinsgzsu234|rhsgrefinszsu234", "zsu234shilka", "", "wikipedia_zsu_23_4_shilka", [19000, 0, 0, 0, 0, "", ""]]
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
