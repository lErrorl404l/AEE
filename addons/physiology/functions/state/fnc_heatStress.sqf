#include "..\..\script_component.hpp"

/*
Heat stress kernel (will to live).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Maps the
wet-bulb globe temperature to the heat-stress risk the survival model
consumes.

The WBGT comes from the ISO 7243 model (computed by core/updateEnvironment
as aee_core_currentWBGT).  The risk is the fraction of each hour a soldier
doing heavy work must rest, from the TB MED 507 work/rest table (Table 1,
heavy work, up to 4 h of training; DHA CPHE heat poster):

  below 78 F (25.6 C)      no limit      0
  cat 1  78-81.9 F         40/20         1/3
  cat 2  82-84.9 F         30/30         1/2
  cat 3  85-87.9 F         30/30         1/2
  cat 4  88-89.9 F         20/40         2/3
  cat 5  90 F (32.2 C) up  10/50         5/6

Arguments:
  0: Number - wet-bulb globe temperature, degC

Returns:
  Number - the heat stress risk, 0 to 1
*/

params [["_wbgt", 0, [0]]];

private _f = _wbgt * 9 / 5 + 32;
private _rest = 0;
if (_f >= 78) then { _rest = 20 / 60; };
if (_f >= 82) then { _rest = 30 / 60; };
if (_f >= 88) then { _rest = 40 / 60; };
if (_f >= 90) then { _rest = 50 / 60; };

_rest
