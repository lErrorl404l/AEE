#include "..\..\script_component.hpp"

/*
Atmospheric-desaturation kernel (human-vision model, colour slice).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The base-grade
driver calls this; the kernel maps the atmospheric scattering state to a
desaturation alpha for the ColorCorrections colorize slot.  It is a new CAUSE
feeding the SAME desaturation mechanism fnc_perceptionMesopicColor uses, not a
second colour stage.

Model.  Cloud, rain and haze each mix scattered white light into every line of
sight, which lowers the saturation of the scene.  The kernel treats each of the
three as an independent coverage and combines them with the probability-union
form 1 - (1 - a)(1 - b)(1 - c): 0 when all three are clear, 1 when any one is
total.  The alpha is that coverage times the cap.

The cap is the engine's desaturation budget.  The engine can only desaturate
(it cannot oversaturate), so the alpha is bounded.  The union form is a
documented modelling choice, not a published constant, and the cap is
UNSOURCED; both are marked.

Per-constant source register:
  union coverage form    UNSOURCED: a coverage combination, not a published
                         constant.
  desaturation cap 0.4   UNSOURCED: operator-tunable; the engine desaturates
                         only and the image must not drain to grey.
  alpha band 0 to 0.5    UNSOURCED: the engine desaturation budget.

Arguments:
  0: Number - overcast fraction, 0 to 1
  1: Number - rain fraction, 0 to 1
  2: Number - haze fraction, 0 to 1
  3: Number - desaturation cap, 0 to 0.5 (default 0.4)

Returns:
  Number - desaturation alpha, 0 to the cap.
*/

params [
    ["_overcast", 0, [0]],
    ["_rain", 0, [0]],
    ["_haze", 0, [0]],
    ["_cap", 0.4, [0]]
];

if !(_overcast isEqualType 0) then { _overcast = 0; };
if !(_rain isEqualType 0) then { _rain = 0; };
if !(_haze isEqualType 0) then { _haze = 0; };
if !(_cap isEqualType 0) then { _cap = 0.4; };

private _ov = (_overcast max 0) min 1;
private _ra = (_rain max 0) min 1;
private _ha = (_haze max 0) min 1;
private _c = (_cap max 0) min 0.5;

private _coverage = 1 - ((1 - _ov) * (1 - _ra) * (1 - _ha));

(_c * _coverage) max 0
