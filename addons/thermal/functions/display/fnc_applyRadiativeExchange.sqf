#include "..\..\script_component.hpp"
/*
 * Radiative heat exchange between nearby objects (issue #204).
 *
 * A hot barrel heats the weapon around it from the inside out; a hot
 * engine heats the hull interior; a burning wreck heats everything
 * nearby.  This is RADIATIVE transfer - the Stefan-Boltzmann exchange
 * between two surfaces - which the per-object solve does not model
 * (each object exchanges with the AMBIENT sky/ground only).  Real
 * physics: q = F_ij * eps * sigma * (T_hot^4 - T_cold^4), where F_ij
 * is the view factor (how much of the cold surface 'sees' the hot
 * one).
 *
 * Implementation: for every nearby pair of objects, compute the
 * radiative flux from the hotter to the colder, scaled by the view
 * factor (approximated from the distance and the surface areas), and
 * apply it as an internal flux on the colder object's selections.  The
 * two-node solve then drives the cold surface toward the radiative
 * equilibrium - the 'inside out' warming of the weapon around a hot
 * barrel.
 *
 * Cost: pairwise over near objects is O(n^2); throttle to once per
 * second and cap the candidate set to the immediate area (30 m - the
 * radiative footprint of a hot object is short-range).
 *
 * Params:
 *   0: _mode (STRING, optional) - unused (kept for dispatch symmetry).
 *
 * Returns: SCALAR - the number of exchanges applied.
 */
params [["_mode", ""]];

if (!hasInterface) exitWith { 0 };

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith { 0 };

// Throttle: the radiative field changes at the thermal timescale (s).
private _nowT = diag_tickTime;
private _lastT = missionNamespace getVariable [QGVAR(radiativeLastT), 0];
if (_nowT - _lastT < 1) exitWith { 0 };
missionNamespace setVariable [QGVAR(radiativeLastT), _nowT];

private _near = _player nearObjects 30;
private _n = count _near;
if (_n < 2) exitWith { 0 };

private _selMap = missionNamespace getVariable [QGVAR(selTemperature), createHashMap];
private _sigma = 5.670374419e-8;

private _applied = 0;
for "_i" from 0 to (_n - 2) do {
    private _a = _near select _i;
    if (isNull _a) then { continue; };
    private _aTemps = [];
    {
        private _t = _selMap getOrDefault [format ["%1|%2", _a, _x], -999];
        if (_t > -900) then { _aTemps pushBack _t; };
    } forEach ([_a] call FUNC(getThermalSelections));
    if (_aTemps isEqualTo []) then { continue; };
    _aTemps sort true;
    private _aTemp = _aTemps select (floor (count _aTemps / 2));
    if !(_aTemp isEqualType 0) then { continue; };

    for "_j" from (_i + 1) to (_n - 1) do {
        private _b = _near select _j;
        if (isNull _b || _b == _a) then { continue; };
        private _bTemps = [];
        {
            private _t = _selMap getOrDefault [format ["%1|%2", _b, _x], -999];
            if (_t > -900) then { _bTemps pushBack _t; };
        } forEach ([_b] call FUNC(getThermalSelections));
        if (_bTemps isEqualTo []) then { continue; };
        _bTemps sort true;
        private _bTemp = _bTemps select (floor (count _bTemps / 2));
        if !(_bTemp isEqualType 0) then { continue; };

        // Radiative exchange: q = F * eps * sigma * (T_hot^4 - T_cold^4).
        private _tHot = (_aTemp max _bTemp);
        private _tCold = (_aTemp min _bTemp);
        if (_tHot - _tCold < 5) then { continue; };   // negligible

        // View factor: distance-falloff.  F ~ 1/(1 + d^2/A) - the
        // fraction of the cold surface seeing the hot one.  A 1 m
        // separation with a 1 m2 hot face gives F ~ 0.5; at 5 m it is
        // ~0.04.
        private _d = (_a distance _b) max 0.5;
        private _area = 1.0;
        private _F = 1 / (1 + ((_d * _d) / (_area max 0.5)));

        // Mean emissivity of the pair (0.9 typical for painted metal).
        private _eps = 0.9;
        private _thK = _tHot + 273.15;
        private _tcK = _tCold + 273.15;
        private _q = _eps * _sigma * (_F / 50.0) * ((_thK ^ 4) - (_tcK ^ 4));
        // The /50 scales the W/m2 into the solver's flux convention
        // (the two-node q_internal is the same order as the object
        // heat sources).  Cap so a large dT cannot blow the solve.
        _q = _q max 0 min 3000;

        // The colder object gains heat; the hotter loses it.
        private _coldObj = [_a, _b] select (_aTemp >= _bTemp);
        private _coldSel = ([_coldObj] call FUNC(getThermalSelections)) select 0;
        private _coldName = (selectionNames _coldObj) param [_coldSel, ""];
        if (_coldName != "") then {
            [_coldObj, _coldName, "", _q, 0.5] call FUNC(applySelectionThermal);
            _applied = _applied + 1;
        };
    };
};

_applied
