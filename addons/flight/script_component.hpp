#define COMPONENT flight
#define COMPONENT_BEAUTIFIED AEE Flight
#include "\z\aee\addons\lib\script_mod.hpp"
#include "\z\aee\addons\lib\script_macros.hpp"

// ── Flight forces ──────────────────────────────────────────────────────────
// Bounds for the scripted flight-force layer.  The gust force is aerodynamic
// and sourced: F = 0.5 rho v^2 (Cd S), the dynamic pressure times the
// airframe's effective drag area.  The drag area and the reference it comes
// from are held in the aircraft corpus (data/aircraft/SCHEMA.md section 5).
// The cap below is a stated perturbation bound, not a measured coefficient.
// See docs/adr/ADR-017-flight-physics-ceiling.md.

// A turbulence force is capped at this fraction of the aircraft weight, so a
// gust can never dominate the airframe.
#define TURBULENCE_FORCE_CAP_FRACTION 0.25
// The air density (kg/m3) is capped at this multiple of ISA sea level before
// it scales a force.
#define TURBULENCE_DENSITY_RATIO_MAX 1.5
// The rotary attitude nudge is this fraction of the applied gust force.
#define TURBULENCE_TORQUE_FRACTION 0.05

// ISA sea-level air density, kg/m3 (ISO 2533).
#define AERO_ISA_SEA_LEVEL_DENSITY 1.225
// Density lift loss is capped here (thin air, before the combined cap).
#define AERO_DENSITY_LIFT_LOSS_MAX 0.6
// Full-severity icing lift loss.  UNSOURCED: FAR 25 App C gives the
// accretion envelope, not a lift-loss coefficient.
#define AERO_ICE_LIFT_LOSS_MAX 0.35
// Full-severity icing drag rise.  UNSOURCED, same reason.
#define AERO_ICE_DRAG_RISE_MAX 0.5
// The combined lift loss is capped here so the airframe cannot be stalled.
#define AERO_LIFT_LOSS_CAP 0.45
// Effective drag area Cd*S for the added-drag term, m2.  The declared default
// the air-engine kernel uses.
#define AERO_DRAG_AREA_M2 0.7
// Fallback mass when the engine reports none for an air vehicle, kg.
#define AERO_DEFAULT_AIRCRAFT_MASS_KG 1000
// The declared default spool time constant for a light turboshaft, s.  It is
// a declared value, not a measurement, and it is the same tau
// fnc_calculateEngineNg.sqf uses.
#define AEE_ENGINE_SPOOL_TAU_S 4
