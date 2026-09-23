#include "..\..\script_component.hpp"

/*
Engine lightning rendering from AEE's strike risk (issue #141).

`time setLightnings value` changes the engine lightnings value smoothly
over `time` seconds.  AEE's lightning model already computes a strike risk
in 0..1; the engine value is the same 0..1 scale, so the bridge is direct.

REQUIREMENT: the mission weather must be on Manual Override (editor, Intel
> Manual Override).  The value changes without it, but the engine renders
no lightning change.

Reads:  QEGVAR(core,currentLightningRisk)
Sets:   engine lightnings (time setLightnings)
*/
if (!hasInterface) exitWith {};

private _risk = missionNamespace getVariable [QEGVAR(core,currentLightningRisk), 0];
if !(_risk isEqualType 0) then { _risk = 0; };
_risk = (_risk max 0) min 1;

0 setLightnings _risk;
