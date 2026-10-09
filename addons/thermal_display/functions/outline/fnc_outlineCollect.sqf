#include "..\..\script_component.hpp"
/*
 * Hot-target collector for the fusion outline (issue #204).
 *
 * Replaces workshop 3811605241 whale_ecoti_llll functions/fn_collectHot.sqf.
 * The source's filter is CAManBase-only and has no notion of heat; here aee's
 * own thermal state decides.  A target is hot when the MAX selection surface
 * temperature in QEGVAR(thermal,selTemperature) exceeds the ambient air temperature by
 * a small margin.  The selection temperature is the same per-selection physics
 * state the thermal display and the fusion overlay already write, and the
 * selection names are resolved exactly as fnc_applyFusionOverlay does.
 *
 * The per-object verdict is cached for 0.25 s in a missionNamespace HashMap,
 * so the expensive selection walk runs about four times a second and not once
 * per frame.  The collected count is logged once per refresh, not per frame.
 *
 * Params:
 *   0: _range (SCALAR, default 300) - search radius in metres.
 *
 * Returns: ARRAY of hot entities, nearest first.
 */
params [["_range", 300, [0]]];

private _margin = 3;
private _ttl = 0.25;
private _now = diag_tickTime;
private _center = positionCameraToWorld [0, 0, 0];

private _selMap = missionNamespace getVariable [QEGVAR(thermal,selTemperature), createHashMap];
if !(_selMap isEqualType createHashMap) then { _selMap = createHashMap; };

private _ambient = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_ambient isEqualType 0) then { _ambient = 15; };

private _cache = missionNamespace getVariable [QGVAR(outlineHotCache), createHashMap];
if !(_cache isEqualType createHashMap) then { _cache = createHashMap; };

private _refreshAt = missionNamespace getVariable [QGVAR(outlineHotRefreshAt), -1e9];
if !(_refreshAt isEqualType 0) then { _refreshAt = -1e9; };
private _doLog = _now >= _refreshAt;
if (_doLog) then { missionNamespace setVariable [QGVAR(outlineHotRefreshAt), _now + _ttl]; };

private _candidates = _center nearEntities [["CAManBase", "Car", "Tank", "StaticWeapon", "Air", "Animal"], _range];
private _hot = [];

{
    private _obj = _x;
    if (isNull _obj) then { continue };
    if (!alive _obj) then { continue };
    if (_obj isEqualTo player) then { continue };

    // Arma 3 HashMaps reject Object keys.  The supported key types are Array,
    // Boolean, Code, Config, Namespace, NaN, Number, Side and String (BIKI
    // HashMap, "Unsupported Key Types"), so an Object key raises "Error Type
    // Object" on every call.  Key on the object's string form instead, the
    // same per-object key convention as fnc_calculateObjectTemperature and
    // fnc_applySelectionThermal.
    private _objKey = str _obj;

    private _entry = _cache getOrDefault [_objKey, []];
    if ((_entry isNotEqualTo []) && ((_now - (_entry select 0)) < _ttl)) then {
        if (_entry select 1) then { _hot pushBack _obj; };
        continue;
    };

    private _selIdxs = [_obj] call EFUNC(thermal,getThermalSelections);
    private _selNames = if (_obj isKindOf "Man") then {
        selectionNames _obj
    } else {
        getArray (configOf _obj >> "hiddenSelections")
    };

    private _maxT = -999;
    {
        private _selName = _selNames param [_x, ""];
        if (_selName == "") then { continue };
        private _t = _selMap getOrDefault [format ["%1|%2", _obj, _selName], -999];
        if ((_t isEqualType 0) && (_t > _maxT)) then { _maxT = _t; };
    } forEach _selIdxs;

    private _isHot = _maxT > (_ambient + _margin);
    _cache set [_objKey, [_now, _isHot]];
    if (_isHot) then { _hot pushBack _obj; };
} forEach _candidates;

missionNamespace setVariable [QGVAR(outlineHotCache), _cache];

private _pairs = [];
{ _pairs pushBack [(_center distance _x), _x]; } forEach _hot;
_pairs sort true;

private _out = [];
{ _out pushBack (_x select 1); } forEach _pairs;

if (_doLog) then {
    private _logMsg = format ["fusion outline collect: %1 hot of %2 candidates within %3 m", count _out, count _candidates, round _range];
    AEE_LOG_DEBUG(_logMsg);
};

_out
