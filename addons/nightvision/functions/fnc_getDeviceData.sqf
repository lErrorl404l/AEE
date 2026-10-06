#include "..\script_component.hpp"
/*
Device runtime lookup (night vision, thermal and optic).

Function: aee_nightvision_fnc_getDeviceData.

This file is GENERATED. The generator tools/validation/gen_device_data.py
writes it from the validated device catalogue under data/device/. Do not
edit it by hand. Edit the corpus and regenerate it.

The lookup is a thin consumer of aee_nightvision_fnc_getDeviceMatch. It
returns the value row of a unique match, or an empty array. A caller that
knows the device family passes it, so a class that two families share
resolves to the row the caller wants.

The value row is the runtime set of the family. A tube row holds the four
image-intensifier fields. A thermal row holds the seven detector fields. An
optic row holds the six sight fields. The lookup reads no config value and
no source registry. It returns no default.

Arguments:
  0: className (STRING, the device classname, default "")
  1: family (STRING, the optional family filter, default "")
*/
params [["_className", "", [""]], ["_family", "", [""]]];
if (_className == "") exitWith { [] };

private _match = [_className, _family] call FUNC(getDeviceMatch);
if (_match isEqualTo []) exitWith { [] };

_match select 5
