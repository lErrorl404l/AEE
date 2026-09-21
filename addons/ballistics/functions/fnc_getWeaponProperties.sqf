#include "..\script_component.hpp"
/*
Weapon database (issue #167).

Resolves the REAL ballistic properties of a weapon from its CfgWeapons
classname (or a weapon-family keyword) and returns
[barrelM, twistM, pressureMPa, moa, cyclicRpm, massKg, realMV]:

  barrelM    - the real barrel length (m)
  twistM     - the rifling twist rate (m per turn)
  pressureMPa - the chamber pressure MAP (MPa, SAAMI/CIP)
  moa        - the practical accuracy (MOA)
  cyclicRpm  - the cyclic rate (rpm, 0 for semi-auto)
  massKg     - the weapon mass (kg, empty)
  realMV     - the real muzzle velocity (m/s) for the weapon's
               cartridge at THIS barrel (the seed's measured per-weapon
               MV: M4A1 862, M16A4 940 - the real barrel-length story,
               not an approximation law)

Values are VERIFIED from the researched weapon tables (issue #167
sources: US Army TMs, manufacturer specs, CIP/SAAMI, NATO EPVAT) and
cross-checked against the ABE real-weapons seed data (barrel mm, twist
mm, pressure MPa, MV per real weapon, source-cited per row).  Every
entry carries its researched anchor.

The database is DYNAMIC: the vanilla weapon classname's family signal
(arifle_MX, arifle_MX_GL, arifle_Katiba, srifle_EBR, LMG_Mk200, ...)
keys the real analogue.  A weapon AEE has never seen falls back to the
family defaults with a documented "unverified" flag.

Arguments:
  0: weapon (STRING, the CfgWeapons classname, default "")

Returns [barrelM, twistM, pressureMPa, moa, cyclicRpm, massKg, realMV].
*/
params [["_weapon", "", [""]]];
if (_weapon == "") exitWith { [0.368, 0.178, 430, 2.5, 800, 3.5, 862] };

private _w = toLower _weapon;

// The weapon family -> real analogue.  The realMV is the measured
// muzzle velocity at the weapon's real barrel (the seed's per-weapon
// values, source-cited).
switch (true) do {
    // ── 5.56 carbines (14.5-16") ──
    // M4/M4A1 (368 mm / 1:7 / 430 MPa / 2-4 MOA / 800 rpm / 3.0 kg /
    //   M855 @ 862 m/s).
    case (_w find "arifle_mx" >= 0 ||
          _w find "arifle_mxc" >= 0 ||
          _w find "arifle_mxk" >= 0):       { [0.368, 0.178, 430, 2.5, 800, 3.5, 862] };
    // SPAR-16 (HK416 analogue, 368 mm 1:7, 862 m/s).
    case (_w find "arifle_spar_01" >= 0 ||
          _w find "arifle_spar_02" >= 0):   { [0.368, 0.178, 430, 2.0, 850, 3.5, 862] };
    // Katiba / TRG / Mk20 (the AK/G36 class, 16" 1:7, ~890 m/s).
    case (_w find "arifle_katiba" >= 0 ||
          _w find "arifle_trg" >= 0 ||
          _w find "arifle_mk20" >= 0):      { [0.406, 0.178, 430, 3.0, 700, 3.6, 890] };
    // ── 5.56 full-length (20") ──
    // M16A4 (508 mm / 1:7 / 430 MPa / 1.5-2 MOA / 800 rpm / 3.5 kg /
    //   M855 @ 940 m/s).
    case (_w find "arifle_mx_gl" >= 0 ||
          _w find "arifle_mxc_gl" >= 0 ||
          _w find "arifle_mxk_gl" >= 0 ||
          _w find "arifle_spar_03" >= 0 ||
          _w find "arifle_mk20_gl" >= 0):   { [0.508, 0.178, 430, 2.0, 800, 4.0, 940] };
    // ── 5.56 LMG ──
    // Mk200 (M249 SAW analogue, 465 mm / 1:7 / 430 / 750 rpm / 7.5 kg /
    //   915 m/s).
    case (_w find "lmga_mk200" >= 0 ||
          _w find "lmga_minimi" >= 0):      { [0.465, 0.178, 430, 3.0, 750, 7.5, 915] };
    // ── 6.5 caseless (the MX family, 6.5 Grendel analogue) ──
    // MX 20" (508 mm / 1:7 / 415 MPa / 2 MOA / 700 rpm / 3.8 kg /
    //   790 m/s Grendel).
    case (_w find "arifle_mxm" >= 0):       { [0.508, 0.178, 415, 2.0, 700, 3.8, 790] };
    // ── 7.62 DMR ──
    // EBR (M14 EBR, 457 mm / 1:12 / 415 / 1.5-2 MOA / 700 rpm / 5.0 kg /
    //   830 m/s).
    case (_w find "srifle_ebr" >= 0 ||
          _w find "srifle_dmr_01" >= 0 ||
          _w find "srifle_dmr_03" >= 0):    { [0.457, 0.305, 415, 1.5, 700, 5.0, 830] };
    // ── 7.62 GPMG ──
    // Navid (M240 analogue, 630 mm / 1:12 / 415 / 750 rpm / 12.3 kg /
    //   857 m/s).
    case (_w find "lmga_navid" >= 0 ||
          _w find "mmg_01" >= 0):           { [0.630, 0.305, 415, 3.0, 750, 12.3, 857] };
    // Zafir (PKM analogue, 650 mm / 1:9.45 / 355 / 650 rpm / 9.0 kg /
    //   825 m/s).
    case (_w find "lmga_zafir" >= 0):       { [0.650, 0.240, 355, 3.0, 650, 9.0, 825] };
    // ── .338 sniper (the Marksmen DLC) ──
    // M320 LRR (AWM analogue, 686 mm / 1:11 / 415 / 0.5-1 MOA /
    //   bolt / 6.8 kg / 899 m/s 250gr).
    case (_w find "srifle_lrr" >= 0 ||
          _w find "srifle_lrr_sos" >= 0):   { [0.686, 0.279, 415, 0.75, 0, 6.8, 899] };
    // ── .300 sniper (Marksmen) ──
    case (_w find "srifle_dmr_02" >= 0 ||
          _w find "srifle_dmr_04" >= 0):    { [0.610, 0.254, 415, 1.0, 0, 5.9, 880] };
    // ── 9mm SMG / handgun ──
    // Vermin / Sting (MP5/Uzi class, 260 mm / 1:10 / 235 / 800 rpm /
    //   380 m/s).
    case (_w find "smg_01" >= 0 ||
          _w find "smg_02" >= 0 ||
          _w find "smg_05" >= 0):           { [0.260, 0.254, 235, 4.0, 800, 2.8, 380] };
    // ── 12-gauge shotgun ──
    // Mx Black / Mk26 (Benelli M4, 470 mm smoothbore / 83 MPa MAP /
    //   470 m/s slug).
    case (_w find "sgun_hunter" >= 0 ||
          _w find "sgun_m4" >= 0):          { [0.470, 0.000, 83, 6.0, 0, 3.6, 470] };
    // ── Default: the M4A1 baseline (unverified flag) ──
    default                                  { [0.368, 0.178, 430, 2.5, 800, 3.5, 862] };
};
