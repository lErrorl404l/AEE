#include "..\script_component.hpp"
/*
Runtime dive loop for the ZH-L16C model (issue #118).

Called once per second for each unit underwater (the ADE-verified cadence
and eyePos z < 0 detection).  Integrates the 16-compartment tissues,
computes the ceiling and NDL, and drives the consequences:

  - NDL (no-decompression limit): time remaining at the current depth
    before the controlling compartment hits its M-value.
  - Ceiling: the shallowest depth the diver may ascend to without a deco
    stop (GF-configured).  Violating it (ascending above the ceiling with
    remaining obligation) accumulates DCS and applies ACE pain.
  - ppO2 / ppN2 toxicity: MOD (max operating depth) from 1.4 bar ppO2;
    CNS O2 and ppN2 limits accumulate at excessive partial pressures.
  - DCS accumulator: 0..1; crossing 1.0 triggers the DCS hit (damage via
    ACE medical when present, otherwise setDamage).

State is per-UID in aee_physiology_diveStates (see fnc_getDiveState).

Input:  [_unit] - the unit to update (default: player)
Output: the updated state array
*/

params [["_unit", objNull, [objNull]]];
if (isNull _unit) then { _unit = call CBA_fnc_currentUnit; };
if (_unit != call CBA_fnc_currentUnit) exitWith {};

private _entry = [_unit] call FUNC(getDiveState);
private _tissues = _entry select [0, 32];

// ─── Depth and gas ──────────────────────────────────────────────────────
private _depthM = 0 max ((getPosASL _unit) select 2) * -1;
private _fN2 = _entry select 32;
private _fHe = _entry select 33;
private _fO2 = _entry select 34;
private _pAmb = (_depthM / 10) + 1;

// ─── Integrate one second ────────────────────────────────────────────────
private _gf = missionNamespace getVariable [QGVAR(diveGradientFactor), 1.0];
if !(_gf isEqualType 0) then { _gf = 1.0; };
private _step = [_depthM, _fN2, _fHe, _tissues, _gf] call FUNC(zh16cStep);
private _newTissues = _step select 0;
private _ceilingM = _step select 1;

for "_i" from 0 to 31 do { _entry set [_i, _newTissues select _i]; };
_entry set [35, _depthM];

// ─── NDL: time to M-value at the current depth ───────────────────────────
// NDL = time until the controlling compartment's ceiling first exceeds
// the SURFACE (you can no longer ascend directly without a stop).  The
// M-value at the surface is a + 1/b (P_amb = 1); solve the exponential
// loading for the time to reach it.  Min over compartments.
private _tHalfN2 = [4.0, 8.0, 12.5, 18.5, 27.0, 38.3, 54.3, 77.0,
                    109.0, 146.0, 187.0, 239.0, 305.0, 390.0, 498.0, 635.0];
private _aN2Arr = [1.2599, 1.0, 0.8618, 0.7562, 0.62, 0.5043, 0.441, 0.4,
                   0.375, 0.35, 0.3295, 0.3065, 0.2835, 0.261, 0.248, 0.2327];
private _bN2Arr = [0.5050, 0.6514, 0.7222, 0.7825, 0.8126, 0.8434, 0.8693, 0.8910,
                   0.9092, 0.9222, 0.9319, 0.9403, 0.9477, 0.9544, 0.9602, 0.9653];
private _aHeArr = [1.7424, 1.383, 1.1919, 1.0458, 0.922, 0.8205, 0.7305, 0.6502,
                   0.595, 0.5545, 0.5333, 0.5189, 0.5181, 0.5176, 0.5172, 0.5119];
private _bHeArr = [0.4245, 0.5747, 0.6527, 0.7223, 0.7582, 0.7957, 0.8279, 0.8553,
                   0.8757, 0.8903, 0.8997, 0.9073, 0.9122, 0.9171, 0.9217, 0.9267];

private _ndl = 9999;
for "_i" from 0 to 15 do {
    private _pn2 = _newTissues select _i;
    private _phe = _newTissues select (16 + _i);
    private _total = _pn2 + _phe;
    private _pInspiredN2 = (_pAmb - 0.0627) * _fN2;
    // Mixed a/b by tissue gas fraction.
    private _fN2t = if (_total > 0) then { _pn2 / _total } else { 0 };
    private _fHet = if (_total > 0) then { _phe / _total } else { 0 };
    private _a = ((_aN2Arr select _i) * _fN2t) + ((_aHeArr select _i) * _fHet);
    private _b = ((_bN2Arr select _i) * _fN2t) + ((_bHeArr select _i) * _fHet);
    // Surface M-value, GF-adjusted: the ceiling first exceeds 0 m when
    // P_t > GF*a + (1 - GF*(1 - 1/b)).  GF=1 reduces to a + 1/b.
    private _mValue = (_gf * _a) + (1 - _gf * (1 - 1 / _b));
    if (_mValue > _total) then {
        private _k = ln 2 / (60 * (_tHalfN2 select _i));
        private _tMin = ln ((_pInspiredN2 - _total) / (_pInspiredN2 - _mValue)) / _k;
        if (_tMin > 0) then { _ndl = _ndl min _tMin; };
    };
};
_entry set [38, _ndl];  // minutes remaining

// ─── Oxygen / nitrogen toxicity ──────────────────────────────────────────
private _ppO2 = _pAmb * _fO2;
private _ppN2 = _pAmb * _fN2;
private _o2Cns = 0;
if (_ppO2 > 1.4) then { _o2Cns = (_ppO2 - 1.4) * 0.01; };  // per-second CNS charge
_entry set [39, _o2Cns];
private _n2Narc = if (_ppN2 > 3.5) then { (_ppN2 - 3.5) * 0.01 } else { 0 };
_entry set [40, _n2Narc];

// ─── Ceiling violation → DCS ─────────────────────────────────────────────
private _dcs = _entry select 36;
private _ascentRate = (_entry select 35) - _depthM;  // positive = ascending
private _violation = 0;
if ((_ceilingM > _depthM + 1) && _ascentRate > 0.5) then {
    // Ascending above the ceiling with tissue still over-saturated.
    _violation = 0.01 * _ascentRate;
};
if (_ascentRate > 1.5 && _ceilingM > 0) then {
    // Fast ascent from any depth with a ceiling.
    _violation = _violation + 0.02;
};
_entry set [36, (_dcs + _violation) min 1];

// ─── Consequences ───────────────────────────────────────────────────────
if ((_entry select 36) >= 1) then {
    // DCS hit.  ACE medical: lung/spinal hit; vanilla: damage.
    if (isClass (configFile >> "CfgPatches" >> "ace_medical")) then {
        [_unit, 0.3, "body", "DCS"] call ace_medical_fnc_addDamageToUnit;
    } else {
        _unit setDamage (getDammage _unit) + 0.3;
    };
    _entry set [36, 0.6];  // recoverable, but persistent between hits
};

if ((_entry select 39) >= 1) then {
    // CNS O2 toxicity: convulsion-like hit.
    if (isClass (configFile >> "CfgPatches" >> "ace_medical")) then {
        [_unit, 0.2, "body", "O2Tox"] call ace_medical_fnc_addDamageToUnit;
    };
    _entry set [39, 0];
};

if ((_entry select 36) > 0 && {_entry select 40 > 0.5}) then {
    if (isClass (configFile >> "CfgPatches" >> "ace_medical")) then {
        // Nitrogen narcosis: small periodic pain as a warning.
        private _pain = _unit getVariable ["ACE_medical_pain", 0];
        [_unit, _pain + 0.05] call ace_medical_fnc_adjustPainLevel;
    };
};

// ─── Store ───────────────────────────────────────────────────────────────
private _state = missionNamespace getVariable [QGVAR(diveStates), createHashMap];
private _uid = _unit getVariable [QGVAR(diveUID), ""];
_state set [_uid, _entry];
missionNamespace setVariable [QGVAR(diveStates), _state];

_entry
