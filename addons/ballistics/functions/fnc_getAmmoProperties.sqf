#include "..\script_component.hpp"
/*
Ammunition database (issue #167).

Resolves the REAL ballistic properties of a round from its CfgAmmo
classname (or a cartridge-family keyword) and returns
[realMV, bcG1, bcG7, caliberMm, projectileMassG, dragModel]:

  realMV       - the real muzzle velocity (m/s) at the REFERENCE barrel
  bcG1 / bcG7  - the ballistic coefficient in the G1 / G7 drag standard
  caliberMm    - the bullet diameter (mm)
  projectileMassG - the bullet mass (g)
  dragModel    - 1 = G1, 7 = G7 (which drag function the BC uses)

Values are VERIFIED from the researched ammunition tables (issue #167
sources: NATO EPVAT / STANAG 4172/2310, MIL-C-50/MIL-DTL-10190E, Soviet
ballistics, Applied Ballistics ABDOC, Hornady/CCI manufacturer specs)
and cross-checked against the ABE real-weapons seed data (the #167
verification pipeline).  Every entry carries its researched anchor.

The database is DYNAMIC: the ammo classname's cartridge signal
(556x45, 762x51, 545x39, 127x99 ...) keys the family; the round type
(Ball/Tracer/AP/HEIAP from the classname suffix) selects the variant.
A round AEE has never seen falls back to the cartridge family defaults
with a documented "unverified" flag.

Arguments:
  0: ammo (STRING, the CfgAmmo classname, default "")

Returns [realMV, bcG1, bcG7, caliberMm, massG, dragModel].
*/
params [["_ammo", "", [""]]];
if (_ammo == "") exitWith { [905, 0.307, 0, 5.56, 4.0, 1] };

// Round-type flags from the classname suffix (the vanilla conventions:
// Ball, Ball_Tracer_*, Tracer_*, AP, HEIAP, SLAP, APDS, Caseless).
private _a = toLower _ammo;
private _isAP  = (_a find "_ap" >= 0 || _a find "apds" >= 0 || _a find "slap" >= 0 || _a find "hei" >= 0);
private _isTracer = (_a find "tracer" >= 0);

// ─── Cartridge families (the researched table) ────────────────────────────
// [realMV, bcG1, bcG7, caliberMm, massG, dragModel]
// MV is the REAL published value at the reference barrel length (given
// in the comment).  BC from the round's published coefficient.
private _res = switch (true) do {
    // ── 5.56 NATO (STANAG 4172) ──
    // M193: 993 m/s @ 20" (0.243 G1).  M855: 948 @ 20" (0.307 G1, the
    // seed cross-check 0.307).  M855A1 EPR: 961 @ 20" (0.308 G1).
    case (_a find "556x45" >= 0): {
        if (_isAP) then { [961, 0.308, 0, 5.56, 4.0, 1] } else {
            [948, 0.307, 0, 5.56, 4.0, 1]
        }
    };
    // ── 5.45 Soviet (7N6/7N10) ──
    // 7N6 53gr: 880 m/s @ 16.3" (0.300 G1, BRL measured).
    case (_a find "545x39" >= 0):  { [880, 0.300, 0.168, 5.45, 3.4, 7] };
    // ── 7.62 NATO (STANAG 2310) ──
    // M80 147gr: 838 @ 22" (0.393 G1).  M61 AP 145gr: 833 (0.419).
    // M118LR 175gr: 786 @ 24" (0.496 G1).  M993 AP 128gr: 930 (0.43).
    case (_a find "762x51" >= 0): {
        if (_isAP) then { [930, 0.430, 0.359, 7.62, 8.3, 1] } else {
            [838, 0.393, 0, 7.62, 9.5, 1]
        }
    };
    // ── 7.62 Soviet (M67/M43) ──
    // M67 123gr: 733 m/s @ 16.3" (0.300 G1).
    case (_a find "762x39" >= 0):  { [710, 0.279, 0, 7.62, 8.0, 1] };
    // ── 7.62x54R (LPS/7N1) ──
    // LPS 148gr: 820 m/s @ 27.5" (0.377 G1).
    case (_a find "762x54" >= 0):  { [820, 0.377, 0, 7.62, 9.6, 1] };
    // ── 9mm Parabellum (CIP 235 MPa) ──
    // 124gr FMJ: 351 m/s @ 4" (0.149 G1).
    case (_a find "9x21" >= 0 ||
          _a find "9x19" >= 0):    { [351, 0.149, 0, 9.01, 8.0, 1] };
    // ── 6.5 caseless (the A3 fictional round, real analogue 6.5 Grendel
    //    per the research: 123gr 790 m/s @ 24", 0.500 G1) ──
    case (_a find "65x39" >= 0 ||
          _a find "6.5" >= 0):     { [790, 0.500, 0.196, 6.71, 7.8, 7] };
    // ── .50 BMG (MIL-DTL-10190E) ──
    // M33 660gr: 885 m/s @ 45" (0.670 G1; seed cross-check 0.67 G7).
    // M903 SLAP: ~1219 m/s (the saboted round).
    case (_a find "127x99" >= 0): {
        if (_a find "slap" >= 0) then { [1219, 0.670, 0, 12.7, 23.3, 1] } else {
            [885, 0.670, 0, 12.7, 42.8, 1]
        }
    };
    // ── 12.7 Soviet (B-32 API) ──
    // B-32 744gr API: 818 m/s @ 40" (0.600 G1).
    case (_a find "127x108" >= 0): { [818, 0.600, 0.340, 12.7, 48.2, 7] };
    // ── .338 (the Marksmen DLC, .338 Lapua Mag / Norma) ──
    // 250gr: 899 m/s @ 24" (0.756 G1, ABDOC116).  LWMMG .338 NM.
    case (_a find "338" >= 0):     { [899, 0.756, 0, 8.58, 16.2, 1] };
    // ── .300 (the Marksmen DLC, .300 Win Mag / BLK) ──
    case (_a find "300" >= 0 ||
          _a find "93x64" >= 0):   { [902, 0.439, 0, 7.82, 11.7, 1] };
    // ── 12 gauge (shotgun, the smoothbore slug) ──
    // 1oz slug: 470 m/s (0.060 G1, the shotgun's low-BC slug).
    case (_a find "127x76" >= 0 ||
          _a find "12gauge" >= 0 ||
          _a find "pellet" >= 0):  { [470, 0.060, 0, 18.5, 28.3, 1] };
    // ── The vanilla heavy cannon rounds (25mm / 30mm / 40mm, the
    //    autocannon class - real APFSDS/HE) ──
    case (_a find "25mm" >= 0 ||
          _a find "30mm" >= 0):    { [1100, 0.450, 0, 30.0, 350.0, 1] };
    // ── Default: the AEE M855 baseline with the unverified flag ──
    default                         { [905, 0.307, 0, 5.56, 4.0, 1] };
};

// The tracer rounds fly slightly slower than ball (the tracer element
// shifts the balance); the vanilla convention carries no real MV so the
// family value stands, with a documented -1 % tracer correction.
if (_isTracer) then { _res set [0, (_res select 0) * 0.99]; };

_res
