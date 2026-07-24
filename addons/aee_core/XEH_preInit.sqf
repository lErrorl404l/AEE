#include "script_component.hpp"

params ["_logic", "_isActivating"];

// ─── CBA Settings Registration ─────────────────────────────────────────────
// Register all compile-time CfgSettings(CBA) defaults at mission start so the
// in-game CBA Settings UI and the simulation code share the same values.
#include "initSettings.inc.sqf"

// ─── Module Init ───────────────────────────────────────────────────────────
// Mark the addon as initialised.  Downstream conditions check
// aee_core_isReady before querying any environment function.
missionNamespace setVariable [QGVAR(isReady), true];

// Log successful initialisation.
AEE_LOG("Core module initialised");
