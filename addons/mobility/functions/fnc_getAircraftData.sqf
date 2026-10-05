#include "..\script_component.hpp"
/*
Aircraft runtime lookup (issue #117).

Function: aee_mobility_fnc_getAircraftData.

This file is GENERATED. The generator tools/validation/gen_aircraft_data.py
writes it from the validated aircraft catalogue under data/aircraft/. Do not
edit it by hand. Edit the corpus and regenerate it.

The lookup is a thin consumer of aee_mobility_fnc_getAircraftMatch. It
returns the value row of a unique match, or an empty array. A variant
selector keeps a row only when its variant id matches.

The value row holds the four flight-model inputs in fixed order: operating
weight kg, rated power W, drag area m^2 and rotor disc area m^2. The lookup
reads no config value and no source registry. It returns no default.

Arguments:
  0: className (STRING, the CfgVehicles classname, default "")
  1: variantId (STRING, the optional variant selector, default "")
*/
params [["_className", "", [""]], ["_variantId", "", [""]]];
if (_className == "") exitWith { [] };

private _match = [_className] call FUNC(getAircraftMatch);
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
