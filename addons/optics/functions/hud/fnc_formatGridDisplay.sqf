#include "..\..\script_component.hpp"
/*
 * ECOTI environment HUD grid-display selector (pure kernel).
 *
 * Returns the MGRS reference from the aee worldToMgrs kernel (task 5) when
 * the operator setting is on, else the legacy numeric grid from
 * FUNC(hudFormatGrid).  FUNC(hudUpdate) supplies every input, so this kernel
 * reads no world, no player and no setting.
 *
 * Arguments:
 *   0: _position  <ARRAY>  world position of the player [x, y, z], metres
 *   1: _anchor    <ARRAY>  the 9-element geo anchor from EFUNC(lib,getGeoAnchor)
 *   2: _precision <NUMBER> MGRS total digits, 4, 6, 8 or 10
 *   3: _gridRaw   <STRING> mapGridPosition of the player (the legacy source)
 *   4: _enabled   <BOOL>   the aee_optics_mgrsEnabled setting value
 *
 * Returns: <STRING> the MGRS reference, or the legacy grid when the setting
 *          is off or MGRS is unavailable.
 */
params [
    ["_position", [0, 0, 0], [[]]],
    ["_anchor", [], [[]]],
    ["_precision", 10, [0]],
    ["_gridRaw", "", [""]],
    ["_enabled", true, [true]]
];

private _mgrsText = "";
if (_enabled) then {
    private _converted = [_position, _anchor, _precision] call EFUNC(lib,worldToMgrs);
    if ((count _converted) >= 1) then {
        _mgrsText = _converted select 0;
    };
};

if (_mgrsText isEqualTo "") exitWith { [_gridRaw] call FUNC(hudFormatGrid); };

_mgrsText
