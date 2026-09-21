#include "..\script_component.hpp"

/*
Integrates AEE CBRN persistence with Advanced Combat Medicine (ACM).

When AEE's aee_core_cbrnPersistence rises, the local patient is marked
contaminated with a nerve hazard and the ACM exposure system drives the
effects. When persistence clears, the contamination and buildup reset.

aee_core_cbrnPersistence is a DECAY MODIFIER (0.225 clear ... 2.1 heavy
persistence), NOT a 0..1 contamination fraction.  It is normalised to
0..1 for the contaminated-state gate, and the buildup is scaled to ACM's
0..100 exposure range (lethal at 100).

Requires: ACM (Workshop 3235483358, CfgPatches ACM_main/ACM_cbrn).
*/

params [["_unit", objNull, [objNull]]];

if (isNull _unit || !alive _unit) exitWith {};
if (isNil "ACM_CBRN_fnc_updateExposureEffects") exitWith {};

private _contamination = missionNamespace getVariable [QEGVAR(core,cbrnPersistence), 0];
private _hazard = "ACM_CBRN_chemical_sarin_";

// Normalise the decay modifier (0.225..2.1) to a 0..1 contamination level.
// The unit's CBRN kit (issue #119, the respirator + suit in the gear
// slots) blocks part of the agent: a full kit scales the exposure by
// 0.05, no kit by 1.0.
private _normalised = ((_contamination - 0.225) / (2.1 - 0.225)) max 0 min 1;
private _protection = [_unit] call EFUNC(environmental,getCbrnProtection);
_normalised = _normalised * (1 - _protection);

if ((_normalised > (missionNamespace getVariable [QEGVAR(compat_acm,CBRNContamThreshold), 0.01]))) then {
    _unit setVariable [(_hazard + "Contaminated_State"), true, true];
    _unit setVariable [(_hazard + "Exposed_State"), true, true];
    _unit setVariable ["ACM_CBRN_Chemical_Sarin_Buildup", ((_normalised * 100) min (missionNamespace getVariable [QEGVAR(compat_acm,CBRNMaxBuildup), 100]))];
} else {
    _unit setVariable [(_hazard + "Contaminated_State"), false, true];
    _unit setVariable [(_hazard + "Exposed_State"), false, true];
    _unit setVariable ["ACM_CBRN_Chemical_Sarin_Buildup", 0];
};

[_unit, true] call ACM_CBRN_fnc_updateExposureEffects;
