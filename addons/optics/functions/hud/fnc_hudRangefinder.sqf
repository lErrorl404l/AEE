#include "..\..\script_component.hpp"
/*
 * ECOTI environment HUD rangefinder.
 *
 * Registers one Draw3D worker.  The worker casts from the eye along the
 * camera view, caches the first surface hit and its distance, and draws the
 * distance as 3D text at the hit point.  The cast is throttled to twice a
 * second so the per-frame cost is one draw, never one raycast.
 *
 * Ported from workshop 3759527903 FPANO_ECOTI/scripts/FPANO_fnc_rangefinder.sqf.
 * The source reads a cached ping set by a keybind; this version casts real
 * geometry itself (lineIntersectsSurfaces), which the source uses in its ping
 * handler.  The engine map icon is replaced by empty-icon 3D text, so no
 * raster asset is referenced.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};
if (!isNil QGVAR(hudRangeEH)) exitWith {};

missionNamespace setVariable [QGVAR(hudRangeEH), addMissionEventHandler ["Draw3D", {
    if (!(missionNamespace getVariable [QGVAR(hudEnabled), false])) exitWith {};
    if (!(missionNamespace getVariable [QGVAR(hudOn), false])) exitWith {};
    if ((currentVisionMode player) != 1) exitWith {};
    if (visibleMap) exitWith {};

    private _now = diag_tickTime;
    private _last = missionNamespace getVariable [QGVAR(hudRangeTime), -10];
    if ((_now - _last) > 0.5) then {
        private _startASL = AGLToASL (positionCameraToWorld [0, 0, 0]);
        private _endASL = AGLToASL (positionCameraToWorld [0, 0, 5000]);
        private _hits = lineIntersectsSurfaces [
            _startASL, _endASL, player, vehicle player, true, 1, "GEOM", "VIEW"
        ];
        private _posAGL = positionCameraToWorld [0, 0, 5000];
        if ((count _hits) > 0) then {
            _posAGL = ASLToAGL ((_hits select 0) select 0);
        };
        missionNamespace setVariable [QGVAR(hudRangePos), _posAGL];
        missionNamespace setVariable [QGVAR(hudRangeDist), round ((eyePos player) distance _posAGL)];
        missionNamespace setVariable [QGVAR(hudRangeTime), _now];
    };

    private _dist = missionNamespace getVariable [QGVAR(hudRangeDist), 0];
    if (_dist > 0) then {
        private _pos = missionNamespace getVariable [QGVAR(hudRangePos), [0, 0, 0]];
        drawIcon3D [
            "",
            [1, 1, 1, 0.85],
            _pos,
            0, 0, 0,
            ([_dist] call FUNC(hudFormatRange)),
            2,
            0.030,
            "PuristaMedium",
            "center"
        ];
    };
}]];
