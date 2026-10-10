#include "..\..\script_component.hpp"

/*
Register a particle source with the allocator (issue #149).

The tracker is a list of RECORDS, one per live source, so the allocator can
weigh each source by priority and particle count, and the pipeline can
advect and cull it.  A record is a HashMap:

  source    - the #particlesource object
  effect    - the config effect name
  priority  - allocation priority
  particles - estimated live particle count
  expiry    - mission time the source dies, or -1 for no expiry
  key       - the stacking key (effect + emitter), "" for a one-shot
  params    - the last ParticleArray, for the per-tick advect update

Arguments (all optional except the source):
  0: source (OBJECT)
  1: effect (STRING)
  2: priority (NUMBER)
  3: particles (NUMBER)
  4: ttl (NUMBER, seconds; -1 = no expiry)
  5: key (STRING)
*/

params [
    ["_source", objNull, [objNull]],
    ["_effect", "", [""]],
    ["_priority", 0, [0]],
    ["_particles", 0, [0]],
    ["_ttl", -1, [0]],
    ["_key", "", [""]]
];
if (isNull _source) exitWith {};

private _record = createHashMapFromArray [
    ["source", _source],
    ["effect", _effect],
    ["priority", _priority],
    ["particles", _particles],
    ["expiry", [-1, time + _ttl] select (_ttl >= 0)],
    ["key", _key],
    ["params", []]
];

private _sources = missionNamespace getVariable [QGVAR(particleSources), []];
_sources pushBack _record;
missionNamespace setVariable [QGVAR(particleSources), _sources];

