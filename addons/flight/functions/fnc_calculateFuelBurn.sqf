#include "..\script_component.hpp"

/*
Burn one interval of aircraft fuel and shift the centre of gravity, from
scalars only.

WHY THIS FUNCTION EXISTS.  The engine burns no fuel of its own here.  The
generated config sets fuelConsumptionRate to zero for every bound aircraft
class, so the two never double-count, and the sourced rate drives this
scripted burn instead.  This kernel is PURE ARITHMETIC over scalars plus no
engine call, so the headless harness runs it with no vehicle.

THE BURN.  A rate in kg/s over an interval in s removes mass:

  burn      = rate * dt                          [kg]
  remaining = max (fuelMass - burn, 0)           [kg]

The rate is the sourced fuel_consumption_rate when the corpus holds one.
When it does not, the burn derives from the specific fuel consumption and the
rated power:

  fuel_burn_kg_s = sfc_kg_kwh * rated_power_w / 3.6e6   [kg/s]

The 3.6e6 divisor converts kWh to J, because 1 kWh is 3.6e6 J and the sfc is
kg per kWh.

THE CENTRE-OF-GRAVITY SHIFT.  The fuel sits at its arm fuel_cg_arm_m from the
datum.  The scripted centre of gravity is the fuel's mass-weighted share of
that arm:

  cgOffset = fuel_cg_arm_m * (remaining / fullFuelMass)   [m]

At full fuel the offset equals the arm, and as the fuel burns the centre of
gravity moves toward the datum.  This is a DECLARED scripted model, not a
measured centre of gravity.

THE CEILING.  Fuel transfer between tanks and fuel jettison are scripted only.
The engine exposes no transfer and no jettison, so this kernel does not model
them.

Guards, each explicit:
  - A negative fuel mass is refused with [-1, -1], because a mass cannot be
    negative.
  - A negative interval is refused with [-1, -1], because time does not run
    backward.
  - A non-positive full fuel mass is refused with [-1, -1], because the
    centre-of-gravity fraction divides by it.
  - A non-positive rate means no burn.  The fuel mass is returned unchanged.

Arguments:
  0:  _fuelMassKg       (NUMBER) current fuel mass, kg, >= 0
  1:  _sourcedRateKgS   (NUMBER) sourced fuel_consumption_rate, kg/s, 0 when absent
  2:  _sfcKgKwh         (NUMBER) specific fuel consumption, kg/kWh
  3:  _ratedPowerW      (NUMBER) rated power, W, for the derived fallback
  4:  _deltaTimeS       (NUMBER) elapsed interval, s, >= 0
  5:  _fullFuelMassKg   (NUMBER) full fuel mass, kg, > 0
  6:  _fuelCgArmM       (NUMBER) fuel centre-of-gravity arm, m

Return Value: ARRAY - [remainingFuelMassKg, cgOffsetM], or [-1, -1] when an
input is unusable.
Example: [500, 0.1, 0, 0, 10, 600, 2.5] call aee_mobility_fnc_calculateFuelBurn
Public: No
*/

params [
    ["_fuelMassKg", 0, [0]],
    ["_sourcedRateKgS", 0, [0]],
    ["_sfcKgKwh", 0, [0]],
    ["_ratedPowerW", 0, [0]],
    ["_deltaTimeS", 0, [0]],
    ["_fullFuelMassKg", 0, [0]],
    ["_fuelCgArmM", 0, [0]]
];

if (_fuelMassKg < 0) exitWith { [-1, -1] };
if (_deltaTimeS < 0) exitWith { [-1, -1] };
if (_fullFuelMassKg <= 0) exitWith { [-1, -1] };

// The sourced rate wins. When the corpus holds none, derive the burn from
// the specific fuel consumption and the rated power.
private _rate = _sourcedRateKgS;
if (_rate <= 0) then {
    _rate = (_sfcKgKwh * _ratedPowerW) / 3.6e6;
};
_rate = _rate max 0;

private _remaining = (_fuelMassKg - (_rate * _deltaTimeS)) max 0;
private _cgOffset = _fuelCgArmM * (_remaining / _fullFuelMassKg);

[_remaining, _cgOffset]
