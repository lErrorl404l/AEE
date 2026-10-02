#include "..\..\script_component.hpp"
/*
 * Contact conduction (issue #204).
 *
 * Any contact from something warm transfers heat to something cold, and
 * vice versa, when the conditions are met - the thermal-contact-
 * resistance reality.  The per-selection substrate solves each object
 * against AMBIENT; this layer adds the OBJECT-TO-OBJECT contact term:
 *
 *   - An operator IN a vehicle conducts to the vehicle interior.  A
 *     warm body warms a cold seat; a hot vehicle interior (engine
 *     heat) warms the operator.  The vehicle's temperature comes from
 *     its own solved selections (QGVAR(selTemperature)).
 *   - A PRONE operator conducts to the ground.
 *   - Hands on a weapon conduct body heat into the grip (the weapon
 *     path already adds the grip flux; this adds the reverse: a cold
 *     weapon cools the hands).
 *
 * The contact flux is q_contact = h_contact * (T_skin - T_surface)
 * (W/m2), h_contact from the thermal-contact-resistance range for
 * skin-to-metal/plastic (50-200 W/m2K; reduced when clothed).  It is
 * applied per body selection as an internal flux so the two-node solve
 * drives the skin toward the contact surface - the exchange is
 * BIDIRECTIONAL: the body cools a hot surface when T_body < T_surface
 * and warms it when T_body > T_surface.
 *
 * Params:
 *   0: _mode (STRING, optional) - unused (kept for dispatch symmetry).
 *
 * Returns: SCALAR - the number of selections touched.
 */
params [["_mode", ""]];

if (!hasInterface) exitWith { 0 };

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith { 0 };

private _veh = vehicle _player;
private _contactTemp = -999;   // the surface we are touching
private _contactConductance = 0;

// ─── In a vehicle: conduct to the interior ────────────────────────────────
if (_veh != _player) then {
    // The vehicle's current temperature: the median of its solved
    // selections.  Fall back to the engine-heat state if no selections
    // have been solved yet (first frames).
    private _selMap = missionNamespace getVariable [QGVAR(selTemperature), -1];
    if (_selMap isEqualType 0) then {
        _selMap = createHashMap;
        missionNamespace setVariable [QGVAR(selTemperature), _selMap];
    };
    private _temps = [];
    {
        private _key = format ["%1|%2", _veh, _x];
        private _t = _selMap getOrDefault [_key, -999];
        if (_t > -900) then { _temps pushBack _t; };
    } forEach ([_veh] call FUNC(getThermalSelections));
    if (_temps isNotEqualTo []) then {
        _temps sort true;   // ascending
        _contactTemp = _temps select (floor (count _temps / 2));  // median
    } else {
        private _heat = [_veh] call FUNC(calculateVehicleHeat);
        private _air = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
        if !(_air isEqualType 0) then { _air = 15; };
        _contactTemp = _air + (_heat * 40);
    };
    // Skin-to-seat contact: clothed operator, moderate conductance.
    _contactConductance = 80;
};

// ─── Prone on the ground: conduct to the ground ───────────────────────────
if (_contactTemp < -900 && {stance _player == "PRONE"}) then {
    // The ground temperature at the position (issue #204): the
    // surface-specific value - asphalt stays warmer than soil at night.
    // The prone body presses into it, so the contact is direct.
    _contactTemp = [getPosASL _player] call FUNC(calculateGroundTemperature);
    // Clothing reduces the contact: still a strong path through the
    // pressed clothing, but less than bare skin.
    _contactConductance = 40;
};

// Standing on the ground: footwear is the contact (already modelled by
// the fGround view factor in the substrate - no extra flux).

// ─── Vehicle tyre-ground conduction (issue #204) ──────────────────────────
// The user's 'no heat transfer to/from ground': the ground is not an
// object (it is the baked terrain), so the AABB object pass cannot
// exchange with it.  Add the dedicated term: the player's vehicle tyres
// conduct to the GROUND TEMPERATURE beneath them (position-based -
// asphalt stays warmer than soil at night).  Each rubber/tyre selection
// exchanges heat with the ground it sits on.
private _applied = 0;
if (_veh != _player) then {
    private _groundT = [getPosASL _veh] call FUNC(calculateGroundTemperature);
    private _selMap = missionNamespace getVariable [QGVAR(selTemperature), -1];
    if (_selMap isEqualType 0) then {
        _selMap = createHashMap;
        missionNamespace setVariable [QGVAR(selTemperature), _selMap];
    };
    private _vehSels = [_veh] call FUNC(getThermalSelections);
    private _vehNames = selectionNames _veh;
    {
        private _vIdx = _x;
        private _vName = if (_vIdx < count _vehNames) then { _vehNames select _vIdx } else { "" };
        if (_vName == "") then { continue; };
        // Only the tyre/wheel selections conduct to the ground (rubber
        // sits on it).  Identified by the material (rubber k ~0.22).
        private _matClass = [_veh, _vName] call FUNC(getSelectionMaterials);
        private _matDef = _matClass call FUNC(getMaterialThermal);
        private _k = _matDef select 4;
        if !(_k isEqualType 0) then { _k = 0; };
        if (_k >= 0.1 && _k <= 2.0) then {
            private _tireT = _selMap getOrDefault [format ["%1|%2", _veh, _vName], -999];
            if (_tireT > -900) then {
                private _dT = _tireT - _groundT;
                // The tyre and ground converge: the tyre conducts to the
                // ground (or the warm tarmac heats the tyre).  h ~30
                // W/m2K for rubber-earth contact.
                private _flux = (-30 * _dT) max -2000 min 2000;
                [_veh, _vName, "", _flux, 0.7] call FUNC(applySelectionThermal);
                _applied = _applied + 1;
            };
        };
    } forEach _vehSels;
};

if (_contactTemp < -900) exitWith { _applied };

// ─── Apply: pull the body's skin toward the contact surface ──────────────
// For each body selection, the flux is h * (T_skin - T_surface).  We do
// NOT know the current skin temp here (the solve computes it), so we
// drive it through the two-node solve: pass q_internal = h * dT where
// dT is the signed difference between the body's LAST skin temp and the
// contact surface.  The solve then moves the skin toward the surface.
private _selMap = missionNamespace getVariable [QGVAR(selTemperature), -1];
if (_selMap isEqualType 0) then {
    _selMap = createHashMap;
    missionNamespace setVariable [QGVAR(selTemperature), _selMap];
};
private _bodySels = [_player] call FUNC(getThermalSelections);
private _names = selectionNames _player;
{
    private _idx = _x;
    private _name = if (_idx < count _names) then { _names select _idx } else { "" };
    if (_name == "") then { continue; };
    private _skin = _selMap getOrDefault [format ["%1|%2", _player, _name], -999];
    if (_skin < -900) then { continue; };   // no solved temp yet
    private _dT = _skin - _contactTemp;
    // Flux sign: positive heats the skin (body warmer than surface),
    // negative cools it.  Limited to a sane band so a large dT does not
    // blow the solve.
    private _flux = (_contactConductance * _dT) max -2000 min 2000;
    [_player, _name, "", _flux, 0.3] call FUNC(applySelectionThermal);
    _applied = _applied + 1;
} forEach _bodySels;

// ─── Object-to-object contact (issue #204: blend adjacent surfaces) ───────
// Where two objects touch - a road meeting bare ground, a building
// footing meeting the earth, a vehicle parked on tarmac - heat conducts
// between them.  In Arma these are DIFFERENT objects with different
// thermal states (asphalt stores heat and stays warm at night; soil
// cools faster), so without a contact term there is a hard thermal
// edge exactly at the material boundary.  Real scenes blend it.
//
// Mechanism: objects whose bounding boxes touch exchange a flux
// proportional to their temperature difference (thermal-contact
// conductance, h_contact ~20 W/m2K for earth/stone pairs).  The
// exchange is BIDIRECTIONAL and symmetric - the warmer side cools, the
// colder side warms - so the two converge over the contact.
//
// Cost: pairwise over the near objects is O(n^2); throttle to once per
// second and cap the candidate set to the immediate area.
private _nowT = diag_tickTime;
private _lastT = missionNamespace getVariable [QGVAR(contactLastT), 0];
if (_nowT - _lastT < 1) exitWith { _applied };
missionNamespace setVariable [QGVAR(contactLastT), _nowT];

private _near = _player nearObjects 40;
private _n = count _near;
if (_n < 2) exitWith { _applied };

private _selMap2 = missionNamespace getVariable [QGVAR(selTemperature), -1];
if (_selMap2 isEqualType 0) then {
    _selMap2 = createHashMap;
    missionNamespace setVariable [QGVAR(selTemperature), _selMap2];
};

// ─── Hoist every PER-OBJECT value out of the pair loop ────────────────────
// getThermalSelections (a selection/texture/material walk), selectionNames
// and boundingBoxReal were all evaluated once PER PAIR, so this O(n^2) loop
// carried O(n^2) engine work and stalled the frame once a second.  Each is
// now computed once per object; the pair loop below reads arrays only.
private _tempArr = [];
private _minArr = [];
private _maxArr = [];
private _selNameArr = [];
private _selWorldArr = [];
private _centreArr = [];
{
    private _obj = _x;
    if (isNull _obj) then {
        _tempArr pushBack -999;
        _minArr pushBack [0, 0, 0];
        _maxArr pushBack [0, 0, 0];
        _selNameArr pushBack [];
        _selWorldArr pushBack [];
        _centreArr pushBack [0, 0, 0];
    } else {
        private _sels = [_obj] call FUNC(getThermalSelections);
        private _allNames = selectionNames _obj;
        // The thermal selection NAMES and their WORLD points, resolved once
        // per object.  The pair loop then picks the touching face with
        // array maths only - no engine call returns to the O(n^2) loop.
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
            private _t = _selMap2 getOrDefault [format ["%1|%2", _obj, _x], -999];
            if (_t > -900) then { _ts pushBack _t; };
        } forEach _sels;
        if (_ts isEqualTo []) then {
            _tempArr pushBack -999;
        } else {
            _ts sort true;
            _tempArr pushBack (_ts select (floor (count _ts / 2)));
        };
        private _box = boundingBoxReal _obj;
        _minArr pushBack (_obj modelToWorld (_box select 0));
        _maxArr pushBack (_obj modelToWorld (_box select 1));
    };
} forEach _near;

for "_i" from 0 to (_n - 2) do {
    private _a = _near select _i;
    private _aTemp = _tempArr select _i;
    if (isNull _a || _aTemp < -900 || !(_aTemp isEqualType 0)) then { continue; };
    private _aMin = _minArr select _i;
    private _aMax = _maxArr select _i;

    for "_j" from (_i + 1) to (_n - 1) do {
        private _b = _near select _j;
        private _bTemp = _tempArr select _j;
        if (isNull _b || _b == _a || _bTemp < -900 || !(_bTemp isEqualType 0)) then { continue; };
        // Skip pairs the player is not between (only blend the local
        // scene - the nearObjects radius is already tight at 40 m).
        // AABB overlap test (conservative; contact surfaces touch).  The
        // corners were hoisted above.
        private _bMin = _minArr select _j;
        private _bMax = _maxArr select _j;
        private _touch = (
            (_aMin select 0) <= (_bMax select 0)
            && {(_aMax select 0) >= (_bMin select 0)}
            && {(_aMin select 1) <= (_bMax select 1)}
            && {(_aMax select 1) >= (_bMin select 1)}
        );
        if !(_touch) then { continue; };

        private _dT = _aTemp - _bTemp;
        if (abs _dT < 0.5) then { continue; };   // negligible

        // Symmetric exchange: the warmer object LOSES heat (negative
        // flux), the colder GAINS it (positive flux).  _dT = a - b, so
        // a is warmer when _dT > 0: a gets the negative flux.
        private _fluxAB = (-20 * _dT) max -1500 min 1500;   // heats a: -h*dT
        private _fluxBA = -_fluxAB;
        // The touching faces: for each object, the part whose model point
        // is nearest the OTHER object.  Not the first selection of the
        // list, and never position 0 by rule.  Both sides were resolved to
        // world points in the hoist, so this is array maths.
        private _aName = [
            (_selNameArr select _i),
            (_selWorldArr select _i),
            (_centreArr select _j)
        ] call FUNC(getNearestSelection);
        private _bName = [
            (_selNameArr select _j),
            (_selWorldArr select _j),
            (_centreArr select _i)
        ] call FUNC(getNearestSelection);
        if (_aName != "" && _bName != "") then {
            [_a, _aName, "", _fluxAB, 0.5] call FUNC(applySelectionThermal);
            [_b, _bName, "", _fluxBA, 0.5] call FUNC(applySelectionThermal);
            _applied = _applied + 2;
        };
    };
};

_applied
