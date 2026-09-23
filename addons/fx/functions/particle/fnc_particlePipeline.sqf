#include "..\..\script_component.hpp"

/*
Particle pipeline (issue #149) — the ONE lifecycle handler for every AEE
particle effect.

Called once per tick from fnc_updateEnvironment, it replaces the four
per-function emitters (and the new weather emitters) with a single pass:

  register -> allocate -> emit -> advect -> cull

1. Each effect gate returns a request (or none) after its own object gate.
2. A request whose stacking key is already live is skipped.
3. fnc_particleAllocate grants the source by priority.
4. The pipeline builds the ParticleArray from the material physics
   (fnc_particleState / fnc_kickupParams), the emission numbers
   (fnc_particleEmission) and the LOCAL wind field (#136 getLocalWind).
5. Live sources are advected from the local wind and culled on expiry.

Client-gated inside the function: the tick that calls this has no
hasInterface guard, so a dedicated server must not create sources.

The emission numbers are deterministic (fnc_particleEmission); only the
cosmetic spawn here varies per machine, and only in setParticleRandom,
which shapes a billboard sprite.  No simulation state depends on it.
*/

if (!hasInterface) exitWith {};

private _cfg = call FUNC(particleEffectConfig);

// ─── 1. Collect requests from the effect gates ───────────────────────────
// Each gate keeps its own physics gate and returns an ARRAY of requests
// (empty when gated out).
private _gates = [
    FUNC(applyVehicleDust),
    FUNC(applyFootfallDust),
    FUNC(applyAtmosphericDust),
    FUNC(applyRotorWash),
    FUNC(applyWeatherParticles)
];
private _requests = [];
{
    private _reqs = [] call _x;
    if (_reqs isEqualType []) then { _requests append _reqs; };
} forEach _gates;

// ─── 2. Live sources by stacking key ─────────────────────────────────────
private _sources = missionNamespace getVariable [QGVAR(particleSources), []];
private _liveByKey = createHashMap;
{
    if (alive (_x getOrDefault ["source", objNull])) then {
        _liveByKey set [_x getOrDefault ["key", ""], _x];
    };
} forEach _sources;

// ─── 3. Allocate and emit ────────────────────────────────────────────────
{
    private _req = _x;
    private _effect = _req getOrDefault ["effect", ""];
    private _key = _req getOrDefault ["key", ""];
    private _row = _cfg getOrDefault [_effect, createHashMap];
    private _live = _liveByKey getOrDefault [_key, createHashMap];
    if (count _live > 0) then {
        // The gate still passes: keep the live source, refresh its expiry so
        // it survives while the condition holds and dies when it stops.
        private _ttl = _row getOrDefault ["ttl", -1];
        if (_ttl >= 0) then { _live set ["expiry", time + _ttl]; };
    } else {
        private _priority = _req getOrDefault ["priority", _row getOrDefault ["priority", 0]];
        private _particles = _row getOrDefault ["particles", 0];
        if ([_effect, _priority, _particles] call FUNC(particleAllocate)) then {
            private _record = [_effect, _req, _row] call FUNC(particlePipelineEmit);
            if (count _record > 0 && _key != "") then {
                _liveByKey set [_key, _record];
            };
        };
    };
} forEach _requests;

// ─── 4. Advect live sources from the local wind field ────────────────────
// The engine's rubbing couples the particle to the wind continuously; this
// refresh keeps the initial velocity and the angle aligned with the LOCAL
// field (#136), so smoke curls around a building and dust channels down a
// street as the wind turns.
_sources = missionNamespace getVariable [QGVAR(particleSources), []];
{
    private _source = _x getOrDefault ["source", objNull];
    private _row = _cfg getOrDefault [_x getOrDefault ["effect", ""], createHashMap];
    private _params = _x getOrDefault ["params", []];
    if (alive _source && {_params isNotEqualTo []} && {count _row > 0}) then {
        private _wind = [getPosASL _source] call EFUNC(atmos,getLocalWind);
        private _slant = _row getOrDefault ["slant", 0];
        _params set [6, [(_wind select 0) * _slant, (_wind select 1) * _slant, _row getOrDefault ["fall", 0]]];
        _params set [19, (_wind select 0) atan2 (_wind select 1)];
        _source setParticleParams _params;
    };
} forEach _sources;

// ─── 5. Cull dead and expired sources ────────────────────────────────────
private _now = time;
_sources = _sources select {
    private _source = _x getOrDefault ["source", objNull];
    private _alive = alive _source;
    private _expiry = _x getOrDefault ["expiry", -1];
    if (_alive && _expiry >= 0 && _now > _expiry) then {
        deleteVehicle _source;
        _alive = false;
    };
    _alive
};
missionNamespace setVariable [QGVAR(particleSources), _sources];
