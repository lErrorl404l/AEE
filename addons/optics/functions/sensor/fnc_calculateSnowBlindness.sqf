#include "..\..\script_component.hpp"
/*
Snow blindness (photokeratitis): a UV burn of the cornea, 0-1 impairment.

The ocular UV dose accumulates while the unit is out on snow:
  - ambient erythemal irradiance from the UV index (aee_core_currentUVIndex):
    1 UVI = 25 mW/m2 (WHO, Global Solar UV Index, 2002);
  - the share reaching the eye: 4-23 % of ambient at solar noon by contact-lens
    dosimetry (Behar-Cohen et al. 2014, Clin Ophthalmol 8:87, review), taken
    at the middle of that band, 13.5 %, measured over ordinary ground;
  - snow reflects 94 % of UV against ~3 % for grass (same review), so the
    reflected component the eye sees is raised by (1 + 0.94) / (1 + 0.03);
  - eyewear: sunglasses or goggles transmit at most 5 % of UV-B
    (ISO 12312-1); an HMD or an optic at the eye shades it likewise.
Photokeratitis follows a radiant exposure of 30-40 J/m2 (the ICNIRP / ACGIH
UV hazard level, EU Directive 2006/25/EC); the lower value is used.  The
erythemal irradiance is converted to the photokeratitis-weighted one by
0.22: the ratio of the ICNIRP 2004 UV hazard weighting S(lambda) to the
CIE erythema action spectrum integrated over the SPCTRAL2 clear-sky solar
spectrum (data/daylight), 0.21-0.24 for sun elevations 20-60 deg.  Symptoms appear several hours after exposure and last 24-48 h (same
review): onset 6 h after the threshold is crossed, recovery 36 h after
onset.  The impairment rises with the dose over the threshold,
1 - threshold / dose, a DISPLAY mapping.

Stored in GVAR(snowBlindness), GVAR(ocularUvDose) (J/m2).
*/
params [["_unit", objNull, [objNull]]];
if (isNull _unit) exitWith { 0 };

private _now = time;
private _state = missionNamespace getVariable [QGVAR(snowBlindState), [0, -1, _now]];
if !((_state isEqualType []) && {(count _state) == 3}) then { _state = [0, -1, _now]; };
_state params ["_dose", "_onset", "_last"];
private _dt = ((_now - _last) max 0) min 600;

private _snowDepth = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];
if !(_snowDepth isEqualType 0) then { _snowDepth = 0; };
private _uvi = missionNamespace getVariable [QEGVAR(core,currentUVIndex), 0];
if !(_uvi isEqualType 0) then { _uvi = 0; };

private _protect = 1;
private _g = toLower (goggles _unit);
if ((_g find "shades" >= 0) || {_g find "aviator" >= 0} || {_g find "goggle" >= 0} || {_g find "tinted" >= 0} || {_g find "dark" >= 0}) then { _protect = 0.05; };
if (hmd _unit != "") then { _protect = _protect min 0.05; };
if ((cameraView == "GUNNER") && {_unit == call CBA_fnc_currentUnit}) then { _protect = _protect min 0.05; };
if (!isNull objectParent _unit) then { _protect = 0; };

if (_snowDepth > 0) then {
    private _ocular = (_uvi * 0.025) * 0.22 * 0.135 * ((1 + 0.94) / (1 + 0.03)) * _protect;
    _dose = _dose + _ocular * _dt;
};
private _threshold = 30;
if (_onset < 0 && _dose >= _threshold) then { _onset = _now + 6 * 3600; };

private _blindness = 0;
if (_onset >= 0 && _now >= _onset) then {
    _blindness = (1 - (_threshold / (_dose max _threshold))) max 0.2;
    if (_now > _onset + 36 * 3600) then { _dose = 0; _onset = -1; _blindness = 0; };
};
missionNamespace setVariable [QGVAR(snowBlindState), [_dose, _onset, _now]];
missionNamespace setVariable [QGVAR(ocularUvDose), _dose];
missionNamespace setVariable [QGVAR(snowBlindness), _blindness];
_blindness
