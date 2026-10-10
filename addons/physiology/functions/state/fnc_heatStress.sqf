#include "..\..\script_component.hpp"

/*
Heat stress kernel (will to live).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Maps the
wet-bulb globe temperature to the heat-stress risk the survival model
consumes.

The WBGT comes from the ISO 7243 model (computed by core/updateEnvironment
as aee_core_currentWBGT).  The TB MED 507 flag bands and the heavy-work
cycles:

  white   25.6-27.7 C   no limit
  green   27.8-29.4 C   30/30
  yellow  29.4-31.1 C   30/30
  red     31.1-32.2 C   20/40
  black   over 32.2 C   15/45

The survival calibration anchors the risk at 29 C = 0.3, 34 = 0.6 and
38 = 0.8, and the risk is linear between the anchors.  The onset anchor at
18 C is the top of the ISO 7243 safe category.  The upper anchor at 45 C
(full pressure) is UNSOURCED: the issue gives no WBGT for full pressure, so
it is a bounded clamp above the black flag.

Arguments:
  0: Number - wet-bulb globe temperature, degC

Returns:
  Number - the heat stress risk, 0 to 1
*/

params [["_wbgt", 0, [0]]];

private _risk = 0;
if (_wbgt <= 18) then {
    _risk = 0;
} else {
    if (_wbgt <= 29) then {
        _risk = (_wbgt - 18) * (0.3 / 11);
    } else {
        if (_wbgt <= 34) then {
            _risk = 0.3 + (_wbgt - 29) * (0.3 / 5);
        } else {
            if (_wbgt <= 38) then {
                _risk = 0.6 + (_wbgt - 34) * (0.2 / 4);
            } else {
                _risk = 0.8 + (_wbgt - 38) * (0.2 / 7);
            };
        };
    };
};

((_risk max 0) min 1)
