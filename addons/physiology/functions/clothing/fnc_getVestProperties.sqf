#include "..\..\script_component.hpp"
/*
Vest properties (issue #119).

Classifies the vest slot (CfgWeapons V_ classes) by family keywords and
returns [weight kg, armor NIJ 0..3, nirReflectance, clo].  The values
are the researched IRL figures from equipment-library.md.

Groups (sortable by country -> company -> era):
  USSR/Russia 1981-2015  | 6B2/3/4/5 (Soviet) -> 6B11-18 Zabralo
    (Russia) -> 6B23 -> 6B43/6B45 Ratnik -> 6Sh92/117/46 webbing
  USA military 1951-2018 | M-12/51/52/69 flak -> IBA/IOTV -> SPCS ->
    CIRAS -> PlateFrame/MBAV/MSV
  USA commercial 1999+   | Crye (CPC/AVS/JPC) -> Spiritus (LV-119/34A)
    -> Ferro (Slickster/FCPC/3AC) -> Velocity (Scarab/Mayflower/LWPC)
    -> Shaw (ARC V2) -> Defense Mechanisms (MEPC) -> Agilite (K19/
    K-Zero) -> 5.11 (Tactec/LV6) -> Direct Action (Spitfire/Ghost/
    Hellcat) -> Condor (MOPC/EXO/Sentry/Vanquish) -> LBT (6094/SRT) ->
    Tyr (PICO) -> Shellback (Banshee/Rampage) -> FirstSpear (Strandhogg/
    Siege/AAC) -> Warrior (DCS/RICAS/LPAAC/QRC/RPC) -> HSGI ->
    Paraclete (RAV/SOE/HPC) -> Eagle (MMAC) -> Tactical Tailor -> HRT
  UK 1980s-2016          | CBA/ECBA -> Osprey -> Virtus
  China/other 1980s      | Type 81/86 (no published weight - skip)

Arguments:
  0: unit (OBJECT, default player)

Returns [weight, armor, nirReflectance, clo].
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { [2.5, 2, 0.38, 0.10] };

private _vestItem = vest _unit;
if (_vestItem == "") exitWith { [2.5, 2, 0.38, 0.10] };

private _vestDef = [2.5, 2, 0.38, 0.10];
private _v = toLower _vestItem;
switch (true) do {
    // ── USSR/Russia: the 6B series ──
    // 6B45 (Ratnik, 2015): GOST 5a/6a ~III/IV, 8-13 kg.
    case (_v find "6b45" >= 0):      { [9.0, 3, 0.40, 0.15] };
    // 6B43 (Zabralo-Sh, 2000s): GOST 6a ~IV, 9-13 kg.
    case (_v find "6b43" >= 0):      { [11.0, 3, 0.40, 0.15] };
    // 6B23 (2003): aramid + steel/ceramic, III-IV, 7.9 kg.
    case (_v find "6b23" >= 0):      { [7.9, 3, 0.40, 0.14] };
    // 6B13 (Zabralo, 1999): ceramic, ~III, 7-11 kg.
    case (_v find "6b13" >= 0):      { [9.0, 3, 0.40, 0.14] };
    // 6B2 (1981): titanium + aramid, ~IIIA, 4.5 kg.
    case (_v find "6b2" >= 0):       { [4.5, 2, 0.40, 0.12] };
    // 6B3T (1983): titanium plates, ~III, 8-12 kg.
    case (_v find "6b3" >= 0):       { [10.0, 3, 0.40, 0.13] };
    // 6B4 (1985): ceramic/boron tiles, ~III, 7-12 kg.
    case (_v find "6b4" >= 0):       { [9.5, 3, 0.40, 0.13] };
    // 6B5 (1986): series, ~II-IIIA soft to ~III plates, 3-11.5 kg.
    case (_v find "6b5" >= 0):       { [7.0, 2, 0.40, 0.13] };
    // 6B11/6B12/6B17/6B18 (Zabralo soft, ~IIIA, 5-7 kg).
    case (_v find "6b11" >= 0 ||
          _v find "6b12" >= 0 ||
          _v find "6b17" >= 0 ||
          _v find "6b18" >= 0):      { [5.0, 2, 0.40, 0.12] };
    // 6Sh92/6Sh117/6Sh46 (assault vest / webbing, ~2-3 kg).
    case (_v find "6sh92" >= 0 ||
          _v find "6sh117" >= 0 ||
          _v find "6sh46" >= 0):      { [2.5, 1, 0.40, 0.09] };
    // Chicom / Lifchik / Vydra (Russian chest rigs, no ballistic).
    case (_v find "chicom" >= 0 ||
          _v find "lifchik" >= 0 ||
          _v find "vydra" >= 0):      { [1.2, 0, 0.40, 0.06] };
    // ── USA military ──
    // Historical flak vests (M-1951/52, M-69, M-12, Vietnam-era OTV):
    // unrated soft nylon.
    case (_v find "m1951" >= 0 ||
          _v find "m1952" >= 0 ||
          _v find "m69" >= 0 ||
          _v find "m12" >= 0 ||
          _v find "otv" >= 0):       { [3.8, 1, 0.40, 0.08] };
    // IOTV (2007): IIIA soft + ESAPI plates, 4.5 kg bare
    // (TM 10-8470-208-10) + the SPC (modular scalable plate carrier).
    case (_v find "iotv" >= 0 ||
          _v find "spc" >= 0):       { [4.5, 3, 0.38, 0.18] };
    // SPCS (2010): plate carrier, ~2.7 kg bare + IV plates.
    case (_v find "spcs" >= 0):      { [2.7, 3, 0.38, 0.16] };
    // CIRAS (2001): BALCS soft + plates, ~1.8 kg carrier.
    case (_v find "ciras" >= 0):     { [3.5, 3, 0.38, 0.15] };
    // PlateFrame / MBAV / MSV (modern plate carriers).
    case (_v find "plateframe" >= 0 ||
          _v find "mbav" >= 0 ||
          _v find "msv" >= 0):       { [5.5, 3, 0.38, 0.16] };
    // ── USA commercial: Crye Precision (1999+) ──
    // CPC (Cage Plate Carrier, 2009): 1.7-2.1 kg carrier.
    case (_v find "cpc" >= 0):       { [5.5, 3, 0.35, 0.18] };
    // AVS (Adaptive Vest System): heavy assault carrier ~2.5 kg.
    case (_v find "avs" >= 0):       { [2.5, 3, 0.38, 0.16] };
    // JPC/JPC 2.0 (Jumpable Plate Carrier): ~1.1 kg.
    case (_v find "jpc" >= 0):       { [1.0, 3, 0.38, 0.15] };
    // ── USA commercial: Spiritus Systems (LV-119/34A/Covert) ──
    case (_v find "lv-119" >= 0 ||
          _v find "lv119" >= 0 ||
          _v find "34a" >= 0 ||
          _v find "covert" >= 0):    { [2.5, 3, 0.38, 0.16] };
    // ── USA commercial: Ferro Concepts (Slickster ~0.9 kg, FCPC,
    //    3AC) ──
    case (_v find "slickster" >= 0): { [0.9, 3, 0.38, 0.15] };
    case (_v find "fcpc" >= 0 ||
          _v find "3ac" >= 0):       { [2.5, 3, 0.38, 0.16] };
    // ── USA commercial: Velocity Systems (Scarab/Mayflower/LWPC) ──
    case (_v find "scarab" >= 0 ||
          _v find "mayflower" >= 0 ||
          _v find "lwpc" >= 0):      { [2.5, 3, 0.38, 0.16] };
    // ── USA commercial: Shaw Concepts ARC V2 (1.02 kg) ──
    case (_v find "arc_v2" >= 0 ||
          _v find "arcv2" >= 0 ||
          _v find "arc-" >= 0):      { [1.0, 3, 0.38, 0.15] };
    // ── USA commercial: Defense Mechanisms MEPC, 5.11 (Tactec/LV6),
    //    HSGI (Weesatch/Wasatch/MPC/SPC), Paraclete (RAV/SOE/HPC),
    //    Tactical Tailor Fight Light, HRT ──
    case (_v find "mepc" >= 0 ||
          _v find "tactec" >= 0 ||
          _v find "lv6" >= 0 ||
          _v find "weesatch" >= 0 ||
          _v find "wasatch" >= 0 ||
          _v find "rav" >= 0 ||
          _v find "fightlight" >= 0 ||
          _v find "hrt" >= 0):       { [2.5, 3, 0.38, 0.16] };
    // ── USA commercial: Agilite (K19 1.10 kg, K-Zero 0.97 kg) ──
    case (_v find "k19" >= 0):       { [1.1, 3, 0.38, 0.15] };
    case (_v find "k-zero" >= 0 ||
          _v find "kzero" >= 0):     { [0.97, 3, 0.38, 0.15] };
    // ── USA commercial: Direct Action (Spitfire 0.47 kg, Ghost,
    //    Hellcat) ──
    case (_v find "spitfire" >= 0):  { [0.47, 3, 0.38, 0.15] };
    case (_v find "ghost" >= 0 ||
          _v find "hellcat" >= 0):   { [2.5, 3, 0.38, 0.16] };
    // ── USA commercial: Condor (MOPC/EXO/Sentry/Vanquish) ──
    case (_v find "mopc" >= 0 ||
          _v find "vanquish" >= 0 ||
          _v find "sentry" >= 0):    { [2.5, 3, 0.38, 0.16] };
    // ── USA commercial: LBT (6094/SRT), Tyr (PICO), Shellback
    //    (Banshee/Rampage), FirstSpear (Strandhogg/Siege/AAC), Warrior
    //    (DCS/RICAS/LPAAC/QRC/RPC), Eagle MMAC ──
    case (_v find "6094" >= 0 ||
          _v find "srt" >= 0 ||
          _v find "pico" >= 0 ||
          _v find "banshee" >= 0 ||
          _v find "rampage" >= 0 ||
          _v find "strandhogg" >= 0 ||
          _v find "siege" >= 0 ||
          _v find "aac" >= 0 ||
          _v find "ricas" >= 0 ||
          _v find "lpaac" >= 0 ||
          _v find "qrc" >= 0 ||
          _v find "rpc" >= 0 ||
          _v find "dcs" >= 0 ||
          _v find "mmac" >= 0):      { [2.5, 3, 0.38, 0.16] };
    // ── UK 1980s-2016 ──
    // CBA/ECBA (1980s-90s): aramid soft, ~4-5 kg.
    case (_v find "ecba" >= 0 ||
          _v find "cba" >= 0):       { [4.5, 2, 0.40, 0.10] };
    // Osprey (2006): aramid + ceramic, ~8-9 kg bare.
    case (_v find "osprey" >= 0):    { [8.5, 3, 0.40, 0.15] };
    // Virtus (2016): aramid + ceramic, ~5-6 kg bare.
    case (_v find "virtus" >= 0):    { [5.5, 3, 0.40, 0.14] };
    // ── Generic vanilla families ──
    case (_v find "platecarrier" >= 0): { [5.5, 3, 0.35, 0.18] };
    case (_v find "tacvest" >= 0):      { [2.0, 2, 0.38, 0.10] };
    case (_v find "bandollier" >= 0):   { [1.0, 1, 0.40, 0.06] };
    case (_v find "chestrig" >= 0):     { [1.2, 1, 0.40, 0.07] };
    case (_v find "harness" >= 0):      { [1.5, 1, 0.40, 0.08] };
    case (_v find "rebreather" >= 0):   { [3.0, 0, 0.20, 0.15] };
    // Belts, suspenders, webbing, belt-mounted rigs (ALICE, 6Sh,
    // vest_commander / vest_pistol_holster): load-bearing only.
    case (_v find "belt" >= 0 ||
          _v find "suspend" >= 0 ||
          _v find "webbing" >= 0 ||
          _v find "vest_commander" >= 0 ||
          _v find "vest_pistol" >= 0): { [1.2, 0, 0.40, 0.07] };
    default                            { _vestDef };
};
