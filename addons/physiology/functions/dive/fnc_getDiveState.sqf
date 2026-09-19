#include "..\..\script_component.hpp"
/*
Per-diver state tracker for the ZH-L16C decompression model (issue #118).

Holds the 16-compartment tissue loads per unit (keyed by getPlayerUID),
plus the breathing-gas mix.  Integrated at 1 Hz while the unit is
underwater (eyePos z < 0, the ADE-verified detection); the tissues relax
toward surface equilibrium when surfaced.

State (per UID, array):
  0..15        N2 partial pressure in compartments 1-16 (bar)
  16..31       He partial pressure in compartments 1-16 (bar)
  32           fN2 of the current breathing gas (0..1)
  33           fHe of the current breathing gas (0..1)
  34           fO2 of the current breathing gas (0..1)
  35           last depth (m)
  36           DCS accumulator (0..1, threshold 1.0 triggers hit)
  37           ascent-rate violation count (fast ascent without deco)

Input:  [_unit] - the unit to track (default: player)
Output: the unit's state array (read-only reference)
*/

params [["_unit", objNull, [objNull]]];
if (isNull _unit) then { _unit = call CBA_fnc_currentUnit; };

private _state = missionNamespace getVariable [QGVAR(diveStates), createHashMap];
private _uid = _unit getVariable [QGVAR(diveUID), ""];
if (_uid == "") then {
    _uid = getPlayerUID _unit;
    if (_uid == "") then { _uid = str (_unit call BIS_fnc_objectVar); };
    _unit setVariable [QGVAR(diveUID), _uid, true];
};

private _entry = _state get _uid;
if (isNil "_entry") then {
    // Fresh diver: N2 at surface equilibrium, no He, air mix, no exposure.
    private _baseline = 0.74047;
    _entry = [];
    for "_i" from 0 to 15 do { _entry pushBack _baseline; };
    for "_i" from 0 to 15 do { _entry pushBack 0; };
    _entry pushBack 0.79;   // fN2
    _entry pushBack 0;      // fHe
    _entry pushBack 0.21;   // fO2
    _entry pushBack 0;      // last depth
    _entry pushBack 0;      // DCS accumulator
    _entry pushBack 0;      // ascent violations
    _state set [_uid, _entry];
    missionNamespace setVariable [QGVAR(diveStates), _state];
};

// Gas selection: the current breathing mix.  Default air; a compatible
// addon (e.g. ADE) can set aee_physiology_diveMix to [fN2, fHe, fO2].
private _mix = missionNamespace getVariable [QGVAR(diveMix), [0.79, 0, 0.21]];
if (_mix isEqualType []) then {
    _entry set [32, _mix select 0];
    _entry set [33, _mix select 1];
    _entry set [34, _mix select 2];
};

_entry
