#include "..\script_component.hpp"
/*
Aircraft identity matcher (issue #117).

Function: aee_flight_fnc_getAircraftMatch.

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
  family        the class text names a family and no mark: exactly one
                row of the family table carries a designation of 3 or
                more characters in the query. A family row is
                identity-only and answers only when it is the only
                one, so it never takes an answer from a mark.           7
  type          nothing above names the aircraft, so the ENGINE kind is
                the answer: "helicopter", "fixed-wing aircraft",
                "unmanned aerial vehicle" or "aircraft". A type entry
                names a kind, never a model, and carries no figure.     8

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
    ["a10a_thunderbolt_ii", "a10a", "fixed_wing", "Plane", "bplanecas01clusterf|bplanecas01f|bplanecas01dynamicloadoutf|plane|planecas01basef", "a10|wipeout|thunderboltii", "cas|fairchilda10athunderboltii|a10a|fairchilda10a|a10athunderbolt", "src_to_1a10a1", [12701, 0, 0, 0]],
    ["a10c_thunderbolt_ii", "a10c", "fixed_wing", "", "", "", "fairchilda10cthunderboltii|a10c|a10|fairchilda10c|a10cthunderbolt|thunderboltii", "", [0, 0, 0, 0]],
    ["a1h_skyraider", "a1h", "fixed_wing", "", "", "skyraider|spad", "douglasa1hskyraider|a1h|douglasa1h|a1hskyraider", "", [0, 0, 0, 0]],
    ["a29_super_tucano", "a29_super_tucano", "fixed_wing", "", "", "a29|supertucano", "embraera29supertucano|embraera29|a29super", "", [0, 0, 0, 0]],
    ["a4e_skyhawk", "a4e", "fixed_wing", "", "", "skyhawk|scooter", "douglasa4eskyhawk|a4e|douglasa4e|a4eskyhawk", "", [0, 0, 0, 0]],
    ["a6a_intruder", "a6a", "fixed_wing", "", "", "intruder", "grummana6aintruder|a6a|grummana6a|a6aintruder", "", [0, 0, 0, 0]],
    ["a7d_corsair_ii", "a7d", "fixed_wing", "", "", "corsairii|sluf", "ltva7dcorsairii|a7d|ltva7d|a7dcorsair", "", [0, 0, 0, 0]],
    ["aermacchi_mb339", "mb339", "fixed_wing", "", "", "mb339", "aermacchimb339", "", [0, 0, 0, 0]],
    ["ah1g_cobra", "ah1g", "rotary_wing", "", "", "", "bellah1gcobra|ah1g|bellah1g|ah1gcobra", "", [0, 0, 0, 0]],
    ["ah1j_seacobra", "ah1j_seacobra", "rotary_wing", "Helicopter", "", "seacobra", "bellah1jseacobra|ah1j|bellah1j|ah1jseacobra", "", [0, 0, 0, 0]],
    ["ah1s_cobra", "ah1s_cobra", "rotary_wing", "Helicopter", "", "cobra", "bellah1scobra|ah1s|bellah1s|ah1scobra", "", [0, 0, 0, 0]],
    ["ah1w_super_cobra", "ah1w_super_cobra", "rotary_wing", "Helicopter", "", "supercobra", "bellah1wsupercobra|ah1w|bellah1w|ah1wsupercobra", "", [0, 0, 0, 0]],
    ["ah1z_viper", "ah1z_viper", "rotary_wing", "Helicopter", "", "viper", "bellah1zviper|ah1z|bellah1z|ah1zviper", "", [0, 0, 0, 0]],
    ["ah64a_apache", "ah64a_apache", "rotary_wing", "Helicopter", "", "apache", "hughesah64aapache|ah64a|ah64|hughesah64a|ah64aapache", "", [0, 0, 0, 0]],
    ["ah64d_apache_longbow", "ah64d", "rotary_wing", "", "rhsah64d|rhsah64dgrey|rhsah64daa|rhsah64dcs|rhsah64dgs|fzaah64db1|fzaah64db2e", "", "boeingah64dapachelongbow|ah64d|ah64|boeingah64d|ah64dapache|apachelongbow", "", [0, 0, 0, 0]],
    ["ah64e_apache_guardian", "ah64e_apache_guardian", "rotary_wing", "Helicopter", "", "apacheguardian", "boeingah64eapacheguardian|ah64e|ah64|boeingah64e|ah64eapache", "", [0, 0, 0, 0]],
    ["ah6_little_bird", "ah6_little_bird", "rotary_wing", "Helicopter", "", "littlebird", "hughesah6littlebird|ah6|hughesah6|ah6little", "", [0, 0, 0, 0]],
    ["alphajet_e", "alphajet_e", "fixed_wing", "", "", "alphajet", "dassaultbreguetdornieralphajete|dassaultbreguetdornier|dornieralpha", "", [0, 0, 0, 0]],
    ["amx_gibli", "amx_gibli", "fixed_wing", "", "", "ghibli", "amxinternationalamxghibli|amxinternational|internationalamx|amxghibli", "", [0, 0, 0, 0]],
    ["an2_colt", "an2_colt", "fixed_wing", "", "", "an2|colt", "antonovan2", "", [0, 0, 0, 0]],
    ["as332_super_puma", "as332_super_puma", "rotary_wing", "Helicopter", "", "superpuma", "aerospatialeas332superpuma|as332|332super", "", [0, 0, 0, 0]],
    ["as350_ecureuil", "as350_ecureuil", "rotary_wing", "Helicopter", "", "ecureuil|squirrel", "aerospatialeas350ecureuil|as350|350ecureuil", "", [0, 0, 0, 0]],
    ["as355_twinstar", "as355_twinstar", "rotary_wing", "Helicopter", "", "twinstar", "aerospatialeas355twinstar|as355|355twinstar", "", [0, 0, 0, 0]],
    ["as365_dauphin", "as365_dauphin", "rotary_wing", "Helicopter", "", "dauphin", "aerospatialeas365dauphin|as365|365dauphin", "", [0, 0, 0, 0]],
    ["as532_cougar", "as532_cougar", "rotary_wing", "Helicopter", "", "cougar", "eurocopteras532cougar|eurocopteras|as532|532cougar", "", [0, 0, 0, 0]],
    ["av8b_harrier_ii", "av8b", "fixed_wing", "", "", "", "mcdonnelldouglasav8bharrierii|av8b|av8|douglasav8b|av8bharrier|harrierii", "", [0, 0, 0, 0]],
    ["avro_lancaster_b1", "lancaster_b1", "fixed_wing", "", "", "lancaster", "avrolancasterbmki|avrolancaster|lancasterb", "", [0, 0, 0, 0]],
    ["aw101_hm2", "aw101_hm2", "rotary_wing", "Helicopter", "", "merlin", "agustawestlandaw101hm2merlin|aw101|hm2|agustawestlandaw101|aw101hm2|hm2merlin", "", [0, 0, 0, 0]],
    ["aw101_merlin", "aw101", "rotary_wing", "Helicopter", "cbrnmohawk|cidaphelitransport02f|helitransport02basef|ihelitransport02f", "merlin|aw101|mohawk", "heavy|agustawestlandaw101merlin|agustawestlandaw101|aw101merlin", "src_leonardo_aw101", [15600, 5652000.0, 0, 271.716349]],
    ["aw139", "aw139", "rotary_wing", "Helicopter", "", "aw139", "agustawestlandaw139", "", [0, 0, 0, 0]],
    ["aw149", "aw149", "rotary_wing", "Helicopter", "", "aw149", "agustawestlandaw149", "", [0, 0, 0, 0]],
    ["aw159_wildcat", "aw159", "rotary_wing", "Helicopter", "iehelilight03dynamicloadoutf|iehelilight03unarmedf|ihelilight03f|ihelilight03dynamicloadoutf|ihelilight03unarmedf", "wildcat|aw159", "maritime|agustawestlandaw159wildcat|agustawestlandaw159|aw159wildcat", "", [0, 0, 0, 0]],
    ["b17g_flying_fortress", "b17g", "fixed_wing", "", "", "", "boeingb17gflyingfortress|b17g|b17|boeingb17g|b17gflying|flyingfortress", "", [0, 0, 0, 0]],
    ["b24j_liberator", "b24j", "fixed_wing", "", "", "liberator", "consolidatedb24jliberator|b24j|b24|consolidatedb24j|b24jliberator", "", [0, 0, 0, 0]],
    ["b29_superfortress", "b29", "fixed_wing", "", "", "superfortress", "boeingb29superfortress|b29|boeingb29|b29superfortress", "", [0, 0, 0, 0]],
    ["b52h_stratofortress", "b52h", "fixed_wing", "", "", "stratofortress|buff", "boeingb52hstratofortress|b52h|b52|boeingb52h|b52hstratofortress", "", [0, 0, 0, 0]],
    ["bae_hawk_t1", "hawk_t1", "fixed_wing", "", "", "hawk", "baesystemshawkt1|baesystems|systemshawk|hawkt1", "", [0, 0, 0, 0]],
    ["bell205", "bell205", "rotary_wing", "Helicopter", "", "bell205", "", "", [0, 0, 0, 0]],
    ["bell206b_jetranger", "bell206b_jetranger", "rotary_wing", "Helicopter", "", "jetranger", "bell206bjetranger|206b|bell206b|206bjetranger", "", [0, 0, 0, 0]],
    ["bell212", "bell212", "rotary_wing", "Helicopter", "", "bell212", "", "", [0, 0, 0, 0]],
    ["bell407", "bell407", "rotary_wing", "Helicopter", "", "bell407", "", "", [0, 0, 0, 0]],
    ["bell412", "bell412", "rotary_wing", "Helicopter", "", "bell412", "", "", [0, 0, 0, 0]],
    ["bell412ep", "bell412ep", "rotary_wing", "Helicopter", "", "bell412", "bell412ep|412ep|412e", "", [0, 0, 0, 0]],
    ["bell429", "bell429", "rotary_wing", "Helicopter", "", "bell429", "", "", [0, 0, 0, 0]],
    ["bell525", "bell525", "rotary_wing", "Helicopter", "", "relentless", "bell525relentless|bell525|525relentless", "", [0, 0, 0, 0]],
    ["bf109g6", "bf109g6", "fixed_wing", "", "", "", "messerschmittbf109g6|messerschmittbf|bf109|109g6", "", [0, 0, 0, 0]],
    ["bk117", "bk117", "rotary_wing", "Helicopter", "", "bk117", "kawasakibk117|kawasakibk", "", [0, 0, 0, 0]],
    ["blackburn_buccaneer", "blackburn_buccaneer", "fixed_wing", "", "", "buccaneer", "blackburnbuccaneer", "", [0, 0, 0, 0]],
    ["bo105", "bo105", "rotary_wing", "Helicopter", "", "bo105", "messerschmittbolkowblohmbo105|messerschmittbolkowblohmbo", "", [0, 0, 0, 0]],
    ["bristol_britannia", "bristol_britannia", "fixed_wing", "", "", "britannia", "bristolbritannia", "", [0, 0, 0, 0]],
    ["c130_hercules", "c130_hercules", "fixed_wing", "", "", "c130|hercules", "lockheedc130hercules|lockheedc130|c130hercules", "", [0, 0, 0, 0]],
    ["camcopter_s100", "camcopter_s100", "rotary_wing", "Helicopter", "", "camcopter", "schiebelcamcopters100|s100|schiebelcamcopter|camcopters100", "", [0, 0, 0, 0]],
    ["cessna_172_skyhawk", "172s", "fixed_wing", "Plane", "cplanecivil01f|cplanecivil01racingf|icplanecivil01f", "skyhawk|c172", "civil|cessna172skyhawk|cessna172|172skyhawk", "src_faa_tcds_3a12", [1157, 134225.97696, 0, 0]],
    ["ch46_sea_knight", "ch46_sea_knight", "rotary_wing", "Helicopter", "", "seaknight", "boeingch46seaknight|ch46|boeingch46|ch46sea", "", [0, 0, 0, 0]],
    ["ch47_chinook", "ch47d", "rotary_wing", "Helicopter", "bhelitransport03f|bhelitransport03blackf|bhelitransport03unarmedf|bhelitransport03unarmedgreenf", "chinook", "heavy|boeingch47chinook|boeingch47|ch47chinook", "src_tm_1_1520_240_10", [22680, 0, 0, 0]],
    ["ch47a_chinook", "ch47a_chinook", "rotary_wing", "Helicopter", "", "chinook", "boeingch47achinook|ch47a|boeingch47a|ch47achinook", "", [0, 0, 0, 0]],
    ["ch47b_chinook", "ch47b_chinook", "rotary_wing", "Helicopter", "", "chinook", "boeingch47bchinook|ch47b|boeingch47b|ch47bchinook", "", [0, 0, 0, 0]],
    ["ch47c_chinook", "ch47c_chinook", "rotary_wing", "Helicopter", "", "chinook", "boeingch47cchinook|ch47c|boeingch47c|ch47cchinook", "", [0, 0, 0, 0]],
    ["ch47f_chinook", "ch47f", "rotary_wing", "", "", "", "boeingch47fchinook|ch47f|boeingch47f|ch47fchinook", "", [0, 0, 0, 0]],
    ["ch53d_sea_stallion", "ch53d_sea_stallion", "rotary_wing", "Helicopter", "", "seastallion", "sikorskych53dseastallion|ch53d|sikorskych53d|ch53dsea", "", [0, 0, 0, 0]],
    ["ch53e_super_stallion", "ch53e_super_stallion", "rotary_wing", "Helicopter", "", "superstallion", "sikorskych53esuperstallion|ch53e|sikorskych53e|ch53esuper", "", [0, 0, 0, 0]],
    ["ch53k_king_stallion", "ch53k_king_stallion", "rotary_wing", "Helicopter", "", "kingstallion", "sikorskych53kkingstallion|ch53k|sikorskych53k|ch53kking", "", [0, 0, 0, 0]],
    ["ch5_rainbow", "ch5", "fixed_wing", "UAV", "otuav04casf", "rainbow|ch5", "ucav|cascch5rainbow|cascch5|ch5rainbow", "", [0, 0, 0, 0]],
    ["chengdu_j10a", "j10a", "fixed_wing", "", "", "vigorousdragon", "chengduj10a|j10a|j10", "", [0, 0, 0, 0]],
    ["chengdu_j7_ii", "j7_ii", "fixed_wing", "", "", "fishbed|mig21", "chengduj7ii|j7ii|j7i", "", [0, 0, 0, 0]],
    ["dehavilland_mosquito_b", "mosquito_b", "fixed_wing", "", "", "mosquito|woodenwonder", "dehavillandmosquitobmkiv|dehavilland|havillandmosquito|mosquitob", "", [0, 0, 0, 0]],
    ["ec135", "ec135", "rotary_wing", "Helicopter", "", "ec135", "eurocopterec135", "", [0, 0, 0, 0]],
    ["ec145", "ec145", "rotary_wing", "Helicopter", "", "ec145", "eurocopterec145", "", [0, 0, 0, 0]],
    ["ec155", "ec155", "rotary_wing", "Helicopter", "", "ec155", "eurocopterec155", "", [0, 0, 0, 0]],
    ["ec225_super_puma", "ec225_super_puma", "rotary_wing", "Helicopter", "", "superpuma", "eurocopterec225superpuma|ec225|eurocopterec225|ec225super", "", [0, 0, 0, 0]],
    ["ec665_tiger", "ec665_tiger", "rotary_wing", "Helicopter", "", "tiger", "eurocoptertiger|ec665", "", [0, 0, 0, 0]],
    ["ef2000_typhoon_fgr4", "ef2000_fgr4", "fixed_wing", "", "", "", "eurofightertyphoonfgr4|fgr4|eurofightertyphoon|typhoonfgr4|typhoon", "", [0, 0, 0, 0]],
    ["f100d_super_sabre", "f100d", "fixed_wing", "", "", "supersabre", "northamericanf100dsupersabre|f100d|f100|americanf100d|f100dsuper", "", [0, 0, 0, 0]],
    ["f104g_starfighter", "f104g", "fixed_wing", "", "", "starfighter", "lockheedf104gstarfighter|f104g|f104|lockheedf104g|f104gstarfighter", "", [0, 0, 0, 0]],
    ["f105d_thunderchief", "f105d", "fixed_wing", "", "", "thunderchief", "republicf105dthunderchief|f105d|f105|republicf105d|f105dthunderchief", "", [0, 0, 0, 0]],
    ["f111a_ardvark", "f111a", "fixed_wing", "", "", "aardvark", "generaldynamicsf111aaardvark|f111a|f111|generaldynamics|dynamicsf111a|f111aaardvark", "", [0, 0, 0, 0]],
    ["f14a_tomcat", "f14a", "fixed_wing", "", "", "", "grummanf14atomcat|f14a|f14|grummanf14a|f14atomcat", "", [0, 0, 0, 0]],
    ["f14b_tomcat", "f14b", "fixed_wing", "", "", "tomcat", "grummanf14btomcat|f14b|f14|grummanf14b|f14btomcat", "", [0, 0, 0, 0]],
    ["f15a_eagle", "f15a", "fixed_wing", "", "", "eagle", "mcdonnelldouglasf15aeagle|f15a|f15|douglasf15a|f15aeagle", "", [0, 0, 0, 0]],
    ["f15c_eagle", "f15c", "fixed_wing", "", "", "", "mcdonnelldouglasf15ceagle|f15c|f15|douglasf15c|f15ceagle", "", [0, 0, 0, 0]],
    ["f15e_strike_eagle", "f15e", "fixed_wing", "", "", "strikeeagle", "boeingf15estrikeeagle|f15e|f15|boeingf15e|f15estrike", "", [0, 0, 0, 0]],
    ["f16a_block10", "f16a_block10", "fixed_wing", "", "", "falcon|viper", "lockheedf16ablock10|f16a|f16|lockheedf16a|f16ablock|block10", "", [0, 0, 0, 0]],
    ["f16c_block50", "f16c_block50", "fixed_wing", "", "", "", "lockheedmartinf16cblock50|f16c|f16|martinf16c|f16cblock|block50", "", [0, 0, 0, 0]],
    ["f16c_block52", "f16c_block52", "fixed_wing", "", "", "falcon", "lockheedmartinf16cblock52|f16c|f16|martinf16c|f16cblock|block52", "", [0, 0, 0, 0]],
    ["f22a_raptor", "f22a", "fixed_wing", "", "", "", "lockheedmartinf22araptor|f22a|f22|martinf22a|f22araptor", "", [0, 0, 0, 0]],
    ["f35a_lightning_ii", "f35a", "fixed_wing", "", "", "", "lockheedmartinf35alightningii|f35a|f35|martinf35a|f35alightning|lightningii", "", [0, 0, 0, 0]],
    ["f4c_phantom_ii", "f4c", "fixed_wing", "", "", "phantom", "mcdonnellf4cphantomii|f4c|mcdonnellf4c|f4cphantom|phantomii", "", [0, 0, 0, 0]],
    ["f4e_phantom_ii", "f4e", "fixed_wing", "", "", "", "mcdonnelldouglasf4ephantomii|f4e|douglasf4e|f4ephantom|phantomii", "", [0, 0, 0, 0]],
    ["f4j_phantom_ii", "f4j", "fixed_wing", "", "", "phantom", "naval|mcdonnelldouglasf4jphantomii|f4j|douglasf4j|f4jphantom|phantomii", "", [0, 0, 0, 0]],
    ["f4u4_corsair", "f4u4", "fixed_wing", "", "", "corsair|whistlingdeath", "voughtf4u4corsair|f4u4|voughtf4u4|f4u4corsair|f4u", "", [0, 0, 0, 0]],
    ["f5e_tiger_ii", "f5e", "fixed_wing", "", "", "tiger", "northropf5etigerii|f5e|northropf5e|f5etiger|tigerii", "", [0, 0, 0, 0]],
    ["f6f5_hellcat", "f6f5", "fixed_wing", "", "", "hellcat", "grummanf6f5hellcat|f6f5|grummanf6f5|f6f5hellcat|f6f", "", [0, 0, 0, 0]],
    ["f80c_shooting_star", "f80c", "fixed_wing", "", "", "shootingstar", "lockheedf80cshootingstar|f80c|f80|lockheedf80c|f80cshooting", "", [0, 0, 0, 0]],
    ["f84f_thunderstreak", "f84f", "fixed_wing", "", "", "thunderstreak", "republicf84fthunderstreak|f84f|f84|republicf84f|f84fthunderstreak", "", [0, 0, 0, 0]],
    ["f86d_sabre", "f86d", "fixed_wing", "", "", "sabredog", "northamericanf86dsabre|f86d|f86|americanf86d|f86dsabre", "", [0, 0, 0, 0]],
    ["f86f_sabre", "f86f", "fixed_wing", "", "", "", "northamericanf86fsabre|f86f|f86|americanf86f|f86fsabre", "", [0, 0, 0, 0]],
    ["f8e_crusader", "f8e", "fixed_wing", "", "", "crusader", "voughtf8ecrusader|f8e|voughtf8e|f8ecrusader", "", [0, 0, 0, 0]],
    ["fa18a_hornet", "fa18a", "fixed_wing", "", "", "hornet", "mcdonnelldouglasf|douglasf|a18ahornet|a18a|a18", "", [0, 0, 0, 0]],
    ["fa18c_hornet", "fa18c", "fixed_wing", "", "", "hornet", "mcdonnelldouglasf|douglasf|a18chornet|a18c|a18", "", [0, 0, 0, 0]],
    ["fa18e_super_hornet", "fa18e", "fixed_wing", "Plane", "bplanefighter01casmoduleheavybomber2f|bplanefighter01casmoduleheavybomberf|bplanefighter01casmoduleheavynapalm2f|bplanefighter01casmoduleheavynapalmf|bplanefighter01casmodulemediumbomber2f|bplanefighter01casmodulemediumbomberf|bplanefighter01casmodulemediumnapalm2f|bplanefighter01casmodulemediumnapalmf|bplanefighter01casmodulenapalmf|bplanefighter01clusterf|bplanefighter01f|bplanefighter01napalmf|bplanefighter01stealthf", "superhornet|fa18", "multirole|boeingf|a18esuperhornet|a18e|a18|a18esuper", "src_fa18_natops", [14288, 66316756.798983, 0, 0]],
    ["fa18f_super_hornet", "fa18f", "fixed_wing", "", "firecmdummy2", "superhornet", "boeingf|a18fsuperhornet|a18f|a18|a18fsuper", "", [0, 0, 0, 0]],
    ["focke_wulf_fw190d", "fw190d", "fixed_wing", "", "", "dora", "fockewulffw190d|190d|fockewulffw|fw190d|fw190", "", [0, 0, 0, 0]],
    ["folland_gnat", "folland_gnat", "fixed_wing", "", "", "gnat", "follandgnat", "", [0, 0, 0, 0]],
    ["fw190a8", "fw190a8", "fixed_wing", "", "", "", "fockewulffw190a8|fockewulffw|fw190|190a8", "", [0, 0, 0, 0]],
    ["harrier_gr9", "harrier_gr9", "fixed_wing", "", "", "harrier", "vtol|baesystemsharriergr9|gr9|baesystems|systemsharrier|harriergr9", "", [0, 0, 0, 0]],
    ["hawker_hurricane_mk_i", "hurricane_i", "fixed_wing", "", "", "hurricane", "hawkerhurricanemki|hawkerhurricane|hurricanemk", "", [0, 0, 0, 0]],
    ["hawker_typhoon_mk_ib", "typhoon_ib", "fixed_wing", "", "", "typhoon|tiffy", "hawkertyphoonmkib|hawkertyphoon|typhoonmk", "", [0, 0, 0, 0]],
    ["hh60g_pave_hawk", "hh60g_pave_hawk", "rotary_wing", "Helicopter", "vtxhh60", "pavehawk", "sikorskyhh60gpavehawk|hh60g|sikorskyhh60g|hh60gpave", "", [0, 0, 0, 0]],
    ["hs681", "hs681", "fixed_wing", "", "", "hs681", "hawkersiddeleyhs681|hawkersiddeley|siddeleyhs681", "", [0, 0, 0, 0]],
    ["hs_nimrod", "hs_nimrod", "fixed_wing", "", "", "nimrod", "hawkersiddeleynimrod|hawkersiddeley|siddeleynimrod", "", [0, 0, 0, 0]],
    ["jas39c_gripen", "jas39c", "fixed_wing", "Plane", "iplanefighter04clusterf|iplanefighter04f", "gripen|jas39", "multirole|saabjas39cgripen|39c|saabjas|jas39c|39cgripen", "src_saab_gripen_c", [14000, 31305555.5645, 0, 0]],
    ["junkers_ju87d_stuka", "ju87d", "fixed_wing", "", "", "stuka", "junkersju87dstuka|87d|junkersju|ju87d|87dstuka|ju87", "", [0, 0, 0, 0]],
    ["ka27_helix", "ka27_helix", "rotary_wing", "Helicopter", "", "helix", "kamovka27helix|ka27|kamovka27|ka27helix", "", [0, 0, 0, 0]],
    ["ka29_helix_b", "ka29_helix_b", "rotary_wing", "Helicopter", "", "helix", "kamovka29helixb|ka29|kamovka29|ka29helixb", "", [0, 0, 0, 0]],
    ["ka32_helix_c", "ka32_helix_c", "rotary_wing", "Helicopter", "", "helix", "kamovka32helixc|ka32|kamovka32|ka32helixc", "", [0, 0, 0, 0]],
    ["ka50_hokum", "ka50", "rotary_wing", "Helicopter", "", "hokum", "gunship|kamovka50hokuma|ka50|kamovka50|ka50hokuma", "src_opfor_weg", [7692, 1640539.7184, 0, 165.129964]],
    ["ka52_alligator", "ka52", "rotary_wing", "", "", "", "kamovka52alligator|ka52|kamovka52|ka52alligator", "", [0, 0, 0, 0]],
    ["ka60_kasatka", "ka60_kasatka", "rotary_wing", "Helicopter", "helilight02basef|ohelilight02f|ohelilight02dynamicloadoutf|ohelilight02unarmedf|ohelilight02v2f", "kasatka|orca", "kamovka60kasatka|ka60|kamovka60|ka60kasatka", "", [0, 0, 0, 0]],
    ["l159_alca", "l159", "fixed_wing", "Plane", "iplanefighter03aaf|iplanefighter03casf|iplanefighter03clusterf|iplanefighter03dynamicloadoutf|planefighter03basef", "alca|l159|buzzard", "lightattack|aerol159alca|aerol159|l159alca", "", [0, 0, 0, 0]],
    ["l18_lodestar", "l18_lodestar", "fixed_wing", "", "", "l18", "lockheedl18lodestar|lockheedl18|l18lodestar", "", [0, 0, 0, 0]],
    ["light_utility_rotary", "mi2", "rotary_wing", "Helicopter", "", "hoplite|mi2", "milmi2", "src_opfor_weg", [1076, 298279.9488, 0, 167.415473]],
    ["lynx_has3", "lynx_has3", "rotary_wing", "Helicopter", "", "lynx", "westlandlynxhas3|has3|westlandlynx|lynxhas3", "", [0, 0, 0, 0]],
    ["md500", "md500e", "rotary_wing", "Helicopter", "bhelilight01f|bhelilight01armedf|bhelilight01dynamicloadoutf|bhelilight01strippedf|chelilight01bluelinef|chelilight01bluef|chelilight01digitalf|chelilight01ellipticalf|chelilight01furiousf|chelilight01graywatcherf|chelilight01ionf|chelilight01jeansf|chelilight01lightf|chelilight01luxef|chelilight01redf|chelilight01shadowf|chelilight01sherifff|chelilight01speedyf|chelilight01strippedf|chelilight01sunsetf|chelilight01vranaf|chelilight01waspf|chelilight01wavef|helilight01armedbasef|helilight01basef", "md500|hummingbird|pawnee", "mdhelicoptersmd500", "src_md500e_2023", [752, 313000.0, 0, 50.895764]],
    ["md500_civil", "md500_civil", "rotary_wing", "Helicopter", "chelilight01civilf|helilight01civilbasef|ichelilight01civilf", "md500civil|m900", "civil|mdhelicoptersmd500civil|md500|500civil|md500civi", "src_md500e_2023", [752, 313000.0, 0, 50.895764]],
    ["md530_defender", "md530f", "rotary_wing", "Helicopter", "", "md530|defender", "mdhelicoptersmd530defender|530defender", "src_md530f_2023", [782, 478000.0, 0, 55.154115]],
    ["md902_explorer", "md902_explorer", "rotary_wing", "Helicopter", "", "explorer", "mdhelicoptersmd902explorer|md902|902explorer", "", [0, 0, 0, 0]],
    ["messerschmitt_bf109e", "bf109e", "fixed_wing", "", "", "bf109|emil", "messerschmittbf109e|109e|messerschmittbf|bf109e", "", [0, 0, 0, 0]],
    ["messerschmitt_me262a", "me262a", "fixed_wing", "", "", "schwalbe", "messerschmittme262a|262a|messerschmittme|me262a|me262", "", [0, 0, 0, 0]],
    ["mh47g_chinook", "mh47g_chinook", "rotary_wing", "Helicopter", "", "chinook", "boeingmh47gchinook|mh47g|mh47|boeingmh47g|mh47gchinook", "", [0, 0, 0, 0]],
    ["mh53e_sea_dragon", "mh53e_sea_dragon", "rotary_wing", "Helicopter", "", "seadragon", "sikorskymh53eseadragon|mh53e|mh53|sikorskymh53e|mh53esea", "", [0, 0, 0, 0]],
    ["mh60g_pave_hawk", "mh60g_pave_hawk", "rotary_wing", "Helicopter", "", "pavehawk", "sikorskymh60gpavehawk|mh60g|mh60|sikorskymh60g|mh60gpave", "", [0, 0, 0, 0]],
    ["mh60m", "mh60m", "rotary_wing", "", "121soarhibyrdslick", "mh60m", "sikorskymh60mblackhawk|mh60|sikorskymh60m|mh60mblack", "", [0, 0, 0, 0]],
    ["mh60r_seahawk", "mh60r_seahawk", "rotary_wing", "Helicopter", "", "seahawk", "sikorskymh60rseahawk|mh60r|mh60|sikorskymh60r|mh60rseahawk", "", [0, 0, 0, 0]],
    ["mh60s_knighthawk", "mh60s_knighthawk", "rotary_wing", "Helicopter", "", "knighthawk", "sikorskymh60sknighthawk|mh60s|mh60|sikorskymh60s|mh60sknighthawk", "", [0, 0, 0, 0]],
    ["mh6m_mission_enhanced", "mh6m_mission_enhanced", "rotary_wing", "Helicopter", "", "littlebird", "boeingmh6mmissionenhancedlittlebird|mh6m|mh6|boeingmh6m|mh6mmission|missionenhanced|enhancedlittle", "", [0, 0, 0, 0]],
    ["mi10_harke", "mi10_harke", "rotary_wing", "Helicopter", "", "harke", "milmi10harke|mi10|milmi10|mi10harke", "", [0, 0, 0, 0]],
    ["mi14_haze", "mi14_haze", "rotary_wing", "Helicopter", "", "haze", "milmi14haze|mi14|milmi14|mi14haze", "", [0, 0, 0, 0]],
    ["mi171_hip_h", "mi171_hip_h", "rotary_wing", "Helicopter", "", "hip|mi8amt", "milmi171hiph|mi171|milmi171|mi171hiph|mi8am", "", [0, 0, 0, 0]],
    ["mi17_hip", "mi17_hip", "rotary_wing", "Helicopter", "", "hip|mi8mt", "milmi17hiph|mi17|milmi17|mi17hiph|mi8m", "src_opfor_weg", [7100, 1454114.7504, 0, 356.327293]],
    ["mi24a_hind_a", "mi24a_hind_a", "rotary_wing", "Helicopter", "", "hind", "milmi24ahinda|mi24a|milmi24a|mi24ahinda", "", [0, 0, 0, 0]],
    ["mi24d_hind_d", "mi24d", "rotary_wing", "", "", "", "milmi24dhindd|mi24d|milmi24d|mi24dhindd", "", [0, 0, 0, 0]],
    ["mi24p_hind_f", "mi24p", "rotary_wing", "Helicopter", "rhsmi24pcasvvsbase", "hind", "gunship|milmi24phindf|mi24p|milmi24p|mi24phindf", "src_opfor_weg", [8500, 1640539.7184, 0, 235.061816]],
    ["mi24v_hind_e", "mi24v", "rotary_wing", "", "", "", "milmi24vhinde|mi24v|milmi24v|mi24vhinde", "", [0, 0, 0, 0]],
    ["mi26_halo", "mi26", "rotary_wing", "Helicopter", "ohelitransport04f|ohelitransport04ammof|ohelitransport04ammoblackf|ohelitransport04benchf|ohelitransport04benchblackf|ohelitransport04blackf|ohelitransport04boxf|ohelitransport04boxblackf|ohelitransport04coveredf|ohelitransport04coveredblackf|ohelitransport04fuelf|ohelitransport04fuelblackf|ohelitransport04medevacf|ohelitransport04medevacblackf|ohelitransport04repairf|ohelitransport04repairblackf", "halo|mi26", "heavy|milmi26halo|milmi26|mi26halo", "src_opfor_weg", [12809, 8500978.5408, 0, 804.247719]],
    ["mi28_havoc", "mi28", "rotary_wing", "Helicopter", "heliattack02basef|oheliattack02f|oheliattack02blackf|oheliattack02dynamicloadoutf|oheliattack02dynamicloadoutblackf", "havoc|mi28|kajman", "gunship|milmi28havoc|milmi28|mi28havoc", "src_opfor_weg", [3175, 1640539.7184, 0, 232.352193]],
    ["mi28n_havoc", "mi28n", "rotary_wing", "", "", "", "milmi28nhavoc|mi28n|mi28|milmi28n|mi28nhavoc", "", [0, 0, 0, 0]],
    ["mi35m_hind_e", "mi35m_hind_e", "rotary_wing", "Helicopter", "", "hind", "milmi35mhinde|mi35m|mi35|milmi35m|mi35mhinde", "", [0, 0, 0, 0]],
    ["mi38_halo", "mi38_halo", "rotary_wing", "Helicopter", "", "halo", "milmi38|mi38", "", [0, 0, 0, 0]],
    ["mi4_hound", "mi4_hound", "rotary_wing", "Helicopter", "", "hound", "milmi4hound|mi4|milmi4|mi4hound", "", [0, 0, 0, 0]],
    ["mi6_hook", "mi6_hook", "rotary_wing", "Helicopter", "", "hook", "milmi6hook|mi6|milmi6|mi6hook", "", [0, 0, 0, 0]],
    ["mi8_hip", "mi8_hip", "rotary_wing", "Helicopter", "", "hip|mi8t", "milmi8thipc|mi8|milmi8t|mi8thipc", "src_opfor_weg", [6990, 1267689.7824, 0, 356.327293]],
    ["mi8amtsh", "mi8amtsh", "rotary_wing", "", "", "mi8amtsh|mi171sh|terminator", "milmi8amtsh|mi8amts|mi8|mi171s", "", [0, 0, 0, 0]],
    ["mig15bis", "mig15bis", "fixed_wing", "", "", "", "mikoyangurevichmig15bis|mig15bis|mig15bi|mig15", "", [0, 0, 0, 0]],
    ["mig17f_fresco", "mig17f", "fixed_wing", "", "", "fresco", "mikoyangurevichmig17ffresco|mig17f|mig17|mikoyangurevichmig17f|mig17ffresco", "", [0, 0, 0, 0]],
    ["mig19s_farmer", "mig19s", "fixed_wing", "", "", "farmer", "mikoyangurevichmig19sfarmer|mig19s|mig19|mikoyangurevichmig19s|mig19sfarmer", "", [0, 0, 0, 0]],
    ["mig21bis", "mig21bis", "fixed_wing", "", "", "fishbed", "mikoyangurevichmig21bis|mig21bis|mig21bi|mig21", "", [0, 0, 0, 0]],
    ["mig21f13", "mig21f13", "fixed_wing", "", "", "fishbed", "mikoyangurevichmig21f13|mig21f13|mig21", "", [0, 0, 0, 0]],
    ["mig21mf", "mig21mf", "fixed_wing", "", "", "", "mikoyangurevichmig21mf|mig21mf|mig21m|mig21", "", [0, 0, 0, 0]],
    ["mig23m_flogger", "mig23m", "fixed_wing", "", "", "flogger", "mikoyangurevichmig23mfloggerb|mig23m|mig23|mikoyangurevichmig23m|mig23mfloggerb", "", [0, 0, 0, 0]],
    ["mig23ml_flogger", "mig23ml", "fixed_wing", "", "", "flogger", "mikoyangurevichmig23mlfloggerg|mig23ml|mig23m|mikoyangurevichmig23ml|mig23mlfloggerg|mig23", "", [0, 0, 0, 0]],
    ["mig25_foxbat", "mig25", "fixed_wing", "", "", "foxbat", "mikoyangurevichmig25foxbat|mig25|mikoyangurevichmig25|mig25foxbat", "", [0, 0, 0, 0]],
    ["mig27_flogger_d", "mig27", "fixed_wing", "", "", "flogger", "mikoyangurevichmig27floggerd|mig27|mikoyangurevichmig27|mig27floggerd", "", [0, 0, 0, 0]],
    ["mig29a_fulcrum", "mig29a", "fixed_wing", "", "", "fulcrum", "mikoyanmig29afulcrum|mig29a|mikoyanmig29a|mig29afulcrum", "", [0, 0, 0, 0]],
    ["mig29s_fulcrum_c", "mig29s", "fixed_wing", "", "", "", "mikoyanmig29sfulcrumc|mig29s|mikoyanmig29s|mig29sfulcrumc", "", [0, 0, 0, 0]],
    ["mig31b_foxhound", "mig31b", "fixed_wing", "", "", "foxhound", "mikoyanmig31bfoxhound|mig31b|mig31|mikoyanmig31b|mig31bfoxhound", "", [0, 0, 0, 0]],
    ["mig31bm_foxhound", "mig31bm", "fixed_wing", "", "", "", "mikoyanmig31bmfoxhound|mig31bm|mig31b|mikoyanmig31bm|mig31bmfoxhound|mig31", "", [0, 0, 0, 0]],
    ["mig35_fulcrum_f", "mig35", "fixed_wing", "", "", "fulcrum", "mikoyanmig35fulcrumf|mig35|mikoyanmig35|mig35fulcrumf", "", [0, 0, 0, 0]],
    ["mirage_2000c", "mirage2000c", "fixed_wing", "", "", "mirage", "dassaultmirage2000c|2000c|dassaultmirage|mirage2000c|mirage2000", "", [0, 0, 0, 0]],
    ["mirage_f1_cr", "mirage_f1_cr", "fixed_wing", "", "", "mirage", "dassaultmiragef1cr|f1cr|f1c|dassaultmirage|miragef1cr|miragef1", "", [0, 0, 0, 0]],
    ["mirage_iii_e", "mirage3e", "fixed_wing", "", "", "mirage", "dassaultmirageiiie|dassaultmirage|mirageiiie|mirageiii", "", [0, 0, 0, 0]],
    ["mitsubishi_a6m2_zero", "a6m2", "fixed_wing", "", "", "zero|reisen", "mitsubishia6m2zero|a6m2|mitsubishia6m2|a6m2zero|a6m", "", [0, 0, 0, 0]],
    ["mq8_fire_scout", "mq8_fire_scout", "rotary_wing", "Helicopter", "", "firescout", "northropgrummanmq8firescout|mq8|northropgrumman|grummanmq8|mq8fire", "", [0, 0, 0, 0]],
    ["mq8c_fire_scout", "mq8c_fire_scout", "rotary_wing", "Helicopter", "", "firescout", "northropgrummanmq8cfirescout|mq8c|mq8|northropgrumman|grummanmq8c|mq8cfire", "", [0, 0, 0, 0]],
    ["mq9a_reaper", "mq9a", "fixed_wing", "UAV", "buav02casf|buav02f|buav02dynamicloadoutf|iuav02casf|iuav02f|iuav02dynamicloadoutf|ouav02casf|ouav02f|ouav02dynamicloadoutf|uav02basef", "reaper|mq9a|greyhawk", "generalatomicsmq9areaper|mq9|generalatomics|atomicsmq9a|mq9areaper", "src_odin_weg_2025", [4763, 0, 0, 0]],
    ["nh90_nfh", "nh90_nfh", "rotary_wing", "Helicopter", "", "nh90", "nhindustriesnh90nfh|nhindustriesnh90|nh90nfh", "", [0, 0, 0, 0]],
    ["nh90_tth", "nh90_tth", "rotary_wing", "", "", "", "nhindustriesnh90tth|nh90|nhindustriesnh90|nh90tth", "", [0, 0, 0, 0]],
    ["o3a_skymaster", "o3a_skymaster", "fixed_wing", "", "", "o3a", "cessnao3a", "", [0, 0, 0, 0]],
    ["oh58a_kiowa", "oh58a_kiowa", "rotary_wing", "Helicopter", "", "kiowa", "belloh58akiowa|oh58a|oh58|belloh58a|oh58akiowa", "", [0, 0, 0, 0]],
    ["oh58c_kiowa", "oh58c_kiowa", "rotary_wing", "Helicopter", "", "kiowa", "belloh58ckiowa|oh58c|oh58|belloh58c|oh58ckiowa", "", [0, 0, 0, 0]],
    ["oh58d_kiowa_warrior", "oh58d_kiowa_warrior", "rotary_wing", "Helicopter", "", "kiowawarrior", "belloh58dkiowawarrior|oh58d|oh58|belloh58d|oh58dkiowa", "", [0, 0, 0, 0]],
    ["oh6a_cayuse", "oh6a_cayuse", "rotary_wing", "Helicopter", "", "cayuse|loach", "hughesoh6acayuse|oh6a|oh6|hughesoh6a|oh6acayuse", "", [0, 0, 0, 0]],
    ["p38j_lightning", "p38j", "fixed_wing", "", "", "lightning", "lockheedp38jlightning|p38j|p38|lockheedp38j|p38jlightning", "", [0, 0, 0, 0]],
    ["p40e_warhawk", "p40e", "fixed_wing", "", "", "warhawk|kittyhawk", "curtissp40ewarhawk|p40e|p40|curtissp40e|p40ewarhawk", "", [0, 0, 0, 0]],
    ["p47d_thunderbolt", "p47d", "fixed_wing", "", "", "", "republicp47dthunderbolt|p47d|p47|republicp47d|p47dthunderbolt", "", [0, 0, 0, 0]],
    ["p51d_mustang", "p51d", "fixed_wing", "", "", "", "northamericanp51dmustang|p51d|p51|americanp51d|p51dmustang", "", [0, 0, 0, 0]],
    ["p61b_black_widow", "p61b", "fixed_wing", "", "", "blackwidow", "northropp61bblackwidow|p61b|p61|northropp61b|p61bblack", "", [0, 0, 0, 0]],
    ["panavia_tornado_gr4", "tornado_gr4", "fixed_wing", "", "", "tornado", "panaviatornadogr4|gr4|panaviatornado|tornadogr4", "", [0, 0, 0, 0]],
    ["parrot_ar_drone_2", "parrot_ar_drone_2", "rotary_wing", "", "buav01f|ouav01f|uav01basef", "ardrone20|ardrone|darter|parrotardrone20", "parrotardrone", "", [0, 0, 0, 0]],
    ["pchela_1t", "pchela_1t", "fixed_wing", "", "", "pchela|pchela1t", "yakovlevpchela1t|pchela1", "", [0, 0, 0, 0]],
    ["rafale_c", "rafale_c", "fixed_wing", "", "", "", "dassaultrafalec|dassaultrafale|rafalec|rafale", "", [0, 0, 0, 0]],
    ["rah66_comanche", "rah66", "rotary_wing", "Helicopter", "bheliattack01f|bheliattack01dynamicloadoutf|bheliattack01pylonsdynamicloadoutf|heliattack01basef", "comanche|rah66|blackfoot", "scout|boeingsikorskyrah66comanche|boeingsikorskyrah66|rah66comanche", "src_rah66_case", [3526, 0, 0, 0]],
    ["rq8_fire_scout", "rq8_fire_scout", "rotary_wing", "Helicopter", "", "firescout", "northropgrummanrq8firescout|rq8|northropgrumman|grummanrq8|rq8fire", "", [0, 0, 0, 0]],
    ["s70i_black_hawk", "s70i_black_hawk", "rotary_wing", "", "", "s70i", "sikorskys70i|s70", "", [0, 0, 0, 0]],
    ["s76", "s76", "rotary_wing", "Helicopter", "", "s76", "sikorskys76", "", [0, 0, 0, 0]],
    ["s92", "s92", "rotary_wing", "Helicopter", "", "s92", "sikorskys92", "", [0, 0, 0, 0]],
    ["sa321_super_frelon", "sa321_super_frelon", "rotary_wing", "Helicopter", "", "superfrelon", "aerospatialesa321superfrelon|sa321|321super", "", [0, 0, 0, 0]],
    ["sa330_puma", "sa330_puma", "rotary_wing", "Helicopter", "", "puma", "aerospatialesa330puma|sa330|330puma", "", [0, 0, 0, 0]],
    ["sa341_gazelle", "sa341", "rotary_wing", "Helicopter", "", "gazelle", "aerospatialesa341gazelle|sa341|341gazelle", "src_opfor_weg", [998, 439962.92448, 0, 86.590148]],
    ["sa342_gazelle", "sa342_gazelle", "rotary_wing", "Helicopter", "", "gazelle", "aerospatialesa342gazelle|sa342|342gazelle", "", [0, 0, 0, 0]],
    ["saab_105", "saab_105", "fixed_wing", "", "", "saab105", "", "", [0, 0, 0, 0]],
    ["saab_35_draken", "saab_35", "fixed_wing", "", "", "draken", "saab35draken|saab35|35draken", "", [0, 0, 0, 0]],
    ["saab_37_viggen", "saab_37", "fixed_wing", "", "", "viggen", "saab37viggen|saab37|37viggen", "", [0, 0, 0, 0]],
    ["sepecat_jaguar_gr1", "jaguar_gr1", "fixed_wing", "", "", "jaguar", "sepecatjaguargr1|gr1|sepecatjaguar|jaguargr1", "", [0, 0, 0, 0]],
    ["sh60b_seahawk", "sh60b_seahawk", "rotary_wing", "Helicopter", "", "seahawk", "sikorskysh60bseahawk|sh60b|sh60|sikorskysh60b|sh60bseahawk", "", [0, 0, 0, 0]],
    ["shenyang_j8_ii", "j8_ii", "fixed_wing", "", "", "finback", "shenyangj8ii|j8ii|j8i", "", [0, 0, 0, 0]],
    ["spitfire_mk_ix", "spitfire_ix", "fixed_wing", "", "", "", "supermarinespitfiremkix|supermarinespitfire|spitfiremk|spitfire", "", [0, 0, 0, 0]],
    ["su17_fitter_c", "su17", "fixed_wing", "", "", "fitter", "sukhoisu17fitterc|su17|sukhoisu17|su17fitterc", "", [0, 0, 0, 0]],
    ["su22_fitter_f", "su22", "fixed_wing", "", "", "fitter", "sukhoisu22fitterf|su22|sukhoisu22|su22fitterf", "", [0, 0, 0, 0]],
    ["su24_fencer", "su24", "fixed_wing", "", "", "fencer", "sukhoisu24fencer|su24|sukhoisu24|su24fencer", "", [0, 0, 0, 0]],
    ["su25_frogfoot", "su25", "fixed_wing", "Plane", "", "frogfoot", "cas|sukhoisu25", "src_opfor_weg", [4320, 0, 0, 0]],
    ["su25sm_frogfoot", "su25sm", "fixed_wing", "", "rhssu25smcasvvs|rhssu25smcasvvsc", "frogfoot|grach", "sukhoisu25smfrogfoot|su25sm|su25s|sukhoisu25sm|su25smfrogfoot", "", [0, 0, 0, 0]],
    ["su25t_frogfoot", "su25t", "fixed_wing", "", "", "frogfoot", "sukhoisu25tfrogfoot|su25t|sukhoisu25t|su25tfrogfoot", "", [0, 0, 0, 0]],
    ["su27s_flanker_b", "su27s", "fixed_wing", "", "", "", "sukhoisu27sflankerb|su27s|su27|sukhoisu27s|su27sflankerb", "", [0, 0, 0, 0]],
    ["su27sk_flanker_b", "su27sk", "fixed_wing", "", "", "flanker", "sukhoisu27skflankerb|su27sk|su27s|sukhoisu27sk|su27skflankerb|su27", "", [0, 0, 0, 0]],
    ["su30mki_flanker_h", "su30mki", "fixed_wing", "", "", "flanker", "sukhoisu30mkiflankerh|su30mki|su30mk|sukhoisu30mki|su30mkiflankerh|su30", "", [0, 0, 0, 0]],
    ["su33_flanker_d", "su33", "fixed_wing", "", "", "flanker", "sukhoisu33flankerd|su33|sukhoisu33|su33flankerd", "", [0, 0, 0, 0]],
    ["su34_fullback", "su34", "fixed_wing", "", "", "fullback", "sukhoisu34fullback|su34|sukhoisu34|su34fullback", "", [0, 0, 0, 0]],
    ["su35s_flanker_e", "su35s", "fixed_wing", "", "", "", "sukhoisu35sflankere|su35s|su35|sukhoisu35s|su35sflankere", "", [0, 0, 0, 0]],
    ["su57_felon", "su57", "fixed_wing", "Plane", "oplanefighter02clusterf|oplanefighter02f|oplanefighter02stealthf", "felon|su57|t50|pakfa", "stealth|multirole|sukhoisu57", "src_odin_weg_2025", [18000, 0, 0, 0]],
    ["su7b_fitter", "su7b", "fixed_wing", "", "", "fitter", "sukhoisu7bfitter|su7b|su7|sukhoisu7b|su7bfitter", "", [0, 0, 0, 0]],
    ["t38a_talon", "t38a", "fixed_wing", "", "", "talon", "northropt38atalon|t38a|t38|northropt38a|t38atalon", "", [0, 0, 0, 0]],
    ["th67_creek", "th67_creek", "rotary_wing", "Helicopter", "", "creek", "bellth67creek|th67|bellth67|th67creek", "", [0, 0, 0, 0]],
    ["tu22m_backfire", "tu22m_backfire", "fixed_wing", "", "", "tu22m|backfire", "tupolevtu22m|tu22", "", [0, 0, 0, 0]],
    ["tu95_bear", "tu95_bear", "fixed_wing", "", "", "tu95|bear", "tupolevtu95", "", [0, 0, 0, 0]],
    ["uh1h_iroquois", "uh1h", "rotary_wing", "", "rhsuh1hhidfgunship", "huey|iroquois", "belluh1hiroquois|uh1h|belluh1h|uh1hiroquois", "", [0, 0, 0, 0]],
    ["uh1n_twin_huey", "uh1n_twin_huey", "rotary_wing", "Helicopter", "", "twinhuey", "belluh1ntwinhuey|uh1n|belluh1n|uh1ntwin", "", [0, 0, 0, 0]],
    ["uh1y_venom", "uh1y_venom", "rotary_wing", "Helicopter", "", "venom", "belluh1yvenom|uh1y|belluh1y|uh1yvenom", "", [0, 0, 0, 0]],
    ["uh60a_black_hawk", "uh60a", "rotary_wing", "Helicopter", "bctrghelitransport01assaultf|bctrghelitransport01dapf|bctrghelitransport01sandf|bctrghelitransport01tropicf|bhelitransport01f|bhelitransport01camof|bhelitransport01pylonsf|bhelitransport01unarmedf|helitransport01basef|helicopter", "blackhawk|ghosthawk|ghost|mh80", "sikorskyuh60ablackhawk|uh60a|sikorskyuh60a|uh60ablack", "src_tm_1_1520_237_10", [9185, 0, 0, 210.211504]],
    ["uh60l_black_hawk", "uh60l_black_hawk", "rotary_wing", "Helicopter", "", "blackhawk", "sikorskyuh60lblackhawk|uh60l|sikorskyuh60l|uh60lblack", "", [0, 0, 0, 0]],
    ["uh60m_black_hawk", "uh60m", "rotary_wing", "", "vtxh60base", "", "sikorskyuh60mblackhawk|uh60m|sikorskyuh60m|uh60mblack", "", [0, 0, 0, 0]],
    ["uh72a_lakota", "uh72a_lakota", "rotary_wing", "Helicopter", "", "lakota", "eurocopteruh72alakota|uh72a|uh72|eurocopteruh72a|uh72alakota", "", [0, 0, 0, 0]],
    ["v22_osprey", "v22_osprey", "rotary_wing", "", "", "v22|osprey", "bellboeingv22osprey|bellboeing|boeingv22|v22osprey", "", [0, 0, 0, 0]],
    ["w3_sokol", "w3_sokol", "rotary_wing", "Helicopter", "", "sokol", "pzlw3sokol|pzlw3|w3sokol", "", [0, 0, 0, 0]],
    ["westland_sea_king", "westland_sea_king", "rotary_wing", "", "", "seaking", "westlandseaking|westlandsea", "", [0, 0, 0, 0]],
    ["wg13_lynx", "wg13_lynx", "rotary_wing", "Helicopter", "", "lynx", "westlandwg13lynx|wg13|westlandwg13|wg13lynx", "", [0, 0, 0, 0]],
    ["yak130_mitten", "yak130", "fixed_wing", "", "oplanecas02clusterf|oplanecas02f|oplanecas02dynamicloadoutf|planecas02basef", "mitten|neophron", "yakovlevyak130mitten|yak130|yakovlevyak130|yak130mitten", "", [0, 0, 0, 0]],
    ["yak38_forger", "yak38", "fixed_wing", "", "", "forger|vtol", "yakovlevyak38forger|yak38|yakovlevyak38|yak38forger", "", [0, 0, 0, 0]],
    ["z10_thunderbolt", "z10_thunderbolt", "rotary_wing", "Helicopter", "", "thunderbolt", "changhez10|z10", "", [0, 0, 0, 0]],
    ["z19_thunderbolt", "z19_thunderbolt", "rotary_wing", "Helicopter", "", "thunderbolt", "harbinz19|z19", "", [0, 0, 0, 0]],
    ["z20_black_eagle", "z20_black_eagle", "rotary_wing", "Helicopter", "", "blackeagle", "harbinz20|z20", "", [0, 0, 0, 0]],
    ["z8_haoyang", "z8_haoyang", "rotary_wing", "Helicopter", "", "haoyang", "harbinz8haoyang|harbinz8|z8haoyang", "", [0, 0, 0, 0]],
    ["z9_haitun", "z9_haitun", "rotary_wing", "Helicopter", "", "haitun", "harbinz9haitun|harbinz9|z9haitun", "", [0, 0, 0, 0]]
];

// Family rows. A family entry names a family and no mark, so it is
// identity-only and lives in its own table: no layer above can reach it,
// and the last layer alone reads it. The columns are the ones above.
private _families = [
    ["ah1_family", "ah1_family", "rotary_wing", "", "", "", "ah1", "", [0, 0, 0, 0]],
    ["ch47_family", "ch47_family", "rotary_wing", "", "", "", "ch47", "", [0, 0, 0, 0]],
    ["ch53_family", "ch53_family", "rotary_wing", "", "", "", "ch53", "", [0, 0, 0, 0]],
    ["hh60_family", "hh60_family", "rotary_wing", "", "", "", "hh60", "", [0, 0, 0, 0]],
    ["mi24_family", "mi24_family", "rotary_wing", "", "", "", "mi24", "", [0, 0, 0, 0]],
    ["mig29_family", "mig29_family", "fixed_wing", "", "", "", "mig29", "", [0, 0, 0, 0]],
    ["su25_family", "su25_family", "fixed_wing", "", "", "", "su25", "", [0, 0, 0, 0]],
    ["uh1_family", "uh1_family", "rotary_wing", "", "", "", "uh1", "", [0, 0, 0, 0]],
    ["uh60_family", "uh60_family", "rotary_wing", "", "", "", "uh60", "", [0, 0, 0, 0]]
];

// [catalogue_id, variant_id, vehicle_type, confidence, matched_by,
//  source_record_id, value_row]
private _result = {
    params ["_row", "_confidence", "_layer"];
    [_row select 0, _row select 1, _row select 2, _confidence, _layer,
     _row select 7, _row select 8]
};

private _typeAnswer = {
    // The type rung. It answers the KIND of the class when no identity layer
    // can, and it is also what a tie falls to: two candidate marks name no
    // single mark, but the engine still states the kind. It names a kind,
    // never a model, and carries no figure.
    //
    // Nothing above named the aircraft, so the ENGINE kind is the answer: the config's own taxonomy says whether this is a
    // helicopter, a fixed-wing aircraft or an unmanned aerial vehicle. A type
    // entry names a kind, never a model, and carries no figure.
    params ["_className"];
    private _kind = "";
    if (_className isKindOf "Helicopter") then { _kind = "helicopter" };
    if ((_kind == "") && {_className isKindOf "Plane"}) then { _kind = "fixed-wing aircraft" };
    if ((_kind == "") && {_className isKindOf "UAV"}) then { _kind = "unmanned aerial vehicle" };
    if (_kind == "") then { _kind = "aircraft" };
    [_kind, "", "", 8, "type", "", []]
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
if ((count _candidates) > 1) exitWith { [_className] call _typeAnswer };

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
if ((count _candidates) > 1) exitWith { [_className] call _typeAnswer };

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
if ((count _candidates) > 1) exitWith { [_className] call _typeAnswer };

// Layer 4: inheritance. The class isKindOf the entry class token.
_candidates = [];
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    if (_token != "" && {_className isKindOf _token}) then {
        _candidates pushBack _x;
    };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 4, "inheritance"] call _result };
if ((count _candidates) > 1) exitWith { [_className] call _typeAnswer };

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

// Layer 7: family. The class text names a family and no mark. A family row
// is identity-only, so it carries no class, no alias and no value, and it
// is read here alone. The scan is the keyword rule, over the declared
// family designations. Exactly one candidate answers: two families in one
// query name no single family, and none names nothing.
_candidates = [];
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _hit = false;
    {
        if ((count _x) >= 3 && {_query find _x >= 0}) then { _hit = true; };
    } forEach (_keywords splitString "|");
    if (_hit) then { _candidates pushBack _row; };
} forEach _families;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 7, "family"] call _result };

[_className] call _typeAnswer
