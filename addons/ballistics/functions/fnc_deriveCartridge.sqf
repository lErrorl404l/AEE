#include "..\script_component.hpp"
/*
Cartridge derivation (issue #170).

DERIVES the real ballistic properties of a round from its class name
and the weapon's measured barrel length — the dynamic layer on top of
the #167 table.  The derivation chain:

  ammo class name (B_556x45_Ball) -> parse caliber -> cartridge family
    -> the family's velocity-LENGTH curve evaluated at the weapon's
       real barrel length -> real MV
    -> the family's BC from the researched bullet geometry

The MV is a FUNCTION of barrel length, not a lookup: a 14.5" M4A1 and
a 20" M16A4 compute DIFFERENT MVs from the SAME cartridge curve.  The
interior-ballistics velocity-length relationship is the saturation
curve:

  v(L) = v_ref * (1 - exp(-k * (L - L_min) / L_ref))   (L > L_min)

fitted to the real measured barrel->MV data (the #167 seed: a 5.56
reaches ~723 m/s at 211 mm, ~862 at 368 mm, ~940 at 508 mm; the
velocity saturates toward the cartridge's maximum).  The curve is the
physics; the #167 table values are the anchor points it is fitted to.

The #167 table (fnc_getAmmoProperties) becomes the FALLBACK: the
derivation runs first; if the class cannot be parsed into a family, the
table's family values stand.

Arguments:
  0: ammo (STRING, the CfgAmmo classname)
  1: barrelM (NUMBER, the weapon's measured barrel length, m; 0 = use
     the family reference barrel)
  2: airTempC (NUMBER, the propellant temperature, default 21 C)

Returns [realMV, bcG1, bcG7, caliberMm, massG, dragModel, twistM,
pressureMPa] - the derived values with the temperature correction
applied to the MV. Twist (metres per turn) and chamber pressure (MAP,
MPa) are cartridge properties and come from the same family row: the
chambering fixes both, so a weapon of any mod resolves them from its
ammunition.
*/
params [["_ammo", "", [""]], ["_barrelM", 0, [0]], ["_airTempC", 21, [0]]];
if (_ammo == "") exitWith { [905, 0.307, 0, 5.56, 4.0, 1, 0.178, 430] };

// ─── Parse the class name into the cartridge family ─────────────────────
// The vanilla convention: B_556x45_Ball, B_762x51_Ball, B_545x39_Ball,
// B_127x99_Ball ...  The caliber encodes the family.
private _a = toLower _ammo;
private _family = switch (true) do {
    case (_a find "556x45" >= 0):   { "556x45" };
    case (_a find "545x39" >= 0):   { "545x39" };
    case (_a find "762x51" >= 0):   { "762x51" };
    case (_a find "762x39" >= 0):   { "762x39" };
    case (_a find "762x54" >= 0):   { "762x54" };
    case (_a find "9x21" >= 0 ||
          _a find "9x19" >= 0):     { "9x19" };
    case (_a find "127x99" >= 0):   { "127x99" };
    case (_a find "127x108" >= 0):  { "127x108" };
    case (_a find "338" >= 0):      { "338" };
    case (_a find "65x39" >= 0 ||
          _a find "6.5" >= 0):      { "65x39" };
    case (_a find "127x76" >= 0 ||
          _a find "12gauge" >= 0 ||
          _a find "pellet" >= 0):   { "12gauge" };
    case (_a find "m829" >= 0 ||
          _a find "apfsds" >= 0):   { "120mm_m256_m829" };
    case (_a find "m830" >= 0 ||
          _a find "120mm" >= 0 ||
          _a find "m256" >= 0):     { "120mm_m256" };
    default                         { "" };
};

// The family base properties (the #167 researched anchors).  The
// velocity-LENGTH curve per family is fitted to the seed's MEASURED
// barrel->MV pairs (interior ballistics: the velocity rises with
// barrel length and saturates at the cartridge maximum).  The 5.56
// pairs (211mm->723, 368->862, 508->940 m/s) give the curve; the
// family carries its anchor points.
//   [refMV, refBarrelM, vShort, shortBarrelM, vMin, bcG1, bcG7,
//    caliberMm, massG, dragModel, twistM, pressureMPa]
//
// Twist and pressure are CARTRIDGE properties, not weapon properties:
// the chambering fixes both.  Twist is metres per turn, pressure is
// the maximum average pressure (MAP) in MPa.  A weapon of any mod
// resolves them from its ammunition, so no weapon is listed anywhere.
//
// Twist sources: STANAG 4172 (5.56, 1:7); the NATO 7.62 standard
// (1:12 = 305 mm, NATO EPVAT MAP 415 MPa); the AK-74 and AKM barrel
// data (200 mm and 240 mm, 4 RH grooves); SAAMI/CIP for the pistol,
// .50 BMG and 12.7x108 MAPs.  The ABE seed agrees on every value
// except 7.62x51, where its row count splits 279/305 mm and the NATO
// standard 305 mm wins.
//
// The curve: linear between the short barrel (vShort) and the
// reference barrel (refMV) - the measured relationship is nearly
// linear in this band (the velocity-length power-law flattens only
// past the reference).  Below the short barrel the velocity falls
// toward vMin.
private _AMMO_FAMILIES = createHashMapFromArray [
    ["556x45", [948, 0.508, 723, 0.211, 500, 0.307, 0, 5.56, 4.0, 1, 0.178, 430]],
    ["545x39", [880, 0.414, 700, 0.210, 500, 0.300, 0.168, 5.45, 3.4, 7, 0.200, 355]],
    ["762x51", [838, 0.559, 700, 0.330, 480, 0.393, 0, 7.62, 9.5, 1, 0.305, 415]],
    ["762x39", [710, 0.414, 650, 0.210, 420, 0.279, 0, 7.62, 8.0, 1, 0.240, 355]],
    ["762x54", [820, 0.699, 700, 0.400, 450, 0.377, 0, 7.62, 9.6, 1, 0.240, 390]],
    ["9x19",   [351, 0.102, 280, 0.051, 250, 0.149, 0, 9.01, 8.0, 1, 0.250, 250]],
    ["127x99", [885, 1.143, 800, 0.610, 500, 0.670, 0, 12.7, 42.8, 1, 0.381, 379]],
    ["127x108",[818, 1.016, 750, 0.610, 480, 0.600, 0.340, 12.7, 48.2, 7, 0.381, 360]],
    ["338",    [899, 0.610, 800, 0.508, 500, 0.756, 0, 8.58, 16.2, 1, 0.254, 420]],
    ["65x39",  [790, 0.610, 700, 0.406, 450, 0.500, 0.196, 6.71, 7.8, 7, 0.203, 415]],
    ["12gauge",[470, 0.711, 400, 0.508, 300, 0.060, 0, 18.5, 28.3, 1, 0.0, 65]],
    // The 120 mm smoothbore tank cannon (M256). Two rows, one per
    // projectile, because the two rounds have different service
    // velocities and the M829 subprojectile mass is not published.
    // M830 HEAT-MP-T: velocity 1139.95 m/s and pressure 479.87 MPa from
    // TM 43-0001-28 page 2-115; mass from the projectile record, itself
    // from the same page. Twist 0 because the barrel is a smoothbore.
    // vMin is derived, not published: it is the fallback floor for a
    // barrel shorter than the reference. The M256 barrel is 5.28 m
    // (44 calibres), so the below-reference branch is not reachable and
    // the floor is set to the reference velocity.
    ["120mm_m256",[1139.95, 5.28, 1139.95, 5.28, 1139.95, 0, 0, 120, 13607.77, 1, 0, 479.87]],
    // M829 APFSDS-T: velocity 1679.45 m/s and pressure 510 MPa from
    // TM 43-0001-28 page 2-109. The subprojectile mass and diameter are
    // not published, so massG is 0 and the row derives no BC. vMin is
    // derived as above.
    ["120mm_m256_m829",[1679.45, 5.28, 1679.45, 5.28, 1679.45, 0, 0, 120, 0, 14, 0, 510]]
];
private _base = _AMMO_FAMILIES get _family;
// The table fallback carries no twist or pressure data: 0 means
// "unknown", and the caller decides what to do with it.
if (isNil "_base") exitWith {
    // No researched curve for this cartridge. Fall back to physics: the
    // projectile and cartridge records give the inputs, and the
    // interior-ballistics model gives the velocity. A round that no
    // table knows still gets a physical muzzle velocity.
    private _projectile = [_ammo] call FUNC(getProjectileData);
    private _cartridge = [_ammo] call FUNC(getCartridgeData);
    if ((_projectile isEqualTo []) || {_cartridge isEqualTo []}) exitWith {
        [0, 0, 0, 0, 0, 1, 0, 0]
    };
    private _calibreMm = (_projectile select 2) * 1000;
    private _massG = _projectile select 1;
    private _pressure = _cartridge select 3;
    private _mv = [_calibreMm, _massG, _barrelM, _pressure] call FUNC(calculateInteriorBallistics);
    [_mv, 0, 0, _calibreMm, _massG, 1, _cartridge select 2, _pressure]
};

// ─── The velocity-length curve ───────────────────────────────────────────
private _refMV = _base select 0;
private _refBarrel = _base select 1;
private _vShort = _base select 2;
private _shortBarrel = _base select 3;
private _vMin = _base select 4;

private _useBarrel = [_refBarrel, _barrelM] select (_barrelM > 0.01);

// The velocity-length curve: linear between the short-barrel anchor
// (vShort at shortBarrel) and the reference (refMV at refBarrel) - the
// measured relationship.  Below the short barrel the velocity falls
// off toward the family minimum.  At/above the reference it holds the
// cartridge maximum.
private _mv = _refMV;
if (_useBarrel >= _refBarrel) then {
    _mv = _refMV;
} else {
    if (_useBarrel >= _shortBarrel) then {
        _mv = linearConversion [_shortBarrel, _refBarrel, _useBarrel, _vShort, _refMV, true];
    } else {
        _mv = _vShort * (_useBarrel / _shortBarrel);
        _mv = _mv max _vMin;
    };
};

// ─── Temperature correction (the EPVAT 21 C reference) ───────────────────
// The propellant sensitivity coefficient per family (the #167 table):
// double-base ball 1.5 fps/degF, 9mm 1.2, temp-stable 0.3.  The
// relative shift is normalised to the derived MV.
private _coeff = [_ammo] call FUNC(calculatePropellantSensitivity);
private _mpsPerDegC = _coeff * 0.3048 * 1.8;
private _pctPerDegC = _mpsPerDegC / _mv * 100;
_mv = _mv * (1 + (_pctPerDegC * (_airTempC - 21) / 100));
_mv = _mv max 0.85 * _refMV min 1.15 * _refMV;

[_mv, _base select 5, _base select 6, _base select 7, _base select 8, _base select 9, _base select 10, _base select 11]
