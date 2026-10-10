#include "..\script_component.hpp"

/*
    AEE — Seismic Source Module Init

    EDEN / Zeus module handler. Reads the module arguments and publishes the
    seismic event into AEE's shared state:

      aee_core_seismicActive     — true while the event is live
      aee_core_seismicMagnitude  — moment magnitude (Mw)
      aee_core_seismicEpicentre  — [x, y, z] ASL of the module position
      aee_core_seismicDepth      — focal depth (km)
      aee_core_seismicStart      — mission time (s) the event started

    Intended consumption: the persistence module reads these in
    fnc_calculateSeismicActivity.sqf and computes the ground motion, the camera
    shake and the secondary terrain effects.  The module position is the
    epicentre, so a mission designer places it on the map.  The event is a
    deterministic function of the module position and its arguments, so every
    machine publishes the same state without a broadcast.

    The module logic is deleted after reading, so the module cannot be
    re-triggered by toggling it in Zeus.
*/

params ["_logic", "_isActivating"];

if (!_isActivating) exitWith {};

private _magnitude = _logic getVariable ["magnitude", 6.5];
private _depthKm = _logic getVariable ["depthKm", 10];

private _magClamped = (_magnitude max 0) min 10;
private _depthClamped = _depthKm max 0;

missionNamespace setVariable [QEGVAR(core,seismicActive), true];
missionNamespace setVariable [QEGVAR(core,seismicMagnitude), _magClamped];
missionNamespace setVariable [QEGVAR(core,seismicEpicentre), getPosASL _logic];
missionNamespace setVariable [QEGVAR(core,seismicDepth), _depthClamped];
missionNamespace setVariable [QEGVAR(core,seismicStart), time];

deleteVehicle _logic;
