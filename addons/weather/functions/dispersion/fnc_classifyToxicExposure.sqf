#include "..\..\script_component.hpp"

/*
Acute toxic-exposure tier from a gas concentration (issue #120).

Classifies an airborne concentration against the published acute
endpoints for the agent, most severe first:

  aegl-3  at or above the AEGL-3 (life-threatening, 60 min)
  idlh    at or above the NIOSH IDLH (immediately dangerous)
  aegl-2  at or above the AEGL-2 (disabling, 60 min)
  tlv     at or above the ACGIH/NIOSH ceiling (occupational)
  none    below every endpoint

For chlorine the AEGL-3 (60 min) is 20 ppm and the IDLH is 10 ppm, so the
IDLH sits between the AEGL-2 and the AEGL-3; the ladder orders by
severity, not by number alone.  An endpoint passed as 0 is not published
for the agent and is skipped, so an agent with no acute data classifies
as "none" rather than against an invented figure.

The endpoints themselves live in FUNC(getGasProperties) (single source);
this kernel is the pure comparison.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: NUMBER - concentration, mg/m3
  1: NUMBER - AEGL-2, mg/m3 (0 to skip)
  2: NUMBER - AEGL-3, mg/m3 (0 to skip)
  3: NUMBER - NIOSH IDLH, mg/m3 (0 to skip)
  4: NUMBER - ceiling TLV, mg/m3 (0 to skip)

Returns:
  STRING - "aegl-3" | "idlh" | "aegl-2" | "tlv" | "none"
*/

params [
    ["_concentration", 0, [0]],
    ["_aegl2", 0, [0]],
    ["_aegl3", 0, [0]],
    ["_idlh", 0, [0]],
    ["_tlv", 0, [0]]
];

private _tier = "none";
if ((_aegl3 > 0) && (_concentration >= _aegl3)) then {
    _tier = "aegl-3";
} else {
    if ((_idlh > 0) && (_concentration >= _idlh)) then {
        _tier = "idlh";
    } else {
        if ((_aegl2 > 0) && (_concentration >= _aegl2)) then {
            _tier = "aegl-2";
        } else {
            if ((_tlv > 0) && (_concentration >= _tlv)) then {
                _tier = "tlv";
            };
        };
    };
};

_tier
