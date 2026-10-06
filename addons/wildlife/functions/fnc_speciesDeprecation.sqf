#include "..\script_component.hpp"

/*
One INFO deprecation for the retired fnc_speciesForBiome.

Impure by design: it reads and writes the once-guard on the mission
namespace and emits the log.  The guard holds a Bool, so a repeat call does
nothing.  Kept apart from the pure shim so the kernel tests can stub it.

Arguments: none.

Returns:
  Nothing.
*/

if (missionNamespace getVariable [QGVAR(speciesDeprecationLogged), false]) exitWith {};

missionNamespace setVariable [QGVAR(speciesDeprecationLogged), true];
AEE_LOG_INFO("fnc_speciesForBiome is deprecated; use fnc_getSpeciesMatch")
