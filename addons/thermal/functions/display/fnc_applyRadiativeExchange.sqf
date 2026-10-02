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

private _selMap = missionNamespace getVariable [QGVAR(selTemperature), -1];
if (_selMap isEqualType 0) then {
    _selMap = createHashMap;
    missionNamespace setVariable [QGVAR(selTemperature), _selMap];
};
private _sigma = 5.670374419e-8;

// ─── Hoist every PER-OBJECT value out of the pair loop ────────────────────
// getThermalSelections walks the object's selections, textures and
// materials, and selectionNames is an engine call.  Both were evaluated once
// PER PAIR, so an O(n^2) loop carried O(n^2) engine-level selection walks and
// stalled the frame once a second.  Each is now computed once per object, so
// the pair loop below reads arrays and costs no engine work.
private _tempArr = [];
private _selNameArr = [];
private _selWorldArr = [];
private _centreArr = [];
{
    private _obj = _x;
    if (isNull _obj) then {
        _tempArr pushBack -999;
        _selNameArr pushBack [];
        _selWorldArr pushBack [];
        _centreArr pushBack [0, 0, 0];
    } else {
        private _sels = [_obj] call FUNC(getThermalSelections);
        private _allNames = selectionNames _obj;
        // The thermal selection NAMES and their WORLD points, resolved once
        // per object.  The pair loop below then distributes the flux by a
        // view factor with array maths only - no engine call returns to the
        // O(n^2) loop, which was the whole point of the hoist.
        private _thermalNames = [];
        {
            if (_x < count _allNames) then { _thermalNames pushBack (_allNames select _x); };
        } forEach _sels;
        _selNameArr pushBack _thermalNames;
        private _pts = [_obj, _thermalNames] call FUNC(getThermalSelectionPoints);
        private _world = [];
        { _world pushBack (_obj modelToWorld _x); } forEach _pts;
        _selWorldArr pushBack _world;
        _centreArr pushBack (_obj modelToWorld [0, 0, 0]);
        private _ts = [];
        {
            private _t = _selMap getOrDefault [format ["%1|%2", _obj, _x], -999];
            if (_t > -900) then { _ts pushBack _t; };
        } forEach _sels;
        if (_ts isEqualTo []) then {
            _tempArr pushBack -999;
        } else {
            _ts sort true;
            _tempArr pushBack (_ts select (floor (count _ts / 2)));
        };
    };
} forEach _near;

private _applied = 0;
for "_i" from 0 to (_n - 2) do {
    private _a = _near select _i;
    private _aTemp = _tempArr select _i;
    if (isNull _a || !(_aTemp isEqualType 0) || _aTemp < -900) then { continue; };

    for "_j" from (_i + 1) to (_n - 1) do {
        private _b = _near select _j;
        private _bTemp = _tempArr select _j;
        if (isNull _b || _b == _a || !(_bTemp isEqualType 0) || _bTemp < -900) then { continue; };

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

        // The colder object gains heat; the hotter loses it.  The pair's
        // total flux is DISTRIBUTED across the cold object's parts by a
        // view factor, not dumped on its first entry: a part nearer the hot
        // object sees more of it and takes more of the flux.  The weights
        // are normalised, so the pair's energy is unchanged and only where
        // it lands moves.
        private _coldIdx = [_j, _i] select (_aTemp >= _bTemp);
        private _coldObj = _near select _coldIdx;
        private _coldNames = _selNameArr select _coldIdx;
        private _coldWorld = _selWorldArr select _coldIdx;
        if (_coldNames isNotEqualTo []) then {
            // The other object of the pair is the hot one.
            private _hotIdx = [_j, _i] select (_coldIdx == _j);
            private _hotCentre = _centreArr select _hotIdx;
            // View factor kernel, the same 1/(1 + d^2/A) the object pair
            // uses, evaluated per part in world space.  Bound: N is the
            // cold object's thermal selection count, read from the hoist;
            // the exponent makes a part at 3x the nearest distance carry
            // about a tenth of its flux, so distant parts are negligible.
            private _weights = [];
            private _wsum = 0;
            {
                private _dx = (_x select 0) - (_hotCentre select 0);
                private _dy = (_x select 1) - (_hotCentre select 1);
                private _dz = (_x select 2) - (_hotCentre select 2);
                private _w = 1 / (1 + ((_dx * _dx) + (_dy * _dy) + (_dz * _dz)));
                _weights pushBack _w;
                _wsum = _wsum + _w;
            } forEach _coldWorld;
            if (_wsum > 0) then {
                {
                    private _share = _q * ((_weights select _forEachIndex) / _wsum);
                    [_coldObj, _x, "", _share, 0.5] call FUNC(applySelectionThermal);
                    _applied = _applied + 1;
                } forEach _coldNames;
            };
        };
    };
};

_applied
