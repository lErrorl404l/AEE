#include "..\..\script_component.hpp"

/*
Register a particle source with the budget tracker.

Parameter: _source — #particlesource object to track

Adds the source to QGVAR(particleSources) array.  Called by
particle-creating functions after spawning a new source.
*/

params ["_source"];
if (isNull _source) exitWith {};

private _sources = missionNamespace getVariable [QGVAR(particleSources), []];
_sources pushBack _source;
missionNamespace setVariable [QGVAR(particleSources), _sources];
