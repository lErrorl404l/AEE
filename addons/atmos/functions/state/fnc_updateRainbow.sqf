#include "..\..\script_component.hpp"

/*
Engine rainbow from AEE's solar and rain state (issue #141).

`time setRainbow value` changes the engine rainbow smoothly over `time`
seconds.  The engine only shows the bow when the physics allows it, and the
wiki note is the gate: a rainbow appears after rainfall and opposite the
sun when it is low on the horizon.  AEE's solar model supplies all three.

Conditions (all three must hold):
  1. Sun elevation below 42 deg.  The primary bow is a 42 deg cone around
     the anti-solar point, so at 42 deg the bow apex reaches the horizon;
     above that the bow is below the horizon and cannot show.
  2. Rain present.  The bow needs falling drops in front of the observer.
  3. The observer faces the anti-solar hemisphere.  The bow sits opposite
     the sun, so the view direction needs a positive component along the
     anti-solar direction.

The command is local only (BI wiki: no synchronisation, no JIP), so it
runs per client and needs no publicVariable.

Reads:  QEGVAR(core,currentSunElevation), QEGVAR(core,currentSunAzimuth),
        rain (engine)
Sets:   engine rainbow (time setRainbow)
*/
if (!hasInterface) exitWith {};

private _maxSunElev = 42;   // primary bow apex reaches the horizon here

private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), -90];
if !(_sunElev isEqualType 0) then { _sunElev = -90; };
private _sunAz = missionNamespace getVariable [QEGVAR(core,currentSunAzimuth), 0];
if !(_sunAz isEqualType 0) then { _sunAz = 0; };

// Rain present (engine 0..1).
private _rain = rain;

// Anti-solar geometry.  The anti-solar azimuth is the sun azimuth + 180;
// the anti-solar elevation is the sun elevation mirrored below the horizon.
// Arma world axes: x = east, y = south, z = up (north = -y).
private _antiAz = _sunAz + 180;
private _antiElev = -_sunElev;
private _antiDir = [
    (sin _antiAz) * (cos _antiElev),
    -(cos _antiAz) * (cos _antiElev),
    sin _antiElev
];

private _facingAnti = false;
private _camPos = positionCameraToWorld [0, 0, 0];
private _camAim = positionCameraToWorld [0, 0, 100];
private _viewDir = _camAim vectorDiff _camPos;
if ((vectorMagnitude _viewDir) > 0.001) then {
    _facingAnti = ((vectorNormalized _viewDir) vectorDotProduct (vectorNormalized _antiDir)) > 0;
};

private _show = (_sunElev < _maxSunElev) && (_rain > 0) && _facingAnti;
0 setRainbow ([0, 1] select _show);
