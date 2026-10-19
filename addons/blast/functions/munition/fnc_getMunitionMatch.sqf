#include "..\..\script_component.hpp"
/*
Munition identity matcher.

Function: aee_blast_fnc_getMunitionMatch.

This file is GENERATED. The generator tools/validation/gen_munition_data.py
writes it from the munition catalogue under data/munition/. Do not edit it
by hand. Edit the corpus and regenerate it.

What a round carries is a real, published figure, and the blast and
fragmentation kernels need it. This resolves a game class - vanilla, modded
or one nobody has written yet - to the real munition it names, using only
the text the class carries: its classname and its display name. No per-mod
class list exists anywhere in this file.

An entry is usually a FAMILY: the AGM-114 Hellfire row answers for
AGM-114K, AGM-114L and AGM-114N, because the figures the sources publish
are the family's.

The ladder, in order:

  1 exact class   the normalised class equals a mapped game class
  2 alias         a query token equals a curated alias
  3 keyword       the query holds a derived designation of at least 3
                  characters
  4 closest       the best-scoring entry, where a designation carrying a
                  type number counts double because a type number
                  identifies while a plain word only describes

An ambiguous match returns an empty array, and so does an unknown class.
There is no default: the caller falls back on its own documented estimate
and says so.

Returns [catalogue_id, munition_type, confidence, matched_by, source, values],
or an empty array. The value row is
[totalMassKg, warheadMassKg, chargeMassKg, calibreMm, lengthMm, filling]
and a zero or an empty string means the corpus holds no published figure
for that field.

A class that names equipment rather than a munition - a cockpit switch, a
targeting pod, a countermeasure discharger, an aircraft weapon bay - returns
an empty array whatever it declares. The kinds are the ones in
tools/validation/munition_kind.py, so the runtime and the coverage
measurement share one filter.

Arguments:
  0: className (STRING, a CfgAmmo, CfgMagazines or CfgWeapons classname,
     default "")
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

// Identity text only: the classname and the display name, read from
// whichever config root declares the class. Vehicle armament is spread
// across CfgAmmo, CfgMagazines and CfgWeapons, and a vanilla class stores
// a $STR key in displayName, so the localised text is read too. None of
// this carries a figure.
private _rawName = "";
{
    private _entry = configFile >> _x >> _className;
    if (isClass _entry) exitWith {
        _rawName = getText (_entry >> "displayName");
        if (_rawName == "") then { _rawName = getText (_entry >> "displayNameShort"); };
    };
} forEach ["CfgAmmo", "CfgMagazines", "CfgWeapons"];
private _localName = if ((_rawName select [0,1]) == "$") then { localize _rawName } else { _rawName };
private _identity = _className + " " + _rawName + " " + _localName;
private _query = [_identity] call _normalise;
private _tokens = [];
{
    private _token = _x call _normalise;
    if (_token != "") then { _tokens pushBack _token; };
} forEach (_identity splitString " _-.");

// Kind screen. A class that names equipment rather than a munition
// never resolves, whatever it declares. The terms are the folded kinds in
// tools/validation/munition_kind.py, which the coverage tool shares.
private _screened = false;
{
    if (_query find _x >= 0) exitWith { _screened = true; };
} forEach ["masterarm", "inhibit", "burstlimit", "salvolimit", "internalbay", "targetingpod", "reconpod", "tarps", "dircm", "irjam", "jammer", "smokegenerator", "smokescreen", "pdu5", "vls", "actioninprogress", "rocketlauncher"];

if (_screened) exitWith { [] };

private _table = [
    ["2a42", "cannon", "", "2a42", "shipunov2a42|2a42", "wikipedia_shipunov_2a42", [115, 0, 0, 30, 3027, ""]],
    ["2a46", "cannon", "", "2a26|2a46|d81|d81t", "2a46125mmgun|2a46|2a46125|125mm|mmgun|2a26|d81|d81t", "wikipedia_2a46_125_mm_gun", [2675, 0, 0, 125, 6350, ""]],
    ["2a70", "cannon", "", "2a70", "2a70", "wikipedia_2a70", [311.6, 0, 0, 99.06, 3942.08, ""]],
    ["2b14_podnos", "mortar", "", "2b14|podnos", "2b14podnos|2b14|podnos", "wikipedia_2b14_podnos", [41.88, 0, 0, 82, 0, ""]],
    ["a_darter", "missile", "", "adarter", "adarter", "wikipedia_a_darter", [89, 0, 0, 165.1, 2971.8, ""]],
    ["aam3", "missile", "", "aam3", "aam3", "wikipedia_mitsubishi_aam_3", [91, 0, 0, 0, 0, ""]],
    ["aam4", "missile", "", "aam4", "aam4", "wikipedia_mitsubishi_aam_4", [222, 31.3, 0, 203, 3667, ""]],
    ["aam5", "missile", "", "aam5", "aam5missile|aam5", "wikipedia_mitsubishi_aam_5", [95, 0, 0, 130, 3105, ""]],
    ["aden", "cannon", "", "aden", "adencannon|aden", "wikipedia_aden_cannon", [196, 0, 0, 30, 1590, ""]],
    ["agm114_hellfire", "missile", "", "agm114|hellfire", "agm114hellfire|agm114|hellfire", "wikipedia_agm_114_hellfire", [45, 0, 0, 180, 1600, ""]],
    ["agm123_skipper", "missile", "", "agm123|skipper", "agm123skipperii|agm123|agm123skipper|skipperii|skipper", "wikipedia_agm_123_skipper", [582, 450, 0, 500, 4300, ""]],
    ["agm154_jsow", "missile", "", "agm154|jsow", "agm154jointstandoffweapon|agm154|agm154joint|jointstandoff|standoffweapon|jsow", "wikipedia_agm_154_joint_standoff_weapon", [497, 0, 0, 330, 4100, ""]],
    ["agm158_jassm", "missile", "", "agm158|jassm", "agm158jassm|agm158|jassm", "wikipedia_agm_158_jassm", [1021, 450, 0, 0, 4287, ""]],
    ["agm176_griffin", "missile", "", "agm176|griffin", "agm176griffin|agm176|griffin", "wikipedia_agm_176_griffin", [20, 5.9, 0, 140, 1100, ""]],
    ["agm179_jagm", "missile", "", "agm179|jagm", "agm179jagm|agm179|jagm", "wikipedia_agm_179_jagm", [49, 0, 0, 178, 1778, ""]],
    ["agm62_walleye", "bomb", "", "agm62|walleye", "agm62walleye|agm62|walleye", "wikipedia_agm_62_walleye", [0, 374, 0, 0, 0, ""]],
    ["agm65_maverick", "missile", "", "agm65|maverick", "agm65maverick|agm65|maverick", "wikipedia_agm_65_maverick", [210, 57, 0, 300, 2490, ""]],
    ["agm84_harpoon", "missile", "", "agm84|harpoon|slamer", "harpoonmissile|agm84|harpoon|slamer", "wikipedia_harpoon_missile", [691, 221, 0, 340, 3800, ""]],
    ["agm88_harm", "missile", "", "agm88|harm", "agm88harm|agm88|harm", "wikipedia_agm_88_harm", [361, 68, 0, 254, 4170, ""]],
    ["ags30", "grenade", "", "ags30", "ags30", "wikipedia_ags_30", [16, 0, 0, 30, 1165, ""]],
    ["aim120_amraam", "missile", "", "aim120|amraam|catm120", "aim120amraam|aim120|amraam|catm120", "wikipedia_aim_120_amraam", [161.5, 20, 0, 178, 3650, ""]],
    ["aim132_asraam", "missile", "", "aim132|asraam", "asraam|aim132", "wikipedia_aim_132_asraam", [88, 10, 0, 166, 2900, ""]],
    ["aim174b", "missile", "", "aim174|aim174b|gunslinger", "aim174bgunslinger|aim174b|aim174|gunslinger", "wikipedia_aim_174b_gunslinger", [830, 64, 0, 340, 5000, ""]],
    ["aim54_phoenix", "missile", "", "aim54|catm54|phoenix", "aim54phoenix|aim54|catm54|phoenix", "wikipedia_aim_54_phoenix", [443, 60.33, 0, 380, 3900, ""]],
    ["aim7_sparrow", "missile", "", "aim7|catm7|sparrow", "aim7sparrow|aim7|catm7|sparrow", "wikipedia_aim_7_sparrow", [230, 29, 0, 200, 3700, ""]],
    ["aim9_sidewinder", "missile", "", "aim9|catm9|catm9m|sidewinder", "aim9sidewinder|aim9|catm9|catm9m|sidewinder", "wikipedia_aim_9_sidewinder", [85.3, 9.4, 0, 127, 3020, ""]],
    ["akd10", "missile", "", "akd10|akd10a", "akd10|akd10a", "", [0, 0, 0, 0, 0, ""]],
    ["alarm", "missile", "", "alarm", "alarm", "wikipedia_alarm_missile", [268, 0, 0, 230, 4240, ""]],
    ["apkws", "rocket", "", "apkws", "advancedprecisionkillweaponsystem|advancedprecision|precisionkill|killweapon|weaponsystem|apkws", "wikipedia_advanced_precision_kill_weapon_system", [15, 0, 0, 70, 1870, ""]],
    ["as30", "missile", "", "as30|as30l", "as30|as30l", "wikipedia_as_30", [520, 240, 0, 340, 3840, ""]],
    ["asm1_type80", "missile", "", "asm1", "type80airtoshipmissile|type80|80airtoship|airtoshipmissile|asm1", "wikipedia_type_80_air_to_ship_missile", [600, 150, 0, 350, 4000, ""]],
    ["asm2_type93", "missile", "", "asm2", "type93airtoshipmissile|type93|93airtoship|airtoshipmissile|asm2", "wikipedia_type_93_air_to_ship_missile", [530, 0, 0, 350, 4000, ""]],
    ["aspide", "missile", "", "aspide", "aspide", "wikipedia_aspide", [220, 35, 0, 203, 3700, ""]],
    ["azp23", "cannon", "", "azp23|zu23", "zu232|azp23|zu23", "wikipedia_zu_23_2", [949.822, 0, 0, 23, 4570, ""]],
    ["bgl", "bomb", "", "bgl|bgl1000|bgl400|bgl66", "bglbombeguideelaser|bglbombe|bombeguidee|guideelaser|bgl1000|bgl400|bgl66", "", [0, 0, 0, 0, 0, ""]],
    ["bgm71_tow", "missile", "", "bgm71|tow", "bgm71tow|bgm71", "wikipedia_bgm_71_tow", [0, 3.9, 0, 152, 1160, ""]],
    ["bk27", "cannon", "", "bk27", "mauserbk27|bk27", "wikipedia_mauser_bk_27", [100, 0, 0, 27, 2310, ""]],
    ["bl755", "bomb", "", "bl755", "bl755", "wikipedia_bl755", [264, 0, 0, 419, 2451, ""]],
    ["blu107_durandal", "bomb", "", "blu107|durandal", "matradurandal|blu107|durandal", "wikipedia_matra_durandal", [200, 100, 0, 223, 2700, ""]],
    ["brimstone", "missile", "", "brimstone", "brimstonemissile|brimstone", "wikipedia_brimstone_missile", [50, 6.3, 0, 180, 1800, ""]],
    ["cbu100_rockeye", "bomb", "", "cbu100|mk20|mk20rockeyeii|rockeye|rockeyeii", "cbu100rockeyeii|cbu100|cbu100rockeye|rockeyeii|mk20|mk20rockeyeii|20rockeye|rockeye", "wikipedia_cbu_100_cluster_bomb", [222, 0, 0, 0, 0, ""]],
    ["cbu87", "bomb", "", "cbu87|cem", "cbu87combinedeffectsmunition|cbu87|cbu87combined|combinedeffects|effectsmunition", "wikipedia_cbu_87_combined_effects_munition", [430, 0, 0, 396, 2330, ""]],
    ["cbu89_gator", "bomb", "", "cbu104|cbu78|cbu89|gator", "cbu89gator|cbu89|cbu104|cbu78|gator", "wikipedia_gator_mine_system", [450, 0, 0, 410, 2340, ""]],
    ["cbu97_sfw", "bomb", "", "cbu105|cbu97|sfw", "cbu97sensorfuzedweapon|cbu97|cbu97sensor|sensorfuzed|fuzedweapon|cbu105", "wikipedia_cbu_97_sensor_fuzed_weapon", [427, 0, 0, 400, 2340, ""]],
    ["crv7", "rocket", "", "crv7", "crv7", "wikipedia_crv7", [0, 4.5, 0, 70, 0, ""]],
    ["d10_tank_gun", "cannon", "", "d10|d10t2s|d10tg", "d10tankgun|d10|d10tank|tankgun|d10t2s|d10t2|d10tg|d10t", "wikipedia_d_10_tank_gun", [1438, 0, 0, 100, 5608, ""]],
    ["d30_2a18", "cannon", "", "2a18|2a18m|d30|d30a", "122mmhowitzer2a18d30|2a18|d30|122mm|mmhowitzer|howitzer2a18|2a18d30|2a18m|d30a", "wikipedia_122_mm_howitzer_2a18_d_30", [0, 0, 0, 122, 5400, ""]],
    ["dagr", "rocket", "", "dagr", "dagrdirectattackguidedrocket|dagrdirect|directattack|attackguided|guidedrocket|dagr", "wikipedia_direct_attack_guided_rocket", [15.8, 0, 0, 70, 1900, ""]],
    ["defa_553", "cannon", "", "defa", "defacannon|defa", "wikipedia_defa_cannon", [80, 0, 0, 30, 1660, ""]],
    ["delilah", "missile", "", "delilah", "delilahmissile|delilah", "wikipedia_delilah_missile", [187, 30, 0, 25.4, 279.4, ""]],
    ["derby", "missile", "", "derby|derbyer", "pythonmissile|derby|derbyer", "wikipedia_rafael_derby", [103.6, 11, 0, 0, 0, ""]],
    ["desert_sting", "bomb", "", "desertsting|desertsting16", "desertsting|desertsting16|sting16", "wikipedia_desert_sting", [0, 5, 0, 0, 0, ""]],
    ["dshk", "cannon", "", "dshk|dshkm", "dshk|dshkm", "wikipedia_dshk", [34, 0, 0, 0, 1625, ""]],
    ["dt_machine_gun", "cannon", "", "dt", "degtyaryovmachinegun|degtyaryovmachine", "wikipedia_degtyaryov_machine_gun", [9.12, 0, 0, 7.62, 1270, ""]],
    ["exocet", "missile", "", "am39|exocet", "exocet|am39", "wikipedia_exocet", [780, 165, 0, 348, 6000, ""]],
    ["fab250", "bomb", "", "fab250", "fab250", "wikipedia_fab_250", [250, 0, 100, 300, 1920, ""]],
    ["fab500", "bomb", "", "fab500", "fab500", "wikipedia_fab_500", [500, 0, 201, 398.78, 2468.88, ""]],
    ["fagot", "missile", "", "9m111", "9k111fagot|9k111|9m111", "wikipedia_9m111_fagot", [12.5, 1.7, 0, 120, 1100, ""]],
    ["fim92_stinger", "missile", "", "atas|fim92|fim92f|stinger", "fim92stinger|fim92|atas|fim92f|stinger", "wikipedia_fim_92_stinger", [10.1, 3, 0, 70, 1530, ""]],
    ["gau12_equalizer", "cannon", "", "gau12|gau22", "gau12equalizer|gau12|gau22", "wikipedia_gau_12_equalizer", [120, 0, 0, 25, 2110, ""]],
    ["gau19", "cannon", "", "gau19", "gau19", "wikipedia_gau_19", [63, 0, 0, 0, 1369, ""]],
    ["gau8_avenger", "cannon", "", "gau8", "gau8avenger|gau8", "wikipedia_gau_8_avenger", [281, 0, 0, 30, 6060, ""]],
    ["gbu10_paveway", "bomb", "", "gbu10|pavewayii|pw2", "gbu10pavewayii|gbu10|gbu10paveway|pavewayii|pw2", "wikipedia_gbu_10_paveway_ii", [910, 0, 0, 460, 4370, ""]],
    ["gbu12_paveway", "bomb", "", "egbu12|gbu12|pavewayii", "gbu12pavewayii|gbu12|gbu12paveway|pavewayii|egbu12", "wikipedia_gbu_12_paveway_ii", [230, 0, 0, 273, 3270, ""]],
    ["gbu16_paveway", "bomb", "", "gbu16", "gbu16pavewayii|gbu16|gbu16paveway|pavewayii", "wikipedia_gbu_16_paveway_ii", [450, 0, 202, 355.6, 0, ""]],
    ["gbu24_paveway", "bomb", "", "gbu24|pavewayiii|pw3", "gbu24pavewayiii|gbu24|gbu24paveway|pavewayiii|pw3", "wikipedia_gbu_24_paveway_iii", [1050, 0, 910, 457.2, 4390, ""]],
    ["gbu31_jdam", "bomb", "", "gbu31|gbu56", "gbu31jdam|gbu31|gbu56", "wikipedia_joint_direct_attack_munition", [910, 0, 0, 0, 0, ""]],
    ["gbu32_jdam", "bomb", "", "gbu32|gbu55", "gbu32jdam|gbu32|gbu55", "wikipedia_joint_direct_attack_munition", [450, 0, 0, 0, 0, ""]],
    ["gbu38_jdam", "bomb", "", "gbu38|gbu54|jdam|ljdam", "gbu38jdam|gbu38|gbu54|jdam|ljdam", "wikipedia_joint_direct_attack_munition", [230, 0, 0, 0, 0, ""]],
    ["gbu39_sdb", "bomb", "", "gbu39|sdb", "gbu39smalldiameterbomb|gbu39|gbu39small|smalldiameter|diameterbomb", "wikipedia_gbu_39_small_diameter_bomb", [129, 93, 0, 0, 1800, ""]],
    ["gbu53_stormbreaker", "bomb", "", "gbu53|sdbii|stormbreaker", "gbu53|bstormbreaker|sdbii|stormbreaker", "wikipedia_gbu_53_b_stormbreaker", [93, 48, 0, 150, 1760, ""]],
    ["gsh23", "cannon", "", "gsh23", "gryazevshipunovgsh23|gsh23", "wikipedia_gryazev_shipunov_gsh_23", [49.2, 0, 0, 23, 1387, ""]],
    ["gsh302", "cannon", "", "gsh30|gsh302", "gryazevshipunovgsh301|gsh301|gsh302|gsh30", "wikipedia_gryazev_shipunov_gsh_30_1", [46, 0, 0, 30, 1978, ""]],
    ["hydra70", "rocket", "", "hydra|hydra70|m151|m229|m255|m257|m261|m278", "hydra70|hydra|m151|m229|m255|m257|m261|m278", "wikipedia_hydra_70", [6.2, 0, 0, 70, 1060, ""]],
    ["igla", "missile", "", "9k38|djigit|igla", "9k38igla|9k38|djigit|igla", "wikipedia_9k38_igla", [10.8, 1.17, 0, 72, 1574, ""]],
    ["iris_t", "missile", "", "irist", "irist", "wikipedia_iris_t", [87.4, 11.4, 0, 127, 2940, ""]],
    ["kab500l", "bomb", "", "kab250l|kab500|kab500kr|kab500l|kab500se", "kab500l|kab500|kab250l|kab250|kab500kr|kab500k|kab500se|kab500s", "wikipedia_kab_500l", [525, 450, 0, 0, 0, ""]],
    ["kggb", "bomb", "", "kggb", "kggb", "wikipedia_kggb", [316, 0, 0, 0, 50.8, ""]],
    ["kh25", "missile", "", "kh25|kh25ml|kh25mp|kh25mt", "kh25|kh25ml|kh25m|kh25mp|kh25mt", "wikipedia_kh_25", [299, 89.6, 0, 275, 3705, ""]],
    ["kh29", "missile", "", "kh29|kh29d|kh29l|kh29t", "kh29|kh29d|kh29l|kh29t", "wikipedia_kh_29", [660, 320, 0, 380, 3900, ""]],
    ["kh31", "missile", "", "kh31|kh31a|kh31p", "kh31|kh31a|kh31p", "wikipedia_kh_31", [610, 94, 0, 360, 4700, ""]],
    ["kh59", "missile", "", "kh59|kh59me", "kh59|kh59me|kh59m", "wikipedia_kh_59", [930, 320, 0, 380, 5700, ""]],
    ["konkurs", "missile", "", "9m113", "9m113konkurs|9m113", "wikipedia_9m113_konkurs", [14.6, 2.7, 0, 135, 1150, ""]],
    ["kornet", "missile", "", "9k133|9m133|kornet", "9m133kornet|9m133|9k133|kornet", "wikipedia_9m133_kornet", [27, 4.6, 0, 152, 1200, ""]],
    ["kpvt", "cannon", "", "kpv|kpvt", "kpvheavymachinegun|kpvheavy|heavymachine|kpvt", "wikipedia_kpv_heavy_machine_gun", [49, 0, 0, 14.5, 1980, ""]],
    ["ls_pgb", "bomb", "", "ls6|ls6500|lspgb", "lspgb|ls6|ls6500", "wikipedia_ls_pgb", [50, 0, 0, 0, 0, ""]],
    ["lt_pgb", "bomb", "", "lt2|lt3|ltpgb", "ltpgb|lt2|lt3", "wikipedia_lt_pgb", [570, 0, 0, 380, 3580, ""]],
    ["m101_howitzer", "cannon", "", "howitzer105|m101", "m101howitzer|m101|howitzer105", "wikipedia_m101_howitzer", [2260, 0, 0, 105, 5940, ""]],
    ["m119", "cannon", "", "m119a2", "m119howitzer|m119|m119a2", "wikipedia_m119_howitzer", [2320, 0, 0, 105, 0, ""]],
    ["m134_minigun", "cannon", "", "m134|m134d|minigun", "m134minigun|m134|m134d|minigun", "wikipedia_m134_minigun", [39, 0, 0, 0, 801.6, ""]],
    ["m197", "cannon", "", "m197", "m197electriccannon|m197|m197electric|electriccannon", "wikipedia_m197_electric_cannon", [60, 0, 0, 20, 1828.8, ""]],
    ["m230", "cannon", "", "m230|m230e1", "m230chaingun|m230|m230chain|chaingun|m230e1", "wikipedia_m230_chain_gun", [59.5, 0, 0, 29.972, 2181, ""]],
    ["m240", "cannon", "", "m240|m240b|m240c|m240d", "m240machinegun|m240|m240machine|m240b|m240c|m240d", "wikipedia_m240_machine_gun", [12.5, 0, 0, 0, 1260, ""]],
    ["m242_bushmaster", "cannon", "", "25mmm242|m242", "m242bushmaster|m242|25mmm242|25mm|25m", "wikipedia_m242_bushmaster", [119, 0, 0, 0, 2672, ""]],
    ["m2_browning", "cannon", "", "m2|m2hb|m3hmg|m3p", "m2browning|m2hb|m2h|m3hmg|m3p", "wikipedia_m2_browning", [38, 0, 0, 0, 1654, ""]],
    ["m39_atacms", "missile", "", "atacms|m39|m39a2", "atacms|m39|m39a2", "wikipedia_mgm_140_atacms", [1670, 213, 0, 610, 4000, ""]],
    ["m3m_gau21", "cannon", "", "gau21|m3m", "gau21|m3m", "wikipedia_m3m_machine_gun", [38, 0, 0, 0, 1654, ""]],
    ["m61_vulcan", "cannon", "", "m61|m61a2|vulcan", "m61vulcan|m61|m61a2|vulcan", "wikipedia_m61_vulcan", [112, 0, 0, 20, 1827, ""]],
    ["m777", "cannon", "", "howitzer155|m777", "m777howitzer|m777|howitzer155", "wikipedia_m777_howitzer", [0, 0, 0, 155, 10700, ""]],
    ["malyutka", "missile", "", "9k11|9m14", "9m14malyutka|9m14|9k11", "wikipedia_9m14_malyutka", [10.9, 2.6, 0, 125, 860, ""]],
    ["martel", "missile", "", "aj168|as37|martel", "martelmissile|aj168|as37|martel", "wikipedia_martel_missile", [550, 150, 0, 400, 4180, ""]],
    ["martlet_lmm", "missile", "", "lmm|martlet", "lightweightmultirolemissile|lightweightmultirole|multirolemissile|martlet", "wikipedia_martlet_missile", [13, 3, 0, 76, 1300, ""]],
    ["meteor", "missile", "", "meteor", "meteormissile|meteor", "wikipedia_meteor_missile", [190, 0, 0, 178, 3650, ""]],
    ["mk19", "grenade", "", "mk19", "mk19grenadelauncher|19grenade|grenadelauncher|mk19", "wikipedia_mk_19_grenade_launcher", [35.2, 0, 0, 0, 1090, ""]],
    ["mk77", "bomb", "", "mk77|napalm", "mark77bomb|mark77|77bomb|mk77|napalm", "wikipedia_mark_77_bomb", [340, 0, 0, 0, 0, ""]],
    ["mk81", "bomb", "", "mk81|mk81e|snakeeye", "mark81bomb|mark81|81bomb|mk81|mk81e|snakeeye", "wikipedia_mark_81_bomb", [119, 0, 44, 230, 1880, "Tritonal"]],
    ["mk82", "bomb", "", "mk82", "mark82bomb|mark82|82bomb|mk82", "wikipedia_mk_82_bomb", [241, 0, 89, 273, 2210, "Tritonal"]],
    ["mk83", "bomb", "", "mk83", "mark83bomb|mark83|83bomb|mk83", "wikipedia_mark_83_bomb", [447, 202, 0, 350, 3000, "PBXN-109"]],
    ["mk84", "bomb", "", "mk84", "mark84bomb|mark84|84bomb|mk84", "wikipedia_mark_84_bomb", [925, 429, 0, 460, 3840, "Tritonal"]],
    ["mokopa", "missile", "", "mokopa|zt6", "mokopa|zt6", "wikipedia_mokopa", [49.8, 0, 0, 178, 1995, ""]],
    ["mw1", "bomb", "", "mw1", "mw1munitionsdispenser|mw1|mw1munitions|munitionsdispenser", "", [0, 0, 0, 0, 0, ""]],
    ["nsv", "cannon", "", "nsv|nsvt", "nsvmachinegun|nsvmachine|nsvt", "wikipedia_nsv_machine_gun", [25, 0, 0, 12.7, 1560, ""]],
    ["pab100", "bomb", "", "pab|pab100", "pab100practicebomb|pab100|pab100practice|practicebomb", "", [0, 0, 0, 0, 0, ""]],
    ["paveway_iv", "bomb", "", "pavewayiv|pw4", "pavewayiv|pw4", "wikipedia_paveway_iv", [230, 0, 0, 0, 0, ""]],
    ["pkt", "cannon", "", "pkm|pkt", "pkmachinegun|pkmachine", "wikipedia_pk_machine_gun", [9, 0, 0, 0, 1203, ""]],
    ["pl10", "missile", "", "pl10", "pl10", "wikipedia_pl_10", [0, 0, 0, 160, 3000, ""]],
    ["pl11", "missile", "", "pl11", "pl11missile|pl11", "wikipedia_pl_11_missile", [0, 0, 0, 0, 3700, ""]],
    ["pl12", "missile", "", "pl12", "pl12", "wikipedia_pl_12", [180, 0, 0, 0, 0, ""]],
    ["pl15", "missile", "", "pl15", "pl15", "wikipedia_pl_15", [200, 0, 0, 203, 3996, ""]],
    ["pl2", "missile", "", "pl2", "pl2", "wikipedia_pl_2", [60, 11.3, 0, 127, 2150, ""]],
    ["pl5", "missile", "", "pl5", "pl5", "wikipedia_pl_5", [148, 6, 0, 127, 3128, ""]],
    ["pl8", "missile", "", "pl8", "pl8missile|pl8", "wikipedia_pl_8_missile", [115, 11, 0, 160, 2950, ""]],
    ["pl9", "missile", "", "pl9", "pl9", "wikipedia_pl_9", [123, 11.8, 0, 157, 2900, ""]],
    ["popeye_agm142", "missile", "", "agm142|popeye|raptor", "popeyemissile|agm142|popeye|raptor", "wikipedia_popeye_missile", [1360, 340, 0, 533, 4820, ""]],
    ["python_missile", "missile", "", "python|python3|python4|python5", "python|python3|python4|python5", "wikipedia_python_missile", [103.6, 11, 0, 0, 0, ""]],
    ["r27", "missile", "", "r27|r27er|r27et", "r27airtoairmissile|r27|r27airtoair|airtoairmissile|r27er|r27e|r27et", "wikipedia_r_27_air_to_air_missile", [253, 39, 0, 230, 4080, ""]],
    ["r530", "missile", "", "matra530|matra530d|r530", "r530|matra530|matra530d|530d", "wikipedia_r_530", [192, 27.2, 0, 263, 3280, ""]],
    ["r550_magic", "missile", "", "magic|matra550|r550", "r550magic|r550|magic|matra550", "wikipedia_r_550_magic", [89, 12.7, 0, 157, 2720, ""]],
    ["r60", "missile", "", "r60|r60m", "r60missile|r60|r60m", "wikipedia_r_60_missile", [44, 3, 0, 120, 2090, ""]],
    ["r73", "missile", "", "r73", "r73missile|r73", "wikipedia_r_73_missile", [105, 7.4, 0, 165.1, 177.8, ""]],
    ["r77", "missile", "", "r77", "r77", "wikipedia_r_77", [175, 22.5, 0, 200, 3600, ""]],
    ["rbk250", "bomb", "", "rbk250", "rbk250", "wikipedia_rbk_250", [250, 0, 0, 0, 0, ""]],
    ["rbk500", "bomb", "", "rbk500|rbk500spbed", "rbk500|rbk500spbed", "wikipedia_rbk_500", [500, 0, 0, 0, 0, ""]],
    ["rbs15", "missile", "", "rbs15", "rbs15", "wikipedia_rbs_15", [746, 200, 0, 500, 4350, ""]],
    ["rim162_essm", "missile", "", "essm|rim162", "rim162essm|rim162|essm", "wikipedia_rim_162_essm", [280, 39, 0, 254, 3660, ""]],
    ["s13", "rocket", "", "s13", "s13rocket|s13", "wikipedia_s_13_rocket", [0, 0, 0, 122, 0, ""]],
    ["s24_rocket", "rocket", "", "s24|s24b", "s24rocket|s24|s24b", "wikipedia_s_24_rocket", [235, 123, 0, 240, 0, ""]],
    ["s25", "rocket", "", "s25|s25l|s25o", "s25rocket|s25|s25l|s25o", "wikipedia_s_25_rocket", [370, 0, 0, 340, 3560, ""]],
    ["s5_rocket", "rocket", "", "57mm|s5|s5k|s5m|s5mo", "s5rocket|57mm|57m|s5k|s5m|s5mo", "wikipedia_s_5_rocket", [5, 0, 0, 55, 0, ""]],
    ["s8_rocket", "rocket", "", "s8|s8kom|s8ofp", "s8rocket|s8kom|s8ko|s8ofp|s8of", "wikipedia_s_8_rocket", [11.3, 0, 0, 80, 0, ""]],
    ["sea_eagle", "missile", "", "seaeagle", "seaeaglemissile|seaeagle|eaglemissile", "wikipedia_sea_eagle_missile", [580, 230, 0, 400, 4140, ""]],
    ["sea_skua", "missile", "", "seaskua", "seaskua", "wikipedia_sea_skua", [145, 30, 0, 250, 2500, "RDX"]],
    ["sea_venom", "missile", "", "seavenom", "seavenommissile|seavenom|venommissile", "wikipedia_sea_venom_missile", [120, 30, 0, 200, 2500, ""]],
    ["skyflash", "missile", "", "skyflash", "skyflash", "wikipedia_skyflash", [193, 39.5, 0, 203, 3680, ""]],
    ["sneb", "rocket", "", "sneb", "sneb", "wikipedia_sneb", [0, 0, 0, 68, 0, ""]],
    ["spear3", "missile", "", "spear3", "spear3", "wikipedia_spear_3", [90, 0, 0, 180, 1800, ""]],
    ["spg9", "cannon", "", "spg9", "spg9", "wikipedia_spg_9", [47.5, 0, 0, 73, 2110, ""]],
    ["spike", "missile", "", "spike|spikeer|spikenlos", "spikemissile|spike|spikeer|spikenlos", "wikipedia_spike_missile", [34, 0, 0, 130, 1200, ""]],
    ["standard_missile", "missile", "", "rim66|standardmissile", "rim66standard|rim66|standardmissile", "wikipedia_rim_66_standard", [707, 0, 0, 343, 4720, ""]],
    ["storm_shadow", "missile", "", "scalp|stormshadow", "stormshadow|scalp", "wikipedia_storm_shadow", [1300, 450, 0, 0, 5100, ""]],
    ["taurus_kepd350", "missile", "", "kepd350|taurus", "tauruskepd350|tauruskepd|kepd350|taurus", "wikipedia_taurus_kepd_350", [1400, 480, 0, 0, 5100, ""]],
    ["tochka", "missile", "", "9m79|9m791", "otr21tochka|otr21|9m79|9m791", "wikipedia_otr_21_tochka", [2000, 0, 0, 650, 6400, ""]],
    ["ty90", "missile", "", "ty90", "ty90", "wikipedia_ty_90", [25, 3, 0, 90, 0, ""]],
    ["u5ts_2a20", "cannon", "", "2a20|u5ts", "u5ts|u5t|2a20", "wikipedia_u_5ts", [0, 0, 0, 115.062, 0, ""]],
    ["vikhr", "missile", "", "9k121|vikhr", "9k121vikhr|9k121|vikhr", "wikipedia_9k121_vikhr", [45, 8, 0, 130, 2800, ""]],
    ["wcmd", "bomb", "", "cbu103|cbu104|wcmd", "windcorrectedmunitionsdispenser|windcorrected|correctedmunitions|munitionsdispenser|cbu103|cbu104|wcmd", "wikipedia_wind_corrected_munitions_dispenser", [0, 0, 0, 0, 0, ""]],
    ["yj91", "missile", "", "yj91", "yj91", "wikipedia_yj_91", [0, 87, 0, 0, 0, ""]],
    ["zis_s53", "cannon", "", "ziss53", "85mmairdefensegunm193952k|m1939|52k|mmair|airdefense|defensegun|gunm1939|m193952k|ziss53|s53", "wikipedia_zis_s_53", [4500, 0, 0, 85, 7050, ""]],
    ["zu23_2a14", "cannon", "", "2a14|azp23|zu23", "2a14|azp23|zu23", "wikipedia_zu_23_2", [949.822, 0, 0, 23, 4570, ""]],
    ["zuni", "rocket", "", "zuni", "zunirocket|zuni", "wikipedia_zuni_rocket", [36.1, 0, 0, 127, 2000, ""]]
];

private _result = {
    params ["_row", "_confidence", "_layer"];
    [_row select 0, _row select 1, _confidence, _layer, _row select 5, _row select 6]
};

private _candidates = [];

// Layer 1: exact class.
{
    _x params ["_catalogue", "_type", "_classes", "_aliases", "_keywords", "_source", "_values"];
    if (((_classes splitString "|") find _key) >= 0) then {
        _candidates pushBack _x;
    };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 1, "exact_class"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 2: alias. A query token equals a curated alias.
_candidates = [];
{
    _x params ["_catalogue", "_type", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _hit = false;
    {
        if (_x in _tokens) then { _hit = true; };
    } forEach (_aliases splitString "|");
    if (_hit) then { _candidates pushBack _row; };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 2, "alias"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 3: keyword. The query holds a derived designation.
_candidates = [];
{
    _x params ["_catalogue", "_type", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _hit = false;
    {
        if ((count _x) >= 3 && {_query find _x >= 0}) then { _hit = true; };
    } forEach ((_aliases + "|" + _keywords) splitString "|");
    if (_hit) then { _candidates pushBack _row; };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 3, "keyword"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 4: closest. The total of every designation of the entry that the
// query holds, with a type number worth double.
private _bestRow = [];
private _bestScore = 0;
private _runnerUp = 0;
private _bestCount = 0;
private _bestName = 0;
private _tie = false;
{
    _x params ["_catalogue", "_type", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _score = 0;
    private _count = 0;
    private _longest = 0;
    {
        _count = _count + 1;
        if ((count _x) >= 3 && {_query find _x >= 0}) then {
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
                // Equal evidence. The entry advertising FEWER designations
                // is the less qualified one, and failing that the entry
                // whose own longest designation is SHORTER carries the less
                // qualified name. When a query names the family but not the
                // mark, the family is the right answer.
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
    [_bestRow, 4, "closest"] call _result
};
[]
