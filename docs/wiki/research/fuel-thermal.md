# Ground-vehicle fuel consumption and coolant thermal management

Issue #111. This note records the sources and the formulas behind
`data/physics/fuel.json`, the four pure kernels in `addons/vehicles/functions`,
and the driver `aee_vehicles_fnc_updateFuelConsumption`. It does not restate
the code.

## The road load

The drive power is the road-load force times the speed. The force is the
published road-load equation (Gillespie, "Fundamentals of Vehicle Dynamics",
the road-load chapter):

    F = C_rr * m * g
      + 0.5 * rho * Cd * A * v^2
      + m * g * sin(theta)
      + m * a

The rolling-resistance anchors are Gillespie's published bands: car
0.010-0.015, heavy truck 0.006-0.008, tracked vehicle 0.02-0.04, dirt road
0.0385-0.073, and about 0.30 on sand. The corpus records the midpoint of a
band as a named derivation and the single value as documented.

## The fuel rate

    fuel_L_h = BSFC[g/kWh] * (P_idle + P_drive)[kW] / rho_fuel[g/L]

The units close: BSFC times power is grams per hour, and grams per hour over
grams per litre is litres per hour.

The brake-specific fuel consumption is a best-point scalar per engine class
(Heywood, "Internal Combustion Engine Fundamentals", the BSFC maps): petrol
naturally aspirated 225 g/kWh, petrol turbocharged 240 g/kWh, diesel 206
g/kWh. The brief's own figures are 225, 230-250 and 206 (the sweet spot at
40.6 percent). The corpus records the turbo scalar at the low end of its band.

The fuel densities and lower heating values are Heywood's fuel properties:
petrol 740 g/L and 43.9 MJ/kg, diesel 840 g/L and 42.7 MJ/kg, JP-8 800 g/L
and 43.0 MJ/kg.

The relation is the ground sibling of the existing flight kernel
`aee_flight_fnc_calculateFuelBurn`, which converts a specific fuel consumption
to a mass rate, `sfc_kg_kwh * power_w / 3.6e6`. The ground kernel is the same
relation in the ground units.

## The terrain multiplier

The mobility ground state scales the rolling-resistance base: Normal 1.0,
Dusty 1.5, Frozen 1.5, Snow 2.0, Mud 2.5. The brief states surface
multipliers (highway 1.0, gravel 1.3, dirt 1.5, packed snow 1.5-2.0, deep snow
2.0-2.5, mud 2.0-3.0, sand 2.5-3.5). The corpus maps the brief's surface
bands onto the five ground states the mobility model publishes, and each
mapping names its basis. The brief is a compilation, so the mappings are held
at grade claimed.

A sustained grade needs no separate multiplier: the grade term is already in
the road-load equation, and a 5 percent grade lifts the load about 3.5 times
at low speed, which matches the brief's about 3.4 times.

## The coolant

The coolant follows the engine heat balance:

    C * dT/dt = Q_reject - UA * (T - T_ambient)

with the equilibrium T_inf = T_ambient + Q_reject / UA and the exact
exponential step T' = T_inf + (T - T_inf) exp(-dt / tau). This is the same
first-order lag and exact-exponential integration the thermal addon's vehicle
kernel `aee_thermal_fnc_calculateVehicleHeat` already uses, and UA is the same
Holman flat-plate air correlation h = 5.6 + 3.9 v times the surface area. The
two kernels answer different questions: the thermal kernel returns the engine
body heat fraction for the infrared display; the coolant kernel returns the
coolant temperature for the power derate.

The heat rejected to the coolant is one third of the fuel energy (Heywood, the
engine heat balance, the same one-third fraction the vehicle thermal kernel
already cites). The fuel mass rate the coolant consumes is the fuel kernel's
own output, so the two chains are joined, not duplicated.

The coolant bands are the brief's: normal 85-100 C, hot 100-115 C with the fan
and a power limit, overheat above 115 C derating to 50 percent, and critical
above 130 C. The derate kernel maps the temperature to the derate and the fan
state.

## The ceilings, stated

- The engine owns the tank. The driver publishes the consumption, the range
  and the coolant derate, and never calls `setFuel`, so it does not
  double-count the engine's own `fuelConsumptionRate`. A future change that
  drains the tank must first zero the engine's own rate, as the flight fuel
  system does.
- The engine class is a user setting. The corpus holds no per-vehicle engine
  class, so a per-vehicle class would be an invented value.
- The rolling-resistance base is the vehicle type, not a per-vehicle value:
  the corpus holds no per-vehicle rolling coefficient.
- A part-load BSFC penalty is not modelled. The corpus holds the best-point
  scalar; a part-load curve is a per-class calibration the corpus does not
  carry.
- The idle power is a declared default, the same declared fraction of the same
  declared rated power the engine-load kernel declares.

## References

- Gillespie, T. D. "Fundamentals of Vehicle Dynamics." SAE International,
  1992.
- Heywood, J. B. "Internal Combustion Engine Fundamentals." McGraw-Hill, 2nd
  edition, 2018.
- SAE J1349, the density and temperature correction the existing engine power
  model already cites.
- FM 4-01.41, the US Army fuel consumption data the brief names.
- ADR-042 (this feature) and ADR-033 (the aircraft fuel ceiling).
