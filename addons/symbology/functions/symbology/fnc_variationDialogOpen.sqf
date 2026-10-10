#include "..\..\script_component.hpp"
/*
 * aee_symbology_fnc_variationDialogOpen
 *
 * Opens the variation selector display.  A real engine display (createDialog).
 * A safe no-op when there is no interface, when the map is closed (the
 * selector edits map markers), or when the display is already open.
 *
 * Return: <DISPLAY> the display, or displayNull.
 */
if (!hasInterface) exitWith { displayNull };
if (isNull (findDisplay 12)) exitWith { displayNull };
if (!isNull (uiNamespace getVariable [QGVAR(variationDisplay), displayNull])) exitWith {
    uiNamespace getVariable [QGVAR(variationDisplay), displayNull]
};
createDialog "RscDisplayAEEVariation"
