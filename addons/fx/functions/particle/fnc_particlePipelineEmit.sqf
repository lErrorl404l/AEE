#include "..\..\script_component.hpp"

/*
Emit one particle source for the pipeline (issue #149).

Split out of fnc_particlePipeline so the lifecycle stays readable: this
function owns the engine call surface, the pipeline owns the order of
operations.  It builds the ParticleArray from three sources and no others:

  - the material physics (fnc_particleState, or fnc_kickupParams for a
    surface effect): weight, volume, rubbing, bounceOnSurface
  - the emission numbers from the request (fnc_particleEmission):
    intensity, colour, rate
  - the LOCAL wind field (#136 getLocalWind): moveVelocity slant and angle

Water spray is placed on the surface (ParticleArray index 20, onSurface)
with the wave height as the emitter offset, so it rides the actual wave
(issue #150).  The cosmetic spawn randomness lives only in
setParticleRandom.

Arguments:
  0: effect (STRING)
  1: request (HASHMAP)
  2: row (HASHMAP, the config row)

Returns: the source record (HASHMAP), or an empty HashMap when nothing
         was created.
*/

params [
    ["_effect", "", [""]],
    ["_req", createHashMap, [createHashMap]],
    ["_row", createHashMap, [createHashMap]]
];

private _material = _req getOrDefault ["material", _row getOrDefault ["material", "dust"]];
private _pos = _req getOrDefault ["position", [0, 0, 0]];
private _emitter = _req getOrDefault ["emitter", objNull];
private _intensity = _req getOrDefault ["intensity", 0];
private _colour = _req getOrDefault ["colour", [1, 1, 1, 1]];
private _rate = _req getOrDefault ["rate", 0];
private _lift = _req getOrDefault ["lift", 0.6];

// ─── Material physics ────────────────────────────────────────────────────
private _state = if (_row getOrDefault ["surface", false]) then {
    [_material, _lift, _colour, _pos] call FUNC(kickupParams)
} else {
    [_material, _pos] call FUNC(particleState)
};
private _weight = _state select 0;
private _volume = _state select 1;
private _rubbing = _state select 2;
private _bounce = _state select 3;
private _keepOnSurface = _state select 5;
private _surfaceOffset = _state select 6;

// ─── Geometry, lifetime, wind slant ──────────────────────────────────────
private _lifetime = _row getOrDefault ["lifetime", 1];
private _size = _row getOrDefault ["size", [0.2, 0.5]];
private _circle = _req getOrDefault ["radius", _row getOrDefault ["circle", 1]];
private _fall = _row getOrDefault ["fall", 0];
private _slant = _row getOrDefault ["slant", 0];

private _wind = [_pos] call EFUNC(atmos,getLocalWind);
private _moveVelocity = [(_wind select 0) * _slant, (_wind select 1) * _slant, _fall];
private _angle = (_wind select 0) atan2 (_wind select 1);

// Water spray rides the wave surface (issue #150): onSurface places the
// particle on the surface, and the wave height is the offset above the
// flat sea plane.
private _onSurface = _keepOnSurface || (_row getOrDefault ["onSurface", false]);
private _emitZ = if (_keepOnSurface) then { (_pos select 2) + _surfaceOffset } else { _pos select 2 };
private _emitPos = [_pos select 0, _pos select 1, _emitZ];

// ─── Create and configure the source ─────────────────────────────────────
private _source = "#particlesource" createVehicleLocal _emitPos;
if ((_row getOrDefault ["attach", true]) && {!isNull _emitter}) then {
    _source attachTo [_emitter, [0, 0, 0]];
};

private _alpha = (_intensity min 1) * 0.6;
private _rgb = [_colour select 0, _colour select 1, _colour select 2];
private _params = [
    ["\A3\data_f\ParticleEffects\Universal\Universal.p3d", 16, 12, 9, 0],
    "",
    "Billboard",
    1,
    _lifetime,
    [0, 0, 0],
    _moveVelocity,
    0,
    _weight,
    _volume,
    _rubbing,
    _size,
    [_rgb + [0], _rgb + [_alpha], _rgb + [0]],
    [0.5],
    1,
    0,
    "",
    "",
    _emitter,
    _angle,
    _onSurface,
    _bounce
];

_source setParticleCircle [_circle, [0, 0, 0]];
_source setParticleRandom [
    _lifetime * 0.3,
    [(_circle * 0.5) max 0.1, (_circle * 0.5) max 0.1, 0],
    [0, 0, 0],
    0,
    0,
    [0, 0, 0, 0],
    0,
    0,
    _angle
];
_source setParticleParams _params;
_source setDropInterval (1 / (_rate max 0.01));

// ─── Register with the allocator ─────────────────────────────────────────
private _priority = _req getOrDefault ["priority", _row getOrDefault ["priority", 0]];
private _particles = _row getOrDefault ["particles", 0];
private _ttl = _row getOrDefault ["ttl", -1];
private _key = _req getOrDefault ["key", ""];
[_source, _effect, _priority, _particles, _ttl, _key] call FUNC(registerParticleSource);

// Keep the ParticleArray on the record so the pipeline's advect pass can
// update the slant in place without rebuilding it.  Return the record so
// the pipeline can refresh its expiry while the gate keeps passing.
private _record = createHashMap;
{
    if ((_x getOrDefault ["source", objNull]) isEqualTo _source) exitWith {
        _x set ["params", _params];
        _record = _x;
    };
} forEach (missionNamespace getVariable [QGVAR(particleSources), []]);

_record
