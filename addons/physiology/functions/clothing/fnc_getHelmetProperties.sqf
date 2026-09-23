#include "..\..\script_component.hpp"
/*
Helmet properties (issue #119).

Classifies the headgear slot (CfgWeapons H_ classes) by family keywords
and returns [weight kg, armor NIJ 0..3, nirReflectance, clo].  The
values are the researched IRL figures from equipment-library.md.

Groups (sortable by country -> company -> era):
  Historical steel (WW1-WW2) | Adrian, Brodie, Stahlhelm, M1, SSh-40,
    Type 90 - unrated steel, 0.8-1.4 kg
  Cold-war steel            | SSh-68, M56, Modèle 1951/1978 - unrated
  USA military 1983-2013    | PASGT -> MICH -> ACH -> LWH -> ECH
  USA commercial 2009+      | Ops-Core FAST/MT/XP/SF -> Team Wendy
    EXFIL (high-cut IIIA)
  Russia 1990s-2015         | Altyn/ZSh (titanium+aramid) -> 6B7 ->
    6B26/27 -> 6B28 -> 6B47/48 Ratnik -> Kaska
  Aircrew                   | HGU-55/56, SPH-4B, DH-132/CVC (impact
    only), GSSH-18
  Light headwear            | boonie/cap/beret/watchcap/bandanna/
    shemagh (no armour)

Arguments:
  0: unit (OBJECT, default player)

Returns [weight, armor, nirReflectance, clo].
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { [1.4, 2, 0.40, 0.07] };

private _helmetItem = headgear _unit;
if (_helmetItem == "") exitWith { [1.4, 2, 0.40, 0.07] };

private _helmetDef = [1.4, 2, 0.40, 0.07];
private _h = toLower _helmetItem;
private _tier = switch (true) do {
    // ── Historical steel helmets (WW1-WW2) ──
    // Stahlhelm M35/M40/M42, US M1, SSh-68, STSh-81, M56, Modèle
    // 1951: unrated steel, 0.8-1.4 kg by size (the family mean ~1.2).
    case (_h find "m1940" >= 0 ||
          _h find "m1942" >= 0 ||
          _h find "stahlhelm" >= 0 ||
          _h find "ssh68" >= 0 ||
          _h find "ssh60" >= 0 ||
          _h find "stsh81" >= 0 ||
          _h find "m1" >= 0 ||
          _h find "m56" >= 0 ||
          _h find "m1951" >= 0):      { [1.2, 0, 0.40, 0.04] };
    // ── Russia: heavy special-forces (titanium + aramid) ──
    // Altyn (heavy assault, ~2.1 kg with visor).
    case (_h find "altyn" >= 0):      { [2.1, 2, 0.40, 0.08] };
    // ZSh-1-2M (special-forces, ~1.2 kg shell; ~2.1 kg with visor).
    case (_h find "zsh" >= 0):        { [1.6, 2, 0.40, 0.08] };
    // TSh-4 (tanker/flight, titanium + aramid, ~1.2 kg shell).
    case (_h find "tsh4" >= 0):       { [1.3, 2, 0.40, 0.07] };
    // ── Russia: aramid helmets ──
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
    // ── USA military ──
    // PASGT (1983, IIIA Kevlar, ~1.9 kg complete).
    case (_h find "pasgt" >= 0):      { [1.9, 2, 0.40, 0.06] };
    // MICH/ACH/LWH (modern US IIIA Kevlar, 1.36-1.72 kg) + the
    // vanilla generic ballistic helmets (H_HelmetB/IA/O/Spec are IIIA).
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
    // ── USA commercial: high-cut IIIA ──
    // Ops-Core FAST / Team Wendy EXFIL (~0.6-1.2 kg).
    case (_h find "opscore" >= 0 ||
          _h find "fast" >= 0 ||
          _h find "exfil" >= 0):      { [0.9, 2, 0.40, 0.06] };
    // ── Aircrew (impact only, no ballistic core) ──
    // CVC (combat vehicle crewman, DH-132).
    case (_h find "cvc" >= 0):        { [1.4, 1, 0.40, 0.05] };
    case (_h find "crew" >= 0 ||
          _h find "racing" >= 0):   { [1.0, 1, 0.40, 0.05] };
    // HGU-55/56, GSSH-18, pilot/heli shells.
    case (_h find "pilot" >= 0 ||
          _h find "hgu" >= 0 ||
          _h find "gssh" >= 0 ||
          _h find "heli" >= 0):     { [1.1, 1, 0.45, 0.15] };
    // ── Light headwear (no armour) ──
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

// The researched item table outranks the family tier: when a capture
// holds the family, its published mass replaces the tier weight.  Armour,
// NIR and clo stay with the tier.
private _mass = [_helmetItem, ["helmet"]] call FUNC(getItemMass);
if (_mass > 0) then { _tier set [0, _mass] };
_tier
