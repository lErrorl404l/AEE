#include "..\script_component.hpp"
/*
Driver for the underwater light model (issue #14).

Runs once per second.  It reads the water type, computes the per-band
diffuse attenuation, and, when the eye is underwater, the band
transmission at the eye depth, the Snell window, and the bioluminescence
gate.  It publishes the state for consumers.

Water type.  The operator setting aee_maritime_underwaterWaterType selects
the Jerlov type.  A mission script may set the variable directly to change
the water type at run time.

Engine ceiling.  Arma 3 renders its own underwater tint.  The mod cannot
replace that render.  This driver publishes the physical state so a
consumer (NVG, view distance, HUD) can use it.  It does not fight the
engine render.

State (missionNamespace):
  aee_maritime_waterTypeName      the Jerlov type name
  aee_maritime_underwaterKd       [Kd_R, Kd_G, Kd_B] (m^-1)
  aee_maritime_underwaterDepth    eye depth (m)
  aee_maritime_underwaterTrans    [T_R, T_G, T_B] transmission fraction
  aee_maritime_snellCritical      critical angle (degrees)
  aee_maritime_snellCone          full cone angle (degrees)
  aee_maritime_biolumVisible      boolean
  aee_maritime_biolumIntensity    0..1

Input:  [_unit] - the unit to sample (default: current unit)
Output: the published state array, or [] when there is no local unit
*/

params [["_unit", objNull, [objNull]]];
if (isNull _unit) then { _unit = call CBA_fnc_currentUnit; };
if (isNull _unit) exitWith { [] };

// ─── Water type ───────────────────────────────────────────────────────────
private _type = missionNamespace getVariable [QGVAR(underwaterWaterType), 3];
if !(_type isEqualType 0) then { _type = 3; };
private _idx = ((round _type) max 0) min 9;

private _names = ["I", "IA", "IB", "II", "III", "1", "3", "5", "7", "9"];
private _kd = [_idx] call FUNC(waterTypeKd);
private _kdR = _kd select 0;
private _kdG = _kd select 1;
private _kdB = _kd select 2;

// ─── Depth and band transmission ──────────────────────────────────────────
private _eye = eyePos _unit;
private _depth = 0 max (-(_eye select 2));
private _trans = [_depth, _kdR, _kdG, _kdB] call FUNC(calculateUnderwaterLight);

// ─── Snell window ─────────────────────────────────────────────────────────
private _snell = [] call FUNC(calculateSnellWindow);

// ─── Bioluminescence ──────────────────────────────────────────────────────
// Disturbance comes from the unit's own underwater motion: a swimmer or a
// boat stirs the dinoflagellates.  The flash window is stamped when the
// motion first crosses the trigger and cleared when the motion stops.
private _speed = vectorMagnitude (velocity _unit);
private _stirring = _speed > 0.5;
private _stirTime = missionNamespace getVariable [QGVAR(biolumStirTime), -1];
if !(_stirTime isEqualType 0) then { _stirTime = -1; };
if (_stirring) then {
    if (_stirTime < 0) then {
        _stirTime = CBA_missionTime;
        missionNamespace setVariable [QGVAR(biolumStirTime), _stirTime];
    };
} else {
    _stirTime = -1;
    missionNamespace setVariable [QGVAR(biolumStirTime), -1];
};

private _ambientLux = missionNamespace getVariable [QEGVAR(core,ambientLux), 0.001];
if !(_ambientLux isEqualType 0) then { _ambientLux = 0.001; };
private _disturbance = if (_stirring) then { (_speed / 2) min 1 } else { 0 };
private _elapsed = if (_stirTime >= 0) then { CBA_missionTime - _stirTime } else { 0 };
private _biolum = [_ambientLux, _kdB, _disturbance, _elapsed] call FUNC(calculateBioluminescence);

// ─── Publish ──────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(waterTypeName), _names select _idx];
missionNamespace setVariable [QGVAR(underwaterKd), _kd];
missionNamespace setVariable [QGVAR(underwaterDepth), _depth];
missionNamespace setVariable [QGVAR(underwaterTrans), _trans];
missionNamespace setVariable [QGVAR(snellCritical), _snell select 0];
missionNamespace setVariable [QGVAR(snellCone), _snell select 1];
missionNamespace setVariable [QGVAR(biolumVisible), _biolum select 0];
missionNamespace setVariable [QGVAR(biolumIntensity), _biolum select 1];

[
    _depth, _kdR, _kdG, _kdB,
    _trans select 0, _trans select 1, _trans select 2,
    _biolum select 0, _biolum select 1
]
