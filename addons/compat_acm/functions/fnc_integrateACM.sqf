#include "..\script_component.hpp"

params [["_unit", player, [objNull]]];

if (isNil "acm_cbrn_fnc_contaminationZone") exitWith {};
if (isNull _unit) exitWith {};

// Read CBRN persistence from our core (set by fn_calculateCBRNPersistence).
// Air quality defaults to 1.0 (breathable) — AEE doesn't compute air quality.
private _contamination = missionNamespace getVariable ["aee_core_cbrnPersistence", 0];
private _airQuality = 1;

if (_contamination > 0.5) then {
    [_unit, _contamination] call acm_cbrn_fnc_contaminationZone;
};

if (_airQuality < 0.3) then {
    [_unit, _airQuality] call acm_cbrn_fnc_airQualityZone;
};
