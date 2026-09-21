#include "..\..\script_component.hpp"
/*
Drive the engine's view distance from AEE's physics (issue #138).

The mod computes the full visibility state (fog, haze, rain attenuation,
NELM, thermal contrast) but nothing drives viewDistance — a soldier in
dense fog sees to the engine's default range, not the physics range.
This closes the loop: the engine renders what the eye can actually see,
and it is performance-positive (mostly LOWERS view distance in weather).

The driver (vision science):
  viewDistance = min(horizon, Koschmieder V, acuityLimit, 12000)

  sigma_total = sigma_fog + sigma_haze + sigma_rain     (per km)
    sigma_fog  = fogDensity * 10
    sigma_haze = haze * 1.0
    sigma_rain = 0.21 * rainRate^0.74                    (Atlas 1954)
  Koschmieder: V = 3.912 / sigma_total                   (km)
  Horizon: at 1.7 m eye height ~4.7 km; use the player's actual
    eye height: sqrt(2 * R_earth * eyeHeightASL)
  Acuity: the Johnson detection criterion caps useful range at
    ~6 km for a standing man (1.8 m at 1 arcmin); below that the
    eye cannot resolve the target regardless of clarity.
  Night: at NELM < 6 the eye's sensitivity limits range further:
    100 + (NELM - 2) * 300 m, applied when the sun is down.

Rate limiting: 500 m deadband + 4 s ramp, 1 Hz.  The engine fog already
fades objects at the fog range; matching view distance to it makes them
consistent and avoids streaming churn.

Input:  none (reads the shared state)
Output: none (applies setViewDistance + setObjectViewDistance on the
        local player - object distance follows terrain at 1/2, the BI
        guidance for the "CPU killer" lever, issue #139)

Caveat: script-driven per client, so this runs on each machine's own
view distance.  Hosts (dedicated server) have no camera; the function
guards on isMultiplayer + hasInterface.
*/

params [];

// ─── Read the physics inputs ─────────────────────────────────────────────
private _fog   = missionNamespace getVariable [QEGVAR(core,currentFogDensity),      0];
private _haze  = missionNamespace getVariable [QEGVAR(core,currentHaze),             0];
private _nelm  = missionNamespace getVariable [QEGVAR(optics,limitingMagnitude),     6.5];
private _sunDown = (parseNumber (sunOrMoon < 0));

// Rain rate from the engine weather (rain * 25 = mm/h, per the optics
// precipitation model).  Type guards against nil/string inputs.
if !(_fog  isEqualType 0) then { _fog  = 0; };
if !(_haze isEqualType 0) then { _haze = 0; };
if !(_nelm isEqualType 0) then { _nelm = 6.5; };
private _rainMMH = (rain * 25) max 0;

// ─── Extinction coefficients (per km) ────────────────────────────────────
// Atlas 1954 rain extinction is added to fog/haze sigma (spec formula):
//   sigma_fog = fogDensity * 10
//   sigma_haze = haze * 1.0
//   sigma_rain = 0.21 * R^0.74, R in mm/h
private _sigmaFog  = _fog * 10;
private _sigmaHaze = _haze * 1.0;
private _sigmaRain = if (_rainMMH > 0) then { 0.21 * (_rainMMH ^ 0.74) } else { 0 };
private _sigmaTotal = _sigmaFog + _sigmaHaze + _sigmaRain;

// ─── Koschmieder visibility ──────────────────────────────────────────────
private _visKm = if (_sigmaTotal > 0.001) then { 3.912 / _sigmaTotal } else { 300 };
private _visM = _visKm * 1000;

// ─── Horizon from the player's actual eye height ─────────────────────────
private _eye = (eyePos player) select 2;
private _eyeRel = (_eye - (getTerrainHeightASL (getPos player))) max 1.0;
private _horizonM = 1000 * sqrt (2 * 6371 * (_eyeRel / 1000));   // km -> m

// ─── Acuity: Johnson DRI is a TARGET-resolution criterion, not a scene
// view-distance cap.  A standing man is detectable to ~6.2 km but a
// vehicle to ~14 km, and the scene itself (terrain, structures) is
// resolvable much farther.  The spec's own worked example (haze 0.2 ->
// 11.3 km, the horizon) confirms the driver must NOT hard-cap at the
// human-detection range.  Johnson is documented in the issue and left
// to the player's optics; the driver caps by horizon and clarity only.
// (Optic magnification does NOT extend the scene caps: a scope does not
// see through fog or beyond the horizon - it resolves what is already
// within them.  The driver is scene physics, not target resolution.)
private _acuityM = 1e6;

// ─── Night sensitivity ───────────────────────────────────────────────────
// NELM 2 (city) -> ~100 m; NELM 6.5 (dark sky) -> ~1.45 km.
private _nightM = 1e6;   // no limit in daylight
if (_sunDown > 0 && _nelm < 6) then {
    _nightM = 100 + ((_nelm - 2) * 300);
};

// ─── Combine ─────────────────────────────────────────────────────────────
// Explicit min chain (avoids BIS_fnc_min, not compiled on all headless
// loads, and selectMin, which the HEMTT parser rejects in assignments).
private _target = _horizonM min _visM min _acuityM min _nightM min 12000;
_target = _target max 150;   // engine floor; never less than a room

// ─── Rate limit: 500 m deadband + 4 s ramp, 1 Hz ─────────────────────────
// Client-only: the headless server has no camera to set.  The math above
// always runs (cheap, publishes diagnostics); only the engine call is
// interface-gated.
if (!hasInterface) exitWith { nil };
private _current = viewDistance;
private _new = if ((abs (_target - _current)) > 500) then {
    _current + ((_target - _current) min 500 max -500)
} else {
    _current
};
if (_new != _current) then {
    _new spawn {
        params ["_to"];
        private _from = viewDistance;
        private _t = 0;
        while {_t < 4} do {
            setViewDistance (round (_from + ((_to - _from) * (_t / 4))));
            sleep 0.1;
            _t = _t + 0.1;
        };
        setViewDistance (round _to);
    };
};

// ─── Object view distance (issue #139) ───────────────────────────────────
// BI's Performance Optimisation page names OBJECT view distance "the CPU
// killer" - the dominant cost at range, and their guidance is to set it
// to 1/3 to 1/2 of terrain view distance.  AEE drives terrain distance
// from physics (above); this drives object distance to follow, so the
// engine does not render object detail the eye cannot resolve anyway.
// The two-parameter form also sets shadow distance (the shadow impact
// table range 50-200 m maps to ~25% of object distance).
private _objTarget = (_target * 0.5) min 2000;   // 1/2 terrain, cap 2 km
private _objCurrent = getObjectViewDistance select 0;
private _newObj = if ((abs (_objTarget - _objCurrent)) > 200) then {
    _objCurrent + ((_objTarget - _objCurrent) min 200 max -200)
} else {
    _objCurrent
};
if (_newObj != _objCurrent) then {
    _newObj spawn {
        params ["_to"];
        private _from = getObjectViewDistance select 0;
        private _t = 0;
        while {_t < 4} do {
            setObjectViewDistance [
                round (_from + ((_to - _from) * (_t / 4))),
                round (_to * 0.25)
            ];
            sleep 0.1;
            _t = _t + 0.1;
        };
        setObjectViewDistance [round _to, round (_to * 0.25)];
    };
};

// ─── Publish for diagnostics ─────────────────────────────────────────────
missionNamespace setVariable [QGVAR(viewDistanceTarget), _target];
missionNamespace setVariable [QGVAR(viewDistanceSigma), _sigmaTotal];

nil
