#include "..\..\script_component.hpp"
/*
Comprehensive equipment library (issue #119).

The soldier's complete signature = uniform + vest + helmet + backpack,
each with its own physics properties.  Helmets, vests and packs add
weight, ballistic armour (NIJ level), NIR reflectance, and thermal
insulation (clo).

The library is DYNAMIC: every item is classified by its classname's
FAMILY keywords (the codebase's dynamic pattern).  A mod we have never
seen resolves correctly as long as its classnames carry the family
signal (helmet/vest/pack type + era + protection class).  The keyword
tiers carry the researched values from equipment-library.md:

  weight  - kg (real issue weights, WW1 to present)
  armor   - NIJ protection level 0..3 (0 none, 1 IIA, 2 IIIA, 3 III+plates)
  nirReflectance - NIR reflectance 0..1 (the NVG signature)
  clo     - insulation (material-derived: aramid ~0.06-0.07,
            wool knit 0.30, soft armour 0.10-0.12, plate carrier
            0.15-0.18, pack 0.08-0.12)

Arguments:
  0: unit (OBJECT, default player)

Returns [weightKg, armorLevel, nirReflectance, cloTotal]:
  weightKg    - combined uniform + vest + helmet + backpack weight
  armorLevel  - the max NIJ level worn (the vest dominates)
  nirReflectance - the area-weighted NIR (uniform dominant, equipment adds)
  cloTotal    - the combined insulation
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { [8.0, 0, 0.40, 0.75] };

// The uniform properties (the existing resolver).
private _uniformProps = [_unit] call FUNC(getClothingInsulation);   // [clo, alpha, nir, perm, emiss]
private _uniformClo = _uniformProps select 0;
private _uniformNir = _uniformProps select 2;

// The vest + helmet + backpack classnames (the slot disambiguates the
// item type: headgear/vest are CfgWeapons classes, backpacks are
// CfgVehicles classes - but classification needs only the name).
private _vestItem = vest _unit;
private _helmetItem = headgear _unit;
private _packItem = backpack _unit;

// ─── Vest: NIJ-armour plate carriers dominate armour/weight ──────────────
// Historical flak (M-1951/52, M-69, M-12) were unrated soft nylon;
// PASGT-era soft is IIIA.  Plate carriers (IBA/IOTV/SPCS/CIRAS/CPC/6B*)
// stop rifle ball with plates.
private _vestDef = [2.5, 2, 0.38, 0.10];
private _vest = _vestDef;
if (_vestItem != "") then {
    private _v = toLower _vestItem;
    _vest = switch (true) do {
        // Russian 6B45 (Ratnik, 2015): GOST 5a/6a ~III/IV, 8-13 kg.
        case (_v find "6b45" >= 0):      { [9.0, 3, 0.40, 0.15] };
        // Russian 6B43 (Zabralo-Sh): GOST 6a ~IV, 9-13 kg.
        case (_v find "6b43" >= 0):      { [11.0, 3, 0.40, 0.15] };
        // Russian 6B23 (2003): aramid + steel/ceramic, III-IV, 7.9 kg.
        case (_v find "6b23" >= 0):      { [7.9, 3, 0.40, 0.14] };
        // Russian 6B13 (Zabralo, 1999): ceramic, ~III, 7-11 kg.
        case (_v find "6b13" >= 0):      { [9.0, 3, 0.40, 0.14] };
        // Russian 6B2 (1981): titanium + aramid, ~IIIA, 4.5 kg.
        case (_v find "6b2" >= 0):       { [4.5, 2, 0.40, 0.12] };
        // Russian 6B3T (1983): titanium plates, ~III, 8-12 kg.
        case (_v find "6b3" >= 0):       { [10.0, 3, 0.40, 0.13] };
        // Russian 6B4 (1985): ceramic/boron tiles, ~III, 7-12 kg.
        case (_v find "6b4" >= 0):       { [9.5, 3, 0.40, 0.13] };
        // Russian 6B5 (1986): series, ~II-IIIA soft to ~III plates,
        // 3-11.5 kg by variant.
        case (_v find "6b5" >= 0):       { [7.0, 2, 0.40, 0.13] };
        // Russian 6B11/6B12/6B17/6B18 (Zabralo soft, ~IIIA, 5-7 kg).
        case (_v find "6b11" >= 0 ||
              _v find "6b12" >= 0 ||
              _v find "6b17" >= 0 ||
              _v find "6b18" >= 0):      { [5.0, 2, 0.40, 0.12] };
        // US IOTV (2007): IIIA soft + ESAPI plates, 4.5 kg bare
        // (TM 10-8470-208-10) + the SPC (modular scalable plate carrier).
        case (_v find "iotv" >= 0 ||
              _v find "spc" >= 0):       { [4.5, 3, 0.38, 0.18] };
        // US SPCS (2010): plate carrier, ~2.7 kg bare + IV plates.
        case (_v find "spcs" >= 0):      { [2.7, 3, 0.38, 0.16] };
        // US CIRAS (2001): BALCS soft + plates, ~1.8 kg carrier.
        case (_v find "ciras" >= 0):     { [3.5, 3, 0.38, 0.15] };
        // US PlateFrame / MBAV / MSV (modern plate carriers).
        case (_v find "plateframe" >= 0 ||
              _v find "mbav" >= 0 ||
              _v find "msv" >= 0):       { [5.5, 3, 0.38, 0.16] };
        // UK Osprey (2006): aramid + ceramic, ~8-9 kg bare.
        case (_v find "osprey" >= 0):    { [8.5, 3, 0.40, 0.15] };
        // UK Virtus (2016): aramid + ceramic, ~5-6 kg bare.
        case (_v find "virtus" >= 0):    { [5.5, 3, 0.40, 0.14] };
        // UK CBA/ECBA (1980s-90s): aramid soft, ~4-5 kg.
        case (_v find "ecba" >= 0 ||
              _v find "cba" >= 0):       { [4.5, 2, 0.40, 0.10] };
        // Historical flak vests (M-1951/52, M-69, M-12, Vietnam-era OTV):
        // unrated soft nylon.
        case (_v find "m1951" >= 0 ||
              _v find "m1952" >= 0 ||
              _v find "m69" >= 0 ||
              _v find "m12" >= 0 ||
              _v find "otv" >= 0):       { [3.8, 1, 0.40, 0.08] };
        // Russian 6Sh92/6Sh117/6Sh46 (assault vest / webbing, ~2-3 kg).
        case (_v find "6sh92" >= 0 ||
              _v find "6sh117" >= 0 ||
              _v find "6sh46" >= 0):      { [2.5, 1, 0.40, 0.09] };
        // Chicom / Lifchik / Vydra (Russian chest rigs, no ballistic).
        case (_v find "chicom" >= 0 ||
              _v find "lifchik" >= 0 ||
              _v find "vydra" >= 0):      { [1.2, 0, 0.40, 0.06] };
        // Belts, suspenders, webbing, belt-mounted rigs (ALICE, 6Sh,
        // vest_commander / vest_pistol_holster): load-bearing only.
        case (_v find "belt" >= 0 ||
              _v find "suspend" >= 0 ||
              _v find "webbing" >= 0 ||
              _v find "vest_commander" >= 0 ||
              _v find "vest_pistol" >= 0): { [1.2, 0, 0.40, 0.07] };
        case (_v find "platecarrier" >= 0 ||
              _v find "cpc" >= 0):       { [5.5, 3, 0.35, 0.18] };
        case (_v find "tacvest" >= 0):      { [2.0, 2, 0.38, 0.10] };
        case (_v find "bandollier" >= 0):   { [1.0, 1, 0.40, 0.06] };
        case (_v find "chestrig" >= 0):     { [1.2, 1, 0.40, 0.07] };
        case (_v find "harness" >= 0):      { [1.5, 1, 0.40, 0.08] };
        case (_v find "rebreather" >= 0):   { [3.0, 0, 0.20, 0.15] };
        default                            { _vestDef };
    };
};

// ─── Helmet: ballistic helmets are NIJ IIIA ───────────────────────────────
// Historical steel (Stahlhelm, M1, SSh-68) unrated; Kevlar/UHMWPE
// (PASGT/ACH/MICH/LWH/ECH/6B47) IIIA; aircrew impact-only.  Weights
// from equipment-library.md.
private _helmetDef = [1.4, 2, 0.40, 0.07];
private _helmet = _helmetDef;
if (_helmetItem != "") then {
    private _h = toLower _helmetItem;
    _helmet = switch (true) do {
        // Historical steel helmets (Stahlhelm M35/M40/M42, US M1,
        // SSh-68, STSh-81, M56, Modèle 1951): unrated steel, 0.8-1.4 kg
        // by size (the family mean ~1.2 kg).
        case (_h find "m1940" >= 0 ||
              _h find "m1942" >= 0 ||
              _h find "stahlhelm" >= 0 ||
              _h find "ssh68" >= 0 ||
              _h find "ssh60" >= 0 ||
              _h find "stsh81" >= 0 ||
              _h find "m1" >= 0 ||
              _h find "m56" >= 0 ||
              _h find "m1951" >= 0):      { [1.2, 0, 0.40, 0.04] };
        // Altyn (heavy assault, titanium + aramid, ~2.1 kg with visor).
        case (_h find "altyn" >= 0):      { [2.1, 2, 0.40, 0.08] };
        // ZSh-1-2M (special-forces, ~1.2 kg shell; ~2.1 kg with visor).
        case (_h find "zsh" >= 0):        { [1.6, 2, 0.40, 0.08] };
        // TSh-4 (tanker/flight, titanium + aramid, ~1.2 kg shell).
        case (_h find "tsh4" >= 0):       { [1.3, 2, 0.40, 0.07] };
        // 6B47 (Ratnik, 2013): GOST class 2 ~IIIA, ~1.0 kg.
        case (_h find "6b47" >= 0):       { [1.0, 2, 0.40, 0.06] };
        // 6B48 (Ratnik-3, ~1.0 kg).
        case (_h find "6b48" >= 0):       { [1.0, 2, 0.40, 0.06] };
        // 6B7-1M (2000): ~1.1-1.15 kg.
        case (_h find "6b7" >= 0):        { [1.15, 2, 0.40, 0.06] };
        // 6B26/6B27 (2006): 0.95-1.25 kg by size.
        case (_h find "6b26" >= 0 ||
              _h find "6b27" >= 0):       { [1.1, 2, 0.40, 0.06] };
        // 6B28: ~1.3 kg (heavy aramid).
        case (_h find "6b28" >= 0):       { [1.3, 2, 0.40, 0.06] };
        // Russian tanker/crew (6M2, Kaska-1D): IIA-class.
        case (_h find "6m2" >= 0 ||
              _h find "kaska" >= 0):      { [1.2, 2, 0.40, 0.07] };
        // PASGT (1983, IIIA Kevlar, ~1.9 kg complete).
        case (_h find "pasgt" >= 0):      { [1.9, 2, 0.40, 0.06] };
        // MICH/ACH/LWH (modern US IIIA Kevlar, 1.36-1.72 kg).
        case (_h find "mich" >= 0 ||
              _h find "ach" >= 0 ||
              _h find "lwh" >= 0 ||
              _h find "falcon" >= 0 ||
              _h find "helmetb" >= 0 ||
              _h find "helmetia" >= 0 ||
              _h find "helmeto" >= 0 ||
              _h find "helmetleader" >= 0 ||
              _h find "helmet_kerry" >= 0 ||
              _h find "helmetspec" >= 0): { [1.5, 2, 0.40, 0.07] };
        // ECH (2013, UHMWPE, ~1.0-1.1 kg).
        case (_h find "ech" >= 0):        { [1.05, 2, 0.40, 0.06] };
        // Ops-Core FAST / Team Wendy EXFIL (high-cut IIIA, ~0.6-1.2 kg).
        case (_h find "opscore" >= 0 ||
              _h find "fast" >= 0 ||
              _h find "exfil" >= 0):      { [0.9, 2, 0.40, 0.06] };
        // CVC (combat vehicle crewman, DH-132) and aircrew impact shells.
        case (_h find "cvc" >= 0):        { [1.4, 1, 0.40, 0.05] };
        case (_h find "crew" >= 0 ||
              _h find "racing" >= 0):   { [1.0, 1, 0.40, 0.05] };
        case (_h find "pilot" >= 0 ||
              _h find "hgu" >= 0 ||
              _h find "gssh" >= 0 ||
              _h find "heli" >= 0):     { [1.1, 1, 0.45, 0.15] };
        case (_h find "watchcap" >= 0 ||
              _h find "milcap" >= 0 ||
              _h find "beanie" >= 0 ||
              _h find "ushanka" >= 0 ||
              _h find "papakha" >= 0):  { [0.1, 0, 0.30, 0.12] };
        case (_h find "boonie" >= 0 ||
              _h find "hat" >= 0 ||
              _h find "strawhat" >= 0 ||
              _h find "8point" >= 0):   { [0.2, 0, 0.40, 0.05] };
        case (_h find "bandanna" >= 0 ||
              _h find "bandana" >= 0 ||
              _h find "bandmask" >= 0 ||
              _h find "shemag" >= 0 ||
              _h find "headband" >= 0 ||
              _h find "turban" >= 0 ||
              _h find "fakeheadgear" >= 0): { [0.1, 0, 0.35, 0.04] };
        case (_h find "cap" >= 0):         { [0.15, 0, 0.38, 0.05] };
        case (_h find "beret" >= 0):       { [0.15, 0, 0.35, 0.04] };
        default                           { _helmetDef };
    };
};

// ─── Backpack: weight is the pack itself + its contents ───────────────────
// Empty weights from equipment-library.md; the engine load command adds
// the contents.  NIR/clo of the pack fabric (camo 0.40, black 0.10).
private _packDef = [5.0, 0, 0.40, 0.10];
private _pack = _packDef;
if (_packItem != "") then {
    private _b = toLower _packItem;
    _pack = switch (true) do {
        // Russian 6Sh118 (Ratnik rucksack, 60 L, 3.5 kg) + 6Sh117 vest.
        case (_b find "6sh118" >= 0 ||
              _b find "6sh117" >= 0 ||
              _b find "6b38" >= 0):      { [3.5, 0, 0.40, 0.10] };
        // Russian RD-54 (sap-perka assault pack, 16.5 L, 1.3 kg).
        case (_b find "rd54" >= 0):      { [1.3, 0, 0.40, 0.08] };
        // Russian Sidor (veshmeshok, 25-30 L) / Tortila (40 L, 2.15 kg).
        case (_b find "sidor" >= 0):     { [2.2, 0, 0.40, 0.09] };
        case (_b find "tort" >= 0):      { [2.15, 0, 0.40, 0.09] };
        // US ALICE (Large 62 L, 3.2 kg; Medium 30-33 L, lighter).
        case (_b find "alice" >= 0):     { [3.2, 0, 0.40, 0.10] };
        // US MOLLE II (Large 65.5 L, 3.6 kg; Medium 49 L, 1.6 kg).
        case (_b find "molle" >= 0):     { [3.6, 0, 0.40, 0.10] };
        // USMC ILBE (82 L, 3.6 kg, Arc'teryx) / FILBE (81 L, 4.3 kg).
        case (_b find "ilbe" >= 0):      { [3.6, 0, 0.40, 0.11] };
        case (_b find "filbe" >= 0):     { [4.3, 0, 0.40, 0.11] };
        // US Eagle Industries III (assault pack family) + Falcon II +
        // M240/M249 support packs.
        case (_b find "eagle" >= 0 ||
              _b find "falcon" >= 0 ||
              _b find "pack_slackman" >= 0 ||
              _b find "ins_pack" >= 0):  { [2.5, 0, 0.40, 0.09] };
        // UK PLCE bergen (90 L, 2.45 kg) / Virtus 90 L (3.5 kg).
        case (_b find "plce" >= 0):      { [2.45, 0, 0.40, 0.10] };
        case (_b find "virtus" >= 0):    { [3.5, 0, 0.40, 0.10] };
        // Berghaus (Munro 35 L, 1.0 kg; Vulcan 100 L).
        case (_b find "munro" >= 0 ||
              _b find "vulcan" >= 0 ||
              _b find "berghaus" >= 0):  { [2.0, 0, 0.40, 0.09] };
        // RK-SHT-30 (Russian 6Sh104-series patrol pack) + UMBTS assault
        // pack + medic bag + R-148 radio pack + RPG ammunition packs.
        case (_b find "rk_sht" >= 0 ||
              _b find "6sh104" >= 0 ||
              _b find "umbts" >= 0 ||
              _b find "medic_bag" >= 0 ||
              _b find "r148" >= 0 ||
              _b find "rpg" >= 0):       { [2.5, 0, 0.40, 0.09] };
        // Vanilla large packs: assault 3.0, tactical 3.5, field 4.0,
        // kitbag 4.0, bergen 5.0, carryall 6.0 kg (empty).
        case (_b find "assaultpack" >= 0): { [3.0, 0, 0.40, 0.10] };
        case (_b find "tacticalpack" >= 0):{ [3.5, 0, 0.40, 0.10] };
        case (_b find "fieldpack" >= 0):   { [4.0, 0, 0.40, 0.10] };
        case (_b find "kitbag" >= 0):      { [4.0, 0, 0.40, 0.10] };
        case (_b find "bergen" >= 0):      { [5.0, 0, 0.40, 0.11] };
        case (_b find "carryall" >= 0):    { [6.0, 0, 0.40, 0.12] };
        case (_b find "radiobag" >= 0):    { [2.0, 0, 0.40, 0.09] };
        // Generic rucksack/backpack fallback.
        case (_b find "backpack" >= 0 ||
              _b find "rucksack" >= 0):    { [5.0, 0, 0.40, 0.10] };
        default                        { _packDef };
    };
};
// The pack contents add their carried weight (the engine load
// command: 0..1 of the pack's max capacity).
private _packContents = load (unitBackpack _unit);

// Combine: weight sums (incl. the pack contents), armour = max (the
// vest dominates), NIR is the uniform-dominant average, clo sums.
private _weight = (_vest select 0) + (_helmet select 0) + (_pack select 0)
    + _packContents + 4.0;   // +base uniform weight
private _armor = (_vest select 1) max (_helmet select 1);
private _nir = (_uniformNir + (_vest select 2) * 0.3 + (_helmet select 2) * 0.2
    + (_pack select 2) * 0.1) / 1.6;
private _clo = _uniformClo + (_vest select 3) + (_helmet select 3) + (_pack select 3);

[_weight, _armor, _nir, _clo]
