#include "..\..\script_component.hpp"

/*
Seismic activity at the sample position (issue #27).

Reads the seismic event that the core EDEN module or the scripting entry point
published, computes the ground motion at the local position with the BA08 GMPE,
and publishes the derived state.  It applies the reachable effects:

  * camera shake, local and cosmetic, via the engine addCamShake command;
  * liquefaction subsidence and landslide displacement, server-side, only when
    the terrain-deformation setting is on and the engine is 2.10 or later;
  * a structural damage level from the intensity.

Published state (aee_persistence_*):
  seismicPGA                - peak ground acceleration (g)
  seismicPGV                - peak ground velocity (cm/s)
  seismicMMI                - Modified Mercalli intensity
  seismicLiquefactionFS     - liquefaction factor of safety at 5 m
  seismicLandslideM         - landslide displacement at the local slope (m)
  seismicDamageLevel        - 0 none, 1 light, 2 moderate, 3 collapse
  seismicDamageImpassable   - whether a structure at the level is impassable

The event itself is owned by aee_core (seismicActive, seismicMagnitude,
seismicEpicentre, seismicDepth, seismicStart).  Everything here is a
deterministic function of the event and the local position, so no state is
broadcast: each machine computes the same values.

Engine ceiling: setTerrainHeight needs engine 2.10; the mod floor on this
branch is 2.02, so the deformation is guarded by the product version and off
by default.  The camera shake is an engine effect with no physical units; the
PGA-to-power mapping in fnc_seismicShake is UNSOURCED.

Input:  [_posASL] - the sample position (ASL); empty uses the local unit.
Output: PGA (g) at the position.
Public: No
*/

params [["_posASL", [], [[]]]];

// Event state (owned by core).
private _active = missionNamespace getVariable [QEGVAR(core,seismicActive), false];
if (!_active) exitWith {
    missionNamespace setVariable [QGVAR(seismicPGA), 0];
    missionNamespace setVariable [QGVAR(seismicPGV), 0];
    missionNamespace setVariable [QGVAR(seismicMMI), 1];
    missionNamespace setVariable [QGVAR(seismicLiquefactionFS), 99];
    missionNamespace setVariable [QGVAR(seismicLandslideM), 0];
    missionNamespace setVariable [QGVAR(seismicDamageLevel), 0];
    missionNamespace setVariable [QGVAR(seismicDamageImpassable), false];
    0
};

private _mag = missionNamespace getVariable [QEGVAR(core,seismicMagnitude), 6.5];
private _depthKm = missionNamespace getVariable [QEGVAR(core,seismicDepth), 10];
private _epi = missionNamespace getVariable [QEGVAR(core,seismicEpicentre), []];
private _start = missionNamespace getVariable [QEGVAR(core,seismicStart), 0];

if (_epi isEqualTo []) exitWith { 0 };

private _pos2D = [];
if (_posASL isEqualTo []) then {
    private _player = call CBA_fnc_currentUnit;
    if (!isNil "_player" && {!isNull _player}) then { _pos2D = getPos _player; };
} else {
    _pos2D = _posASL select [0, 2];
};
if (_pos2D isEqualTo []) exitWith { 0 };

// Hypocentral (Rjb-proxy) distance: the horizontal epicentral distance and the
// focal depth.  BA08 uses Rjb; the depth is a first-order proxy for the
// unknown surface projection of the rupture.
private _horizM = _pos2D distance2D (_epi select [0, 2]);
private _depthM = _depthKm * 1000;
private _rjbKm = (sqrt (_horizM * _horizM + _depthM * _depthM)) / 1000;

private _gm = [_mag, _rjbKm] call FUNC(seismicGroundMotion);
private _pga = _gm select 0;
private _pgv = _gm select 1;
private _mmi = _gm select 2;

missionNamespace setVariable [QGVAR(seismicPGA), _pga];
missionNamespace setVariable [QGVAR(seismicPGV), _pgv];
missionNamespace setVariable [QGVAR(seismicMMI), _mmi];

// ─── Camera shake (local, cosmetic, once per event) ───────────────────────
if (GVAR(seismicShakeEnabled) && hasInterface) then {
    private _fired = missionNamespace getVariable [QGVAR(seismicShakeFired), -1];
    if (_fired != _start) then {
        missionNamespace setVariable [QGVAR(seismicShakeFired), _start];
        private _shake = [_pga, _mag] call FUNC(seismicShake);
        // addCamShake [power, duration, frequency].  The local command DB
        // records the duration argument as "duration in seconds divided by 2";
        // the source duration in seconds is passed and the effective shake is
        // about half that.  Frequency 25 is the command DB example value.
        addCamShake [(_shake select 0), (_shake select 1), 25];
    };
};

// ─── Liquefaction at a nominal 5 m layer ──────────────────────────────────
private _lq = [_pga, 5, 15, _mag, 1.5] call FUNC(seismicLiquefaction);
missionNamespace setVariable [QGVAR(seismicLiquefactionFS), _lq select 0];

// ─── Landslide from the local slope ───────────────────────────────────────
private _cx = _pos2D select 0;
private _cy = _pos2D select 1;
private _hC = getTerrainHeightASL _pos2D;
private _hN = getTerrainHeightASL [_cx, _cy + 50];
private _hS = getTerrainHeightASL [_cx, _cy - 50];
private _hE = getTerrainHeightASL [_cx + 50, _cy];
private _hW = getTerrainHeightASL [_cx - 50, _cy];
private _maxDiff = (abs (_hC - _hN)) max (abs (_hC - _hS)) max (abs (_hC - _hE)) max (abs (_hC - _hW));
private _slopeDeg = atan (_maxDiff / 50);
private _ls = [_slopeDeg, _pga, 1.5] call FUNC(seismicLandslide);
missionNamespace setVariable [QGVAR(seismicLandslideM), _ls select 1];

// ─── Structural damage ────────────────────────────────────────────────────
private _dmg = [_mmi] call FUNC(seismicDamage);
missionNamespace setVariable [QGVAR(seismicDamageLevel), _dmg select 0];
missionNamespace setVariable [QGVAR(seismicDamageImpassable), _dmg select 1];

// ─── Terrain deformation (server-side, opt-in, engine 2.10) ───────────────
private _ver = productVersion;
private _engineOk = ((_ver select 0) > 2) || (((_ver select 0) == 2) && ((_ver select 1) >= 10));
if (isServer && GVAR(seismicTerrainDeformationEnabled) && _engineOk) then {
    private _deformed = missionNamespace getVariable [QGVAR(seismicDeformed), -1];
    if (_deformed != _start) then {
        missionNamespace setVariable [QGVAR(seismicDeformed), _start];
        if (_lq select 1) then {
            private _pts = [_pos2D, 40, -0.2, 5] call FUNC(seismicTerrainPoints);
            if (_pts isNotEqualTo []) then { setTerrainHeight [_pts, true]; };
        };
        if (_ls select 2) then {
            private _dep = [_pos2D, 30, ((_ls select 1) min 0.5), 5] call FUNC(seismicTerrainPoints);
            if (_dep isNotEqualTo []) then { setTerrainHeight [_dep, true]; };
        };
    };
};

_pga
