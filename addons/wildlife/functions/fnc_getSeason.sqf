#include "..\script_component.hpp"

/*
Season kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It maps the month and the Koppen code to a season enum and a seasonality
factor, the strength of the seasonal swing for that climate.  AEE publishes
no season scalar and reads no engine season, so the month is the source, as
fnc_updateSeasonalFoliage does with "date select 1".

The northern-hemisphere four-season split and the per-family seasonality are
modelling choices, UNSOURCED.  The tropical family swings little, so its
factor is low.

Arguments:
  0: Number - the month, 1 to 12
  1: String - the Koppen biome code

Returns:
  Array - [season, seasonality] with season 0 winter, 1 spring, 2 summer,
          3 autumn; seasonality 0 to 1.
*/

params [
    ["_month", 6, [0]],
    ["_koppen", "", [""]]
];

private _m = (round _month) max 1;
_m = _m min 12;

private _season = 0;
if ((_m >= 3) && (_m <= 5)) then { _season = 1; };
if ((_m >= 6) && (_m <= 8)) then { _season = 2; };
if ((_m >= 9) && (_m <= 11)) then { _season = 3; };

// The climate strength of the seasonal swing.  A tropical climate swings
// little; a cold climate swings hard.
private _family = "temperate";
private _first = toLower (_koppen select [0, 1]);
if (_first == "a") then { _family = "tropical"; };
if (_first == "b") then { _family = "arid"; };
if ((_first == "d") || (_first == "e")) then { _family = "cold"; };

private _seasonality = 1;
if (_family == "tropical") then { _seasonality = 0.25; };
if (_family == "arid") then { _seasonality = 0.6; };

[_season, _seasonality]
