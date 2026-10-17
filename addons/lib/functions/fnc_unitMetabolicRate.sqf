#include "..\script_component.hpp"
/*
 * aee_lib_fnc_unitMetabolicRate
 *
 * Metabolic rate of a unit from what it is doing, watts.
 *
 * On foot: the Pandolf load-carriage equation (fnc_pandolfMetabolicRate)
 * with the real carried mass (loadAbs, the generated real item masses, in
 * the engine's 0.1 lb unit), the ground speed, the grade along the motion,
 * and the Soule & Goldman / Pandolf terrain factor of the surface underfoot.
 * The body mass is the 70 kg reference man of the Gagge two-node model the
 * thermal solver uses.
 * Seated in a vehicle: 1.0 met, 58.2 W/m2 over the 1.8258 m2 DuBois area
 * (ISO 8996:2021 Table A.2, seated at rest).
 *
 * Arguments: 0: unit (OBJECT)
 * Return: metabolic rate, W
 */
params [["_unit", objNull, [objNull]]];
if (isNull _unit || {!alive _unit}) exitWith { 0 };
if (!isNull objectParent _unit) exitWith { 58.2 * 1.8258 };
private _vel = velocity _unit;
private _vH = sqrt (((_vel select 0) ^ 2) + ((_vel select 1) ^ 2));
private _grade = if (_vH > 0.1) then { 100 * (_vel select 2) / _vH } else { 0 };
_grade = (_grade max -45) min 45;
private _pos = getPosASL _unit;
private _snow = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];
if !(_snow isEqualType 0) then { _snow = 0; };
private _eta = [surfaceType _pos, _snow] call FUNC(pandolfTerrainFactor);
private _load = (loadAbs _unit) * ENGINE_MASS_UNIT_KG;
[70, _load, _vH, _grade, _eta] call FUNC(pandolfMetabolicRate)
