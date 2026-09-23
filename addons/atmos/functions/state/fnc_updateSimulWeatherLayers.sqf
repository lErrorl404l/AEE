#include "..\..\script_component.hpp"

/*
Volumetric cloud layer count from AEE's quality setting (issue #141).

`setSimulWeatherLayers layers` sets the number of simul weather layers and
so the altitude resolution of the volumetric clouds.  More layers cost
performance, so the bridge is off by default and gated behind the
`simulWeatherLayers` setting.

Setting contract: 0 leaves the engine default (the command is not called);
1..5 sets that many layers.  The engine documents 0 as "very flat clouds"
and -1 as "reset to defaults" (Arma 3 2.20+); AEE uses 0 as "do not
override" and never calls the command in that case.

One-shot at startup: the effect is persistent across the game instance, so
it is applied once and not from the per-tick loop.

Reads:  QGVAR(simulWeatherLayers)
Sets:   engine simul weather layers (setSimulWeatherLayers)
*/
if (!hasInterface) exitWith {};

private _layers = missionNamespace getVariable [QGVAR(simulWeatherLayers), 0];
if !(_layers isEqualType 0) then { _layers = 0; };
_layers = round _layers;

// 0 = leave the engine default (do not call the command).
if (_layers <= 0) exitWith {};

setSimulWeatherLayers (_layers min 5);
