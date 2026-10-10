#include "..\..\script_component.hpp"

/*
CBRN agent parameters.

Source: FM 3-11, "Chemical Operations" (2003), Table 4-1 (the agent
characteristics table).  LCt50 is the vapour inhalation median-lethal
exposure in mg*min/m3; where the table gives a range the midpoint is used.
The half-life is the FM 3-11 persistence band converted to a single
atmospheric value (days-weeks -> 36 h for the persistent agent VX;
minutes -> 10 min for CG).

  Agent  LCt50 (mg*min/m3)  VP (mmHg)  Volatility (mg/m3)  Half-life (h)
  VX     10                 0.0007     10.5                36
  GB     85 (70-100)        2.1        22000               1
  GD     60 (50-70)         0.4        3900                4
  H      1500               0.11       925                 8
  CG     3200               1215       -                   0.1667 (10 min)

Arguments:
  0: agent name (STRING, "VX"/"GB"/"GD"/"H"/"CG")

Returns [lcT50, vapourPressure, volatility, halfLifeHours].
*/

params [["_agent", "", [""]]];

private _row = [1500, 0.11, 925, 8]; // default: H (distilled mustard)

private _a = toUpper _agent;

if (_a == "VX") then {
    _row = [10, 0.0007, 10.5, 36];
} else {
    if (_a == "GB") then {
        _row = [85, 2.1, 22000, 1];
    } else {
        if (_a == "GD") then {
            _row = [60, 0.4, 3900, 4];
        } else {
            if (_a == "CG") then {
                _row = [3200, 1215, 0, 0.1667];
            };
        };
    };
};

_row
