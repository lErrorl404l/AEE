#include "..\..\script_component.hpp"

/*
Priority particle allocator (issue #149).

Replaces the old first-come budget gate.  Effects compete for the shared
budget by priority: a high-priority effect (hail, hurricane, fire,
lightning, visible CBRN) preempts a lower one (ambient dust) when the
ceiling is reached, instead of the later caller simply being refused.

The ceilings are the ones the gate carried: 20 sources and 18,000
particles (the engine ceiling), from fnc_checkParticleBudget.

Arguments:
  0: effect (STRING, for diagnostics)
  1: priority (NUMBER)
  2: particles (NUMBER, the source's estimated live particle count)

Returns: BOOLEAN — true when the caller may emit.
Side effect: deletes preempted sources and prunes dead ones.
*/

params [
    ["_effect", "", [""]],
    ["_priority", 0, [0]],
    ["_particles", 0, [0]]
];

private _MAX_SOURCES = 20;
private _MAX_PARTICLES = 18000;

private _sources = missionNamespace getVariable [QGVAR(particleSources), []];
// Prune sources the engine has already removed.
_sources = _sources select { alive (_x getOrDefault ["source", objNull]) };

private _count = count _sources;
private _used = 0;
{ _used = _used + (_x getOrDefault ["particles", 0]); } forEach _sources;

// Preempt the lowest-priority source below the requester until the budget
// fits.  A requester can never preempt its own priority or higher.
private _guard = 0;
while {(_count >= _MAX_SOURCES || (_used + _particles) > _MAX_PARTICLES) && _guard < _MAX_SOURCES} do {
    private _victimIndex = -1;
    private _victimPriority = _priority;
    {
        private _p = _x getOrDefault ["priority", 0];
        if (_p < _victimPriority) then {
            _victimPriority = _p;
            _victimIndex = _forEachIndex;
        };
    } forEach _sources;
    if (_victimIndex < 0) exitWith {};
    private _victim = _sources select _victimIndex;
    deleteVehicle (_victim getOrDefault ["source", objNull]);
    _used = _used - (_victim getOrDefault ["particles", 0]);
    _sources deleteAt _victimIndex;
    _count = count _sources;
    _guard = _guard + 1;
};

private _granted = (_count < _MAX_SOURCES) && {(_used + _particles) <= _MAX_PARTICLES};

missionNamespace setVariable [QGVAR(particleSources), _sources];
_granted
