#include "..\..\script_component.hpp"

/*
Vegetation / foliage density (0-1).

Two phenologies:
  - WATER-LIMITED vegetation (savanna Aw, steppe BSh/BSk, Mediterranean
    Csa/Csb) is green in the wet months and browns in the dry ones.  The
    timing comes from the real monthly normals of the map's own station
    (fnc_getClimateNormals): a month is dry in the Bagnouls & Gaussen
    (1957) sense when P (mm) < 2 T (C).  The canopy is the mean of this month
    and the previous one (green-up and browning take weeks).  The station is
    local, so its hemisphere and its wet season are its own.
  - TEMPERATURE / DAY-LENGTH limited deciduous vegetation (Cfa, Cfb, Cwa,
    Dfa, Dfb, Dfc) follows the monthly rows below, written for the northern
    hemisphere; south of the equator the month is shifted six months.
The per-biome canopy values (the rows, and the dormant / green envelope of
the water-limited classes) are a stated modelling envelope, UNSOURCED.

Stored in GVAR(currentFoliageDensity) for use by concealment
modifiers, sound-propagation, and visual-seasonal systems.
*/

private _biome = missionNamespace getVariable [QEGVAR(core,biome), "Cfb"];
if (isNil "_biome" || _biome == "") then { _biome = "Cfb"; };

private _monthIdx = ((date select 1) - 1) max 0 min 11; // 0-based
private _calMonthIdx = _monthIdx;
// The deciduous rows are northern-hemisphere: shift six months in the south.
_monthIdx = ([_calMonthIdx + 1] call EFUNC(lib,seasonalMonth)) - 1;

private _foliage = switch (_biome) do {
    // Tropical — evergreen year-round
    case "Af": { 1.0 };
    case "Am": { 1.0 };
    // Savanna — wet/dry season
    case "Aw": { [0.6,0.6,0.6,0.7,0.8,0.9,1.0,1.0,0.9,0.8,0.7,0.6] select _monthIdx };
    // Arid — always sparse
    case "BWh": { 0.05 };
    case "BWk": { 0.05 };
    case "BSh": { [0.1,0.1,0.15,0.15,0.2,0.2,0.2,0.2,0.15,0.15,0.1,0.1] select _monthIdx };
    case "BSk": { [0.1,0.1,0.15,0.15,0.2,0.2,0.2,0.2,0.15,0.15,0.1,0.1] select _monthIdx };
    // Mediterranean — dry summer, green winter
    case "Csa": { [0.4,0.4,0.5,0.6,0.7,0.8,0.8,0.8,0.7,0.6,0.5,0.4] select _monthIdx };
    case "Csb": { [0.4,0.4,0.5,0.6,0.7,0.8,0.8,0.8,0.7,0.6,0.5,0.4] select _monthIdx };
    // Subtropical — deciduous cycle
    case "Cfa": { [0.2,0.2,0.3,0.5,0.8,1.0,1.0,1.0,0.9,0.6,0.4,0.2] select _monthIdx };
    case "Cfb": { [0.2,0.2,0.3,0.5,0.8,1.0,1.0,1.0,0.9,0.6,0.4,0.2] select _monthIdx };
    case "Cwa": { [0.3,0.3,0.4,0.6,0.8,1.0,1.0,1.0,0.9,0.7,0.5,0.4] select _monthIdx };
    // Continental — strong four-season
    case "Dfa": { [0.0,0.0,0.0,0.2,0.7,1.0,1.0,1.0,0.8,0.4,0.1,0.0] select _monthIdx };
    case "Dfb": { [0.0,0.0,0.0,0.2,0.7,1.0,1.0,1.0,0.8,0.4,0.1,0.0] select _monthIdx };
    case "Dfc": { [0.0,0.0,0.0,0.1,0.5,0.9,1.0,0.9,0.6,0.2,0.0,0.0] select _monthIdx };
    // Polar / alpine
    case "ET":  { 0.0 };
    case "EF":  { 0.0 };
    default     { 0.8 };
};

// Water-limited classes: the station's own wet and dry months.
private _envelope = switch (_biome) do {
    case "Aw": { [0.6, 1.0] };
    case "BSh": { [0.1, 0.2] }; case "BSk": { [0.1, 0.2] };
    case "Csa": { [0.4, 0.8] }; case "Csb": { [0.4, 0.8] };
    default { [] };
};
private _normals = [];
if (_envelope isNotEqualTo []) then { _normals = [_biome] call FUNC(getClimateNormals); };
if ((_envelope isNotEqualTo []) && {(count _normals) >= 6} && {(count (_normals select 2)) == 12} && {(count (_normals select 5)) == 12}) then {
    private _wet = {
        params ["_m"];
        private _t = (((_normals select 2) select _m) + ((_normals select 3) select _m)) / 2;
        parseNumber (((_normals select 5) select _m) >= (2 * _t))
    };
    private _active = (([_calMonthIdx] call _wet) + ([(_calMonthIdx + 11) mod 12] call _wet)) / 2;
    _foliage = (_envelope select 0) + ((_envelope select 1) - (_envelope select 0)) * _active;
};
missionNamespace setVariable [QGVAR(currentFoliageDensity), _foliage];
