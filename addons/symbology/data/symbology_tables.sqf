/*
NATO/OPFOR symbology category tables (generated).

This file is GENERATED. The generator tools/validation/gen_symbology_tables.py
writes it from the validated source data/symbology/symbology_tables.json. Do
not edit it by hand. Edit the source and regenerate it.

The seven sections are, in order:

  0  marker type prefixes -> the family default category
  1  marker type suffixes -> the category
  2  exact marker names -> the category
  3  CfgVehicles vehicleClass and unitClass values -> the category
  4  affiliation -> the CfgMarkers family token (b, o, n, u)
  5  class category -> the CfgMarkers glyph token (inf, armor, ...)
  6  class category -> the battle dimension (land, air, sea, ...)

Each row is [name, category, grade, source]. For sections 0 to 3 the category
is one of the NATO APP-6(C) frame grammar classes. For section 4 the category
is a family token, for section 5 a glyph token and for section 6 a battle
dimension. No value is invented: every row is sourced or derived and carries
its source.
*/
[
    [
        ["b_", "unknown", "derived", "Arma 3 CfgMarkers BLUFOR family; the suffix selects the category"],
        ["o_", "unknown", "derived", "Arma 3 CfgMarkers OPFOR family; the suffix selects the category"],
        ["n_", "unknown", "derived", "Arma 3 CfgMarkers Independent family; the suffix selects the category"],
        ["c_", "unknown", "derived", "Arma 3 CfgMarkers Civilian family; the suffix selects the category"],
        ["hd_", "waypoint", "derived", "Arma 3 CfgMarkers header and objective family; a point marker"],
        ["flag_", "unknown", "derived", "Arma 3 CfgMarkers national and faction flags; no function glyph"],
        ["Contact_", "unknown", "derived", "Arma 3 Contact DLC draw shapes; no function glyph"],
        ["GroundSupport_", "support", "derived", "Arma 3 CfgMarkers fire-support family"],
        ["group_", "unknown", "derived", "Arma 3 CfgMarkers group-size family; no function glyph"],
        ["loc_", "installation", "derived", "Arma 3 CfgMarkers location family; a place marker"]
    ],
    [
        ["inf", "infantry", "sourced", "APP-6(C) infantry; Arma 3 b_inf family"],
        ["armor", "armour", "sourced", "APP-6(C) armour; Arma 3 b_armor family"],
        ["mech_inf", "armour", "derived", "mechanised infantry; a tracked carrier, APP-6(C) armour"],
        ["motor_inf", "motorised", "derived", "motorised infantry; wheeled, APP-6(C) motorised"],
        ["art", "artillery", "sourced", "APP-6(C) artillery; Arma 3 b_art family"],
        ["air", "rotary", "derived", "Arma 3 generic air marker, drawn as a helicopter"],
        ["plane", "fixed_wing", "derived", "Arma 3 b_plane family; a fixed-wing aircraft"],
        ["heli", "rotary", "derived", "Arma 3 b_heli family; a rotary-wing aircraft"],
        ["naval", "sea_surface", "derived", "Arma 3 b_naval family; a surface vessel"],
        ["installation", "installation", "sourced", "APP-6(C) installation; Arma 3 b_installation family"],
        ["hq", "hq", "sourced", "APP-6(C) headquarters; Arma 3 b_hq family"],
        ["med", "medical", "sourced", "APP-6(C) medical; Arma 3 b_med family"],
        ["recon", "recon", "derived", "APP-6(C) reconnaissance"],
        ["support", "support", "derived", "APP-6(C) support"],
        ["unknown", "unknown", "derived", "APP-6(C) unknown; Arma 3 b_unknown family"],
        ["dot", "waypoint", "derived", "Arma 3 hd_dot; a generic point marker"]
    ],
    [
        ["Empty", "unknown", "derived", "Arma 3 empty marker class"],
        ["EmptyIcon", "unknown", "derived", "Arma 3 empty icon marker class"],
        ["Flag", "unknown", "derived", "Arma 3 base flag marker class"],
        ["KIA", "unknown", "derived", "Arma 3 KIA marker class"]
    ],
    [
        ["Men", "infantry", "derived", "Arma 3 vehicleClass Men; dismounted infantry"],
        ["Car", "motorised", "derived", "Arma 3 vehicleClass Car; a wheeled vehicle"],
        ["Armored", "armour", "derived", "Arma 3 vehicleClass Armored; a tracked vehicle"],
        ["Air", "rotary", "derived", "Arma 3 vehicleClass Air; drawn as a helicopter"],
        ["Ship", "sea_surface", "derived", "Arma 3 vehicleClass Ship; a surface vessel"],
        ["Submarine", "subsurface", "derived", "Arma 3 vehicleClass Submarine"],
        ["Support", "support", "derived", "Arma 3 vehicleClass Support"],
        ["Static", "artillery", "derived", "Arma 3 vehicleClass Static; a static weapon"],
        ["Structures", "installation", "derived", "Arma 3 vehicleClass Structures"],
        ["Strategic", "installation", "derived", "Arma 3 vehicleClass Strategic"],
        ["Ammo", "supply", "derived", "Arma 3 vehicleClass Ammo"],
        ["Reammo", "supply", "derived", "Arma 3 vehicleClass Reammo"],
        ["Repair", "support", "derived", "Arma 3 vehicleClass Repair"],
        ["Fuel", "supply", "derived", "Arma 3 vehicleClass Fuel"],
        ["Mines", "unknown", "derived", "Arma 3 vehicleClass Mines"]
    ],
    [
        ["friend", "b", "derived", "Arma 3 CfgMarkers NATO BLUFOR family b_; icon \A3\ui_f\data\map\markers\nato\b_*.paa"],
        ["hostile", "o", "derived", "Arma 3 CfgMarkers NATO OPFOR family o_; icon \A3\ui_f\data\map\markers\nato\o_*.paa"],
        ["neutral", "n", "derived", "Arma 3 CfgMarkers NATO Independent family n_; icon \A3\ui_f\data\map\markers\nato\n_*.paa"],
        ["unknown", "u", "derived", "AEE unknown-affiliation family; Arma 3 ships no u_ family, so the AEE u_ textures are produced"]
    ],
    [
        ["infantry", "inf", "sourced", "APP-6(C) infantry; Arma 3 b_inf"],
        ["armour", "armor", "sourced", "APP-6(C) armour; Arma 3 b_armor"],
        ["motorised", "motor_inf", "derived", "APP-6(C) motorised; Arma 3 b_motor_inf"],
        ["artillery", "art", "sourced", "APP-6(C) artillery; Arma 3 b_art"],
        ["engineer", "eng", "derived", "APP-6(C) engineer; no Arma 3 glyph, AEE produces AEE_*_eng.paa"],
        ["signal", "sig", "derived", "APP-6(C) signal; no Arma 3 glyph, AEE produces AEE_*_sig.paa"],
        ["medical", "med", "sourced", "APP-6(C) medical; Arma 3 b_med"],
        ["supply", "sup", "derived", "APP-6(C) supply; no Arma 3 glyph, AEE produces AEE_*_sup.paa"],
        ["support", "support", "derived", "APP-6(C) support; Arma 3 b_support"],
        ["recon", "recon", "derived", "APP-6(C) reconnaissance; Arma 3 b_recon"],
        ["air_defence", "antiair", "derived", "APP-6(C) air defence; Arma 3 b_antiair"],
        ["fixed_wing", "plane", "derived", "APP-6(C) fixed wing; Arma 3 b_plane"],
        ["rotary", "air", "derived", "APP-6(C) rotary wing; Arma 3 generic b_air"],
        ["uav", "uav", "derived", "APP-6(C) unmanned aerial; Arma 3 b_uav"],
        ["sea_surface", "naval", "derived", "APP-6(C) sea surface; Arma 3 b_naval"],
        ["subsurface", "sub", "derived", "APP-6(C) subsurface; no Arma 3 glyph, AEE produces AEE_*_sub.paa"],
        ["installation", "installation", "sourced", "APP-6(C) installation; Arma 3 b_installation"],
        ["hq", "hq", "sourced", "APP-6(C) headquarters; Arma 3 b_hq"],
        ["waypoint", "dot", "derived", "AEE waypoint; no Arma 3 NATO glyph, AEE produces AEE_*_dot.paa"],
        ["unknown", "unknown", "derived", "APP-6(C) unknown; Arma 3 b_unknown"]
    ],
    [
        ["infantry", "land", "sourced", "APP-6(C) infantry; Arma 3 b_inf"],
        ["armour", "land", "sourced", "APP-6(C) armour; Arma 3 b_armor"],
        ["motorised", "land", "derived", "APP-6(C) motorised; Arma 3 b_motor_inf"],
        ["artillery", "land", "sourced", "APP-6(C) artillery; Arma 3 b_art"],
        ["engineer", "land", "derived", "APP-6(C) engineer; no Arma 3 glyph, AEE produces AEE_*_eng.paa"],
        ["signal", "land", "derived", "APP-6(C) signal; no Arma 3 glyph, AEE produces AEE_*_sig.paa"],
        ["medical", "land", "sourced", "APP-6(C) medical; Arma 3 b_med"],
        ["supply", "land", "derived", "APP-6(C) supply; no Arma 3 glyph, AEE produces AEE_*_sup.paa"],
        ["support", "land", "derived", "APP-6(C) support; Arma 3 b_support"],
        ["recon", "land", "derived", "APP-6(C) reconnaissance; Arma 3 b_recon"],
        ["air_defence", "land", "derived", "APP-6(C) air defence; Arma 3 b_antiair"],
        ["fixed_wing", "air", "derived", "APP-6(C) fixed wing; Arma 3 b_plane"],
        ["rotary", "air", "derived", "APP-6(C) rotary wing; Arma 3 generic b_air"],
        ["uav", "air", "derived", "APP-6(C) unmanned aerial; Arma 3 b_uav"],
        ["sea_surface", "sea", "derived", "APP-6(C) sea surface; Arma 3 b_naval"],
        ["subsurface", "subsurface", "derived", "APP-6(C) subsurface; no Arma 3 glyph, AEE produces AEE_*_sub.paa"],
        ["installation", "installation", "sourced", "APP-6(C) installation; Arma 3 b_installation"],
        ["hq", "land", "sourced", "APP-6(C) headquarters; Arma 3 b_hq"],
        ["waypoint", "land", "derived", "AEE waypoint; no Arma 3 NATO glyph, AEE produces AEE_*_dot.paa"],
        ["unknown", "land", "derived", "APP-6(C) unknown; Arma 3 b_unknown"]
    ]
]
