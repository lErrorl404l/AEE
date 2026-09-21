#include "..\script_component.hpp"
/*
Ammunition database - the hierarchical keyword matcher (issue #167).

Resolves the REAL ballistic properties of a round from its CfgAmmo
classname and returns [realMV, bcG1, bcG7, caliberMm, massG, dragModel].

The matcher works like the equipment library (clothing etc): keyword
layers that go DEEPER when they match, BASE level otherwise.

  Layer 1 - CALIBER:  the cartridge signal (556x45, 762x51, 545x39,
    9x19, 127x99, 300blk ...) selects the caliber's base values.
  Layer 2 - PROJECTILE: the specific round name (M855, M855A1, M995,
    Mk262, M80, M118LR, 7N22 ...) overrides the base with the round's
    own researched MV + BC.  A 5.56 M855 and a 5.56 Mk262 are
    DIFFERENT rounds - each has its own values under the 5.56 caliber.
  Layer 3 - TYPE: the round-type modifier (subsonic, AP, tracer)
    further adjusts (a subsonic round flies slower, a tracer slightly
    slower).

If a layer does not match, the round stays at the previous layer's
base - the generic caliber values.  This is the "if there is more
information it goes deeper, if not it is base level" behaviour.

Values are VERIFIED from the researched ammunition tables (issue #167
sources: NATO EPVAT / STANAG 4172/2310, MIL-C-50/MIL-DTL-10190E, Soviet
ballistics, Applied Ballistics ABDOC) and cross-checked against the
ABE real-weapons seed (ir_ammo.tsv per-projectile BCs).

Arguments:
  0: ammo (STRING, the CfgAmmo classname, default "")

Returns [realMV, bcG1, bcG7, caliberMm, massG, dragModel].
*/
params [["_ammo", "", [""]]];
if (_ammo == "") exitWith { [948, 0.307, 0.151, 5.56, 4.0, 7] };

// The match signal: the classname PLUS the readable displayName (the
// ACE arsenal name - "5.56mm M855A1" carries the same projectile
// signal the mod's opaque classname hides).  The displayName comes
// from the first magazine using this ammo (the engine's readable name).
private _a = toLower _ammo;
private _disp = "";
{
    if (getText (configFile >> "CfgMagazines" >> configName _x >> "ammo") == _ammo) exitWith {
        _disp = toLower (getText (configFile >> "CfgMagazines" >> configName _x >> "displayName"));
    };
} forEach ((configFile >> "CfgMagazines") call BIS_fnc_returnChildren);
_a = _a + " " + _disp;

// ─── Layer 1: the CALIBER base ───────────────────────────────────────────
// [caliberMm, massG, refMV at the reference barrel, bcG1, bcG7, drag].
// The generic caliber values are the researched family anchors; the
// projectile layer overrides them.  The classname is parsed FIRST
// (fnc_parseCaliber: the alias + numeric-conversion matcher - 9x19 =
// 9mm, 45acp = .45 in = 11.43 mm, 300 BLK = 7.62 mm); the fast switch
// below handles the common forms, and the parser's conversion catches
// the names the switch misses.
private _parsed = [_ammo] call FUNC(parseCaliber);
private _base = [5.56, 4.0, 948, 0.307, 0.151, 7];
switch (true) do {
    case (_a find "556x45" >= 0 || _a find "5.56" >= 0):  { _base = [5.56, 4.0, 948, 0.307, 0.151, 7]; };
    case (_a find "545x39" >= 0 || _a find "5.45" >= 0):  { _base = [5.45, 3.4, 880, 0.300, 0.168, 7]; };
    case (_a find "762x51" >= 0 || _a find "7.62x51" >= 0): { _base = [7.62, 9.5, 838, 0.393, 0.200, 7]; };
    case (_a find "762x39" >= 0 || _a find "7.62x39" >= 0): { _base = [7.62, 8.0, 710, 0.279, 0, 1]; };
    case (_a find "762x54" >= 0 || _a find "7.62x54" >= 0): { _base = [7.62, 9.6, 820, 0.377, 0.200, 7]; };
    case (_a find "9x21" >= 0 || _a find "9x19" >= 0 || _a find "9mm" >= 0): { _base = [9.01, 8.0, 351, 0.149, 0, 1]; };
    case (_a find "127x99" >= 0 || _a find "12.7x99" >= 0 || _a find "50bmg" >= 0): { _base = [12.7, 42.8, 885, 0.670, 0.340, 7]; };
    case (_a find "127x108" >= 0 || _a find "12.7x108" >= 0): { _base = [12.7, 48.2, 818, 0.600, 0.340, 7]; };
    case (_a find "338" >= 0):                               { _base = [8.58, 16.2, 899, 0.756, 0.320, 7]; };
    case (_a find "300blk" >= 0 || _a find "300_blackout" >= 0): { _base = [7.82, 8.1, 675, 0.338, 0, 1]; };
    case (_a find "65x39" >= 0 || _a find "6.5" >= 0 || _a find "6arc" >= 0 || _a find "68spc" >= 0): { _base = [6.71, 7.8, 790, 0.500, 0.196, 7]; };
    case (_a find "45acp" >= 0 || _a find "11.43" >= 0): { _base = [11.48, 14.9, 255, 0.163, 0, 1]; };
    case (_a find "127x76" >= 0 || _a find "12gauge" >= 0): { _base = [18.5, 28.3, 470, 0.060, 0, 1]; };
    case (_a find "762x25" >= 0 || _a find "7.62x25" >= 0): { _base = [7.62, 5.5, 488, 0.159, 0, 1]; };
    case (_a find "57x28" >= 0 || _a find "5.7x28" >= 0):    { _base = [5.7, 2.0, 715, 0.233, 0, 1]; };
    case (_a find "9x18" >= 0):       { _base = [9.27, 6.1, 315, 0.140, 0, 1]; };
    default                                                  { _base = [5.56, 4.0, 948, 0.307, 0.151, 7]; };
};

// The parser override: if it resolved a caliber the switch missed
// (the numeric-conversion names - 45acp = .45 in = 11.43 mm, 300 =
// 7.62 mm), the base adopts the parsed caliber's values.  The switch
// values are keyed by the canonical name.
if ((_parsed select 2) > 0 && (_parsed select 0) != (_base select 0)) then {
    private _pCal = _parsed select 1;
    _base = switch (true) do {
        case (_pCal == "5.56x45"):   { [5.56, 4.0, 948, 0.307, 0.151, 7]; };
        case (_pCal == "5.45x39"):   { [5.45, 3.4, 880, 0.300, 0.168, 7]; };
        case (_pCal == "7.62x51"):   { [7.62, 9.5, 838, 0.393, 0.200, 7]; };
        case (_pCal == "7.62x39"):   { [7.62, 8.0, 710, 0.279, 0, 1]; };
        case (_pCal == "7.62x54R"):  { [7.62, 9.6, 820, 0.377, 0.200, 7]; };
        case (_pCal == "9mm"):       { [9.01, 8.0, 351, 0.149, 0, 1]; };
        case (_pCal == ".50 BMG"):   { [12.7, 42.8, 885, 0.670, 0.340, 7]; };
        case (_pCal == "12.7x108"):  { [12.7, 48.2, 818, 0.600, 0.340, 7]; };
        case (_pCal == ".338 LM"):   { [8.58, 16.2, 899, 0.756, 0.320, 7]; };
        case (_pCal == ".300 BLK"):  { [7.82, 8.1, 675, 0.338, 0, 1]; };
        case (_pCal == "6.5 Grendel"): { [6.71, 7.8, 790, 0.500, 0.196, 7]; };
        case (_pCal == ".45 ACP"):   { [11.48, 14.9, 255, 0.163, 0, 1]; };
        case (_pCal == "12 Gauge"):  { [18.5, 28.3, 470, 0.060, 0, 1]; };
        default                      { _base };
    };
};

// ─── Layer 2: the PROJECTILE (the specific round overrides the base) ─────
// Each is [name keyword, mv, bcG1, bcG7, massG].  MOST SPECIFIC FIRST.
private _PROJ = [
    // 5.56
    ["m855a1", 961, 0.308, 0.152, 4.0], ["m995", 1013, 0.310, 0.310, 4.0],
    ["mk262", 838, 0.362, 0.197, 5.0], ["mk318", 915, 0.307, 0.151, 4.0],
    ["m855", 948, 0.307, 0.151, 4.0], ["m193", 993, 0.243, 0.118, 3.6],
    ["ss109", 948, 0.307, 0.151, 4.0], ["tsx", 940, 0.280, 0, 4.0],
    // 5.45
    ["7n22", 890, 0, 0.174, 3.7], ["7n10", 880, 0, 0.176, 3.6],
    ["7n6", 880, 0, 0.168, 3.4],
    // 7.62 NATO
    ["m118lr", 786, 0.496, 0.243, 11.3], ["mk316", 786, 0.496, 0.243, 11.3],
    ["mk319", 860, 0.377, 0.377, 8.4], ["m993", 930, 0.430, 0.359, 8.3],
    ["m80", 838, 0.393, 0.200, 9.5], ["m61", 833, 0.419, 0.218, 9.4],
    // 7.62x39
    ["m67", 733, 0.300, 0, 8.0], ["m43", 710, 0.294, 0, 7.9],
    // 7.62x54R
    ["7n1", 830, 0.400, 0.200, 9.8], ["lps", 820, 0.377, 0.200, 9.6],
    // .50 BMG
    ["slap", 1219, 0.670, 0.670, 23.3], ["amax", 882, 1.050, 0.560, 48.6],
    ["m33", 885, 0.670, 0.340, 42.8], ["m903", 1219, 0.670, 0.670, 23.3],
    // 12.7x108
    ["b32", 818, 0.600, 0.340, 48.2],
    // .338
    ["250gr", 899, 0.756, 0.320, 16.2], ["300gr", 823, 0.605, 0.265, 19.4],
    // .300 BLK
    ["220otmsub", 320, 0.608, 0.235, 14.3], ["125otm", 675, 0.338, 0, 8.1],
    ["115umc", 700, 0.300, 0, 7.5],
    // 9mm (weight + type)
    ["147fmj", 305, 0.155, 0, 9.5], ["147jhp", 300, 0.150, 0, 9.5],
    ["124fmj", 351, 0.149, 0, 8.0], ["124jhp", 340, 0.145, 0, 8.0],
    ["115fmj", 365, 0.145, 0, 7.5], ["115jhp", 355, 0.140, 0, 7.5],
    ["135ftx", 330, 0.152, 0, 8.7], ["98frang", 390, 0.120, 0, 6.4],
    // .45 ACP
    ["230fmj", 255, 0.163, 0, 14.9], ["230ftx", 260, 0.165, 0, 14.9],
    ["230hp", 250, 0.160, 0, 14.9], ["200fmj", 275, 0.150, 0, 13.0],
    ["200hp", 270, 0.148, 0, 13.0], ["185fmj", 290, 0.145, 0, 12.0],
    ["185hp", 285, 0.142, 0, 12.0], ["185ftx", 295, 0.148, 0, 12.0]
];

private _mv = _base select 2;
private _bc1 = _base select 3;
private _bc7 = _base select 4;
private _mass = _base select 1;
{
    if (_a find (_x select 0) >= 0) exitWith {
        _mv = _x select 1;
        _bc1 = _x select 2;
        _bc7 = _x select 3;
        _mass = _x select 4;
    };
} forEach _PROJ;

// ─── Layer 3: the TYPE modifiers ─────────────────────────────────────────
// A subsonic round flies below ~340 m/s; a tracer slightly slower.
if (_a find "sub" >= 0 && _mv > 400) then { _mv = 320; };
if (_a find "tracer" >= 0) then { _mv = _mv * 0.99; };

// ─── The engine-measured bullet (the physical anchor) ────────────────────
// The engine exposes the bullet's own physical data in CfgAmmo: the
// caliber (the diameter the engine uses for penetration) and the hit
// (the kinetic-energy proxy for the mass).  These are the MEASURED
// bullet - the closest the engine has to the model's bullet.  The
// database's researched diameter/mass stand when the engine value is
// missing (a rocket/shell without a caliber).
private _engCal = getNumber (configFile >> "CfgAmmo" >> _ammo >> "caliber");
if (_engCal > 0) then {
    _base set [0, _engCal];   // the engine's bullet diameter overrides
};
private _engMass = getNumber (configFile >> "CfgAmmo" >> _ammo >> "hit") * 0.5;
if (_engMass > 0) then { _mass = _engMass; };

[_mv, _bc1, _bc7, _base select 0, _mass, if (_bc7 > 0) then { 7 } else { 1 }]
