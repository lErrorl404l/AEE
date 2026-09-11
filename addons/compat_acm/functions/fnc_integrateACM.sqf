#include "..\script_component.hpp"

/*
Integrates AEE CBRN persistence with Advanced Combat Medicine (ACM).

When AEE's aee_core_cbrnPersistence rises, the local patient is marked
contaminated with a nerve hazard and the ACM exposure system drives the
effects. When persistence clears, the contamination and buildup reset.

Requires: ACM (Workshop 3235483358, CfgPatches ACM_main/ACM_cbrn).
*/

params [["_unit", objNull, [objNull]]];

if (isNull _unit || !alive _unit) exitWith {};
if (isNil "ACM_CBRN_fnc_updateExposureEffects") exitWith {};

private _contamination = missionNamespace getVariable [QEGVAR(core,cbrnPersistence), 0];
private _hazard = "ACM_CBRN_chemical_sarin_";

if (_contamination > 0.01) then {
    _unit setVariable [(_hazard + "Contaminated_State"), true, true];
    _unit setVariable [(_hazard + "Exposed_State"), true, true];
    _unit setVariable ["ACM_CBRN_Chemical_Sarin_Buildup", _contamination * 100];
} else {
    _unit setVariable [(_hazard + "Contaminated_State"), false, true];
    _unit setVariable [(_hazard + "Exposed_State"), false, true];
    _unit setVariable ["ACM_CBRN_Chemical_Sarin_Buildup", 0];
};

[_unit, true] call ACM_CBRN_fnc_updateExposureEffects;
