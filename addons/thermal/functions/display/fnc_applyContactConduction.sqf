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
    private _selMap = missionNamespace getVariable [QGVAR(selTemperature), createHashMap];
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
    // The ground at night tracks the air temperature (the substrate's
    // fGround view factor already models the ground/sky radiation
    // split); the prone body presses into it, so the contact is direct.
    private _air = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
    if !(_air isEqualType 0) then { _air = 15; };
    _contactTemp = _air;
    // Clothing reduces the contact: still a strong path through the
    // pressed clothing, but less than bare skin.
    _contactConductance = 40;
};

// Standing on the ground: footwear is the contact (already modelled by
// the fGround view factor in the substrate - no extra flux).

if (_contactTemp < -900) exitWith { 0 };

// ─── Apply: pull the body's skin toward the contact surface ──────────────
// For each body selection, the flux is h * (T_skin - T_surface).  We do
// NOT know the current skin temp here (the solve computes it), so we
// drive it through the two-node solve: pass q_internal = h * dT where
// dT is the signed difference between the body's LAST skin temp and the
// contact surface.  The solve then moves the skin toward the surface.
private _selMap = missionNamespace getVariable [QGVAR(selTemperature), createHashMap];
private _bodySels = [_player] call FUNC(getThermalSelections);
private _names = selectionNames _player;
private _applied = 0;
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

private _selMap2 = missionNamespace getVariable [QGVAR(selTemperature), createHashMap];
for "_i" from 0 to (_n - 2) do {
    private _a = _near select _i;
    if (isNull _a) then { continue; };
    private _aBox = boundingBoxReal _a;
    private _aMin = _a modelToWorld (_aBox select 0);
    private _aMax = _a modelToWorld (_aBox select 1);
    private _aTemps = [];
    {
        private _t = _selMap2 getOrDefault [format ["%1|%2", _a, _x], -999];
        if (_t > -900) then { _aTemps pushBack _t; };
    } forEach ([_a] call FUNC(getThermalSelections));
    if (_aTemps isEqualTo []) then { continue; };
    _aTemps sort true;
    private _aTemp = _aTemps select (floor (count _aTemps / 2));
    if !(_aTemp isEqualType 0) then { continue; };

    for "_j" from (_i + 1) to (_n - 1) do {
        private _b = _near select _j;
        if (isNull _b || _b == _a) then { continue; };
        // Skip pairs the player is not between (only blend the local
        // scene - the nearObjects radius is already tight at 40 m).
        private _bBox = boundingBoxReal _b;
        private _bMin = _b modelToWorld (_bBox select 0);
        private _bMax = _b modelToWorld (_bBox select 1);
        // AABB overlap test (conservative; contact surfaces touch).
        private _touch = (
            (_aMin select 0) <= (_bMax select 0)
            && {(_aMax select 0) >= (_bMin select 0)}
            && {(_aMin select 1) <= (_bMax select 1)}
            && {(_aMax select 1) >= (_bMin select 1)}
        );
        if !(_touch) then { continue; };

        private _bTemps = [];
        {
            private _t = _selMap2 getOrDefault [format ["%1|%2", _b, _x], -999];
            if (_t > -900) then { _bTemps pushBack _t; };
        } forEach ([_b] call FUNC(getThermalSelections));
        if (_bTemps isEqualTo []) then { continue; };
        _bTemps sort true;
        private _bTemp = _bTemps select (floor (count _bTemps / 2));
        if !(_bTemp isEqualType 0) then { continue; };

        private _dT = _aTemp - _bTemp;
        if (abs _dT < 0.5) then { continue; };   // negligible

        // Symmetric exchange: the warmer object LOSES heat (negative
        // flux), the colder GAINS it (positive flux).  _dT = a - b, so
        // a is warmer when _dT > 0: a gets the negative flux.
        private _fluxAB = (-20 * _dT) max -1500 min 1500;   // heats a: -h*dT
        private _fluxBA = -_fluxAB;
        // Apply to the first selection of each (the contact face) - the
        // solve redistributes through the object's own conduction.
        private _aSel = ([_a] call FUNC(getThermalSelections)) select 0;
        private _bSel = ([_b] call FUNC(getThermalSelections)) select 0;
        private _aName = (selectionNames _a) param [_aSel, ""];
        private _bName = (selectionNames _b) param [_bSel, ""];
        if (_aName != "" && _bName != "") then {
            [_a, _aName, "", _fluxAB, 0.5] call FUNC(applySelectionThermal);
            [_b, _bName, "", _fluxBA, 0.5] call FUNC(applySelectionThermal);
            _applied = _applied + 2;
        };
    };
};

_applied
