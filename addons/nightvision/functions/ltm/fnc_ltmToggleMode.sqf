#include "..\..\script_component.hpp"
/*
 * Laser target marker mode cycle, blink and steady.
 *
 * Ported from workshop 2041057379 A3TI/LTM/fn_toggleLTMmode.sqf.  The mode
 * cycles 0 to 1 to 0.  LTM_MODE_BLINK is 0 and LTM_MODE_STEADY is 1 in
 * script_component.hpp.
 *
 * Params:
 *   0: _unit (OBJECT) - the operator (default objNull).
 *
 * Returns: nothing.
 */
params [["_unit", objNull, [objNull]]];

if (isNull _unit) exitWith {};
if (isNil { _unit getVariable QGVAR(ltmStartTime) }) exitWith {};

private _mode = _unit getVariable [QGVAR(ltmMode), LTM_MODE_BLINK];
_mode = (_mode + 1) mod 2;
_unit setVariable [QGVAR(ltmMode), _mode, true];
AEE_LOG_INFO("LTM mode toggled");
