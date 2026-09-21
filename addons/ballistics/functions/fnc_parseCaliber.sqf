#include "..\script_component.hpp"
/*
Caliber parser (issue #167).

Extracts the CARTRIDGE CALIBER from an ammo/weapon classname and
returns [caliberMm, caliberName, matchConfidence].

Two resolution layers (the clothing-classifier pattern):

  1. ALIAS MATCH: the classname contains a known alias of a canonical
     caliber.  Each canonical caliber carries ALL its naming forms:
       9mm        <- 9x19, 9mm, 9_19, 9x21, 9mm_
       .45 ACP    <- 45acp, 45_acp, 45, .45, 11.43
       5.56       <- 556, 5.56, 556x45, 5_56, 223
       7.62 NATO  <- 762x51, 7.62x51, 308, .308
       .50 BMG    <- 50bmg, 127x99, 12.7x99, 50, .50
     The aliases include the OTHER UNITS the caliber is named in
     (mm, hundredths of an inch, the cartridge name).

  2. NUMERIC CONVERSION: a numeric token not matched by an alias is
     interpreted in the units the surrounding text implies and
     converted to mm:
       "9x19" -> 9 mm (the leading number is the mm diameter)
       "45"   -> 0.45 in = 11.43 mm (the classic inch-caliber form)
       "556"  -> 5.56 mm (the 3-digit mm form, decimal dropped)
       "300"  -> 0.300 in = 7.62 mm (.300 BLK / .300 Win)
     The converted mm then matches the canonical caliber with the
     nearest diameter, so a naming AEE has never seen still resolves.

A caliber that neither layer resolves returns [0, "", 0] - the caller
falls back to its default.

Arguments:
  0: name (STRING, the classname to parse)

Returns [caliberMm, caliberName, matchConfidence]:
  matchConfidence: 1 = exact alias, 2 = numeric conversion.
*/
params [["_name", "", [""]]];
if (_name == "") exitWith { [0, "", 0] };

private _n = toLower _name;

// ─── Layer 1: the alias table ────────────────────────────────────────────
// [caliberMm, canonicalName, [aliases...]].  The aliases include the
// alternate-unit names (mm, inch, cartridge).
private _CALIBERS = [
    // Small arms (the pistol/rifle family)
    [4.6,   "4.6x30",      ["46x30", "4.6x30", "4.6mm"]],
    [5.45,  "5.45x39",     ["545x39", "5.45x39", "5.45"]],
    [5.56,  "5.56x45",     ["556x45", "5.56x45", "5.56", "223", "5.56mm"]],
    [5.7,   "5.7x28",      ["57x28", "5.7x28", "5.7"]],
    [6.5,   "6.5 Grendel", ["65grendel", "6.5grendel", "6.5", "6arc", "6.5creedmoor"]],
    [6.8,   "6.8 SPC",     ["68spc", "6.8spc", "6.8"]],
    [7.62,  "7.62x39",     ["762x39", "7.62x39"]],
    [7.62,  "7.62x51",     ["762x51", "7.62x51", "308", "7.62nato"]],
    [7.62,  "7.62x54R",    ["762x54", "7.62x54"]],
    [7.62,  "7.62x25",     ["762x25", "7.62x25", "7.62tokarev"]],
    [7.82,  ".300 BLK",    ["300blk", "300_blackout", "300blk", "300aac", "300"]],
    [7.82,  ".308 Win",    ["308", "308win"]],
    [7.92,  "7.92x57",     ["792x57", "7.92x57", "8mm"]],
    [8.58,  ".338 LM",     ["338lm", "338", "8.6", "338lapua", "338norma"]],
    [9.01,  "9mm",         ["9x19", "9mm", "9_19", "9x21", "9mm_", "9mmx19"]],
    [9.27,  "9x18 Makarov",["9x18", "9mm_makarov", "9mak"]],
    [10.16, ".40 S&W",     ["40sw", "40_s_w", "40", ".40"]],
    [11.18, ".44 Mag",     ["44mag", "44", ".44"]],
    [11.43, ".45 ACP",     ["45acp", "45_acp", "45", ".45", "11.43"]],
    [12.7,  ".50 BMG",     ["50bmg", "127x99", "12.7x99", "50", ".50"]],
    [12.7,  "12.7x108",    ["127x108", "12.7x108"]],
    [14.5,  "14.5x114",    ["145x114", "14.5x114"]],
    [18.5,  "12 Gauge",    ["12gauge", "12_ga", "127x76", "shotgun"]],
    [30.0,  "30mm",        ["30mm", "30x173", "30x113"]],
    [25.0,  "25mm",        ["25mm", "25x137"]],
    [20.0,  "20mm",        ["20mm", "20x102"]]
];

// Layer 1 result (empty = no alias matched; the numeric conversion follows).
private _aliasResult = [];
{
    private _caliberRow = _x;        // [caliberMm, canonicalName, aliases]
    private _aliases = _x select 2;
    {
        if (_n find _x >= 0) exitWith {
            _aliasResult = [_caliberRow select 0, _caliberRow select 1, 1];
        };
    } forEach _aliases;
} forEach _CALIBERS;
if (_aliasResult isNotEqualTo []) exitWith { _aliasResult };

// ─── Layer 2: the numeric conversion ─────────────────────────────────────
// A numeric token in the name, interpreted in the implied units:
//   "NNxNN" (caliber x case): the leading NN is the mm diameter.
//   "NNN" (3-digit): 45/50/338/300 -> hundredths of an inch -> mm;
//                   556/762/545/127 -> the mm diameter, decimal dropped.
// Extract the numeric tokens (the first digit run in the name).
private _matches = _n splitString "0123456789";
private _num = "";
if (count _matches > 1) then {
    // The first digit run sits between the first two non-digit splits.
    private _before = _matches select 0;
    private _after = _matches select 1;
    private _start = (count _before);
    private _len = (count _n) - _start - (count _after);
    if (_len > 0) then { _num = _n select [_start, _len]; };
};
if (_num == "") exitWith { [0, "", 0] };

private _val = parseNumber _num;

// Interpret the token.  A decimal (5.56, 7.62) is already mm.  A 3-digit
// token is the ambiguous case: the classic inch calibers (.300, .338,
// .357, .380, .400, .440, .450, .500) are inch-hundredths; the rifle
// calibers (556, 762, 545, 127) are the mm diameter with the decimal
// dropped.  An "x" context with a 3-digit leading number is the mm form
// (556x45 -> 5.56).
private _mm = if (_num find "." >= 0) then {
    _val
} else {
    if (_val >= 200 && _val < 600) then {
        if (_val == 300 || _val == 338 || _val == 357 || _val == 380
            || _val == 400 || _val == 440 || _val == 450 || _val == 500) then {
            _val * 0.0254 * 10   // .300 in -> 7.62 mm
        } else {
            _val / 100   // 556 -> 5.56 mm (the mm-dropped form)
        }
    } else {
        _val   // 9, 45, 12 -> mm
    }
};

// Match the converted mm to the nearest canonical caliber (within 0.5 mm).
private _best = [0, "", 2];
private _bestDiff = 999;
{
    private _diff = abs ((_x select 0) - _mm);
    if (_diff < _bestDiff && _diff < 0.5) then {
        _bestDiff = _diff;
        _best = [_x select 0, _x select 1, 2];
    };
} forEach _CALIBERS;

_best
