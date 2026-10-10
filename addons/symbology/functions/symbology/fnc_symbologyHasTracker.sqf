#include "..\..\script_component.hpp"
/*
 * aee_symbology_fnc_symbologyHasTracker
 *
 * Pure kernel.  Reports whether a carried-item list holds a blue-force
 * tracker device.  PURE: the item list arrives as an argument, so the kernel
 * reads no unit, no player and no world.
 *
 * A tracker is the engine GPS, a UAV terminal, or, when ACE3 is present, its
 * microDAGR or DAGR.  A device absent from the build is simply never in the
 * list, so the check is safe with or without ACE.
 *
 * Arguments:
 *   0: _items <ARRAY> the carried item class names
 *
 * Return: <BOOL> true when the list holds a tracker device
 */
params [
    ["_items", [], [[]]]
];

private _devices = [
    "ItemGPS",
    "B_UavTerminal",
    "O_UavTerminal",
    "I_UavTerminal",
    "ACE_microDAGR",
    "ACE_DAGR"
];

private _has = false;
{
    private _item = _x;
    if ((_devices findIf { _x isEqualTo _item }) >= 0) then {
        _has = true;
    };
} forEach _items;

_has
