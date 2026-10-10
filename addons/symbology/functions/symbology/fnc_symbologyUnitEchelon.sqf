#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyUnitEchelon
 *
 * Engine adapter.  Reads a unit's group size and maps it to an echelon token
 * through the pure kernel FUNC(symbologyEchelon).  The group count is an
 * integer, so the pure kernel's clamp and round are safe.
 *
 * Arguments:
 *   0: _unit <OBJECT> the unit object
 *
 * Return: <STRING> an echelon token, for example "squad".
 */
params [
    ["_unit", objNull, [objNull]]
];

[count units (group _unit)] call FUNC(symbologyEchelon)
