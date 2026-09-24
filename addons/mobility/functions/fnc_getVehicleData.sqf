#include "..\script_component.hpp"
/*
Vehicle runtime lookup (issue #117).

Function: aee_mobility_fnc_getVehicleData.

This file is GENERATED. The generator tools/validation/gen_vehicle_data.py
writes it from the validated vehicle catalogue under data/vehicle/. Do not
edit it by hand. Edit the corpus and regenerate it.

The lookup is a thin consumer of aee_mobility_fnc_getVehicleMatch. It
returns the value row of a unique match, or an empty array. A variant
selector keeps a row only when its variant id matches.

The value row is the seven NRMM inputs of the vehicle type. A wheeled row
holds the two tyre fields. A tracked row holds the two track fields. The
lookup reads no config value and no source registry. It returns no default.

Arguments:
  0: className (STRING, the CfgVehicles classname, default "")
  1: variantId (STRING, the optional variant selector, default "")
*/
params [["_className", "", [""]], ["_variantId", "", [""]]];
if (_className == "") exitWith { [] };

private _match = [_className] call FUNC(getVehicleMatch);
if (_match isEqualTo []) exitWith { [] };
if (_variantId == "") exitWith { _match select 6 };

private _normalise = {
    params ["_text"];
    private _out = "";
    {
        if ((_x >= 48 && _x <= 57) || (_x >= 97 && _x <= 122)) then {
            _out = _out + toString [_x];
        };
    } forEach (toArray (toLower _text));
    _out
};
private _variantKey = [_variantId] call _normalise;
if ((_match select 1) != _variantKey) exitWith { [] };
_match select 6
