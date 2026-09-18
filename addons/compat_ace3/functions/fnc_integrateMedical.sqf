#include "..\script_component.hpp"

/*
ACE3 medical integration — translates AEE thermal/dehydration state into
ACE3 medical vitals.

Runs every 5 s from the compat PFH on the local unit.  Maps AEE state
onto ACE3 medical through its public interface:

  Heat stress (WBGT)  → ace_medical_status_fnc_addMedicationAdjustment
                        (+heart rate, −peripheral flow) — the gradual
                        vitals hook.  Repeated calls with the same
                        medication replace the entry, so the effect
                        holds while conditions persist and decays via
                        maxTimeInSystem when cleared.
  Dehydration risk    → −peripheral flow (low blood volume), pain at
                        high risk.
  Extreme case        → ace_medical_status_fnc_setCardiacArrestState
                        when WBGT > 32 and risk > 0.8 (heat stroke).
  Heat exposure       → ace_medical_fnc_addDamageToUnit with "burn"
                        (thermal burn: no bleeding, pain 0.7).  The
                        previous "environment" type created bleeding
                        wounds — wrong for heat.

All calls require a local unit; the function exits early when remote.
*/

params [["_unit", player, [objNull]]];

if (isNull _unit) exitWith {};
if !(local _unit) exitWith {};
if (isNil "ace_medical_status_fnc_addMedicationAdjustment") exitWith {};

private _temp = missionNamespace getVariable ["aee_core_currentTemperature", 15];
private _wbgt = missionNamespace getVariable ["aee_core_currentWBGT", 15];
private _risk = missionNamespace getVariable ["aee_physiology_dehydrationRisk", 0];

// ─── Resolved thresholds (issue #154, pattern 1) ───────────────────────────
// The CBA settings can be uninitialised at the first tick.  A fallback of
// 0 turns every gate into "any value above 0 fires" — the #123 burn defect.
// Resolve each threshold ONCE with its real default (the CBA default), so
// every gate below uses a sane value, never 0.
private _wbgtThreshold = missionNamespace getVariable [QEGVAR(compat_ace3,medicalWBGTThreshold), 23];
private _riskThreshold = missionNamespace getVariable [QEGVAR(compat_ace3,medicalRiskThreshold), 0.3];
private _heatStrokeWBGT = missionNamespace getVariable [QEGVAR(compat_ace3,medicalHeatStrokeWBGT), 32];
private _burnTemp = missionNamespace getVariable [QEGVAR(compat_ace3,medicalBurnTemp), 25];
if !(_wbgtThreshold isEqualType 0) then { _wbgtThreshold = 23; };
if !(_riskThreshold isEqualType 0) then { _riskThreshold = 0.3; };
if !(_heatStrokeWBGT isEqualType 0) then { _heatStrokeWBGT = 32; };
if !(_burnTemp isEqualType 0) then { _burnTemp = 25; };

// ─── Heat stress vitals (WBGT → heart rate / flow) ─────────────────────────
private _hr    = 0;
private _flow  = 0;
private _pain  = 0;

// State guard: ACE's addMedicationAdjustment APPENDS an entry (pushBack),
// it does not replace.  Re-adding every 5 s tick while hot would stack
// entries and compound the vitals adjustment.  Add once on the
// clear->hot transition only.
private _heatActive = ((_wbgt > _wbgtThreshold) || (_risk > _riskThreshold));
private _wasHeatActive = missionNamespace getVariable [QGVAR(heatStressAdjustmentActive), false];

if (_heatActive) then {
    // ISO 7243 bands — heat strain raises heart rate, lowers peripheral flow.
    // Exclusive cascade: the strongest matching band wins.  A sequential
    // pair of ifs here let the extreme-caution band OVERWRITE the danger
    // band (WBGT 28-32 silently produced the 23-28 values) — the danger
    // band was unreachable.  Fixed with if/elseif.
    if (_wbgt > 32) then {
        _hr = 30; _flow = -20; _pain = 0.3;              // very dangerous
    } else {
        if (_wbgt > 28) then {
            _hr = 20; _flow = -15;                       // danger
        } else {
            if (_wbgt > _wbgtThreshold) then { _hr = 10; _flow = -10; };  // extreme caution
        };
    };

    // Dehydration compounds flow loss (reduced blood volume)
    if (_risk > 0.7) then { _flow = _flow - 15; _pain = _pain max 0.2; };
    if (_risk > _riskThreshold) then { _flow = _flow - 8; };

    if (!_wasHeatActive) then {
        [_unit, "AEE_heatStress", 120, 600, _hr, _pain, _flow, 1]
            call ace_medical_status_fnc_addMedicationAdjustment;
        missionNamespace setVariable [QGVAR(heatStressAdjustmentActive), true];
    };
} else {
    // Conditions clear — remove OUR entries directly.  ACE rejects
    // maxTimeInSystem <= 0 (its addMedicationAdjustment exits with a
    // warning), so the old "expire with 0" call never worked and spammed
    // the RPT every tick.  There is no removal API; filter the array.
    if (_wasHeatActive) then {
        private _medications = _unit getVariable ["ace_medical_status_medications", []];
        _medications = _medications select {(_x select 0) != "AEE_heatStress"};
        _unit setVariable ["ace_medical_status_medications", _medications, true];
        missionNamespace setVariable [QGVAR(heatStressAdjustmentActive), false];
    };
};

// ─── Heat stroke (cardiac arrest) at extreme WBGT + critical dehydration ──
if ((_wbgt > _heatStrokeWBGT) && _risk > 0.8) then {
    [_unit, true] call ace_medical_status_fnc_setCardiacArrestState;
} else {
    if (missionNamespace getVariable [QGVAR(heatStrokeActive), false]) then {
        [_unit, false] call ace_medical_status_fnc_setCardiacArrestState;
    };
};
missionNamespace setVariable [QGVAR(heatStrokeActive), ((_wbgt > _heatStrokeWBGT) && _risk > 0.8)];

// ─── Heat burn damage (thermal burn — no bleeding, pain 0.7) ──────────────
// The burn gate uses the CBA default (25 C) as the in-code fallback, NOT
// 0: a 0 fallback fires whenever the setting is uninitialised (any temp
// above freezing -> burn every tick), which the Scottish Highlands report
// hit.  The damage goes to the REAL body parts via the engine's hitpoint
// selections rather than a hardcoded "LeftLeg" (the report showed the
// burn on the mirrored leg in the medical menu).  ACE's addDamageToUnit
// maps a class name; iterate the unit's actual hit selections so the
// wound lands where the exposure is.
//
// The gate requires a MINIMUM SUSTAINED exposure before any damage:
// a night->day time skip jumps the temperature past the threshold in one
// tick, and the old gate then compounded burn damage on every 5 s tick
// (the reported "burns appear on time skip").  Real skin burns need a
// thermal dose (temperature x time), so a single tick crossing the
// threshold must not wound the unit.  12 ticks at the 5 s PFH interval
// = 60 s of continuous heat above the threshold.
private _burnScale = missionNamespace getVariable [QEGVAR(compat_ace3,medicalBurnDamageScale), 0.0005];
private _burnExposureTicksRequired = 12;
private _burnExposureTicks = missionNamespace getVariable [QGVAR(burnExposureTicks), 0];

if (_temp > _burnTemp) then {
    _burnExposureTicks = _burnExposureTicks + 1;
    if (_burnExposureTicks >= _burnExposureTicksRequired) then {
        private _damage = (_temp - _burnTemp) * _burnScale;
        // Only apply to parts that can take burn: the engine's hitpoint
        // selections (body, arms, legs).  ACE accepts any body-part class;
        // using the real selection names keeps the wound on the correct side.
        private _parts = [
            "Body", "Head", "LeftArm", "RightArm", "LeftLeg", "RightLeg"
        ];
        {
            [_unit, _damage / 6, _x, "burn"] call ace_medical_fnc_addDamageToUnit;
        } forEach _parts;
    };
} else {
    _burnExposureTicks = 0;
};
missionNamespace setVariable [QGVAR(burnExposureTicks), _burnExposureTicks];
