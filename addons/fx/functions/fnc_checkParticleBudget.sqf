#include "..\script_component.hpp"

/*
Particle budget check — counts active AEE particle sources and
returns true if under the budget ceiling.

Budget: 20 sources (safety net; engine ceiling is 18,000 particles).
Stacking guards limit each function to 1 source, so actual count
is typically 5 (one per particle system).

Returns: boolean — true if a new source can be created.
Side effect: cleans up dead sources from the tracking array.
*/

private _sources = missionNamespace getVariable [QGVAR(particleSources), []];

// Clean up dead sources
_sources = _sources select {alive _x};
missionNamespace setVariable [QGVAR(particleSources), _sources];

// ponytail: source-count budget, 20 sources max
// Engine ceiling is 18,000 particles.  With stacking guards,
// actual count is ~5 sources / ~178 particles.
count _sources < 20
