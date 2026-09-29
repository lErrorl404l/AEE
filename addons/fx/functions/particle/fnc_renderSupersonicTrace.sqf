#include "..\..\script_component.hpp"

/*
Refractive shock trace renderer (issue #217 follow-on).

A supersonic round steps the air density across its bow shock, and the
index of refraction of air tracks density, so the step bends light.
fnc_calculateSupersonicTrace returns that refractive index contrast in
units of 1e-4.  This function draws the contrast on the local player's own
round, using the engine's refractive billboard as the sprite.

HONESTY.  Three limits hold and none of them may be dropped from this
file.  First, the kernel models the REFRACTIVE component only.  It does
not model condensation, so this is not a vapour trail and not a
condensation trail.  Second, the kernel value is a CEILING.  A round with
a meplat carries a detached bow shock whose contrast at the surface is
lower than the ceiling, so the drawn distortion is an UPPER BOUND and
never an exact value.  Third, the step from refractive units to a sprite
size and an alpha is a VISUAL MAPPING chosen for legibility.  It is not
an optical relation, and the kernel never sees it.

WHY THIS IS NOT A PARTICLE PIPELINE GATE.  The shared pipeline runs on
the coarse environment interval aee_core_updateInterval, and its advect
step overwrites the velocity of every live source with the local wind.
Both would fight an emitter parented to a fast round, so this renderer
is self-contained and does not register with fnc_registerParticleSource.

CLIENT ONLY.  The handler passes only the local player's own round, so
the source attached here is always local.  The function also refuses
without an interface, so a dedicated server creates nothing.

The live contrast is re-read every tick from the round's CURRENT
velocity, which is argument 0 of the kernel.  The muzzle value published
by the Fired handler is deliberately not read here.

CONCURRENCY.  Several rounds can be in the air.  At most _MAX_TRACES
traces draw at once and a new shot is skipped at the cap, so a running
trace is never cut short to make room.

Arguments:
  0: projectile (OBJECT, the round to draw the trace on)

Returns: nothing.  Side effect: one particle source per accepted shot,
and one record on aee_fx_supersonicTrace until that trace ends.
*/

params [["_projectile", objNull, [objNull]]];

if (!hasInterface) exitWith {};
if (isNull _projectile) exitWith {
    AEE_LOG_WARN("supersonic trace refused: projectile is null");
};

// Bound the cost when several rounds are airborne.
private _MAX_TRACES = 4;

private _traces = missionNamespace getVariable [QGVAR(supersonicTrace), []];
_traces = _traces select { alive (_x getOrDefault ["source", objNull]) };
if (count _traces >= _MAX_TRACES) exitWith {
    private _logMsg = format ["supersonic trace refused: %1 live at the cap of %2", count _traces, _MAX_TRACES];
    AEE_LOG_DEBUG(_logMsg);
};

// The sprite shape is declared once in CfgCloudlets and read here, so the
// engine path has a single source.
private _shape = getText (configFile >> "CfgCloudlets" >> "AEE_SupersonicTrace" >> "particleShape");
if (_shape == "") exitWith {
    AEE_LOG_WARN("supersonic trace refused: CfgCloudlets AEE_SupersonicTrace carries no particleShape");
};

// The kernel takes air density and air temperature.  The flight is short,
// so the values are read once here rather than re-read every tick.
private _environment = call EFUNC(ballistics,getEnvironmentState);
_environment params ["_tempC", "_pressureHPa", "_rhoRel"];

private _source = "#particlesource" createVehicleLocal [0, 0, 0];
_source attachTo [_projectile, [0, 0, 0]];

private _record = createHashMapFromArray [
    ["source", _source],
    ["projectile", _projectile],
    ["contrast", 0]
];
_traces pushBack _record;
missionNamespace setVariable [QGVAR(supersonicTrace), _traces];

// The per-tick re-read and the reap sit in one loop, so a reader can see
// both together.  The loop ends when the round leaves the supersonic
// regime, dies, or outlives the sprite.  A trace the air no longer
// supports must not be forced into being.
// Diagnostics.  AEE_LOG_DEBUG is gated on the aee_fx_logDebug setting,
// AEE FX then Diagnostics, so it costs nothing until that box is ticked.
private _netId = netId _projectile;
private _logMsg = format ["supersonic trace open: %1 %2, rhoRel %3, tempC %4, shape %5", _netId, str _projectile, _rhoRel, _tempC, _shape];
AEE_LOG_DEBUG(_logMsg);

[_projectile, _source, _record, _shape, _rhoRel, _tempC, _netId] spawn {
    params ["_projectile", "_source", "_record", "_spriteShape", "_rhoRel", "_tempC", "_netId"];

    private _born = time;
    private _contrast = 1;
    private _MAX_LIFE = 3;
    private _ticks = 0;
    // 20 ticks at 0.05 s is about 1 Hz, so the fade reads as a trend in
    // the log instead of a wall of lines.
    private _LOG_EVERY = 20;
    private _nextLog = _LOG_EVERY;
    private _logMsg = "";

    while {
        _contrast > 0
        && {alive _projectile}
        && {(time - _born) < _MAX_LIFE}
    } do {
        private _speed = vectorMagnitude (velocity _projectile);
        _contrast = [_speed, _rhoRel, _tempC] call EFUNC(ballistics,calculateSupersonicTrace);
        _record set ["contrast", _contrast];

        // --- Visual mapping, not physics -------------------------------
        // The kernel returns a refractive index contrast in units of 1e-4,
        // and the engine draws a sprite, so the number must become a size
        // and an alpha.  This map is chosen for LEGIBILITY: a round just
        // past Mach 1 shows faintly, and 8 units, about Mach 2.6 at sea
        // level, shows fully.  It is not an optical relation.  The kernel
        // never sees these numbers, and it never scales its own result.
        private _legibility = linearConversion [0, 8, _contrast, 0, 1, true];
        _legibility = _legibility max 0;

        // The drop interval must come from the round's SPEED, not from a fixed
        // time. A fixed interval is wrong at every speed: at 474 m/s and
        // legibility 0.21 the old 0.162 s interval put a 0.49 m sprite every
        // 77 m, which covers 0.6 percent of the path. That is why no trail was
        // visible even though the 2026-09-29 RPT proved 55 traces opened,
        // tracked and closed. Deriving the interval from the speed keeps
        // consecutive sprites overlapping by construction, at any speed.
        private _size = 0.2 + (1.4 * _legibility);
        private _safeSpeed = _speed max 1;
        private _drop = (_size / (2 * _safeSpeed)) max 0.0001;
        // The lifetime is derived from the drop, so the LIVE SPRITE COUNT is
        // what is bounded, at any speed. A fixed 0.10 s lifetime is safe at the
        // 474 m/s the RPT happened to sample and gives 1074 square metres at the
        // 940 m/s muzzle, 1.6 times the 642 that stuttered on 27 Sep. 25 live
        // sprites per trace caps the overdraw at 204 square metres across four
        // and shortens the trail to about 18 m, which is the length of the bow
        // shock itself rather than a contrail.
        private _ttl = 25 * _drop;

        // Measured against the kernel the contrast is NOT small, so the map
        // above is not why a trace is hard to see.  A 5.56 at 940 m/s returns
        // 7.27 and a 7.62 at 725 m/s returns 5.13, so a rifle round sits
        // between legibility 0.64 and 0.91.  A refractive distortion is faint
        // by nature, so the peak alpha is raised to 0.60 from 0.40.  ALPHA IS
        // THE ONLY FREE LEVER: fill rate is sprite count times sprite area,
        // and a refract billboard samples the framebuffer, so an earlier
        // attempt that also widened the sprite to 2.4 m and shortened the
        // drop interval tripled the overdraw (190 to 642 square metres
        // across four traces) and the client stuttered.  Size and interval
        // therefore stay at the original values.  Those values are retained
        // for SIZE, and the ALPHA FLOOR is raised from 0.05 to 0.20 because
        // alpha is free.  The INTERVAL is no longer fixed, for the reason
        // given at its derivation above.  The particle lifetime is shortened
        // to 0.10 s to pay for the higher rate, which keeps the live sprite
        // count at about 192 per trace and the overdraw near the 190 square
        // metres already measured as acceptable, against 642 which stuttered.
        // These remain a VISUAL MAPPING.  None of them is an optical relation
        // and the kernel never sees them.
        _source setParticleParams [
            [_spriteShape, 1, 0, 0, 0], "", "Billboard",
            1, 0.4, [0, 0, 0], [0, 0, 0], _ttl, _ttl, 0.02, 0.02,
            [0.05, _size],
            [[1, 1, 1, 0], [1, 1, 1, 0.20 + (0.55 * _legibility)], [1, 1, 1, 0]],
            [1000], 0.05, 0.02, "", "", _source
        ];
        _source setDropInterval _drop;

        // A throttled trend line, so the fade reads as a series rather
        // than a wall of lines.
        _ticks = _ticks + 1;
        if (_ticks >= _nextLog) then {
            _logMsg = format ["supersonic trace %1: speed %2 m/s, contrast %3, legibility %4", _netId, round _speed, round (_contrast * 100), round (_legibility * 100)];
            AEE_LOG_DEBUG(_logMsg);
            _nextLog = _ticks + _LOG_EVERY;
        };

        sleep 0.05;
    };

    // Name the reason, so a trace that vanishes is diagnosable rather
    // than mysterious.
    private _reason = "sprite lifetime expired";
    if (_contrast <= 0) then { _reason = "round left the supersonic regime" };
    if (!alive _projectile) then { _reason = "round destroyed" };
    _logMsg = format ["supersonic trace %1 closed after %2 ticks: %3", _netId, _ticks, _reason];
    AEE_LOG_DEBUG(_logMsg);

    // Deterministic reap.  On impact the round is gone, so the shock is
    // gone and the trace ends there.  That cut is physics, not a defect:
    // no bow shock stands off a stopped round.
    deleteVehicle _source;
    _record set ["source", objNull];

    private _live = missionNamespace getVariable [QGVAR(supersonicTrace), []];
    _live = _live select { alive (_x getOrDefault ["source", objNull]) };
    missionNamespace setVariable [QGVAR(supersonicTrace), _live];
};
