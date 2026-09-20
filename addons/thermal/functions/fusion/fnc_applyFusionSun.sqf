#include "..\..\script_component.hpp"
/*
 * Fusion diet sun (issue #204, Track B ENVG-B).
 *
 * A3TI (workshop 3725008325, FUSION NVG Thermal) creates a "diet sun"
 * lightpoint for fusion modes: brightness 0.8, setLightDayLight false,
 * attenuation [10e10, 30000/200, 4.3e-5, 4.3e-5], ambient [0.5,0.5,0.5].
 * The light makes the EmissiveWhite-swapped objects VISIBLE over the
 * dark NVG scene - without it the emissive rvmat renders black because
 * the I2 base is near-black at night.
 *
 * Params:
 *   0: _mode (STRING) - "ON" to create/refresh, "EXIT" to delete.
 *
 * Returns: nothing.
 */
params [["_mode", "ON", [""]]];

private _sun = missionNamespace getVariable [QGVAR(fusionSun), objNull];

if (_mode == "EXIT") exitWith {
    if (!isNull _sun) then {
        deleteVehicle _sun;
        missionNamespace setVariable [QGVAR(fusionSun), objNull];
    };
};

if (isNull _sun) then {
    _sun = "#lightpoint" createVehicleLocal [0, 0, 0];
    _sun hideObject true;
    _sun enableSimulation false;
    missionNamespace setVariable [QGVAR(fusionSun), _sun];
};

_sun setLightBrightness 0.8;
_sun setLightDayLight false;
_sun setLightAttenuation [10e10, 150, 4.3e-5, 4.3e-5];
_sun setLightAmbient [0.5, 0.5, 0.5];
_sun setPosASL (getPosASLVisual player);
