#include "..\script_component.hpp"

/*
Visual lightning FX — lightpoint + thunder sound.

Reads QGVAR(currentLightningRisk) (0-1) set by fn_calculateLightning.
Gates on GVAR(atmosphericEventsEnabled).  At high risk generates a
random nearby strike, avoiding tall buildings.

Sets: nothing (side effect only — visual/audio)
*/

// ─── Gate ────────────────────────────────────────────────────────────────
if (!EGVAR(core,atmosphericEventsEnabled)) exitWith {};

private _risk = missionNamespace getVariable [QEGVAR(core,currentLightningRisk), 0];
if (_risk <= 0.8 || random 1 >= 0.05) exitWith {};

// ─── Pick random position near camera ────────────────────────────────────
private _camPos = positionCameraToWorld [0,0,0];
if (_camPos isEqualTo [0,0,0]) exitWith {}; // no active camera

private _dist = 100 + random 400;
private _dir  = random 360;
private _pos  = [
    (_camPos#0) + sin _dir * _dist,
    (_camPos#1) + cos _dir * _dist,
    0
];

// ─── Skip if any building taller than 5 m within 20 m ────────────────────
private _skip     = false;
private _building = nearestBuilding _pos;
if (!isNull _building && _pos distance2D _building < 20) then {
    private _bbox = boundingBoxReal _building;
    private _height = abs ((_bbox#1)#2 - (_bbox#0)#2);
    if (_height > 5) then { _skip = true; };
};
if (_skip) exitWith {};

// ─── Strike position ─────────────────────────────────────────────────────
_pos set [2, getTerrainHeightASL _pos];

// ─── Fallback: BIS_fnc_lightning (preferred if available) ────────────────
if (!isNil "BIS_fnc_lightning") exitWith {
    _pos call BIS_fnc_lightning;
};

// ─── Manual: lightpoint + thunder ───────────────────────────────────────
private _light = "#lightpoint" createVehicleLocal _pos;
_light setLightBrightness 1000;
_light setLightAmbient [1,1,1];
_light setLightColor [1,1,1];
_light setLightAttenuation [0,0,0,0,500,1000];

// Thunder follows the flash: sound travels ~343 m/s, so delay the roll.
[{
    params ["_pos"];
    playSound3D [
        "a3\sounds_f\ambient\thunder\thunder_01.wss",
        objNull,
        false,
        _pos,
        -1,                          // max-distance (unlimited)
        2 + (3 * ([round (time * 10), 201] call EFUNC(core,deterministicRandom))),  // volume
        0.75 + (0.5 * ([round (time * 10), 202] call EFUNC(core,deterministicRandom))), // pitch
        343                          // propagation speed (m/s)
    ];
}, _pos, 2] call CBA_fnc_waitAndExecute;

[{
    deleteVehicle _this;
}, _light, 0.1] call CBA_fnc_waitAndExecute;
