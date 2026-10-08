#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_mgrsEffectivePrecision
 *
 * The MGRS digit count in force.  When the auto setting is on the world map
 * size picks it (6 or 8); else the manual mgrsPrecision list applies.  One
 * reader, so the map, the HUD and the GPS show the same digit count.
 *
 * Arguments:
 *   0: _anchor <ARRAY> the 9-element geo anchor from EFUNC(core,getGeoAnchor)
 *
 * Return: <NUMBER> the total MGRS digit count
 */
params [["_anchor", [], [[]]], ["_span", 0, [0]]];

private _precision = missionNamespace getVariable [QGVAR(mgrsPrecision), 10];
if (missionNamespace getVariable [QGVAR(mgrsPrecisionAuto), true]) then {
    private _mapSize = 0;
    if ((count _anchor) >= 4) then { _mapSize = _anchor select 3; };
    _precision = ([_mapSize, _span] call FUNC(mgrsMapPrecision)) select 0;
};
if !(_precision isEqualType 0) then { _precision = 10; };

_precision
