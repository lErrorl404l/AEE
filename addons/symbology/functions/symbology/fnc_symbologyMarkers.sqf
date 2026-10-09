#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyMarkers
 *
 * Registers the AEE map-marker application layer.  On the "Map" mission event
 * open it applies the AEE symbols as real engine markers
 * (FUNC(symbologyMarkersApply)) and starts a one-second re-scan, so a marker
 * that appears while the map is open is converted too.  On map close it
 * restores every converted marker and deletes the AEE unit markers
 * (FUNC(symbologyMarkersRestore)).
 *
 * There is no symbol Draw event handler.  The symbols are real markers drawn
 * by the engine marker layer, so nothing is painted on the map control.  The
 * one-second re-scan runs on a CBA per-frame handler, not a Draw handler.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};
if (!isNil QGVAR(symbologyMarkersEH)) exitWith {};

GVAR(symbologyMarkersEH) = addMissionEventHandler ["Map", {
    params ["_opened"];

    if (_opened) exitWith {
        if (!(missionNamespace getVariable [QGVAR(symbologyEnabled), false])) exitWith {};
        [] call FUNC(symbologyMarkersApply);
        GVAR(symbologyScanPFH) = [{
            params ["_args", "_handle"];
            if (!visibleMap) exitWith { [_handle] call CBA_fnc_removePerFrameHandler; };
            [] call FUNC(symbologyMarkersApply);
        }, 1, []] call CBA_fnc_addPerFrameHandler;
    };

    // ── Map close: put every marker back. ────────────────────────────────
    [] call FUNC(symbologyMarkersRestore);
    if (!isNil QGVAR(symbologyScanPFH)) then {
        [GVAR(symbologyScanPFH)] call CBA_fnc_removePerFrameHandler;
        GVAR(symbologyScanPFH) = nil;
    };
}];
