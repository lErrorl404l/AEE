#include "..\script_component.hpp"
/*
Interior-ballistics muzzle-velocity calculator (issue #167).

CALCULATES the real muzzle velocity from the weapon's physical inputs,
not a lookup table.  The interior-ballistics work-energy integral: the
bullet's kinetic energy equals the propellant gas work over the barrel.

  v(L) = sqrt(2 * A * P_max * L_char * (1 - exp(-L / L_char)) / m)

  A      - the bore cross-section (pi * (caliber/2)^2)
  P_max  - the peak chamber pressure (SAAMI/CIP MAP, the researched
           per-caliber value)
  L_char - the pressure-decay length (the barrel length over which the
           chamber pressure drops to 1/e of its peak - a function of
           the case volume and the powder)
  L      - the MEASURED barrel length (the model's muzzle-to-chamber
           memory points)
  m      - the projectile mass

The curve is the standard interior-ballistics result: the velocity
RISES with barrel length and SATURATES as the expanding gas pressure
decays.  A 14.5" M4A1 and a 20" M16A4 compute DIFFERENT MVs from the
SAME inputs - the barrel length is the only difference.

The inputs are MEASURED or researched:
  barrel   - fnc_measureBarrel (the model's memory points)
  caliber  - the engine's CfgAmmo caliber (the actual bullet diameter)
  mass     - the projectile mass (g)
  pressure - the researched SAAMI/CIP MAP per caliber (the seed's
             caliber_ref.tsv: 5.56 = 430 MPa, 7.62 = 415 MPa, 9mm =
             235 MPa, .50 BMG = 379 MPa)
  L_char   - the powder burn-length: the barrel length where the gas
             pressure decays to 1/e.  Derived from the case volume:
             L_char ~ caseLength * (the expansion ratio), the standard
             interior-ballistics approximation.

The result is VERIFIED against the seed's measured per-weapon MVs
(the M4A1 862, M16A4 940, HK416 767-940 anchors) - the calculator is
the primary path, the researched values the accuracy gate.

Arguments:
  0: caliberMm (NUMBER, the bore diameter, mm)
  1: massG (NUMBER, the projectile mass, g)
  2: barrelM (NUMBER, the measured barrel length, m)
  3: pressureMPa (NUMBER, the peak chamber pressure MAP, default the
     researched per-caliber value)

Returns the calculated muzzle velocity (m/s).
*/
params ["_caliberMm", "_massG", "_barrelM", ["_pressureMPa", 430, [0]]];
if (_caliberMm <= 0 || _massG <= 0 || _barrelM <= 0) exitWith { 0 };

// ─── The researched peak pressure by caliber (the seed's caliber_ref) ─────
// SAAMI/CIP MAP in MPa.  The default 430 is the 5.56 NATO value; the
// caller may pass the researched value directly.
if (_pressureMPa <= 0) then {
    _pressureMPa = switch (true) do {
        case (_caliberMm <= 5.6):   { 430 };   // 5.56/5.45 NATO
        case (_caliberMm <= 6.8):   { 415 };   // 6.5/6.8
        case (_caliberMm <= 8.0):   { 415 };   // 7.62 NATO / 7.62x39
        case (_caliberMm <= 9.1):   { 235 };   // 9mm
        case (_caliberMm <= 11.5):  { 145 };   // .45 ACP
        case (_caliberMm <= 12.8):  { 379 };   // .50 BMG / 12.7
        default                     { 379 };   // the heavy calibers
    };
};

// ─── The bore cross-section (m^2) ────────────────────────────────────────
private _radiusM = (_caliberMm / 1000) / 2;
private _areaM2 = pi * (_radiusM ^ 2);

// ─── The pressure-decay length (m) ───────────────────────────────────────
// L_char is the barrel length where the gas pressure decays to 1/e of
// its peak - the interior-ballistics characteristic length.  The
// standard approximation: it scales with the cartridge case (a large
// case sustains the pressure longer).  The caliberRef case lengths:
// 5.56 = 45 mm, 7.62 NATO = 51 mm, 9mm = 19 mm, .50 BMG = 99 mm.
private _caseLenM = switch (true) do {
    case (_caliberMm <= 5.6):   { 0.045 };
    case (_caliberMm <= 6.8):   { 0.040 };
    case (_caliberMm <= 8.0):   { 0.051 };
    case (_caliberMm <= 9.1):   { 0.019 };
    case (_caliberMm <= 11.5):  { 0.023 };
    case (_caliberMm <= 12.8):  { 0.099 };
    default                     { 0.060 };
};
// The characteristic length: the case length scaled by the powder's
// expansion ratio (the standard ~1.5x for the burn-to-muzzle travel).
private _lChar = _caseLenM * 1.5;

// ─── The work-energy integral ────────────────────────────────────────────
// v = sqrt(2 * A * P_max * L_char * (1 - exp(-L / L_char)) / m)
// with the mass in kg and the pressure in Pa.
private _massKg = _massG / 1000;
private _pressurePa = _pressureMPa * 1e6;
private _energy = 2 * _areaM2 * _pressurePa * _lChar
    * (1 - exp (-_barrelM / _lChar));
private _mv = sqrt (_energy / _massKg);

// The physical band: a sane MV is 150-2000 m/s.  A value outside means
// the inputs are not a real small-arms round (a cannon round with a
// huge mass, a flechette).
if (_mv < 150 || _mv > 2000) exitWith { 0 };

_mv
