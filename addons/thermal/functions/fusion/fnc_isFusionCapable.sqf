#include "..\..\script_component.hpp"
/*
 * Fusion capability check (issue #204, Track B ENVG-B).
 *
 * Fusion = the operator's headset shows BOTH the image-intensified NVG
 * base AND a thermal overlay.  This mirrors the real L3Harris ENVG-B /
 * AN/PSQ-20 fusion goggles, which blend an I2 tube image with a
 * microbolometer image.
 *
 * The HMD's config is thermal-capable in three ways:
 *   1. A visionMode entry names TI (the TPNVG GPNVG-18 TI variants:
 *      visionMode[] = {"Normal","NVG","TI"}).
 *   2. A visionMode entry names Thermal.
 *   3. It declares a non-empty thermalMode array without naming TI in
 *      visionMode (a mod that uses the modern key).
 * The mode names are matched as case-insensitive substrings, because a mod
 * may spell the mode "TI", "TI_WHITE" or "Thermal".
 *
 * The CBA setting aee_thermal_fusionAlwaysOn forces fusion on any NVG
 * (A3TI's approach - it offers fusion modes whenever the optic has thermal
 * AND the current vanilla mode is NVG).
 *
 * Params:
 *   0: _unit (OBJECT, default player) - the operator.
 *
 * Returns: BOOL - true if fusion may render over this operator's NVG.
 */
params [["_unit", player, [objNull]]];

if (isNull _unit) exitWith { false };

// Headset thermal-capable: the HMD config exposes a thermal channel.  Three
// conditions, matching the ECOTI reference (functions/fn_isThermalNVG.sqf):
// a visionMode entry that names TI, a visionMode entry that names THERMAL, or
// a non-empty thermalMode array.  The mode names are searched as substrings,
// not compared for equality, because a mod may spell the mode "TI",
// "TI_WHITE" or "Thermal" and equality would refuse a headset that works.
// The search folds case first.
private _hmd = hmd _unit;
private _hasThermal = false;
if (_hmd != "") then {
    private _cfg = configFile >> "CfgWeapons" >> _hmd;
    if (isClass _cfg) then {
        {
            private _m = toUpper _x;
            if (("TI" in _m) || ("THERMAL" in _m)) exitWith { _hasThermal = true; };
        } forEach (getArray (_cfg >> "visionMode"));
        if (!_hasThermal) then {
            if ((getArray (_cfg >> "thermalMode")) isNotEqualTo []) then {
                _hasThermal = true;
            };
        };
    };
};

// The rule itself: an active NVG base AND either a thermal channel or the
// fusionAlwaysOn setting.  fnc_fusionGateDecision holds it, so the unit suite
// and the P80 probe execute the real decision and not a mirror.
private _visionMode = currentVisionMode _unit;
private _alwaysOn = missionNamespace getVariable [QGVAR(fusionAlwaysOn), false];
[_visionMode, _hasThermal, _alwaysOn] call FUNC(fusionGateDecision)
