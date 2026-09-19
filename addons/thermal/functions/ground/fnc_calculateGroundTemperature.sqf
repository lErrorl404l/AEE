#include "..\..\script_component.hpp"
/*
Ground surface temperature at a position (issues #124, #194, #198).

This is the CONSUMER-FACING wrapper.  It classifies the material at the
position via the #96 detector, delegates the physics solve to the
4-layer Crank-Nicolson node stack (issue #198), and returns the node
stack's SURFACE node (layer 1) plus any per-position thermal stamp.

The node stack IS the ground model: it carries the diurnal wave, the
per-layer moisture gradient, the evaporative draw and the seasonal deep
anchor (TBOT = slow annual-mean EMA).  Every ground consumer calls this
wrapper - MRT exchange, the object/selection thermal solver, and the
ground-contact stamps - and all of them now see the real surface
temperature instead of a single-node air-anchored equilibrium.

Real elapsed time: the node stack is time-integrated (its per-cell
state stores the last-advance timestamp), so the first caller in a tick
advances by the real interval and subsequent callers in the same tick
read the SAME state - multiple consumers per tick do not triple-advance
the physics.

Input:
  0: position (ARRAY) - world position (ASL preferred) [optional,
     defaults to the current unit's position]
  1: material class (STRING) - override; defaults to the #96
     classification at the position via surfaceType

Output: ground surface temperature in degrees C (number)
*/

params [["_pos", [], [[]]], ["_material", "", [""]]];

private _tAir = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_tAir isEqualType 0) then { _tAir = 15; };

if (_pos isEqualTo []) then {
    private _unit = call CBA_fnc_currentUnit;
    if (!isNil "_unit") then { _pos = getPosASL _unit; };
};

// ─── Material class at the position (#96 detector) ────────────────────────
// `surfaceType` at the ground point gives the engine surface class
// (e.g. #gdtasphalt); the #96 taxonomy maps it to the physical material.
if (_material == "") then {
    if (count _pos >= 2) then {
        private _surf = surfaceType [_pos select 0, _pos select 1];
        if (_surf != "") then {
            _material = [_surf] call EFUNC(material,classifyBySurfaceType);
        };
    };
    if (_material == "") then { _material = "ground"; };
};

// ─── Delegate to the node stack (issue #198) ──────────────────────────────
// The stack returns [t1..t4, tBot, lastTick]; layer 1 (t1) is the
// surface node the MRT exchange and every ground consumer needs.  The
// stack reads the soil-moisture state and weather internally.
private _stack = [_pos, _material] call FUNC(calculateGroundNodeStack);
private _ts = _stack select 0;

// ─── Frost phase-change tier (issue #195) ─────────────────────────────────
// A wet film on the surface pins at 0C while it releases latent heat;
// frost deposits and changes the LWIR emissivity.  Returns the
// frost-adjusted surface temperature and a frost flag the thermal
// contrast consumer reads.  The pin only engages below 0C with film.
private _wind = missionNamespace getVariable [QEGVAR(core,currentWind), [0, 0, 0]];
if !(_wind isEqualType []) then { _wind = [0, 0, 0]; };
private _rh = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
if !(_rh isEqualType 0) then { _rh = 50; };
private _frost = [_pos, _ts, _tAir, vectorMagnitude _wind, _rh / 100, rain] call FUNC(calculateFrostState);
_ts = _frost select 0;

// Per-position thermal stamp (boot print, tyre track, shade patch).
(_ts + ([_pos] call FUNC(getGroundStampOffset)))
