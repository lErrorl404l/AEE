#include "..\..\script_component.hpp"
/*
 * Fusion capability check (issue #204, Track B ENVG-B).
 *
 * Fusion = the operator's headset shows BOTH the image-intensified NVG
 * base AND a thermal overlay.  This mirrors the real L3Harris ENVG-B /
 * AN/PSQ-20 fusion goggles, which blend an I2 tube image with a
 * microbolometer image.
 *
 * Two ways to be fusion-capable:
 *   1. The HMD's config declares TI in visionMode (thermal NVG like the
 *      TPNVG GPNVG-18 TI variants: visionMode[] = {"Normal","NVG","TI"}).
 *   2. The CBA setting aee_thermal_fusionAlwaysOn forces fusion on any
 *      NVG (A3TI's approach - it offers fusion modes whenever the optic
 *      has thermal AND the current vanilla mode is NVG).
 *
 * Params:
 *   0: _unit (OBJECT, default player) - the operator.
 *
 * Returns: BOOL - true if fusion may render over this operator's NVG.
 */
params [["_unit", player, [objNull]]];

// Fusion needs an active NVG (mode 1) - the base layer.
if (currentVisionMode _unit != 1) exitWith { false };
if (isNull _unit) exitWith { false };

// Setting override: fusion on any NVG.
if (missionNamespace getVariable [QGVAR(fusionAlwaysOn), false]) exitWith { true };

// Headset TI-capable: the HMD config declares TI in its visionMode.
private _hmd = hmd _unit;
if (_hmd isEqualTo "") exitWith { false };
private _cfg = configFile >> "CfgWeapons" >> _hmd;
private _modes = getArray (_cfg >> "visionMode");
_modes apply { toLower _x };
(_modes find "ti") >= 0
