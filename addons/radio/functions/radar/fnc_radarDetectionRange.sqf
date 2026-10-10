#include "..\..\script_component.hpp"
/*
Radar detection range - the minimum of the three limits.

  R_det = min( noise-limited, clutter-limited, horizon-limited )

  noise-limited    radar range equation (fnc_radarRangeEquation)
  clutter-limited  fnc_radarClutterRange
  horizon-limited  fnc_radarHorizon (geometric line of sight)

When the target and the radar are inside a trapping duct, the horizon
limit does not apply: the duct carries the energy past the geometric
horizon (issue #104, the R^2 law).  Then only the noise and clutter
limits remain.

Source: Skolnik, "Radar Handbook", 3rd ed.; the minimum-of-limits form
is the issue's recommended model (step 6).

Pure: reads no engine state, writes none.

Arguments:
  0: Number - noise-limited range, m
  1: Number - clutter-limited range, m
  2: Number - horizon distance, m
  3: Boolean - ducted (true when the duct range law applies)

Returns:
  Array - [R_det (m), limiting factor ("noise"|"clutter"|"horizon")]
*/
params [
    ["_noiseRmax", 0, [0]],
    ["_clutterRmax", 0, [0]],
    ["_horizonM", 0, [0]],
    ["_ducted", false, [true]]
];

private _rdet = _noiseRmax min _clutterRmax;
private _limiting = "noise";
if (_clutterRmax < _noiseRmax) then {
    _limiting = "clutter";
};

if (!_ducted) then {
    if (_horizonM < _rdet) then {
        _rdet = _horizonM;
        _limiting = "horizon";
    };
};

[_rdet, _limiting]
