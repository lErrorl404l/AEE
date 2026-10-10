---
title: "Fixed-wing performance: density altitude, ground effect, landing"
---

# Fixed-wing performance (issue #22)

This page records the physics and the sources behind the fixed-wing
performance model: density altitude, the engine power or thrust lapse, the
ground-effect induced-drag reduction, and the landing performance.  Every
value is grounded in a named formula.  A value with no held source is marked
UNSOURCED.

The model is deliberately minimal.  It uses the repo's existing air-density
kernel (`aee_ballistics_fnc_calculateAirDensityKernel`) and the density ratio
`rho / 1.225` that the helicopter lift and airframe load kernels already read.
It adds no second model of the same physics.

## Density altitude

Density altitude is the pressure altitude corrected for a non-standard air
temperature.  The FAA rule of thumb adds 120 ft of density altitude for every
degree Celsius the air is warmer than ISA:

```
DA = PA + 120 * (OAT - ISA_T)
ISA_T = 15 - 1.98 * (PA / 1000 ft)
```

1.98 C per 1000 ft is the ISA lapse rate of 6.5 C per 1000 m.  In SI the rule
is 36.576 m of density altitude per degree C, and the lapse term is 0.0065 C
per metre.

Source: FAA Pilot's Handbook of Aeronautical Knowledge, Ch. 11 (Density
Altitude).  ISA lapse rate 6.5 C/km and sea-level 15 C: ICAO Doc 7488 / ISO
2533.

Implemented in `aee_flight_fnc_calculateDensityAltitude`.

## Engine power and thrust lapse

The available power or thrust falls as the air thins.  The exponent depends on
the engine cycle:

| Engine | Ratio | Source |
|---|---|---|
| Naturally-aspirated piston | `P / P0 = sigma^1.2` | SAE J1349 density correction |
| Turbojet | `T / T0 = sigma` | standard thrust lapse |
| Turbofan | `T / T0 = sigma^0.7` | standard thrust lapse |
| Turboprop | `T / T0 = sigma` | UNSOURCED (see below) |

`sigma` is the density ratio `rho / 1.225` (ISO 2533).  The piston exponent 1.2
reproduces the 3 percent per 1000 ft rule within one to two points: sigma 0.789
at 8000 ft gives 0.752.  The issue names only the piston and the two jets.  A
turboprop is taken as gas-turbine-like; its exponent is UNSOURCED.

Implemented in `aee_flight_fnc_calculatePowerRatio`.

## Ground effect

Within about one wingspan of the ground the wing's trailing vortices are
suppressed, so the induced drag falls.  The FAA Airplane Flying Handbook gives
the empirical reduction against the height-to-wingspan ratio `h/b`:

| h/b | Induced-drag reduction |
|---|---|
| 0.1 | 50 percent |
| 0.25 | 40 percent |
| 0.5 | 25 percent |
| 1.0 | 10 percent |

The curve is linear between those points, clamped to 50 percent at or below
`h/b = 0.1`, and zero above one wingspan (free air).

Source: FAA Airplane Flying Handbook (FAA-H-8083-3), ground effect.  The
McCormick vortex model, `CDi_GE = CDi * (1 - 1/(1 + 16 (h/b)^2))`, is the
analytic alternative.  It overpredicts (86 percent at `h/b = 0.1`) and is not
used here.

Implemented in `aee_flight_fnc_calculateGroundEffect`.

## True airspeed, stall speed and landing

The derived quantities follow from the density ratio:

```
TAS       = IAS / sqrt(sigma)          (FAA, true versus indicated)
V_stall   = V_stall0 / sqrt(sigma)     (lift = 0.5 rho V^2 S CL)
takeoff   = 1 / (sigma * power)        (takeoff ground-roll multiplier)
landing   = 1 / sigma                  (landing ground-roll multiplier)
```

The takeoff multiplier follows the takeoff ground-roll relation
`S_g = 1.21 W^2 / (g rho S CL_max (T - D))`, with the rotation factor
`1.21 = 1.1^2`.  With W, S and CL_max fixed the roll scales as `1/(rho T)`,
that is `1/(sigma * power)`.  It reproduces the issue's jet anchor (1.61 at
8000 ft) and piston anchor (1.6 to 1.7).  The landing roll
`S_L = 1.69 W / (g rho S CL_max mu)` scales as `1/rho = 1/sigma` (1.27 at
8000 ft).

A headwind shortens the ground roll by 1 percent per knot and a tailwind
lengthens it by 5 percent per knot.  Source: FAA Airplane Flying Handbook; the
takeoff and landing ground-roll relations are from the flight-mechanics
references in the issue.

Implemented in `aee_flight_fnc_calculateFixedWingPerformance`.

## The runtime

`aee_flight_fnc_updateFixedWingPerformance` publishes the ambient density
altitude and density ratio once a second when the `aee_flight_fixedWingPerformance`
setting is on.  The per-aircraft performance row is computed on demand from the
pure kernel.  `aee_flight_fnc_logFixedWingState` reports the ambient row under
the flight debug gate.

## Sources

- FAA Pilot's Handbook of Aeronautical Knowledge, Ch. 11 (density altitude,
  TAS versus IAS).
- FAA Airplane Flying Handbook (FAA-H-8083-3), ground effect.
- SAE J1349, engine power density correction.
- ICAO Doc 7488 / ISO 2533, ISA lapse rate and sea-level density.
- McCormick (1979), Aerodynamics, Aeronautics, and Flight Mechanics
  (ground-effect vortex model, the analytic alternative).

## What is not modelled

The engine does not model Mach effects, propeller efficiency, or flap and gear
functions; the issue's honest verdict is to skip them for the minimal model.
The turboprop power exponent is UNSOURCED.  No takeoff or landing roll is
applied to the engine, because the engine exposes no takeoff-distance surface;
the roll is a derived value.
