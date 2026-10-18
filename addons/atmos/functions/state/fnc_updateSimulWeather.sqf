#include "..\..\script_component.hpp"

/*
Simul weather bridge: the cloud-structure axis and the in-cloud probe.

`simulSetHumidity value` sets the SIMUL cloud cover, 0..1, and does not affect
`overcast` (command DB `simulSetHumidity`, acemod/arma3-wiki v2.22).  It is a
second cloud axis: `overcast` is the cloud amount, the simul cover is the
volumetric structure, so a modelled broken sky can differ from an overcast one
in structure, not only in amount.  The command was introduced in Arma 3 0.50
but was NOT IMPLEMENTED until 2.18 (command DB, group Broken Commands), so it
does nothing on an engine before 2.18.

The PROBE, read-only:
  `simulInClouds pos`     -> true when the position is in cloud, Nothing on
                             bad arguments (command DB `simulInClouds`)
  `simulCloudDensity pos` -> cloud density 0..1, false when simul weather is
                             disabled, Nothing on bad arguments (command DB
                             `simulCloudDensity`)
Both feed the icing and turbulence models a real in-cloud test in place of the
overcast/rain inference (fnc_calculateAirframeIcing, fnc_calculateTurbulence).

The write is gated on the same opt-in as the volumetric-layer bridge
(`aee_atmos_simulWeatherLayers` > 0).  The command DB records that simul
weather is disabled in Eden Editor and scenario preview, and the layer bridge
ships off, so the sky is not changed unless the operator enabled the bridge.
The probes run regardless, so a consumer sees the engine's own state.

The command DB also records that `rainParams` returns an empty array on a
dedicated server; the same client-only rule applies here, so the whole bridge
is gated on hasInterface.

Reads:  aee_atmos_simulWeatherLayers, aee_atmos_targetOvercast, overcast,
        current unit position
Sets:   engine simul cloud cover (simulSetHumidity); aee_core_simulInClouds,
        aee_core_simulCloudDensity
Example: [] call aee_atmos_fnc_updateSimulWeather;
Public: No
*/

if (!hasInterface) exitWith {};

// ─── Cloud structure axis (independent of overcast) ─────────────────────────
private _layers = missionNamespace getVariable [QGVAR(simulWeatherLayers), 0];
if !(_layers isEqualType 0) then { _layers = 0; };
if (_layers > 0) then {
    // The modelled cloud fraction is aee_atmos_targetOvercast, which the
    // engine weather writer holds as an absolute value.  Fall back to the
    // engine overcast when the writer has not run (manual weather, or a
    // dedicated client before the first tick).
    private _cover = missionNamespace getVariable [QGVAR(targetOvercast), -1];
    if !(_cover isEqualType 0) then { _cover = -1; };
    if (_cover < 0) then { _cover = overcast; };
    if !(_cover isEqualType 0) then { _cover = 0; };
    simulSetHumidity (_cover max 0 min 1);
};

// ─── In-cloud probe (engine ground truth for the icing/turbulence models) ───
private _unit = call CBA_fnc_currentUnit;
private _haveUnit = (!isNil "_unit" && {!isNull _unit});

private _inClouds = false;
private _density = -1;   // -1 = no reading (simul weather off, or no unit)
if (_haveUnit) then {
    private _pos = getPosASL _unit;

    private _clouds = simulInClouds _pos;
    if (_clouds isEqualType true) then { _inClouds = _clouds; };

    private _probe = simulCloudDensity _pos;
    if (_probe isEqualType 0) then { _density = _probe; };
};

missionNamespace setVariable [QEGVAR(core,simulInClouds), _inClouds];
missionNamespace setVariable [QEGVAR(core,simulCloudDensity), _density];
