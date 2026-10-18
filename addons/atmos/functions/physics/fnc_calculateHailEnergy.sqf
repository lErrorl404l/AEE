#include "..\..\script_component.hpp"

/*
Hailstone size and impact energy from the convective strength (#151 follow-on).

Hail size is set in the growth layer, not at the ground: a stronger updraft
holds a stone aloft longer, so it grows larger.  The CAPE proxy that
fnc_calculateCloudDevelopment publishes is the updraft indicator this model
already uses for the hail gate, so size scales from the same quantity.

The physics (all citable, no invented constants):

  Size from the updraft.  A stone is held while the updraft exceeds its
  terminal velocity, so the largest stone a storm can carry is the one whose
  terminal velocity equals the updraft: inverting the drag balance below,
      D = 3 C_d rho_a w^2 / (4 g rho_h),
  with w the parcel-theory updraft sqrt(2 CAPE).  That updraft is an upper
  bound (Peters et al. 2020), so the size is the largest possible stone,
  capped at the largest ever recorded, 203 mm (Vivian, South Dakota, 2010;
  NOAA NCEI).

  Terminal velocity from the drag balance for a sphere:
      v_t = sqrt( 4 g rho_h D / (3 C_d rho_a) )
  Source: Dieling, Smith & Beruvides 2020, Geosciences 10(12):500, Eq. 2.
  rho_h pure ice 917 kg/m3, C_d 0.6 the best fit for near-spherical hail
  above 1 cm, rho_a AERO_ISA_SEA_LEVEL_DENSITY kg/m3 at sea level.

  Mass from the diameter, spherical:
      m = (pi / 6) rho_h D^3
  Real stones are spheroids with density 0.45-0.9 g/cm3, so this is an upper
  bound; the damage is therefore an upper bound too, which is the safe side.

  Impact energy:
      E = 0.5 m v_t^2
  At 5 cm this gives about 24 J; at 10 cm about 392 J.  Computed from the
  laws above, not read from a table.

HUMAN INJURY THRESHOLD: NWS publishes NO joules-to-injury threshold.  This
model therefore does NOT invent one.  It returns the kinetic energy and the
size, and the caller scales the game's own damage system by that energy.
See the material note in fnc_hailDamage.

Arguments:
  0: CAPE (NUMBER, J/kg) from fnc_calculateCloudDevelopment

Return Value: ARRAY [diameter_m, mass_kg, velocity_ms, energy_j]
Example: [400] call aee_atmos_fnc_calculateHailEnergy
Public: No
*/

params [["_capeProxy", 0, [0]]];

if (_capeProxy <= 0) exitWith { [0, 0, 0, 0] };
// ─── Size from the updraft ───────────────────────────────────────────────
private _w = sqrt (2 * _capeProxy);
private _diameter = ((3 * 0.6 * AERO_ISA_SEA_LEVEL_DENSITY * (_w ^ 2)) / (4 * STANDARD_GRAVITY * 917)) min 0.203;
// ─── Terminal velocity (drag balance, Dieling 2020 Eq. 2) ────────────────
private _rhoH = 917;      // kg/m3, pure ice
private _cd = 0.6;        // near-spherical hail above 1 cm, Dieling 2020
private _rhoA = AERO_ISA_SEA_LEVEL_DENSITY;    // kg/m3, sea level
private _g = STANDARD_GRAVITY;
private _vT = sqrt ((4 * _g * _rhoH * _diameter) / (3 * _cd * _rhoA));

// ─── Mass and impact energy ──────────────────────────────────────────────
private _mass = (pi / 6) * _rhoH * (_diameter ^ 3);
private _energy = 0.5 * _mass * _vT * _vT;

[_diameter, _mass, _vT, _energy]
